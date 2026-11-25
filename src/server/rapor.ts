/**
 * Rapor uçları.
 *
 * Sayaçlar `hit` satırlarından toplanır: `target_count` planlanan sayıdır ve
 * erken durdurulan burst'te gerçekleşeni şişirir, bu yüzden planlanan ayrı
 * döner. Tüm sorgular tarih aralığı ve site/kelime süzgeciyle sınırlanır.
 */
import { Router } from "express";
import { sorgu, tek } from "./veritabani.js";

const yonlendirici = Router();

/** Tarih çipini koşula çevirir; tanınmazsa 30 gün varsayılır. */
function aralik(secim: string | undefined): string {
  switch (secim) {
    case "bugun":
      return "DATE(b.started_at) = UTC_DATE()";
    case "dun":
      return "DATE(b.started_at) = UTC_DATE() - INTERVAL 1 DAY";
    case "hafta":
      return "b.started_at >= UTC_TIMESTAMP(3) - INTERVAL 7 DAY";
    case "hepsi":
      return "1 = 1";
    default:
      return "b.started_at >= UTC_TIMESTAMP(3) - INTERVAL 30 DAY";
  }
}

const HIT = "COUNT(h.id)";
const OK = "CAST(COALESCE(SUM(h.result = 'ok'), 0) AS UNSIGNED)";
const CAPTCHA = "CAST(COALESCE(SUM(h.result = 'captcha'), 0) AS UNSIGNED)";
// Hata tek kalemde toplanır: timeout da başarısızlıktır.
const HATA = "CAST(COALESCE(SUM(h.result IN ('error', 'timeout')), 0) AS UNSIGNED)";
const YOK = "CAST(COALESCE(SUM(h.result = 'not_found'), 0) AS UNSIGNED)";

yonlendirici.get("/rapor", async (istek, yanit) => {
  const kosullar = [aralik(istek.query.aralik as string | undefined)];
  const degerler: unknown[] = [];

  const site = istek.query.site as string | undefined;
  if (site) {
    kosullar.push("s.domain = ?");
    degerler.push(site);
  }
  const kelime = (istek.query.kelime as string | undefined)?.trim();
  if (kelime) {
    // Rapor filtresi seçmeli: kelime metni tam eşleşir.
    kosullar.push("k.text = ?");
    degerler.push(kelime);
  }
  const nerede = `WHERE ${kosullar.join(" AND ")}`;

  // Birleşim ile süzgeç ayrı tutulur: hit birleşimi WHERE'den önce girmek
  // zorunda, burst seviyesi sayaçlar ise birleşimsiz okunur.
  const birlesim = `
    FROM burst b
    JOIN keyword_geo g ON g.id = b.keyword_geo_id
    JOIN keyword k ON k.id = g.keyword_id
    JOIN site s ON s.id = k.site_id
    -- Il yalniz il kapsamli kelimede yazilir: ulusal kelimenin 81 keyword_geo
    -- satiri var, il join'i yapilirsa ayni kelime 81 satir cikiyordu (C85).
    LEFT JOIN geo il ON il.code = g.geo_code AND k.geo_scope = 'province'`;
  const taban = `${birlesim} ${nerede}`;
  const tabanHit = `${birlesim} LEFT JOIN hit h ON h.burst_id = b.id ${nerede}`;

  // Burst seviyesi ayrı okunur: hit ile birleştirilince süre ortalaması ve
  // planlanan sayı hit başına tekrarlanıp şişiyordu.
  const burstTarafi = await tek<Record<string, number>>(
    `SELECT COUNT(*) AS burst,
            CAST(COALESCE(SUM(b.target_count), 0) AS UNSIGNED) AS planlanan,
            CAST(COALESCE(AVG(TIMESTAMPDIFF(SECOND, b.started_at, b.ended_at)), 0) AS UNSIGNED) AS ort_sn
       ${taban}`,
    degerler,
  );

  const hitTarafi = await tek<Record<string, number>>(
    `SELECT ${HIT} AS hit, ${OK} AS ok, ${CAPTCHA} AS captcha,
            ${HATA} AS hata, ${YOK} AS not_found
       ${tabanHit}`,
    degerler,
  );

  const ozet = { ...burstTarafi, ...hitTarafi };

  const siteler = await sorgu(
    `SELECT s.domain, ${HIT} AS hit, ${OK} AS ok, ${CAPTCHA} AS captcha,
            MAX(b.started_at) AS son
       ${tabanHit}
      GROUP BY s.id, s.domain
      ORDER BY hit DESC
      LIMIT 50`,
    degerler,
  );

  const kelimeler = await sorgu(
    `SELECT k.text AS kelime, s.domain,
            CASE WHEN k.geo_scope = 'province' THEN il.name END AS il_adi,
            ${HIT} AS hit, ${OK} AS ok, ${CAPTCHA} AS captcha,
            MAX(b.started_at) AS son
       ${tabanHit}
      GROUP BY k.id, k.text, s.domain, k.geo_scope, il.name
      ORDER BY hit DESC
      LIMIT 100`,
    degerler,
  );

  const gunluk = await sorgu(
    `SELECT DATE(b.started_at) AS gun, ${HIT} AS hit, ${OK} AS ok,
            ${CAPTCHA} AS captcha
       ${tabanHit}
      GROUP BY DATE(b.started_at)
      ORDER BY gun`,
    degerler,
  );

  yanit.json({ ozet, siteler, kelimeler, gunluk });
});

export default yonlendirici;
