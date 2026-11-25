/**
 * Sıralama ölçüm hattı — yalnız orkestrasyon.
 *
 * Ölçümün kendisi worker'da koşar (`worker/olcum_a.py`): gerçek tarayıcı, premium
 * havuz, `gl` doğrulaması ve şüpheli sayfa tekrarı tek yerde durur. Böylece
 * burada ikinci bir SERP istemcisi tutulmaz ve iki yol birbirinden sapmaz.
 *
 * Ölçüm daima ulusaldır ve `clean` kanaldan yapılır (C20); il sıralaması
 * ölçülmez. Boşluk 15 dakikayı geçmesin diye aralık üstten sınırlanır (C12).
 *
 * `position` satırını worker yazar: `ok`, `not_found` ve `supheli` üçü de
 * yazılır, `supheli` satırında rank NULL kalır.
 *
 * Kullanım: src/server/zamanlayici.ts.
 */
import { sorgu } from "./veritabani.js";
import { createHmac } from "node:crypto";
import { ayarOku } from "./ayar.js";
import { dugumSec } from "./dugum_sec.js";
import { gunluk } from "./gunluk.js";

const VARSAYILAN_ARALIK_DK = 15; // C12; boşluk üst sınırı
const TUR_ADET = 3; // tur başına kelime; ölçüm turu kısaltır
const TUR_BUTCE_MS = 60_000; // tur süresi; aşılırsa kalan kelime sonraki tura kalır
const ZAMAN_ASIMI_MS = 120_000; // 10 sayfa gezilebilir

type Aday = { id: number; text: string; domain: string };
type OlcumCevabi = { result?: string; rank?: number | null; suphe?: string; mesaj?: string };

// Çok parçalı uzantılar: son iki etiket kök vermez, üçüncü etiket de kökün
// parçasıdır. Aksi hâlde "site.com.tr" ile her ".com.tr" eşleşiyordu.
// Karşılaştırma aracı (EKSIKLER 80) da bu işlevi kullanacak.
const COK_PARCALI_UZANTI = new Set([
  "com.tr", "net.tr", "org.tr", "gov.tr", "edu.tr", "av.tr", "bel.tr",
  "k12.tr", "gen.tr", "web.tr", "co.uk", "org.uk", "ac.uk", "com.br",
  "com.au", "co.jp", "com.de", "com.ru",
]);

/** Kök alan adı: www. ve alt yollar atılır, çok parçalı uzantı korunur. */
export function kok(adres: string): string {
  const ham = adres.trim().toLowerCase();
  const host = (ham.includes("://") ? new URL(ham).hostname : ham.split("/")[0]) ?? "";
  const etiketler = host.replace(/^www\./, "").split(".").filter(Boolean);
  if (etiketler.length >= 3 && COK_PARCALI_UZANTI.has(etiketler.slice(-2).join("."))) {
    return etiketler.slice(-3).join(".");
  }
  return etiketler.slice(-2).join(".");
}

/** Ölçüm aralığı: ayar 0 ise varsayılan, değilse üst sınırı aşmaz. */
export async function aralikDk(): Promise<number> {
  const ham = Number(await ayarOku("olcum_araligi_dk", "0")) || 0;
  return ham <= 0 ? VARSAYILAN_ARALIK_DK : Math.min(ham, VARSAYILAN_ARALIK_DK);
}

/** Ölçüm kaynaklı uyarı; sessiz kalmaması için alert yazılır. */
async function uyari(kind: string, mesaj: string): Promise<void> {
  await sorgu("INSERT INTO alert (kind, message) VALUES (?, ?)", [kind, mesaj.slice(0, 500)]);
}

/** Ölçüm sırası gelmiş kelimeler; hiç ölçülmemişler önce. */
async function adaylar(aralik: number): Promise<Aday[]> {
  return sorgu<Aday>(
    `SELECT k.id, k.text, s.domain
       FROM keyword k
       JOIN site s ON s.id = k.site_id
       LEFT JOIN (SELECT keyword_id, MAX(checked_at) AS son FROM position
                   WHERE channel = 'clean' GROUP BY keyword_id) p ON p.keyword_id = k.id
      WHERE k.state = 'active' AND s.active = 1
        AND (p.son IS NULL OR p.son < UTC_TIMESTAMP(3) - INTERVAL ? MINUTE)
      ORDER BY p.son IS NULL DESC, p.son ASC
      LIMIT ?`,
    [aralik, TUR_ADET],
  );
}

