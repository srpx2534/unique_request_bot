/**
 * Kelime uçları.
 *
 * Kelime eklenirken keyword_geo satırları aynı işlemde üretilir
 * (sözleşme §7): national 10 core + 30 normal + 41 passive, province tek
 * core satır. Silme sert; geo satırları cascade ile gider.
 */
import { Router } from "express";
import { z } from "zod";
import { dagitim } from "./geo.js";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { islem, sorgu, tek, yaz } from "./veritabani.js";

const yonlendirici = Router();

const SAYFA_VARSAYILAN = 50;
const SAYFA_UST = 200;

const eklemeSemasi = z
  .object({
    site_id: z.number().int().positive(),
    kelime: z.string().trim().min(2).max(191),
    kapsam: z.enum(["national", "province"]),
    il: z.number().int().min(1).max(81).nullable().optional(),
    tier: z.number().int().min(1).max(3).nullable().optional(),
    volume: z.number().int().positive().nullable().optional(),
    mobil: z.boolean().optional(),
  })
  .refine((v) => (v.kapsam === "province" ? Boolean(v.il) : !v.il), {
    message: "province için il zorunlu, national için boş olmalı",
    path: ["il"],
  });

const guncellemeSemasi = z.object({
  kelime: z.string().trim().min(2).max(191).optional(),
  tier: z.number().int().min(1).max(3).nullable().optional(),
  volume: z.number().int().positive().nullable().optional(),
  mobil: z.boolean().optional(),
});

function kimlik(deger: string | undefined): number | null {
  const sayi = Number(deger);
  return Number.isInteger(sayi) && sayi > 0 ? sayi : null;
}

/** Geo satırlarını üretir; sıra nüfus ağırlığından gelir. */
async function geoUret(kelimeId: number, kapsam: string, il: number | null): Promise<number> {
  const kodlar = await sorgu<{ code: number }>("SELECT code FROM geo ORDER BY weight DESC, code ASC");
  const satirlar = dagitim(
    kodlar.map((k) => k.code),
    kapsam as "national" | "province",
    il,
  );

  await islem(async (baglanti) => {
    await baglanti.execute("DELETE FROM keyword_geo WHERE keyword_id = ?", [kelimeId]);
    const yerler = satirlar.map(() => "(?, ?, ?)").join(", ");
    await baglanti.query(
      `INSERT INTO keyword_geo (keyword_id, geo_code, tier) VALUES ${yerler}`,
      satirlar.flatMap((s) => [kelimeId, s.kod, s.tier]),
    );
  });

  return satirlar.length;
}

yonlendirici.get("/kelime", async (istek, yanit) => {
  const kosullar: string[] = [];
  const degerler: unknown[] = [];

  const siteId = kimlik(istek.query.site as string | undefined);
  if (siteId !== null) {
    kosullar.push("k.site_id = ?");
    degerler.push(siteId);
  }
  const durum = istek.query.durum as string | undefined;
  if (durum) {
    kosullar.push("k.state = ?");
    degerler.push(durum);
  }
  const ara = (istek.query.q as string | undefined)?.trim();
  if (ara) {
    kosullar.push("(k.text LIKE ? OR s.domain LIKE ?)");
    degerler.push(`%${ara}%`, `%${ara}%`);
  }
  const nerede = kosullar.length > 0 ? `WHERE ${kosullar.join(" AND ")}` : "";

  const sayfa = Math.max(1, Number(istek.query.sayfa ?? 1) || 1);
  const adet = Math.min(SAYFA_UST, Math.max(1, Number(istek.query.adet ?? SAYFA_VARSAYILAN) || SAYFA_VARSAYILAN));

  const toplam = await tek<{ sayi: number }>(`SELECT COUNT(*) AS sayi FROM keyword k JOIN site s ON s.id = k.site_id ${nerede}`, degerler);
  const satirlar = await sorgu(
    `SELECT k.id, k.site_id, s.domain, k.text, k.geo_scope, k.home_geo, k.tier, k.mobil, k.state,
            k.created_at,
            (SELECT COUNT(*) FROM keyword_geo g WHERE g.keyword_id = k.id) AS geo_adet,
            (SELECT p.rank FROM position p WHERE p.keyword_id = k.id AND p.channel = 'clean'
              ORDER BY p.checked_at DESC LIMIT 1) AS son_sira,
            (SELECT COUNT(*) FROM position p WHERE p.keyword_id = k.id AND p.channel = 'clean') AS olcum_adet,
            il.name AS il_adi, s.active AS site_active
       FROM keyword k
       JOIN site s ON s.id = k.site_id
       LEFT JOIN geo il ON il.code = k.home_geo
       ${nerede}
      ORDER BY k.id DESC
      LIMIT ? OFFSET ?`,
    [...degerler, adet, (sayfa - 1) * adet],
  );

  yanit.json({ toplam: toplam?.sayi ?? 0, sayfa, adet, satirlar });
});

