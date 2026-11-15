/** Cerez defteri silme uclari. */
import { promises as fs } from "node:fs";
import { Router } from "express";
import { sorgu, yaz } from "../veritabani.js";
import { durum } from "./ortak.js";
import { SIL_DOSYA, SIL_PROFIL, YUKLEME_KOK } from "./yollar.js";

export const yonlendirici = Router();

/**
 * Verilen secimle gelen profilleri ve cerezlerini parti parti siler.
 *
 * Tek ifadede milyonlarca satir silmek kilit tablosunu tasiyor (1206);
 * bu yuzden cocuk satir once ve kucuk partilerle silinir, her adim ayri
 * islemde commit olur.
 */
async function profilPartiliSil(secim: string, deger: unknown[]): Promise<number> {
  let silinen = 0;
  for (;;) {
    const idler = await sorgu<{ id: number }>(`${secim} LIMIT ${SIL_PROFIL}`, deger);
    if (!idler.length) break;
    const liste = idler.map((satir) => satir.id);
    const yer = liste.map(() => "?").join(",");
    await yaz(`DELETE FROM cookie WHERE profil_id IN (${yer})`, liste);
    await yaz(`DELETE FROM cookie_profil WHERE id IN (${yer})`, liste);
    silinen += liste.length;
    if (idler.length < SIL_PROFIL) break;
  }
  return silinen;
}

/** Kosula uyan dosya satirlarini parti parti siler. */
async function dosyaPartiliSil(kosul: string, deger: unknown[]): Promise<number> {
  let silinen = 0;
  for (;;) {
    const sonuc = await yaz(`DELETE FROM cookie_dosya WHERE ${kosul} LIMIT ${SIL_DOSYA}`, deger);
    silinen += sonuc;
    if (sonuc < SIL_DOSYA) break;
  }
  return silinen;
}

/** Kullanim ciftlerini parti parti siler; yalnizca tam temizlikte cagrilir. */
async function kullanimPartiliSil(): Promise<void> {
  for (;;) {
    const sonuc = await yaz(`DELETE FROM cookie_kullanim LIMIT ${SIL_DOSYA}`);
    if (sonuc < SIL_DOSYA) break;
  }
}

/** Hatali dosya kayitlarini ve onlarin profillerini siler. */
yonlendirici.delete("/hatali", async (_istek, yanit) => {
  // Cascade tek ifadede tum agaci silip kilit tablosunu dolduruyor;
  // once profil ve cerezler partili gider, dosya satiri en sonda kalir.
  await profilPartiliSil(
    "SELECT p.id FROM cookie_profil p JOIN cookie_dosya d ON d.id = p.dosya_id WHERE d.durum = 'gecersiz' ORDER BY p.id",
    [],
  );
  const silinen = await dosyaPartiliSil("durum = 'gecersiz'", []);
  yanit.json({ silinen });
});

/** Tum cerez defterini siler. */
yonlendirici.delete("/", async (_istek, yanit) => {
  await profilPartiliSil("SELECT id FROM cookie_profil ORDER BY id", []);
  await dosyaPartiliSil("1 = 1", []);
  await kullanimPartiliSil();
  for (;;) {
    const sonuc = await yaz(`DELETE FROM cerez_yukleme LIMIT ${SIL_DOSYA}`);
    if (sonuc < SIL_DOSYA) break;
  }
  // Yukleme defteri ve gecici klasorler de gider.
  await fs.rm(YUKLEME_KOK, { recursive: true, force: true });
  durum.toplam = 0;
  durum.islenen = 0;
  durum.mukerrer = 0;
  durum.hatali = 0;
  yanit.status(204).end();
});