/** Worker'ın imzalı ölçüm ucunu çağırır. */
async function olcumIste(adres: string, token: string, aday: Aday): Promise<OlcumCevabi> {
  const govde = JSON.stringify({
    keyword: aday.text,
    target_domain: aday.domain,
    keyword_id: aday.id,
    ts: Math.floor(Date.now() / 1000),
  });
  const imza = createHmac("sha256", token).update(govde).digest("hex");
  const yanit = await fetch(`${adres}/worker/olcum_a`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      Authorization: `Bearer ${token}`,
      "x-imza": imza,
    },
    body: govde,
    signal: AbortSignal.timeout(ZAMAN_ASIMI_MS),
  });
  if (!yanit.ok) throw new Error(`ölçüm motoru ${yanit.status}`);
  return (await yanit.json()) as OlcumCevabi;
}

/** B kanalında tek ölçüm: kalıcı jar'lı profil, gerçek tarayıcı gibi (C20). */
async function olcumBTry(aday: Aday): Promise<void> {
  const adres = await dugumSec();
  if (!adres) return;
  const token = process.env.WORKER_TOKEN ?? "";
  if (!token) return;
  const govde = JSON.stringify({
    keyword: aday.text,
    target_domain: aday.domain,
    keyword_id: aday.id,
    ts: Math.floor(Date.now() / 1000),
  });
  const imza = createHmac("sha256", token).update(govde).digest("hex");
  const yanit = await fetch(`${adres}/worker/olcum_b`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      Authorization: `Bearer ${token}`,
      "x-imza": imza,
    },
    body: govde,
    signal: AbortSignal.timeout(ZAMAN_ASIMI_MS),
  });
  await yanit.json().catch(() => null);
}

/**
 * Sırası gelen kelimeleri ölçer.
 *
 * @returns Worker'ın yazdığı ölçüm sayısı.
 */
export async function olcumYap(): Promise<number> {
  const adres = await dugumSec();
  if (!adres) return 0; // aktif düğüm yoksa tur boş geçer
  const token = process.env.WORKER_TOKEN ?? "";
  if (!token) return 0;

  const aralik = await aralikDk();
  const liste = await adaylar(aralik);
  const basladi = Date.now();
  let yazilan = 0;

  for (const aday of liste) {
    // Bütçe dolduysa kalan kelime sonraki tura bırakılır; tur kilitlenmez.
    if (Date.now() - basladi > TUR_BUTCE_MS) break;
    try {
      const sonuc = await olcumIste(adres, token, aday);
      if (sonuc.result === "anahtar_yok") {
        await uyari("burst_hata", "SERP anahtarı boş · ölçüm beklemede");
        break;
      }
      if (sonuc.result === "captcha") {
        await uyari("quota", "SERP kotası veya hız sınırı · ölçüm durdu");
        break;
      }
      // Şüpheli SERP uyarısını worker bağlamlı yazar (kelime + site); burada
      // tekrar yazılırsa aynı tur için iki satır düşer.
      // Üç sonuç da satır yazar: ok, not_found ve supheli.
      if (sonuc.result === "ok" || sonuc.result === "not_found" || sonuc.result === "supheli") {
        yazilan += 1;
      }
    } catch (hata) {
      await uyari("burst_hata", `ölçüm ${aday.id}: ${(hata as Error).message}`);
    }
  }

  // B kanalı turda bir kez koşar: küçük havuz, kalıcı jar (C20).
  const bAday = liste[0];
  if (bAday && yazilan > 0 && Date.now() - basladi < TUR_BUTCE_MS) {
    await olcumBTry(bAday).catch((hata: Error) => gunluk.hata("[olcum-b]", hata.message));
  }
  return yazilan;
}