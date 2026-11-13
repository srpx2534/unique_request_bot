/**
 * Rapor uçları.
 *
 * Sayaçlar `burst` kayıtlarındaki stats alanından toplanır; `hit` tablosu
 * dolduğunda aynı uç daha ince veri döndürecek biçimde yazıldı.
 * Tüm sorgular tarih aralığı ve site/kelime süzgeciyle sınırlanır.
 */
import { Router } from "express";
import { sorgu, tek } from "./veritabani.js";

const yonlendirici = Router();

/** Tarih çipini koşula çevirir; tanınmazsa 30 gün varsayılır. */
function aralik(secim: string | undefined): string {
  switch (secim) {
    case "bugun":
      return "DATE(b.started_at) = CURDATE()";
    case "dun":
      return "DATE(b.started_at) = CURDATE() - INTERVAL 1 DAY";
    case "hafta":
      return "b.started_at >= NOW(3) - INTERVAL 7 DAY";
    case "hepsi":
      return "1 = 1";
    default:
      return "b.started_at >= NOW(3) - INTERVAL 30 DAY";
  }
}

const HIT = "COALESCE(SUM(b.target_count), 0)";
const OK = "COALESCE(SUM(CAST(JSON_EXTRACT(b.stats, '$.ok') AS UNSIGNED)), 0)";
const CAPTCHA = "COALESCE(SUM(CAST(JSON_EXTRACT(b.stats, '$.captcha') AS UNSIGNED)), 0)";
const HATA = "COALESCE(SUM(CAST(JSON_EXTRACT(b.stats, '$.error') AS UNSIGNED)), 0)";

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
    kosullar.push("k.text LIKE ?");
    degerler.push(`%${kelime}%`);
  }
  const nerede = `WHERE ${kosullar.join(" AND ")}`;

  const taban = `
    FROM burst b
    JOIN keyword_geo g ON g.id = b.keyword_geo_id
    JOIN keyword k ON k.id = g.keyword_id
    JOIN site s ON s.id = k.site_id
    LEFT JOIN geo il ON il.code = g.geo_code
    ${nerede}`;

  const ozet = await tek<Record<string, number>>(
    `SELECT ${HIT} AS hit, ${OK} AS ok, ${CAPTCHA} AS captcha, ${HATA} AS hata,
            COUNT(*) AS burst,
            COALESCE(AVG(TIMESTAMPDIFF(SECOND, b.started_at, b.ended_at)), 0) AS ort_sn
       ${taban}`,
    degerler,
  );

  const siteler = await sorgu(
    `SELECT s.domain, ${HIT} AS hit, ${OK} AS ok, ${CAPTCHA} AS captcha,
            MAX(b.started_at) AS son
       ${taban}
      GROUP BY s.id, s.domain
      ORDER BY hit DESC
      LIMIT 50`,
    degerler,
  );

  const kelimeler = await sorgu(
    `SELECT k.text AS kelime, s.domain, il.name AS il_adi,
            ${HIT} AS hit, ${OK} AS ok, ${CAPTCHA} AS captcha,
            MAX(b.started_at) AS son
       ${taban}
      GROUP BY k.id, k.text, s.domain, il.name
      ORDER BY hit DESC
      LIMIT 100`,
    degerler,
  );

  const gunluk = await sorgu(
    `SELECT DATE(b.started_at) AS gun, ${HIT} AS hit, ${OK} AS ok, ${CAPTCHA} AS captcha
       ${taban}
      GROUP BY DATE(b.started_at)
      ORDER BY gun`,
    degerler,
  );

  yanit.json({ ozet, siteler, kelimeler, gunluk });
});

export default yonlendirici;