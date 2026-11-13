/**
 * Panel okuma uçları.
 *
 * Ekranların ihtiyaç duyduğu özet, sağlayıcı, uyarı, ayar ve log verisi
 * burada toplanır. Yazma uçları kendi dosyalarında; burada yalnızca
 * panelin tükettiği hafif sorgular var.
 */
import { Router } from "express";
import { z } from "zod";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { sorgu, tek, yaz } from "./veritabani.js";

const yonlendirici = Router();

yonlendirici.get("/ozet", async (_istek, yanit) => {
  const sayim = await tek<Record<string, number>>(
    `SELECT
       (SELECT COUNT(*) FROM keyword WHERE state = 'active') AS aktif_kelime,
       (SELECT COUNT(*) FROM keyword) AS toplam_kelime,
       (SELECT COUNT(*) FROM site WHERE active = 1) AS aktif_site,
       (SELECT COUNT(*) FROM provider WHERE state = 'active' AND gateway IS NOT NULL) AS canli_saglayici,
       (SELECT COUNT(*) FROM alert WHERE acknowledged = 0) AS acik_uyari,
       (SELECT COUNT(*) FROM burst WHERE started_at >= NOW() - INTERVAL 24 HOUR) AS gunluk_burst`,
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
    "SELECT id, kind, message, TIMESTAMPDIFF(MINUTE, created_at, NOW(3)) AS yas_dk FROM alert WHERE acknowledged = 0 ORDER BY created_at DESC LIMIT 3",
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

const saglayiciSemasi = z.object({
  name: z.string().trim().min(2).max(64).optional(),
  kind: z.enum(["residential", "mobile", "datacenter"]).optional(),
  state: z.enum(["active", "quarantine", "disabled"]).optional(),
  weight: z.number().int().min(1).max(100).optional(),
  ulke: z.string().length(2).optional(),
  gateway: z.string().trim().max(128).nullable().optional(),
  kullanici: z.string().trim().max(128).nullable().optional(),
  sifre: z.string().trim().max(128).nullable().optional(),
});

yonlendirici.get("/geo", async (_istek, yanit) => {
  yanit.json(await sorgu("SELECT code, name FROM geo ORDER BY name"));
});

yonlendirici.patch("/provider/:id", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "geçersiz sağlayıcı kimliği" });
    return;
  }
  const govde = dogrula(saglayiciSemasi, istek.body, yanit);
  if (!govde) return;

  const alanlar: string[] = [];
  const degerler: unknown[] = [];
  if (govde.state !== undefined) {
    alanlar.push("state = ?");
    degerler.push(govde.state);
  }
  if (govde.weight !== undefined) {
    alanlar.push("weight = ?");
    degerler.push(govde.weight);
  }
  if (govde.ulke !== undefined) {
    alanlar.push("ulke = ?");
    degerler.push(govde.ulke.toUpperCase());
  }
  if (govde.name !== undefined) {
    alanlar.push("name = ?");
    degerler.push(govde.name);
  }
  if (govde.kind !== undefined) {
    alanlar.push("kind = ?");
    degerler.push(govde.kind);
  }
  for (const alan of ["gateway", "kullanici", "sifre"] as const) {
    if (govde[alan] !== undefined) {
      alanlar.push(`${alan} = ?`);
      degerler.push(govde[alan]);
    }
  }
  if (alanlar.length === 0) {
    yanit.status(400).json({ hata: "güncellenecek alan yok" });
    return;
  }
  degerler.push(id);
  const etkilenen = await yaz(`UPDATE provider SET ${alanlar.join(", ")} WHERE id = ?`, degerler);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "sağlayıcı yok" });
    return;
  }
  await denetim(istek, "saglayici-guncelle", "provider", id);
  yanit.json(await tek("SELECT id, name, kind, ulke, state, weight FROM provider WHERE id = ?", [id]));
});

yonlendirici.post("/provider", async (istek, yanit) => {
  const govde = dogrula(saglayiciSemasi.extend({ name: z.string().trim().min(2).max(64), kind: z.enum(["residential", "mobile", "datacenter"]) }), istek.body, yanit);
  if (!govde) return;

  const son = await tek<{ son: number }>("SELECT COALESCE(MAX(id), 0) AS son FROM provider");
  const id = (son?.son ?? 0) + 1;
  await yaz(
    "INSERT INTO provider (id, name, kind, ulke, gateway, kullanici, sifre, weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    [id, govde.name, govde.kind, (govde.ulke ?? "TR").toUpperCase(), govde.gateway ?? null, govde.kullanici ?? null, govde.sifre ?? null, govde.weight ?? 1],
  );
  await denetim(istek, "saglayici-ekle", "provider", id);
  yanit.status(201).json(await tek("SELECT id, name, kind, ulke, state, weight FROM provider WHERE id = ?", [id]));
});