yonlendirici.post("/kelime", async (istek, yanit) => {
  const govde = dogrula(eklemeSemasi, istek.body, yanit);
  if (!govde) return;

  const site = await tek<{ id: number }>("SELECT id FROM site WHERE id = ?", [govde.site_id]);
  if (!site) {
    yanit.status(404).json({ hata: "site yok" });
    return;
  }

  let kelimeId: number;
  try {
    kelimeId = await islem(async (baglanti) => {
      const [sonuc] = await baglanti.execute(
        "INSERT INTO keyword (site_id, text, geo_scope, home_geo, tier, volume, mobil) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [govde.site_id, govde.kelime, govde.kapsam, govde.il ?? null, govde.tier ?? null, govde.volume ?? null, govde.mobil ? 1 : 0],
      );
      return (sonuc as { insertId: number }).insertId;
    });
  } catch (hata) {
    if ((hata as { code?: string }).code === "ER_DUP_ENTRY") {
      yanit.status(409).json({ hata: "bu kelime sitede zaten var" });
      return;
    }
    throw hata;
  }

  const geoAdet = await geoUret(kelimeId, govde.kapsam, govde.il ?? null);
  await denetim(istek, "kelime-ekle", "keyword", kelimeId);
  yanit.status(201).json({ id: kelimeId, geo_adet: geoAdet });
});

yonlendirici.patch("/kelime/:id", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz kelime kimliği" });
    return;
  }
  const govde = dogrula(guncellemeSemasi, istek.body, yanit);
  if (!govde) return;

  const alanlar: string[] = [];
  const degerler: unknown[] = [];
  if (govde.kelime !== undefined) {
    alanlar.push("text = ?");
    degerler.push(govde.kelime);
  }
  if (govde.tier !== undefined) {
    alanlar.push("tier = ?");
    degerler.push(govde.tier);
  }
  if (govde.volume !== undefined) {
    alanlar.push("volume = ?");
    degerler.push(govde.volume);
  }
  if (govde.mobil !== undefined) {
    alanlar.push("mobil = ?");
    degerler.push(govde.mobil ? 1 : 0);
  }
  if (alanlar.length === 0) {
    yanit.status(400).json({ hata: "güncellenecek alan yok" });
    return;
  }

  // Ayni degerle gelen PATCH'te MySQL 0 satir dondurur; 404 karari bu yuzden
  // etkilenen satir sayisina degil varlik kontrolune baglanir.
  const varMi = await tek<{ id: number }>("SELECT id FROM keyword WHERE id = ?", [id]);
  if (!varMi) {
    yanit.status(404).json({ hata: "kelime yok" });
    return;
  }
  degerler.push(id);
  try {
    const etkilenen = await yaz(`UPDATE keyword SET ${alanlar.join(", ")} WHERE id = ?`, degerler);
    if (etkilenen === 0 && !varMi) {
      yanit.status(404).json({ hata: "kelime yok" });
      return;
    }
  } catch (hata) {
    if ((hata as { code?: string }).code === "ER_DUP_ENTRY") {
      yanit.status(409).json({ hata: "bu kelime sitede zaten var" });
      return;
    }
    throw hata;
  }

  // Metin degisince rotasyon defteri yeni metne bagli kalir: geo satirlari
  // yeniden uretilmezse kelime hicbir ilde kosmaz ve sessizce olu kalir.
  if (govde.kelime !== undefined) {
    const geo = await tek<{ geo_scope: string; home_geo: number | null }>(
      "SELECT geo_scope, home_geo FROM keyword WHERE id = ?",
      [id],
    );
    if (geo) {
      await geoUret(id, geo.geo_scope as "national" | "province", geo.home_geo);
    }
  }

  await denetim(istek, "kelime-guncelle", "keyword", id);
  yanit.json(await tek("SELECT id, site_id, text, tier, volume, mobil, state FROM keyword WHERE id = ?", [id]));
});

yonlendirici.delete("/kelime/:id", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz kelime kimliği" });
    return;
  }
  const etkilenen = await yaz("DELETE FROM keyword WHERE id = ?", [id]);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "kelime yok" });
    return;
  }
  await denetim(istek, "kelime-sil", "keyword", id);
  yanit.status(204).end();
});

/**
 * Kelimenin sıralama ve ilerleme özeti.
 *
 * Panelde "özet" düğmesi bunu açar: ilk ölçülen sıra, şu anki sıra, hit
 * sayacı ve burst geçmişi tek yanıtta gelir. Sıralama yoksa null döner,
 * "hiç ölçülmedi" ile karışmasın diye ölçüm sayısı da verilir.
 */
