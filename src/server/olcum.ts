/**
 * Sıralama ölçüm hattı.
 *
 * Ölçüm daima ulusaldır ve `clean` kanaldan yapılır (C20); il sıralaması
 * ölçülmez. Sonuç SERP API'sinden okunur, hit trafiğinden bağımsızdır; böylece
 * ölçüm ile burst birbirinin IP'sini kirletmez. Boşluk 15 dakikayı geçmesin
 * diye aralık üstten sınırlanır (C12).
 *
 * İlk 100'de olmayan kelime `rank = NULL` ile yazılır: "yok" ile "ölçüm
 * başarısız" ayrı durumlardır (§6.1).
 *
 * Kullanım: src/server/zamanlayici.ts.
 */
import { sorgu, yaz } from "./veritabani.js";
import { ayarOku } from "./ayar.js";

const VARSAYILAN_ARALIK_DK = 15; // C12; boşluk üst sınırı
const TUR_ADET = 3; // tur başına kelime; ölçüm turu kısaltır
const TUR_BUTCE_MS = 40_000; // tur süresi; aşılırsa kalan kelime sonraki tura kalır
const SAYFA_BASI = 10; // API'nin tek yanıtta döndürdüğü sonuç
const AZAMI_SAYFA = 10; // 10 x 10 = ilk 100 sıra
const ZAMAN_ASIMI_MS = 20_000;

type Aday = { id: number; text: string; domain: string };
type Sira = { rank: number | null; kod: number };

/** Kök alan adı: www. ve alt yollar atılır, karşılaştırma kökle yapılır. */
function kok(adres: string): string {
  const ham = adres.trim().toLowerCase();
  const host = (ham.includes("://") ? new URL(ham).hostname : ham.split("/")[0]) ?? "";
  const etiketler = host.replace(/^www\./, "").split(".").filter(Boolean);
  return etiketler.slice(-2).join(".");
}

/** Ölçüm aralığı: ayar 0 ise varsayılan, değilse üst sınırı aşmaz. */
async function aralikDk(): Promise<number> {
  const ham = Number(await ayarOku("olcum_araligi_dk", "0")) || 0;
  return ham <= 0 ? VARSAYILAN_ARALIK_DK : Math.min(ham, VARSAYILAN_ARALIK_DK);
}

/** Ölçüm kaynaklı uyarı; sessiz kalmaması için alert yazılır. */
async function uyari(kind: string, mesaj: string): Promise<void> {
  await yaz("INSERT INTO alert (kind, message) VALUES (?, ?)", [kind, mesaj.slice(0, 500)]);
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

/** Sırayı sayfa sayfa arar; hedef bulununca erken durur. */
async function siraBul(anahtar: string, kelime: string, hedefKok: string): Promise<Sira> {
  for (let sayfa = 1; sayfa <= AZAMI_SAYFA; sayfa += 1) {
    const cevap = await fetch("https://data.decodo.com/v1/search", {
      method: "POST",
      headers: { authorization: `Bearer ${anahtar}`, "content-type": "application/json" },
      body: JSON.stringify({ query: kelime, page: sayfa, locale: "tr-TR", geo: "tr" }),
      signal: AbortSignal.timeout(ZAMAN_ASIMI_MS),
    });
    if (cevap.status === 429) return { rank: null, kod: 429 };
    if (!cevap.ok) return { rank: null, kod: cevap.status };

    const veri = (await cevap.json()) as { organic?: { link?: string }[] };
    const liste = veri.organic ?? [];
    if (liste.length === 0) return { rank: null, kod: 200 };

    const ofset = (sayfa - 1) * SAYFA_BASI;
    const yer = liste.findIndex((k) => Boolean(k.link) && kok(String(k.link)) === hedefKok);
    if (yer >= 0) return { rank: ofset + yer + 1, kod: 200 };
  }
  return { rank: null, kod: 200 };
}

/**
 * Sırası gelen kelimeleri ölçer ve `position` tablosuna yazar.
 *
 * @returns Yazılan ölçüm sayısı.
 */
export async function olcumYap(): Promise<number> {
  const anahtar = (await ayarOku("serp_decodo", "")).trim();
  if (!anahtar) return 0; // anahtar yoksa ölçüm beklemede kalır

  const aralik = await aralikDk();
  const liste = await adaylar(aralik);
  const basladi = Date.now();
  let yazilan = 0;

  for (const aday of liste) {
    // Bütçe dolduysa kalan kelime sonraki tura bırakılır; tur kilitlenmez.
    if (Date.now() - basladi > TUR_BUTCE_MS) break;
    try {
      const sonuc = await siraBul(anahtar, aday.text, kok(aday.domain));
      if (sonuc.kod === 429) {
        await uyari("quota", "SERP kotası veya hız sınırı: 429 · ölçüm durdu");
        break;
      }
      await yaz("INSERT INTO `position` (keyword_id, channel, `rank`) VALUES (?, 'clean', ?)", [
        aday.id,
        sonuc.rank,
      ]);
      yazilan += 1;
    } catch (hata) {
      await uyari("burst_hata", `ölçüm ${aday.id}: ${(hata as Error).message}`);
    }
  }
  return yazilan;
}