/**
 * İş atılacak düğümü seçer.
 *
 * Kayıtlı ve aktif düğüm varsa yalnızca onlar arasından, en az yüklü olanı
 * seçer; 45 saniyeden eski kalbi olan sessiz düğüm atlanır (C37). Kayıt
 * defteri boşsa yerel düğüm varsayılır, böylece tek makine kurulumu bozulmaz.
 * Durdurulan düğüm hiç seçilmez; iş diğerine kayar (C38).
 *
 * Kullanım: src/server/isci.ts, src/server/dugum_sec.test.ts.
 */
import { tek } from "./veritabani.js";

/**
 * İş atılacak düğüm adresini verir.
 *
 * @returns http://ip:port ya da uygun düğüm yoksa null.
 */
export async function dugumSec(): Promise<string | null> {
  const satir = await tek<{ ip: string }>(
    `SELECT ip FROM dugum
      WHERE durum = 'aktif' AND son_kalp_at > UTC_TIMESTAMP(3) - INTERVAL 45 SECOND
      ORDER BY yuk ASC, id ASC LIMIT 1`,
  );
  if (satir) return `http://${satir.ip}:${process.env.WORKER_PORT ?? 8081}`;

  const kayitli = await tek<{ sayi: number }>("SELECT COUNT(*) AS sayi FROM dugum");
  if ((kayitli?.sayi ?? 0) === 0) {
    return `http://127.0.0.1:${process.env.WORKER_PORT ?? 8081}`;
  }
  return null;
}