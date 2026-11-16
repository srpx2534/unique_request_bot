/**
 * Panel okuma uçları.
 *
 * Ekranların ihtiyaç duyduğu özet, sağlayıcı, uyarı, ayar ve log verisi
 * burada toplanır. Yazma uçları kendi dosyalarında; burada yalnızca
 * panelin tükettiği hafif sorgular var.
 */
import { Router } from "express";
import { sorgu, tek } from "./veritabani.js";
import { adetOku, aralikKosulu, sayfaOku } from "./panel_ortak.js";
import { yonlendirici as ayarYonlendirici } from "./panel_ayar.js";
import { yonlendirici as uyariYonlendirici } from "./panel_uyari.js";
import { yonlendirici as saglayiciYonlendirici } from "./panel_saglayici.js";

const yonlendirici = Router();

yonlendirici.get("/ozet", async (_istek, yanit) => {
  const sayim = await tek<Record<string, number>>(
    `SELECT
       (SELECT COUNT(*) FROM keyword WHERE state = 'active') AS aktif_kelime,
       (SELECT COUNT(*) FROM keyword) AS toplam_kelime,
       (SELECT COUNT(*) FROM site WHERE active = 1) AS aktif_site,
       (SELECT COUNT(*) FROM provider WHERE state = 'active' AND gateway IS NOT NULL) AS canli_saglayici,
       (SELECT COUNT(*) FROM alert WHERE acknowledged = 0) AS acik_uyari,
       (SELECT COUNT(*) FROM burst WHERE started_at >= UTC_TIMESTAMP(3) - INTERVAL 24 HOUR) AS gunluk_burst`,
  );
  const son = await sorgu(
    `SELECT b.id, k.text, b.step, b.target_count, b.started_at, b.stats
       FROM burst b JOIN keyword k ON k.id = (SELECT keyword_id FROM keyword_geo WHERE id = b.keyword_geo_id)
      ORDER BY b.id DESC LIMIT 8`,
  );
  const siteler = await sorgu(
    "SELECT id, domain, label FROM site WHERE active = 1 ORDER BY id DESC LIMIT 20",
  );
  const kelimeler = await sorgu(
    `SELECT k.id, k.text, k.state, k.volume, s.domain, g.name AS il_adi,
            (SELECT COUNT(*) FROM keyword_geo kg WHERE kg.keyword_id = k.id) AS geo_adet,
            (SELECT COALESCE(SUM(b.target_count), 0) FROM burst b
               JOIN keyword_geo kg2 ON kg2.id = b.keyword_geo_id
              WHERE kg2.keyword_id = k.id) AS atilan,
            (SELECT MAX(b.started_at) FROM burst b
               JOIN keyword_geo kg3 ON kg3.id = b.keyword_geo_id
              WHERE kg3.keyword_id = k.id) AS son_burst_at
       FROM keyword k
       JOIN site s ON s.id = k.site_id
       LEFT JOIN geo g ON g.code = k.home_geo
      WHERE k.state = 'active'
      ORDER BY k.id DESC LIMIT 20`,
  );
  const havuz = await tek<Record<string, number>>(
    `SELECT
       (SELECT COUNT(*) FROM provider WHERE state = 'active' AND ulke = 'TR' AND gateway IS NOT NULL) AS canli_tr,
       (SELECT COUNT(*) FROM provider WHERE state = 'active' AND ulke <> 'TR' AND gateway IS NOT NULL) AS canli_yabanci,
       (SELECT COUNT(*) FROM provider WHERE state <> 'active') AS olu`,
  );
  const uyarilar = await sorgu(
    "SELECT id, kind, message, TIMESTAMPDIFF(MINUTE, created_at, UTC_TIMESTAMP(3)) AS yas_dk FROM alert WHERE acknowledged = 0 ORDER BY created_at DESC LIMIT 3",
  );
  yanit.json({ ...sayim, son, siteler, kelimeler, havuz, uyarilar });
});

yonlendirici.get("/provider", async (istek, yanit) => {
  const ara = (istek.query.q as string | undefined)?.trim();
  const satirlar = await sorgu(
    `SELECT id, name, kind, ulke, state, weight, gateway, kullanici, captcha_pct, quarantine_until
       FROM provider
      ${ara ? "WHERE name LIKE ? OR gateway LIKE ? OR ulke LIKE ?" : ""}
      ORDER BY state = 'active' DESC, weight DESC, id`,
    ara ? [`%${ara}%`, `%${ara}%`, `%${ara}%`] : [],
  );
  yanit.json(satirlar);
});


yonlendirici.get("/log", async (istek, yanit) => {
  const kosullar: string[] = [];
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
  if (istek.query.sadece_hata === "1") {
    kosullar.push("(b.ended_at IS NULL OR CAST(JSON_EXTRACT(b.stats, '$.error') AS UNSIGNED) > 0)");
  }

  const aralik = aralikKosulu(istek.query.aralik as string | undefined, "b.started_at");
  if (aralik) kosullar.push(aralik);

  const nerede = kosullar.length ? `WHERE ${kosullar.join(" AND ")}` : "";
  const adet = adetOku(istek.query.adet, 50);
  const sayfa = sayfaOku(istek.query.sayfa);
  const toplam =
    (
      await tek<{ sayi: number }>(
        `SELECT COUNT(*) AS sayi FROM burst b
           JOIN keyword_geo g ON g.id = b.keyword_geo_id
           JOIN keyword k ON k.id = g.keyword_id
           JOIN site s ON s.id = k.site_id
           ${nerede}`,
        degerler,
      )
    )?.sayi ?? 0;
  const satirlar = await sorgu(
    `SELECT b.id, k.text AS kelime, s.domain, b.step, b.target_count,
            b.started_at, b.ended_at, b.stats, k.geo_scope,
            -- Il yalniz il kapsamli kelimede yazilir: ulusal kelimede
            -- keyword_geo satiri rotasyon defteridir, hedefleme degildir.
            CASE WHEN k.geo_scope = 'province' THEN g.geo_code END AS geo_code,
            g.tier,
            CASE WHEN k.geo_scope = 'province' THEN geo.name END AS il_adi
       FROM burst b
       JOIN keyword_geo g ON g.id = b.keyword_geo_id
       JOIN keyword k ON k.id = g.keyword_id
       JOIN site s ON s.id = k.site_id
       LEFT JOIN geo ON geo.code = g.geo_code
       ${nerede}
      ORDER BY b.id DESC LIMIT ? OFFSET ?`,
    [...degerler, adet, (sayfa - 1) * adet],
  );
  yanit.json({ satirlar, toplam, sayfa, adet });
});

yonlendirici.use("/uyari", uyariYonlendirici);
yonlendirici.use("/ayar", ayarYonlendirici);

yonlendirici.use(saglayiciYonlendirici);

export default yonlendirici;
