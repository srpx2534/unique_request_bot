/**
 * Sunucu (düğüm) uçları.
 *
 * Kayıt defteri: hangi makine ayakta, ne kadar yüklü, hangi sürüm.
 * Canlılık son kalp atışından hesaplanır; 45 saniyeden eskiyse sessiz
 * sayılır. Durdurulan düğüm iş almaz ama kalp atmaya devam eder.
 */
import { Router, type RequestHandler } from "express";
import { z } from "zod";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { sorgu, tek, yaz } from "./veritabani.js";
import { olay } from "./dugum_olay.js";

const yonlendirici = Router();

const eklemeSemasi = z.object({
  ad: z.string().trim().min(2).max(64),
  ip: z.string().trim().min(7).max(45),
});

const guncellemeSemasi = z.object({
  ad: z.string().trim().min(2).max(64).optional(),
  durum: z.enum(["aktif", "durduruldu"]).optional(),
});

const kalpSemasi = z.object({
  ip: z.string().trim().min(7).max(45),
  yuk: z.number().int().min(0).max(1000).optional(),
  cpu: z.number().min(0).max(100).optional(),
  ram: z.number().min(0).max(100).optional(),
  surum: z.string().trim().max(32).optional(),
});

yonlendirici.get("/dugum", async (istek, yanit) => {
  const kosullar: string[] = [];
  const degerler: unknown[] = [];

  const ara = (istek.query.q as string | undefined)?.trim();
  if (ara) {
    kosullar.push("(ad LIKE ? OR ip LIKE ?)");
    degerler.push(`%${ara}%`, `%${ara}%`);
  }
  const durum = istek.query.durum as string | undefined;
  if (durum === "aktif" || durum === "durduruldu") {
    kosullar.push("durum = ?");
    degerler.push(durum);
  }
  const kalp = istek.query.kalp as string | undefined;
  if (kalp === "canli") {
    kosullar.push("son_kalp_at > UTC_TIMESTAMP(3) - INTERVAL 45 SECOND");
  } else if (kalp === "sessiz") {
    kosullar.push("(son_kalp_at IS NULL OR son_kalp_at <= UTC_TIMESTAMP(3) - INTERVAL 45 SECOND)");
  }

  const nerede = kosullar.length ? `WHERE ${kosullar.join(" AND ")}` : "";
  const satirlar = await sorgu(
    `SELECT id, ad, ip, durum, yuk, cpu, ram, surum, son_kalp_at, kayit_at,
            CASE WHEN son_kalp_at IS NOT NULL AND son_kalp_at > UTC_TIMESTAMP(3) - INTERVAL 45 SECOND
                 THEN 'canli' ELSE 'sessiz' END AS canli
       FROM dugum
       ${nerede}
      ORDER BY canli DESC, id`,
    degerler,
  );
  yanit.json(satirlar);
});

yonlendirici.post("/dugum", async (istek, yanit) => {
  const govde = dogrula(eklemeSemasi, istek.body, yanit);
  if (!govde) return;
  try {
    await yaz("INSERT INTO dugum (ad, ip) VALUES (?, ?)", [govde.ad, govde.ip]);
  } catch (hata) {
    if ((hata as { code?: string }).code === "ER_DUP_ENTRY") {
      yanit.status(409).json({ hata: "bu IP zaten kayıtlı" });
      return;
    }
    throw hata;
  }
  const dugum = await tek<{ id: number }>("SELECT id FROM dugum WHERE ip = ?", [govde.ip]);
  if (dugum) await olay(dugum.id, "kayit", "dugum kaydedildi");
  await denetim(istek, "dugum-ekle", "dugum", dugum?.id ?? null);
  yanit.status(201).json(dugum);
});

yonlendirici.patch("/dugum/:id", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "geçersiz düğüm kimliği" });
    return;
  }
  const govde = dogrula(guncellemeSemasi, istek.body, yanit);
  if (!govde) return;

  const onceki = await tek<{ durum: string }>("SELECT durum FROM dugum WHERE id = ?", [id]);
  const alanlar: string[] = [];
  const degerler: unknown[] = [];
  if (govde.ad !== undefined) {
    alanlar.push("ad = ?");
    degerler.push(govde.ad);
  }
  if (govde.durum !== undefined) {
    alanlar.push("durum = ?");
    degerler.push(govde.durum);
  }
  if (alanlar.length === 0) {
    yanit.status(400).json({ hata: "güncellenecek alan yok" });
    return;
  }
  degerler.push(id);
  const etkilenen = await yaz(`UPDATE dugum SET ${alanlar.join(", ")} WHERE id = ?`, degerler);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "düğüm yok" });
    return;
  }
  // Durum gerçekten değiştiyse deftere yazılır; aynı değerin tekrarı sayılmaz.
  if (onceki && govde.durum !== undefined && govde.durum !== onceki.durum) {
    await olay(id, govde.durum === "durduruldu" ? "durdur" : "baslat", `durum: ${govde.durum}`);
  }
  await denetim(istek, "dugum-guncelle", "dugum", id);
  yanit.json(await tek("SELECT id, ad, ip, durum FROM dugum WHERE id = ?", [id]));
});

yonlendirici.get("/dugum/:id/olay", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "geçersiz düğüm kimliği" });
    return;
  }
  const adet = Math.min(200, Math.max(1, Number(istek.query.adet ?? 50) || 50));
  const sayfa = Math.max(1, Number(istek.query.sayfa ?? 1) || 1);
  const toplam =
    (await tek<{ sayi: number }>("SELECT COUNT(*) AS sayi FROM dugum_olay WHERE dugum_id = ?", [id]))?.sayi ?? 0;
  const satirlar = await sorgu(
    `SELECT id, tur, message, created_at FROM dugum_olay
      WHERE dugum_id = ? ORDER BY id DESC LIMIT ? OFFSET ?`,
    [id, adet, (sayfa - 1) * adet],
  );
  yanit.json({ satirlar, toplam, sayfa, adet });
});

yonlendirici.delete("/dugum/:id", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "geçersiz düğüm kimliği" });
    return;
  }
  // Olaylar cascade ile gider; silme kaydı düğüm gitmeden önce yazılır.
  const varMi = await tek<{ id: number }>("SELECT id FROM dugum WHERE id = ?", [id]);
  if (varMi) await olay(id, "sil", "dugum silindi");
  const etkilenen = await yaz("DELETE FROM dugum WHERE id = ?", [id]);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "düğüm yok" });
    return;
  }
  await denetim(istek, "dugum-sil", "dugum", id);
  yanit.status(204).end();
});

/** Kalp ucu; CSRF ve oturum denetiminin önünde çalışır. */
export const kalpIsleyici: RequestHandler = async (istek, yanit) => {
  const govde = dogrula(kalpSemasi, istek.body, yanit);
  if (!govde) return;

  const etkilenen = await yaz(
    `UPDATE dugum SET son_kalp_at = UTC_TIMESTAMP(3), yuk = ?, cpu = ?, ram = ?, surum = ?
      WHERE ip = ?`,
    [govde.yuk ?? 0, govde.cpu ?? 0, govde.ram ?? 0, govde.surum ?? null, govde.ip],
  );
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "düğüm kayıtlı değil" });
    return;
  }
  const dugum = await tek<{ durum: string }>("SELECT durum FROM dugum WHERE ip = ?", [govde.ip]);
  yanit.json({ durum: dugum?.durum ?? "aktif" });
};

export default yonlendirici;