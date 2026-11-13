/**
 * Ölçüm zamanlayıcısı.
 *
 * Kullanıcı durdurana kadar çalışır; günlük tavan yoktur. Dakikada bir
 * aktif kampanyaların satırlarını tarar ve kuyruğa atar.
 *
 * Cooldown sert engel değil, sıralama tercihidir: soğumadaki satır
 * listenin sonuna düşer, ilin IP'si bitince karışık devam edilir.
 */
import { sorgu, yaz } from "./veritabani.js";
import { ayarOku } from "./ayar.js";
import { kuyruk, type Is } from "./kuyruk.js";
import { toparla } from "./traffic.js";

const TIK_MS = 60_000;
const TUR_SINIRI = 200;
const KELIME_SINIRI = 12;

/** Tier'a göre bekleme; core sık, passive seyrek. */
const COOLDOWN_DK: Record<Is["tier"], number> = { core: 6, normal: 20, passive: 60 };

type Aday = {
  keyword_geo_id: number;
  keyword_id: number;
  campaign_id: number;
  geo_code: number;
  tier: Is["tier"];
  kelime: string;
};

let calisiyor = false;
let zaman: NodeJS.Timeout | null = null;

async function tara(): Promise<void> {
  if (calisiyor) return;
  calisiyor = true;
  try {
    // Günlük özet her turda tazelenir; geç gelen hit de yakalanır.
    await toparla();
    // Ölçüm aralığı ayardan okunur; 0 ise yalnızca cooldown sırası geçerli.
    const aralik = Number(await ayarOku("olcum_araligi_dk", "0")) || 0;

    const adaylar = await sorgu<Aday>(
      `SELECT g.id AS keyword_geo_id, k.id AS keyword_id, c.id AS campaign_id,
              g.geo_code, g.tier, k.text AS kelime
         FROM keyword_geo g
         JOIN keyword k ON k.id = g.keyword_id
         JOIN site s ON s.id = k.site_id
         JOIN campaign c ON c.keyword_id = k.id AND c.stopped_at IS NULL
        WHERE k.state = 'active' AND s.active = 1 AND g.state <> 'running'
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

      await yaz(
        "UPDATE keyword_geo SET state = 'running', cooldown_until = DATE_ADD(NOW(3), INTERVAL ? MINUTE) WHERE id = ?",
        [COOLDOWN_DK[aday.tier], aday.keyword_geo_id],
      );
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
  } catch (hata) {
    console.error("[zamanlayici]", (hata as Error).message);
  } finally {
    calisiyor = false;
  }
}

export function zamanlayiciBaslat(): void {
  if (zaman) return;
  zaman = setInterval(() => void tara(), TIK_MS);
  console.log("[zamanlayici] başladı");
  // Uzun kapalılıktan sonra geçmiş günler telafi edilir; tur beklemeden.
  void toparla(7).catch((hata: Error) => console.error("[traffic]", hata.message));
}

export function zamanlayiciDurdur(): void {
  if (!zaman) return;
  clearInterval(zaman);
  zaman = null;
}