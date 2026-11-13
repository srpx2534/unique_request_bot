/**
 * Site uçları.
 *
 * Site alan adı ve etiketten ibaret; geo dağılımı Türkiye illeriyle
 * sınırlı olduğu için ülke/dil sütunu yok. Silme sert: kelimeler ve
 * geo satırları birlikte gider.
 */
import { Router } from "express";
import { z } from "zod";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { sorgu, tek, yaz } from "./veritabani.js";

const yonlendirici = Router();

const alanAdi = z
  .string()
  .trim()
  .min(3)
  .max(191)
  .regex(/^[a-z0-9.-]+\.[a-z]{2,}$/i, "geçerli bir alan adı yaz");

const eklemeSemasi = z.object({
  domain: alanAdi,
  label: z.string().trim().max(191).optional(),
});

const guncellemeSemasi = z.object({
  label: z.string().trim().max(191).nullable().optional(),
  active: z.boolean().optional(),
});

function kimlik(deger: string | undefined): number | null {
  const sayi = Number(deger);
  return Number.isInteger(sayi) && sayi > 0 ? sayi : null;
}

yonlendirici.get("/site", async (_istek, yanit) => {
  const satirlar = await sorgu(
    `SELECT s.id, s.domain, s.label, s.active, s.created_at,
            (SELECT COUNT(*) FROM keyword k WHERE k.site_id = s.id) AS kelime_adet
       FROM site s
      ORDER BY s.id DESC`,
  );
  yanit.json(satirlar);
});

yonlendirici.post("/site", async (istek, yanit) => {
  const govde = dogrula(eklemeSemasi, istek.body, yanit);
  if (!govde) return;

  const domain = govde.domain.toLowerCase();
  try {
    await yaz("INSERT INTO site (domain, label) VALUES (?, ?)", [domain, govde.label ?? null]);
  } catch (hata) {
    if ((hata as { code?: string }).code === "ER_DUP_ENTRY") {
      yanit.status(409).json({ hata: "bu alan adı zaten kayıtlı" });
      return;
    }
    throw hata;
  }

  const site = await tek("SELECT id, domain, label, active FROM site WHERE domain = ?", [domain]);
  await denetim(istek, "site-ekle", "site", (site as { id: number } | null)?.id ?? null);
  yanit.status(201).json(site);
});

yonlendirici.patch("/site/:id", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz site kimliği" });
    return;
  }
  const govde = dogrula(guncellemeSemasi, istek.body, yanit);
  if (!govde) return;

  const alanlar: string[] = [];
  const degerler: unknown[] = [];
  if (govde.label !== undefined) {
    alanlar.push("label = ?");
    degerler.push(govde.label);
  }
  if (govde.active !== undefined) {
    alanlar.push("active = ?");
    degerler.push(govde.active ? 1 : 0);
  }
  if (alanlar.length === 0) {
    yanit.status(400).json({ hata: "güncellenecek alan yok" });
    return;
  }

  degerler.push(id);
  const etkilenen = await yaz(`UPDATE site SET ${alanlar.join(", ")} WHERE id = ?`, degerler);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "site yok" });
    return;
  }

  await denetim(istek, "site-guncelle", "site", id);
  yanit.json(await tek("SELECT id, domain, label, active FROM site WHERE id = ?", [id]));
});

yonlendirici.delete("/site/:id", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "geçersiz site kimliği" });
    return;
  }
  const etkilenen = await yaz("DELETE FROM site WHERE id = ?", [id]);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "site yok" });
    return;
  }
  await denetim(istek, "site-sil", "site", id);
  yanit.status(204).end();
});

export default yonlendirici;
