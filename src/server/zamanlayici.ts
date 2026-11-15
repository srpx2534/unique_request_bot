/**
 * Ölçüm zamanlayıcısı.
 *
 * Kullanıcı durdurana kadar çalışır; günlük tavan yoktur. Dakikada bir
 * aktif kampanyaların satırlarını tarar ve kuyruğa atar.
 *
 * Cooldown sert engel değil, sıralama tercihidir: soğumadaki satır
 * listenin sonuna düşer, ilin IP'si bitince karışık devam edilir.
 */
import { sorgu } from "./veritabani.js";
import { ayarOku } from "./ayar.js";
import { kuyruk, type Is } from "./kuyruk.js";
import { toparla } from "./traffic.js";
import { kalpKaybiYaz } from "./dugum_olay.js";
import { olcumYap } from "./olcum.js";
import { esikDenetle } from "./esik.js";
import { saklamaDenetle } from "./saklama.js";
import { bolumDenetle } from "./bolum.js";
import { bayatDenetle, cakismaYaz, kilitSuresiDk, sahiplen } from "./kilit.js";

const TIK_MS = 60_000;
const TUR_SINIRI = 200;
const KELIME_SINIRI = 12;

/** Tier'a göre bekleme; core sık, passive seyrek. */
// Sözleşme §9: keyword_geo cooldown 20-35 dakika, rastgele. Tier yalnızca
// sıralamayı belirler, süreyi değil.
const COOLDOWN_MIN_DK = 20;
const COOLDOWN_MAX_DK = 35;

type Aday = {
  keyword_geo_id: number;
  keyword_id: number;
  campaign_id: number;
  geo_code: number;
  tier: Is["tier"];
  kelime: string;
};

/** Cooldown: sözleşmedeki 20-35 dakika aralığından rastgele. */
function rastgeleCooldown(): number {
  return COOLDOWN_MIN_DK + Math.floor(Math.random() * (COOLDOWN_MAX_DK - COOLDOWN_MIN_DK + 1));
}

// Bakım adımları tur işinden ayrı ve seyrek koşar: toparla, kalp kaybı, eşik ve
// saklama dakikalık turu geciktirmesin. Ölçüm kendi kapısını taşıdığı için
// dakikalık döngüde kalır.
const BAKIM_MS = 5 * 60_000;

let calisiyor = false;
let calisiyorBakim = false;
let zaman: NodeJS.Timeout | null = null;
let bakimZamani: NodeJS.Timeout | null = null;

async function bakim(): Promise<void> {
  if (calisiyorBakim) return;
  calisiyorBakim = true;
  try {
    await toparla();
    await kalpKaybiYaz();
    await esikDenetle();
    await saklamaDenetle();
    await bolumDenetle();
    await bayatDenetle();
  } catch (hata) {
    console.error("[bakim]", (hata as Error).message);
  } finally {
    calisiyorBakim = false;
  }
}

async function tara(): Promise<void> {
  if (calisiyor) return;
  calisiyor = true;
  try {
    // Günlük özet her turda tazelenir; geç gelen hit de yakalanır.
    // Ölçüm aralığı ayardan okunur; 0 ise yalnızca cooldown sırası geçerli.
    const aralik = Number(await ayarOku("olcum_araligi_dk", "0")) || 0;
    // Kilit süresi: bu kadar eski 'running' satır sahipsiz sayılır.
    const kilitSn = (await kilitSuresiDk()) * 60;
    const adaylar = await sorgu<Aday>(
      `SELECT g.id AS keyword_geo_id, k.id AS keyword_id, c.id AS campaign_id,
              g.geo_code, g.tier, k.text AS kelime
         FROM keyword_geo g
         JOIN keyword k ON k.id = g.keyword_id
         JOIN site s ON s.id = k.site_id
         JOIN campaign c ON c.keyword_id = k.id AND c.stopped_at IS NULL
        WHERE k.state = 'active' AND s.active = 1
          AND (g.state <> 'running' OR g.kilit_at IS NULL
               OR g.kilit_at < UTC_TIMESTAMP(3) - INTERVAL ${kilitSn} SECOND)
          AND (${aralik} = 0 OR g.last_burst_at IS NULL
               OR g.last_burst_at < DATE_SUB(NOW(3), INTERVAL ${aralik} MINUTE))
        ORDER BY (g.cooldown_until IS NULL OR g.cooldown_until <= NOW(3)) DESC,
                 FIELD(g.tier, 'core', 'normal', 'passive'),
                 g.last_burst_at IS NULL DESC,
                 g.last_burst_at
        LIMIT ${TUR_SINIRI}`,
    );

    const sayac = new Map<number, number>();
    let atilan = 0;
    for (const aday of adaylar) {
      const kullanilan = sayac.get(aday.keyword_id) ?? 0;
      if (kullanilan >= KELIME_SINIRI) continue;

      sayac.set(aday.keyword_id, kullanilan + 1);

      // Koşullu güncelleme: satır iki turda birden seçilirse ikincisi düşer (C16).
      // Kilit başka düğümdeyse iş atlanır; tur durmaz, uyarı yazılır.
      const alindi = await sahiplen(aday.keyword_geo_id, rastgeleCooldown());
      if (!alindi) {
        await cakismaYaz(aday.keyword_geo_id, null).catch(() => {});
        continue;
      }
      const is: Is = {
        campaignId: aday.campaign_id,
        keywordId: aday.keyword_id,
        keywordGeoId: aday.keyword_geo_id,
        kelime: aday.kelime,
        il: aday.geo_code,
        tier: aday.tier,
      };
      await kuyruk.add("burst", is, { jobId: `kg-${aday.keyword_geo_id}-${Date.now()}` });
      atilan += 1;
    }

    if (atilan > 0) console.log(`[zamanlayici] ${atilan} iş kuyruğa atıldı`);

    // Ölçüm her dakika denenir; kendi 15 dakika kapısı var (C12).
    await olcumYap();
  } catch (hata) {
    console.error("[zamanlayici]", (hata as Error).message);
  } finally {
    calisiyor = false;
  }
}

export function zamanlayiciBaslat(): void {
  if (zaman) return;
  zaman = setInterval(() => void tara(), TIK_MS);
  bakimZamani = setInterval(() => void bakim(), BAKIM_MS);
  console.log("[zamanlayici] başladı");
  // Uzun kapalılıktan sonra geçmiş günler telafi edilir; tur beklemeden.
  void toparla(7).catch((hata: Error) => console.error("[traffic]", hata.message));
}

export function zamanlayiciDurdur(): void {
  if (zaman) clearInterval(zaman);
  zaman = null;
  if (bakimZamani) clearInterval(bakimZamani);
  bakimZamani = null;
}