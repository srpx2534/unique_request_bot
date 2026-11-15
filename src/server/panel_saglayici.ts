/** Panel saglayici uclari. */
import { Router } from "express";
import { z } from "zod";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { ekle, sorgu, tek, yaz } from "./veritabani.js";

export const yonlendirici = Router();

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

  const onceki = await tek<{ state: string }>("SELECT state FROM provider WHERE id = ?", [id]);
  const alanlar: string[] = [];
  const degerler: unknown[] = [];
  // Ayni istekte hem karantina hem agirlik gelirse agirlik yedege yazilir;
  // aksi halde sonraki "weight = ?" karantinanin sifirlamasini eziyordu.
  const yeniKarantina = govde.state === "quarantine" && onceki?.state !== "quarantine";
  if (govde.state !== undefined) {
    alanlar.push("state = ?");
    degerler.push(govde.state);
    // Karantina agirligi yedege alir, cikista yedekten doner (§8, C33).
    if (yeniKarantina) {
      alanlar.push("weight_yedek = COALESCE(?, weight)");
      degerler.push(govde.weight ?? null);
      alanlar.push("weight = 0");
      alanlar.push("quarantine_until = DATE_ADD(UTC_TIMESTAMP(3), INTERVAL 2 HOUR)");
    } else if (govde.state === "active" && onceki?.state === "quarantine") {
      alanlar.push("weight = COALESCE(weight_yedek, 10)", "weight_yedek = NULL");
      alanlar.push("quarantine_until = NULL", "captcha_pct = 0");
    }
  }
  if (govde.weight !== undefined && !yeniKarantina) {
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

  // provider.id AUTO_INCREMENT (043); kimlik DB'ye birakilir, panel id gondermez.
  // Sayac bos donerse satir kimliksiz kalirdi, insertId bu yuzden dogrulanir.
  const yeniId = await ekle(
    "INSERT INTO provider (name, kind, ulke, gateway, kullanici, sifre, weight) VALUES (?, ?, ?, ?, ?, ?, ?)",
    [govde.name, govde.kind, (govde.ulke ?? "TR").toUpperCase(), govde.gateway ?? null, govde.kullanici ?? null, govde.sifre ?? null, govde.weight ?? 1],
  );
  const id = yeniId;
  if (!id) {
    throw new Error("saglayici kimligi uretilmedi");
  }
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
