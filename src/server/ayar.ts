/**
 * Ayar tablosu okuma.
 *
 * Değerler 30 saniye önbelleklenir; panelde yapılan değişiklik yarım dakika
 * içinde etkili olur ve her tikte sorgu yapılmaz.
 */
import { tek } from "./veritabani.js";

const ONBELLEK_MS = 30_000;
const onbellek = new Map<string, { deger: string; zaman: number }>();

/**
 * Ayarı okur.
 *
 * @param anahtar ayar.anahtar değeri
 * @param varsayilan değer yoksa dönecek değer
 */
export async function ayarOku(anahtar: string, varsayilan = ""): Promise<string> {
  const simdi = Date.now();
  const kayit = onbellek.get(anahtar);
  if (kayit && simdi - kayit.zaman < ONBELLEK_MS) return kayit.deger || varsayilan;

  const satir = await tek<{ deger: string }>("SELECT deger FROM ayar WHERE anahtar = ?", [anahtar]);
  const deger = (satir?.deger ?? "").trim();
  onbellek.set(anahtar, { deger, zaman: simdi });
  return deger || varsayilan;
}

/** Önbelleği boşaltır. */
export function ayarOnbellekTemizle(): void {
  onbellek.clear();
}