yonlendirici.get("/kelime/:id/ozet", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz kelime kimliği" });
    return;
  }
  const kelime = await tek<{ text: string; state: string; volume: number | null }>(
    "SELECT text, state, volume FROM keyword WHERE id = ?",
    [id],
  );
  if (!kelime) {
    yanit.status(404).json({ hata: "kelime yok" });
    return;
  }

  // Siralama gecmisi: en eski ve en yeni kayit; trend bu ikisinden cikar.
  const gecmis = await sorgu<{ rank: number | null; checked_at: string }>(
    `SELECT rank, checked_at FROM position WHERE keyword_id = ? AND channel = 'clean'
      ORDER BY checked_at ASC LIMIT 500`,
    [id],
  );
  const olcum = gecmis.filter((g) => g.rank !== null);
  const ilk = olcum[0] ?? null;
  const son = olcum[olcum.length - 1] ?? null;

  const hitler = await tek<{ ok: number; fail: number; toplam: number }>(
    `SELECT
       (SELECT COUNT(*) FROM hit h JOIN burst b ON b.id = h.burst_id
          JOIN keyword_geo g ON g.id = b.keyword_geo_id
         WHERE g.keyword_id = ? AND h.result = 'ok') AS ok,
       (SELECT COUNT(*) FROM hit h JOIN burst b ON b.id = h.burst_id
          JOIN keyword_geo g ON g.id = b.keyword_geo_id
         WHERE g.keyword_id = ? AND h.result <> 'ok') AS fail,
       (SELECT COUNT(*) FROM burst b JOIN keyword_geo g ON g.id = b.keyword_geo_id
         WHERE g.keyword_id = ?) AS toplam`,
    [id, id, id],
  );

  const burstlar = await sorgu(
    `SELECT b.id, b.step, b.target_count, b.phase, b.started_at, b.ended_at
       FROM burst b JOIN keyword_geo g ON g.id = b.keyword_geo_id
      WHERE g.keyword_id = ? ORDER BY b.id DESC LIMIT 20`,
    [id],
  );

  yanit.json({
    kelime: kelime.text,
    state: kelime.state,
    volume: kelime.volume,
    olcum_sayisi: olcum.length,
    ilk_sira: ilk?.rank ?? null,
    ilk_at: ilk?.checked_at ?? null,
    son_sira: son?.rank ?? null,
    son_at: son?.checked_at ?? null,
    trend:
      ilk && son && ilk.rank !== null && son.rank !== null
        ? ilk.rank === son.rank
          ? "sabit"
          : son.rank < ilk.rank
            ? "yukari"
            : "asagi"
        : "yok",
    hit_ok: hitler?.ok ?? 0,
    hit_fail: hitler?.fail ?? 0,
    burst_adet: hitler?.toplam ?? 0,
    burstlar,
    seri: gecmis.slice(-60),
  });
});

yonlendirici.post("/kelime/:id/geo-yenile", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz kelime kimliği" });
    return;
  }
  const kelime = await tek<{ geo_scope: string; home_geo: number | null }>(
    "SELECT geo_scope, home_geo FROM keyword WHERE id = ?",
    [id],
  );
  if (!kelime) {
    yanit.status(404).json({ hata: "kelime yok" });
    return;
  }

  const adet = await geoUret(id, kelime.geo_scope, kelime.home_geo);
  await denetim(istek, "kelime-geo-yenile", "keyword", id);
  yanit.json({ geo_adet: adet });
});

yonlendirici.post("/kelime/:id/baslat", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz kelime kimliği" });
    return;
  }
  const satir = await tek<{ state: string; active: number }>(
    "SELECT k.state, s.active FROM keyword k JOIN site s ON s.id = k.site_id WHERE k.id = ?",
    [id],
  );
  if (!satir) {
    yanit.status(404).json({ hata: "kelime yok" });
    return;
  }
  if (satir.active !== 1) {
    yanit.status(409).json({ hata: "site pasif, önce siteyi aç" });
    return;
  }
  if (satir.state === "active") {
    yanit.status(409).json({ hata: "kelime zaten çalışıyor" });
    return;
  }

  // Onceki kampanya kapatilir: acik birakilirsa her baslat yeni kampanya acar,
  // eskiler sonsuza kadar acik kalir ve hacim gecmisi siser.
  const yeniKampanya = await islem(async (baglanti) => {
    await baglanti.execute("UPDATE keyword SET state = 'active' WHERE id = ?", [id]);
    await baglanti.execute(
      "UPDATE campaign SET stopped_at = UTC_TIMESTAMP(3) WHERE keyword_id = ? AND stopped_at IS NULL",
      [id],
    );
    const [sonuc] = await baglanti.execute(
      "INSERT INTO campaign (keyword_id, step_size, config) VALUES (?, ?, ?)",
      [id, 30, "{}"],
    );
    return (sonuc as { insertId: number }).insertId;
  });
  await denetim(istek, "kelime-baslat", "keyword", id);
  yanit.json({ id, state: "active", campaign_id: yeniKampanya });
});

yonlendirici.post("/kelime/:id/durdur", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz kelime kimliği" });
    return;
  }
  // Zaten durmus kelimede affectedRows 0 doner; 404 karari varliga baglanir.
  const varMi = await tek<{ id: number }>("SELECT id FROM keyword WHERE id = ?", [id]);
  if (!varMi) {
    yanit.status(404).json({ hata: "kelime yok" });
    return;
  }
  await yaz("UPDATE keyword SET state = 'paused' WHERE id = ?", [id]);
  await yaz(
    "UPDATE campaign SET stopped_at = UTC_TIMESTAMP(3) WHERE keyword_id = ? AND stopped_at IS NULL",
    [id],
  );
  await denetim(istek, "kelime-durdur", "keyword", id);
  yanit.status(204).end();
});

export default yonlendirici;
