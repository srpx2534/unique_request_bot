/** Cerez yukleme uclari. */
import { promises as fs } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { Router } from "express";
import multer from "multer";
import { islem, sorgu, tek, yaz } from "../veritabani.js";
import { isle } from "./aktarim.js";
import { durum, yukleyenKimlik } from "./ortak.js";
import {
  AZAMI_BOYUT, PARTI_BAYT, PARTI_DOSYA, YUKLEME_KOK, dosyalariTopla, guvenliYol,
} from "./yollar.js";

export const yonlendirici = Router();

const yukle = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: AZAMI_BOYUT, files: PARTI_DOSYA },
});

async function yuklemeAl(id: number) {
  return tek<{ id: number; klasor: string; durum: string }>(
    "SELECT id, klasor, durum FROM cerez_yukleme WHERE id = ?",
    [id],
  );
}

let sonSupurme = 0;

/** Bir gunden eski bitmis islemlerin gecici klasorunu siler. */
async function supur(): Promise<void> {
  if (Date.now() - sonSupurme < 3_600_000) return;
  sonSupurme = Date.now();
  const eskiler = await sorgu<{ klasor: string }>(
    "SELECT klasor FROM cerez_yukleme WHERE durum IN ('bitti','iptal') AND created_at < UTC_TIMESTAMP(3) - INTERVAL 1 DAY",
  ).catch(() => [] as { klasor: string }[]);
  for (const satir of eskiler) {
    await fs.rm(satir.klasor, { recursive: true, force: true }).catch(() => {});
  }
}

/** Son yukleme islemleri. */
yonlendirici.get("/", async (_istek, yanit) => {
  void supur();
  yanit.json(
    await sorgu(
      `SELECT y.id, y.dosya_sayisi, y.boyut, y.durum, y.created_at,
              (SELECT COUNT(*) FROM cookie_dosya d WHERE d.yukleme_id = y.id AND d.durum = 'aktarildi') AS aktarilan
         FROM cerez_yukleme y ORDER BY y.id DESC LIMIT 10`,
    ),
  );
});

