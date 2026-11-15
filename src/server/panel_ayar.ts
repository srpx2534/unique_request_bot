/** Panel ayar uclari (§23.2). */
import { Router } from "express";
import { z } from "zod";
import { dogrula } from "./dogrula.js";
import { denetim } from "./denetim.js";
import { sorgu, tek, yaz } from "./veritabani.js";
import { GIZLI_AYARLAR, ayarMaskele } from "./panel_ortak.js";

export const yonlendirici = Router();
yonlendirici.get("/", async (_istek, yanit) => {
  yanit.json(ayarMaskele(await sorgu("SELECT anahtar, deger FROM ayar ORDER BY anahtar")));
});

/** Bir SERP anahtarÄ±nÄ± tek sorguyla dener. YalnÄ±zca Decodo desteklenir. */
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
    yanit.status(400).json({ hata: "anahtar tanÄ±mlÄ± deÄŸil" });
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
yonlendirici.patch("/", async (istek, yanit) => {
  const govde = dogrula(z.record(z.string().max(255)), istek.body, yanit);
  if (!govde) return;

  const ciftler = Object.entries(govde);
  if (ciftler.length === 0) {
    yanit.status(400).json({ hata: "gÃ¼ncellenecek ayar yok" });
    return;
  }
  for (const [anahtar, deger] of ciftler) {
    // Maskeli deÄŸer geri gÃ¶nderildiyse gerÃ§ek deÄŸer korunur.
    // Maske tam kalÄ±ptÄ±r; gerÃ§ek anahtar bu Ã¶nekle baÅŸlasa bile uzunluÄŸu tutmaz.
    if (GIZLI_AYARLAR.has(anahtar) && /^â€¢â€¢â€¢â€¢.{4}$/.test(deger)) continue;
    // Oranlar saÄŸlayÄ±cÄ±lar ekranÄ±ndan yÃ¶netilir; genel ayar ekranÄ± da onlarÄ±
    // gÃ¶nderdiÄŸi iÃ§in iki uÃ§ birbirinin deÄŸerini eziyordu.
    if (anahtar.startsWith("oran_")) continue;
    await yaz(
      "INSERT INTO ayar (anahtar, deger) VALUES (?, ?) ON DUPLICATE KEY UPDATE deger = VALUES(deger)",
      [anahtar, deger],
    );
  }
  await denetim(istek, "ayar-guncelle", "ayar", null);
  yanit.json(ayarMaskele(await sorgu("SELECT anahtar, deger FROM ayar ORDER BY anahtar")));
});

