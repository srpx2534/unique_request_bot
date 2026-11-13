/**
 * Günlük trafik özeti.
 *
 * `hit` satırları gün ve keyword_geo bazında `traffic_daily`'ye toplanır;
 * rapor ve v_live böylece hit tablosunu taramaz. Toplama mutlak değer yazar,
 * tekrar koşmak zararsızdır. Son iki tam gün her turda yeniden hesaplanır:
 * gece yarısını aşan burst ve bir kaçan tur kendini onarır.
 *
 * `VALUES(x)` MySQL 8.0.20'de deprecated; satır alias'ı (`AS yeni`) MySQL 8'de
 * var ama test ortamı MariaDB olduğu için ortak sözdizimi seçildi. Test ortamı
 * MySQL 8'e taşınınca alias'a geçilecek.
 *
 * Kullanım: src/server/zamanlayici.ts, tools/traffic_toparla.ts.
 */
import { yaz } from "./veritabani.js";

const GERIYE_GUN = 2;

// Gün sınırı UTC'dir (C22). Parametre metin verilir, oturum dönüşümü karışmaz.
const TOPLAMA = `
INSERT INTO traffic_daily (day, keyword_geo_id, hits_ok, hits_fail, fallback_count, bytes)
SELECT DATE(h.created_at), b.keyword_geo_id,
       SUM(h.result = 'ok'),
       SUM(h.result <> 'ok'),
       SUM(h.geo_mode <> 'city'),
       COALESCE(SUM(h.bytes), 0)
  FROM hit h
  JOIN burst b ON b.id = h.burst_id
 WHERE h.created_at >= ? AND h.created_at < DATE_ADD(?, INTERVAL 1 DAY)
 GROUP BY DATE(h.created_at), b.keyword_geo_id
ON DUPLICATE KEY UPDATE
  hits_ok = VALUES(hits_ok),
  hits_fail = VALUES(hits_fail),
  fallback_count = VALUES(fallback_count),
  bytes = VALUES(bytes)`;

/** Geriye doğru gün metni: YYYY-MM-DD, UTC. */
function gunMetni(geriGun: number): string {
  return new Date(Date.now() - geriGun * 86_400_000).toISOString().slice(0, 10);
}

/**
 * Verilen sayıda tam günü yeniden toplar.
 *
 * @param gunSayisi Kaç gün geriye gidileceği; 1 dündür, 0 bugünü de katar.
 * @returns Etkilenen satır sayısı.
 */
export async function toparla(gunSayisi = GERIYE_GUN): Promise<number> {
  let toplam = 0;
  for (let i = 1; i <= gunSayisi; i += 1) {
    const gun = gunMetni(i);
    toplam += await yaz(TOPLAMA, [gun, gun]);
  }
  return toplam;
}