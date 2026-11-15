/** Panel ayar uclari (§23.2). */
import { Router } from "express";
import { z } from "zod";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { islem, sorgu, tek, yaz } from "./veritabani.js";
import { GIZLI_AYARLAR, ayarMaskele } from "./panel_ortak.js";

export const yonlendirici = Router();
yonlendirici.get("/", async (_istek, yanit) => {
  yanit.json(ayarMaskele(await sorgu("SELECT anahtar, deger FROM ayar ORDER BY anahtar")));
});

/** Bir SERP anahtarını tek sorguyla dener. Yalnızca Decodo desteklenir. */
yonlendirici.post("/serp-dene", async (istek, yanit) => {
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
/** Tür oranları: değerler `ayar` tablosunda satır olarak durur (§6.2). */
const oranSemasi = z.object({
  oran_residential: z.coerce.number().int().min(0).max(100),
  oran_mobil: z.coerce.number().int().min(0).max(100),
  oran_datacenter: z.coerce.number().int().min(0).max(100),
});

/**
 * Üç oranı birlikte yazar.
 *
 * Arayüz Sağlayıcılar ekranındadır ama saklama yeri `ayar` tablosudur; genel
 * PATCH / içindeki `oran_` atlaması bu uç yüzünden olduğu gibi kalır. Üçü tek
 * işlemde yazılır ki toplam 100 kuralı yarım kalmış bir yazmayla bozulmasın.
 */
yonlendirici.patch("/oran", async (istek, yanit) => {
  const govde = dogrula(oranSemasi, istek.body, yanit);
  if (!govde) return;

  const toplam = govde.oran_residential + govde.oran_mobil + govde.oran_datacenter;
  if (toplam !== 100) {
    yanit.status(400).json({ hata: `oranların toplamı 100 olmalı, şu an ${toplam}`, alan: "oran" });
    return;
  }

  // Anahtar birincil anahtar olduğu için upsert yeter; satır yoksa doğar.
  await islem(async (baglanti) => {
    for (const [anahtar, deger] of Object.entries(govde)) {
      await baglanti.query(
        "INSERT INTO ayar (anahtar, deger) VALUES (?, ?) ON DUPLICATE KEY UPDATE deger = VALUES(deger)",
        [anahtar, String(deger)],
      );
    }
  });
  await denetim(istek, "oran-guncelle", "ayar", null);
  yanit.json(ayarMaskele(await sorgu("SELECT anahtar, deger FROM ayar ORDER BY anahtar")));
});

yonlendirici.patch("/", async (istek, yanit) => {
  const govde = dogrula(z.record(z.string().max(255)), istek.body, yanit);
  if (!govde) return;

  const ciftler = Object.entries(govde);
  if (ciftler.length === 0) {
    yanit.status(400).json({ hata: "güncellenecek ayar yok" });
    return;
  }
  for (const [anahtar, deger] of ciftler) {
    // Maskeli değer geri gönderildiyse gerçek değer korunur.
    // Maske tam kalıptır; gerçek anahtar bu önekle başlasa bile uzunluğu tutmaz.
    if (GIZLI_AYARLAR.has(anahtar) && /^••••.{4}$/.test(deger)) continue;
    // Oranlar sağlayıcılar ekranından yönetilir; genel ayar ekranı da onları
    // gönderdiği için iki uç birbirinin değerini eziyordu.
    if (anahtar.startsWith("oran_")) continue;
    await yaz(
      "INSERT INTO ayar (anahtar, deger) VALUES (?, ?) ON DUPLICATE KEY UPDATE deger = VALUES(deger)",
      [anahtar, deger],
    );
  }
  await denetim(istek, "ayar-guncelle", "ayar", null);
  yanit.json(ayarMaskele(await sorgu("SELECT anahtar, deger FROM ayar ORDER BY anahtar")));
});

