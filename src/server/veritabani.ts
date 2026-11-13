/**
 * Veritabanı havuzu ve kısa sorgu yardımcıları.
 *
 * Havuz tek; bağlantı sınırı 12. `islem` çok adımlı yazmalar içindir:
 * kelime ve geo satırları ya birlikte yazılır ya da hiç yazılmaz.
 */
import mysql, { type PoolConnection } from "mysql2/promise";

export const havuz = mysql.createPool({
  host: process.env.MYSQL_HOST ?? "127.0.0.1",
  port: Number(process.env.MYSQL_PORT ?? 3306),
  user: process.env.MYSQL_USER ?? "request",
  password: process.env.MYSQL_PASSWORD ?? "",
  database: process.env.MYSQL_DATABASE ?? "unique_request_bot",
  charset: "utf8mb4",
  connectionLimit: 12,
  waitForConnections: true,
  timezone: "Z",
});

// Oturum saat dilimi UTC'ye sabitlenir: NOW() ile UTC_TIMESTAMP() ayni degeri
// verir, burst suresi negatife dusmez, saklama hesaplari kaymaz. Sunucunun
// kendi saat dilimi ne olursa olsun gecerlidir.
havuz.on("connection", (baglanti) => {
  void baglanti.query("SET time_zone = '+00:00'");
});

/** Sorgu çalıştırır ve satırları döndürür. */
export async function sorgu<T>(sql: string, parametreler: unknown[] = []): Promise<T[]> {
  const [satirlar] = await havuz.query(sql, parametreler);
  return satirlar as T[];
}

/** Tek satır döndürür, yoksa null. */
export async function tek<T>(sql: string, parametreler: unknown[] = []): Promise<T | null> {
  const satirlar = await sorgu<T>(sql, parametreler);
  return satirlar[0] ?? null;
}

/** Yazma yapar ve etkilenen satır sayısını döndürür. */
export async function yaz(sql: string, parametreler: unknown[] = []): Promise<number> {
  const [sonuc] = await havuz.query(sql, parametreler);
  return (sonuc as { affectedRows: number }).affectedRows;
}

/** Tek bağlantıda işlem çalıştırır; hata olursa geri alır. */
export async function islem<T>(govde: (baglanti: PoolConnection) => Promise<T>): Promise<T> {
  const baglanti = await havuz.getConnection();
  try {
    await baglanti.beginTransaction();
    const sonuc = await govde(baglanti);
    await baglanti.commit();
    return sonuc;
  } catch (hata) {
    await baglanti.rollback();
    throw hata;
  } finally {
    baglanti.release();
  }
}