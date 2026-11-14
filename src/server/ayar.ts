/**
 * Ayar tablosu okuma.
 *
 * Değerler 30 saniye önbelleklenir; panelde yapılan değişiklik yarım dakika
 * içinde etkili olur ve her tikte sorgu yapılmaz.
 */
import { tek } from "./veritabani.js";

// Sözleşme §3: değişiklik en geç bir dakika içinde etkili olur; worker ile aynı.
const ONBELLEK_MS = 60_000;
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

// SERP anahtar sırası sözleşmededir (§8): birincil, sonra yedekler.
const SERP_ANAHTAR_SIRASI = ["serp_decodo", "serp_serper", "serp_searchapi"];

/**
 * Aktif SERP anahtarını verir.
 *
 * Birincil boşsa yedek denenir; tek anahtar bitince ölçüm durmaz.
 *
 * @returns anahtar ve sağlayıcı adı; hiçbiri yoksa boş dizeler
 */
export async function serpSecim(): Promise<{ saglayici: string; anahtar: string }> {
  for (const ad of SERP_ANAHTAR_SIRASI) {
    const deger = (await ayarOku(ad)).trim();
    if (deger) return { saglayici: ad.replace("serp_", ""), anahtar: deger };
  }
  return { saglayici: "", anahtar: "" };
}