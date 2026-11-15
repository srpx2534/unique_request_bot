/**
 * hit bolumleme bakimi (§6.3, §105).
 *
 * Bolumleme yalnizca `hit` 10 milyon satiri gecince kurulur; kurulduktan sonra
 * bakim turu eksik gelecek gunleri acar. Dusers isini saklama yapar, boylece
 * saklama milyonlarca satirlik DELETE yerine metadata islemine donusur.
 */
import { sorgu, yaz } from "./veritabani.js";

export const ESIK_SATIR = 10_000_000;
export const ILERI_GUN = 7;
export const SAKLAMA_GUN = 30;

const PMAX = "pmax";
const GUN_DESENI = /^p\d{8}$/;

/** Gun metni: YYYY-MM-DD. */
export function gunMetni(gun: Date): string {
  const ay = String(gun.getUTCMonth() + 1).padStart(2, "0");
  const gunu = String(gun.getUTCDate()).padStart(2, "0");
  return `${gun.getUTCFullYear()}-${ay}-${gunu}`;
}

/** Bolum adi: pYYYYMMDD. */
export function bolumAdi(gun: Date): string {
  return `p${gunMetni(gun).replaceAll("-", "")}`;
}

/** Gunu kaydirir. */
export function gunEkle(gun: Date, gunSayisi: number): Date {
  const yeni = new Date(gun.getTime());
  yeni.setUTCDate(yeni.getUTCDate() + gunSayisi);
  return yeni;
}

/** Tek gunun bolum tanimi; gun kendi ust sinirina dahildir. */
export function bolumTanimi(gun: Date): string {
  return `PARTITION ${bolumAdi(gun)} VALUES LESS THAN (TO_DAYS('${gunMetni(gun)}') + 1)`;
}

/** Eksik gelecek gunler; bugun dahil edilmez. */
export function eksikGunler(varOlan: Set<string>, bugun: Date, ileri: number): Date[] {
  const eksik: Date[] = [];
  for (let g = 1; g <= ileri; g += 1) {
    const gun = gunEkle(bugun, g);
    if (!varOlan.has(bolumAdi(gun))) eksik.push(gun);
  }
  return eksik;
}

/** Bolumleri okur; gunluk kalip kurulu mu bilgisini de verir. */
async function bolumleriOku(): Promise<{ varOlan: Set<string>; gunluk: boolean }> {
  const satirlar = await sorgu<{ ad: string }>(
    `SELECT PARTITION_NAME AS ad FROM information_schema.PARTITIONS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit'
        AND PARTITION_NAME IS NOT NULL`,
  );
  const varOlan = new Set(satirlar.map((satir) => satir.ad));
  const gunluk = [...varOlan].some((ad) => GUN_DESENI.test(ad));
  return { varOlan, gunluk };
}

/** Gunluk bolumlemeyi kurar; eski aylik kalip once kaldirilir. */
async function kur(bugun: Date): Promise<number> {
  const { varOlan, gunluk } = await bolumleriOku();
  if (varOlan.size && !gunluk) await yaz("ALTER TABLE hit REMOVE PARTITIONING");
  // Bolum kolonu benzersiz anahtarda bulunmak zorunda.
  await yaz("ALTER TABLE hit DROP PRIMARY KEY, ADD PRIMARY KEY (id, created_at)");
  const gunler: Date[] = [];
  for (let g = SAKLAMA_GUN; g >= 0; g -= 1) gunler.push(gunEkle(bugun, -g));
  for (let g = 1; g <= ILERI_GUN; g += 1) gunler.push(gunEkle(bugun, g));
  const tanimlar = gunler.map(bolumTanimi).join(", ");
  await yaz(
    `ALTER TABLE hit PARTITION BY RANGE (TO_DAYS(created_at)) (${tanimlar}, PARTITION ${PMAX} VALUES LESS THAN MAXVALUE)`,
  );
  return gunler.length;
}

/**
 * Esigi asan hit varsa bolumlemeyi kurar ya da ileri gunleri acar.
 *
 * @returns Acilan gun sayisi; esik altinda ya da islem yoksa 0.
 */
export async function bolumDenetle(): Promise<number> {
  // Tahmin once denenir; COUNT(*) 10 milyon satirda pahali.
  const tahmin = await sorgu<{ satir: number }>(
    `SELECT TABLE_ROWS AS satir FROM information_schema.TABLES
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit'`,
  );
  if (Number(tahmin[0]?.satir ?? 0) < ESIK_SATIR) return 0;
  const tam = await sorgu<{ adet: number }>("SELECT COUNT(*) AS adet FROM hit");
  const adet = Number(tam[0]?.adet ?? 0);
  if (adet < ESIK_SATIR) return 0;

  const bugun = new Date();
  const { varOlan, gunluk } = await bolumleriOku();
  let acilan = 0;
  if (!varOlan.size || !gunluk) {
    acilan = await kur(bugun);
  } else {
    const eksik = eksikGunler(varOlan, bugun, ILERI_GUN);
    if (eksik.length) {
      const tanimlar = eksik.map(bolumTanimi).join(", ");
      await yaz(
        `ALTER TABLE hit REORGANIZE PARTITION ${PMAX} INTO (${tanimlar}, PARTITION ${PMAX} VALUES LESS THAN MAXVALUE)`,
      );
      acilan = eksik.length;
    }
  }
  if (acilan) {
    await yaz("INSERT INTO alert (kind, message) VALUES ('partition', ?)", [
      `hit ${adet} satiri gecti · ${acilan} gunluk bolum acildi`,
    ]);
  }
  return acilan;
}