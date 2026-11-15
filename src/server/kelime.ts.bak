/**
 * Kelime uçları.
 *
 * Kelime eklenirken keyword_geo satırları aynı işlemde üretilir
 * (sözleşme §7): national 10 core + 30 normal + 41 passive, province tek
 * core satır. Silme sert; geo satırları cascade ile gider.
 */
import { Router } from "express";
import { z } from "zod";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { islem, sorgu, tek, yaz } from "./veritabani.js";
import {
  SAYFA_UST, SAYFA_VARSAYILAN, eklemeSemasi, geoUret, guncellemeSemasi, kimlik,
} from "./kelime_ortak.js";
import { yonlendirici as listeYonlendirici } from "./kelime_liste.js";
import { yonlendirici as ozetYonlendirici } from "./kelime_ozet.js";

const yonlendirici = Router();

yonlendirici.use("/kelime", listeYonlendirici);
yonlendirici.use("/kelime", ozetYonlendirici);

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