yonlendirici.delete("/provider/:id", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "geçersiz sağlayıcı kimliği" });
    return;
  }
  try {
    const etkilenen = await yaz("DELETE FROM provider WHERE id = ?", [id]);
    if (etkilenen === 0) {
      yanit.status(404).json({ hata: "sağlayıcı yok" });
      return;
    }
    await denetim(istek, "saglayici-sil", "provider", id);
    yanit.status(204).end();
  } catch (hata) {
    // Hit kaydı olan sağlayıcı silinemez; kapatılır.
    if ((hata as { code?: string }).code === "ER_ROW_IS_REFERENCED_2") {
      await yaz("UPDATE provider SET state = ? WHERE id = ?", ["disabled", id]);
      await denetim(istek, "saglayici-kapat", "provider", id);
      yanit.json({ kapatildi: true });
      return;
    }
    throw hata;
  }
});

/** Tarih aralığı çipini SQL koşuluna çevirir. */
function aralikKosulu(aralik: string | undefined, kolon: string): string | null {
  switch (aralik) {
    case "bugun":
      return `DATE(${kolon}) = CURDATE()`;
    case "dun":
      return `DATE(${kolon}) = CURDATE() - INTERVAL 1 DAY`;
    case "hafta":
      return `${kolon} >= NOW(3) - INTERVAL 7 DAY`;
    case "ay":
      return `${kolon} >= NOW(3) - INTERVAL 30 DAY`;
    default:
      return null;
  }
}

yonlendirici.get("/uyari", async (istek, yanit) => {
  const kosullar: string[] = [];
  const degerler: unknown[] = [];

  const tur = istek.query.tur as string | undefined;
  if (tur) {
    kosullar.push("a.kind = ?");
    degerler.push(tur);
  }
  const durum = istek.query.durum as string | undefined;
  if (durum === "acik") kosullar.push("a.acknowledged = 0");
  if (durum === "kapali") kosullar.push("a.acknowledged = 1");

  const aralik = aralikKosulu(istek.query.aralik as string | undefined, "a.created_at");
  if (aralik) kosullar.push(aralik);

  const ara = (istek.query.q as string | undefined)?.trim();
  if (ara) {
    kosullar.push("a.message LIKE ?");
    degerler.push(`%${ara}%`);
  }

  const siteAdi = istek.query.site as string | undefined;
  if (siteAdi) {
    kosullar.push("s.domain = ?");
    degerler.push(siteAdi);
  }
  const kelimeAdi = (istek.query.kelime as string | undefined)?.trim();
  if (kelimeAdi) {
    kosullar.push("k.text LIKE ?");
    degerler.push(`%${kelimeAdi}%`);
  }

  const nerede = kosullar.length ? `WHERE ${kosullar.join(" AND ")}` : "";
  const adet = adetOku(istek.query.adet, 50);
  const sayfa = sayfaOku(istek.query.sayfa);
  const toplam =
    (
      await tek<{ sayi: number }>(
        `SELECT COUNT(*) AS sayi FROM alert a
           LEFT JOIN keyword k ON k.id = a.keyword_id
           LEFT JOIN site s ON s.id = a.site_id
           ${nerede}`,
        degerler,
      )
    )?.sayi ?? 0;
  const satirlar = await sorgu(
    `SELECT a.id, a.kind, a.ref_id, a.message, a.acknowledged, a.created_at,
            TIMESTAMPDIFF(MINUTE, a.created_at, NOW(3)) AS yas_dk,
            k.text AS kelime, s.domain
       FROM alert a
       LEFT JOIN keyword k ON k.id = a.keyword_id
       LEFT JOIN site s ON s.id = a.site_id
       ${nerede}
      ORDER BY a.acknowledged ASC, a.created_at DESC
      LIMIT ?`,
    [...degerler, adet, (sayfa - 1) * adet],
  );
  const ozet = await tek<Record<string, number>>(
    `SELECT SUM(acknowledged = 0) AS acik, SUM(acknowledged = 1) AS kapali FROM alert`,
  );
  yanit.json({ satirlar, ozet, toplam, sayfa, adet });
});

yonlendirici.post("/uyari/tumunu-kapat", async (istek, yanit) => {
  const kosullar = ["acknowledged = 0"];
  const degerler: unknown[] = [];

  const tur = istek.body?.tur as string | undefined;
  if (tur) {
    kosullar.push("kind = ?");
    degerler.push(tur);
  }
  const aralik = aralikKosulu(istek.body?.aralik as string | undefined, "created_at");
  if (aralik) kosullar.push(aralik);

  const etkilenen = await yaz(`UPDATE alert SET acknowledged = 1 WHERE ${kosullar.join(" AND ")}`, degerler);
  await denetim(istek, "uyari-tumunu-kapat", "alert", null);
  yanit.json({ kapatilan: etkilenen });
});

