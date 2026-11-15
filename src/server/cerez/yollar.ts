/** Cerez yollari ve sabitleri. */
import { promises as fs } from "node:fs";
import path from "node:path";

export const AZAMI_BOYUT = 2 * 1024 * 1024; // dosya basi bayt
export const AZAMI_DOSYA = 300_000; // tarama tavani
export const PAKET = 200; // dosya basi islem
export const PARTI_DOSYA = 500;
export const PARTI_BAYT = 32 * 1024 * 1024;
export const KIRALAMA_DK = 10; // dakika; olu dugumun kiraladigi satir geri alinir
export const SIL_PROFIL = 400; // parti basina profil; kilit tablosunu sisirmemek icin
export const SIL_DOSYA = 1000; // parti basina dosya satiri

export const YUKLEME_KOK = process.env.CEREZ_YUKLEME_KOK
  ? path.resolve(process.env.CEREZ_YUKLEME_KOK)
  : path.join(process.cwd(), "cerez_yukleme");

/** Klasoru dogrular ve gercek yolunu dondurur. */
export async function yolDogrula(ham: string): Promise<string> {
  const tam = path.resolve(ham);
  const bilgi = await fs.stat(tam);
  if (!bilgi.isDirectory()) throw new Error("yol klasor degil");
  return fs.realpath(tam);
}

/** Klasoru ozyinelemeli tarar; yalnizca .json/.txt dosyalari. */
export async function dosyalariTopla(kokDizin: string): Promise<string[]> {
  const bulunan: string[] = [];
  const gez = async (dizin: string): Promise<void> => {
    const girdiler = await fs.readdir(dizin, { withFileTypes: true });
    for (const girdi of girdiler) {
      if (bulunan.length >= AZAMI_DOSYA) return;
      const tam = path.join(dizin, girdi.name);
      if (girdi.isDirectory()) await gez(tam);
      else if (/\.(json|txt)$/i.test(girdi.name)) bulunan.push(tam);
    }
  };
  await gez(kokDizin);
  return bulunan;
}

/** Tarayicidan gelen goreli yolu guvenli hale getirir; uzanti tutmuyorsa null. */
export function guvenliYol(ham: string): string | null {
  const parcalar = String(ham ?? "")
    .replace(/\\/g, "/")
    .split("/")
    .filter((parca) => parca !== "" && parca !== "." && parca !== "..");
  const temiz = parcalar
    .map((parca) => parca.replace(/[:*?"<>|]/g, "_").slice(0, 120))
    .filter((parca) => parca !== "");
  if (!temiz.length) return null;
  const son = temiz[temiz.length - 1];
  if (!son) return null;
  if (!/\.(json|txt)$/i.test(son)) return null;
  // Il kodu ilk klasordedir (or. "34/"); kirpma bastan degil ortadan
  // yapilir ki il eslesmesi sessizce kaybolmasin.
  const kirpik = temiz.length > 6 ? [temiz[0], ...temiz.slice(-5)] : temiz;
  return kirpik.join("/").slice(0, 400);
}