/** Yukleme islemi acar; gecici klasor dondurur. */
yonlendirici.post("/", async (istek, yanit) => {
  const bilgi = await fs.statfs(YUKLEME_KOK).catch(() => null);
  if (bilgi && bilgi.bavail * bilgi.bsize < 500 * 1024 * 1024) {
    yanit.status(507).json({ hata: "sunucuda yeterli disk yok" });
    return;
  }
  await fs.mkdir(YUKLEME_KOK, { recursive: true });
  const klasor = path.join(
    YUKLEME_KOK,
    `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
  );
  await fs.mkdir(klasor, { recursive: true });
  const kim = await yukleyenKimlik(istek);
  const id = await islem(async (baglanti) => {
    const [sonuc] = await baglanti.query(
      "INSERT INTO cerez_yukleme (kullanici_id, klasor, modalite, durum) VALUES (?, ?, ?, 'yukleniyor')",
      [kim, klasor, istek.body?.modalite === 1 || istek.body?.modalite === true ? 1 : 0],
    );
    return (sonuc as { insertId: number }).insertId;
  });
  yanit.status(201).json({ id, klasor: path.basename(klasor) });
});
/** Tek parti dosya alir; yollar ayri alanda sirayla gelir. */
yonlendirici.post("/:id/parti", yukle.array("dosyalar", PARTI_DOSYA), async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "gecersiz islem" });
    return;
  }
  const kayit = await yuklemeAl(id);
  if (!kayit) {
    yanit.status(404).json({ hata: "islem yok" });
    return;
  }
  if (kayit.durum !== "yukleniyor") {
    yanit.status(409).json({ hata: "islem kapali" });
    return;
  }
  const dosyalar = (istek.files ?? []) as Express.Multer.File[];
  if (!dosyalar.length) {
    yanit.status(400).json({ hata: "dosya gelmedi" });
    return;
  }
  const toplamBayt = dosyalar.reduce((toplam, dosya) => toplam + dosya.size, 0);
  if (toplamBayt > PARTI_BAYT) {
    yanit.status(413).json({ hata: "parti cok buyuk" });
    return;
  }

  let yollar: string[] = [];
  try {
    const cozulen = JSON.parse(String((istek.body as { yollar?: string }).yollar ?? "[]")) as unknown;
    if (Array.isArray(cozulen)) yollar = cozulen.map((deger) => String(deger));
  } catch {
    yollar = [];
  }

  let yazilan = 0;
  const kim = await yukleyenKimlik(istek);
  for (let i = 0; i < dosyalar.length; i += 1) {
    const dosya = dosyalar[i];
    if (!dosya) continue;
    const goreli = guvenliYol(yollar[i] ?? dosya.originalname);
    if (!goreli) continue;
    const hedef = path.join(kayit.klasor, goreli);
    await fs.mkdir(path.dirname(hedef), { recursive: true });
    await fs.writeFile(hedef, dosya.buffer);
    await yaz(
      `INSERT IGNORE INTO cookie_dosya (yol, ad, tur, kaynak, yukleyen, yukleme_id, boyut, ozet, durum)
       VALUES (?, ?, 'json', 'yukleme', ?, ?, 0, ?, 'bekliyor')`,
      [hedef, path.basename(hedef), kim, id, createHash("sha256").update(hedef).digest("hex")],
    );
    yazilan += 1;
  }
  durum.toplam += yazilan;
  void isle(kayit.klasor).catch((hata) => console.error("[cerez] kuyruk:", hata));
  await yaz(
    "UPDATE cerez_yukleme SET dosya_sayisi = dosya_sayisi + ?, boyut = boyut + ? WHERE id = ?",
    [yazilan, toplamBayt, id],
  );
  const guncel = await tek<{ dosya_sayisi: number; boyut: number }>(
    "SELECT dosya_sayisi, boyut FROM cerez_yukleme WHERE id = ?",
    [id],
  );
  yanit.json({ alinan: yazilan, atlanan: dosyalar.length - yazilan, toplam: guncel });
});

/** Islemi kapatir, aktarimi baslatir, bitince gecici klasoru siler. */
yonlendirici.post("/:id/baslat", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "gecersiz islem" });
    return;
  }
  const kayit = await yuklemeAl(id);
  if (!kayit) {
    yanit.status(404).json({ hata: "islem yok" });
    return;
  }
  if (kayit.durum !== "yukleniyor") {
    yanit.status(409).json({ hata: "islem kapali" });
    return;
  }
  const dosyalar = await dosyalariTopla(kayit.klasor);
  if (!dosyalar.length) {
    await yaz("UPDATE cerez_yukleme SET durum = 'bitti' WHERE id = ?", [id]);
    yanit.json({ kuyruk: 0 });
    return;
  }
  const kim = await yukleyenKimlik(istek);
  for (const tam of dosyalar) {
    await yaz(
      `INSERT IGNORE INTO cookie_dosya (yol, ad, tur, kaynak, yukleyen, yukleme_id, boyut, ozet, durum)
       VALUES (?, ?, 'json', 'yukleme', ?, ?, 0, ?, 'bekliyor')`,
      [tam, path.basename(tam), kim, id, createHash("sha256").update(tam).digest("hex")],
    );
  }
  await yaz("UPDATE cerez_yukleme SET durum = 'aktarim', dosya_sayisi = ? WHERE id = ?", [
    dosyalar.length, id,
  ]);

  void (async () => {
    await isle(kayit.klasor).catch(() => {});
    await yaz("UPDATE cerez_yukleme SET durum = 'bitti' WHERE id = ?", [id]).catch(() => {});
    await fs.rm(kayit.klasor, { recursive: true, force: true }).catch(() => {});
  })();
  yanit.json({ kuyruk: dosyalar.length });
});
/** Islem ilerlemesi. */
yonlendirici.get("/:id", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "gecersiz islem" });
    return;
  }
  const satir = await tek(
    `SELECT y.id, y.durum, y.dosya_sayisi, y.boyut,
            (SELECT COUNT(*) FROM cookie_dosya d WHERE d.yukleme_id = y.id AND d.durum = 'bekliyor') AS bekleyen,
            (SELECT COUNT(*) FROM cookie_dosya d WHERE d.yukleme_id = y.id AND d.durum = 'aktarildi') AS aktarildi,
            (SELECT COUNT(*) FROM cookie_dosya d WHERE d.yukleme_id = y.id AND d.durum = 'mukerrer') AS mukerrer,
            (SELECT COUNT(*) FROM cookie_dosya d WHERE d.yukleme_id = y.id AND d.durum = 'gecersiz') AS gecersiz
       FROM cerez_yukleme y WHERE y.id = ?`,
    [id],
  );
  if (!satir) {
    yanit.status(404).json({ hata: "islem yok" });
    return;
  }
  yanit.json(satir);
});

/** Islemi iptal eder. */
yonlendirici.delete("/:id", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "gecersiz islem" });
    return;
  }
  const kayit = await yuklemeAl(id);
  if (!kayit) {
    yanit.status(404).json({ hata: "islem yok" });
    return;
  }
  await yaz("UPDATE cerez_yukleme SET durum = 'iptal' WHERE id = ?", [id]);
  if (kayit.durum === "yukleniyor") {
    await fs.rm(kayit.klasor, { recursive: true, force: true }).catch(() => {});
  }
  yanit.status(204).end();
});