yonlendirici.post("/uyari/:id/kapat", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "geçersiz uyarı kimliği" });
    return;
  }
  const etkilenen = await yaz("UPDATE alert SET acknowledged = 1 WHERE id = ?", [id]);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "uyarı yok" });
    return;
  }
  await denetim(istek, "uyari-kapat", "alert", id);
  yanit.status(204).end();
});

/** Sayfa boyunu sınırlar: 1-500 arası, geçersizse varsayılan. */
function adetOku(ham: unknown, varsayilan = 100): number {
  const sayi = Number(ham);
  return Number.isInteger(sayi) && sayi > 0 ? Math.min(sayi, 500) : varsayilan;
}
/** Sayfa numarasını 1'den başlatır. */
function sayfaOku(ham: unknown): number {
  const sayi = Number(ham);
  return Number.isInteger(sayi) && sayi > 0 ? sayi : 1;
}
const GIZLI_AYARLAR = new Set(["serp_decodo", "serp_serper", "serp_searchapi"]);

/** Sır ayarları son dört hane dışında maskeler. */
function ayarMaskele(satirlar: { anahtar: string; deger: string }[]) {
  return satirlar.map((satir) =>
    GIZLI_AYARLAR.has(satir.anahtar) && satir.deger
      ? { anahtar: satir.anahtar, deger: `••••${satir.deger.slice(-4)}` }
      : satir,
  );
}
yonlendirici.get("/ayar", async (_istek, yanit) => {
  yanit.json(ayarMaskele(await sorgu("SELECT anahtar, deger FROM ayar ORDER BY anahtar")));
});

/** Bir SERP anahtarını tek sorguyla dener. Yalnızca Decodo desteklenir. */
yonlendirici.post("/ayar/serp-dene", async (istek, yanit) => {
  const govde = dogrula(
    z.object({ anahtar: z.enum(["serp_decodo", "serp_serper", "serp_searchapi"]) }),
    istek.body,
    yanit,
  );
  if (!govde) return;

  const satir = await tek<{ deger: string }>("SELECT deger FROM ayar WHERE anahtar = ?", [govde.anahtar]);
  const anahtar = satir?.deger?.trim() ?? "";
  if (!anahtar) {
    yanit.status(400).json({ hata: "anahtar tanımlı değil" });
    return;
  }

  const basladi = Date.now();
  try {
    const cevap = await fetch("https://data.decodo.com/v1/search", {
      method: "POST",
      headers: { authorization: `Bearer ${anahtar}`, "content-type": "application/json" },
      body: JSON.stringify({ query: "veteriner", locale: "tr-TR", geo: "tr" }),
      signal: AbortSignal.timeout(20_000),
    });
    const sure = Date.now() - basladi;
    if (!cevap.ok) {
      yanit.json({ ok: false, kod: cevap.status, sure_ms: sure });
      return;
    }
    const veri = (await cevap.json()) as { organic?: unknown[] };
    yanit.json({
      ok: true,
      organik: Array.isArray(veri.organic) ? veri.organic.length : 0,
      sure_ms: sure,
    });
  } catch (hata) {
    yanit.json({ ok: false, hata: (hata as Error).message, sure_ms: Date.now() - basladi });
  }
});
yonlendirici.patch("/ayar", async (istek, yanit) => {
  const govde = dogrula(z.record(z.string().max(255)), istek.body, yanit);
  if (!govde) return;

  const ciftler = Object.entries(govde);
  if (ciftler.length === 0) {
    yanit.status(400).json({ hata: "güncellenecek ayar yok" });
    return;
  }
  for (const [anahtar, deger] of ciftler) {
    // Maskeli değer geri gönderildiyse gerçek değer korunur.
    if (GIZLI_AYARLAR.has(anahtar) && deger.startsWith("••••")) continue;
    await yaz(
      "INSERT INTO ayar (anahtar, deger) VALUES (?, ?) ON DUPLICATE KEY UPDATE deger = VALUES(deger)",
      [anahtar, deger],
    );
  }
  await denetim(istek, "ayar-guncelle", "ayar", null);
  yanit.json(ayarMaskele(await sorgu("SELECT anahtar, deger FROM ayar ORDER BY anahtar")));
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
            b.started_at, b.ended_at, b.stats, g.geo_code, g.tier, geo.name AS il_adi
       FROM burst b
       JOIN keyword_geo g ON g.id = b.keyword_geo_id
       JOIN keyword k ON k.id = g.keyword_id
       JOIN site s ON s.id = k.site_id
       LEFT JOIN geo ON geo.code = g.geo_code
       ${nerede}
      ORDER BY b.id DESC LIMIT ?`,
    [...degerler, adet, (sayfa - 1) * adet],
  );
  yanit.json({ satirlar, toplam, sayfa, adet });
});

export default yonlendirici;