/**
 * Bağlı kayıtlarla birlikte silme.
 *
 * `hit` tablosunda FK yoktur (hacim yüksek, §6). Bu yüzden bağlı kayıtlar
 * burada açıkça, en dipten yukarı doğru silinir: önce hit, sonra burst,
 * kampanya, kelime-geo, konum, uyarı ve kelime. Hepsi tek işlemde koşar;
 * yarıda kalan silme bırakmaz.
 *
 * Sağlayıcı silmede ölçüm geçmişi korunur: `hit.provider_id` NULL'a çekilir,
 * sağlayıcıya bağlı profil ve il sayaçları silinir; çerez dosyaları kalır.
 */
import type { PoolConnection } from "mysql2/promise";

/** Kelimeye bağlı her şeyi siler. */
export async function kelimeSil(baglanti: PoolConnection, keywordId: number): Promise<void> {
  const q = (sql: string) => baglanti.query(sql, [keywordId]);

  await q(
    `DELETE h FROM hit h
       JOIN burst b ON b.id = h.burst_id
       JOIN keyword_geo kg ON kg.id = b.keyword_geo_id
      WHERE kg.keyword_id = ?`,
  );
  await q(
    `DELETE b FROM burst b
       JOIN keyword_geo kg ON kg.id = b.keyword_geo_id
      WHERE kg.keyword_id = ?`,
  );
  await q(
    `DELETE t FROM traffic_daily t
       JOIN keyword_geo kg ON kg.id = t.keyword_geo_id
      WHERE kg.keyword_id = ?`,
  );
  await q("DELETE FROM position WHERE keyword_id = ?");
  await q("DELETE FROM campaign WHERE keyword_id = ?");
  await q("DELETE FROM cookie_kullanim WHERE keyword_id = ?");
  await q("DELETE FROM alert WHERE keyword_id = ?");
  await q("DELETE FROM keyword_geo WHERE keyword_id = ?");
  await q("DELETE FROM keyword WHERE id = ?");
}

/** Siteye bağlı bütün kelimeleri ve site kaydını siler. */
export async function siteSil(baglanti: PoolConnection, siteId: number): Promise<void> {
  const q = (sql: string) => baglanti.query(sql, [siteId]);
  // Iki yer tutuculu sorgular icin: site kimligi iki kez baglanir.
  const q2 = (sql: string) => baglanti.query(sql, [siteId, siteId]);

  await q(
    `DELETE h FROM hit h
       JOIN burst b ON b.id = h.burst_id
       JOIN keyword_geo kg ON kg.id = b.keyword_geo_id
       JOIN keyword k ON k.id = kg.keyword_id
      WHERE k.site_id = ?`,
  );
  await q(
    `DELETE b FROM burst b
       JOIN keyword_geo kg ON kg.id = b.keyword_geo_id
       JOIN keyword k ON k.id = kg.keyword_id
      WHERE k.site_id = ?`,
  );
  await q(
    `DELETE t FROM traffic_daily t
       JOIN keyword_geo kg ON kg.id = t.keyword_geo_id
       JOIN keyword k ON k.id = kg.keyword_id
      WHERE k.site_id = ?`,
  );
  await q(
    `DELETE p FROM position p
       JOIN keyword k ON k.id = p.keyword_id
      WHERE k.site_id = ?`,
  );
  await q(
    `DELETE c FROM campaign c
       JOIN keyword k ON k.id = c.keyword_id
      WHERE k.site_id = ?`,
  );
  await q2(
    `DELETE ck FROM cookie_kullanim ck
      WHERE ck.site_id = ?
         OR ck.keyword_id IN (SELECT id FROM keyword WHERE site_id = ?)`,
  );
  await q2(
    `DELETE a FROM alert a
      WHERE a.site_id = ?
         OR a.keyword_id IN (SELECT id FROM keyword WHERE site_id = ?)`,
  );
  await q(
    `DELETE kg FROM keyword_geo kg
       JOIN keyword k ON k.id = kg.keyword_id
      WHERE k.site_id = ?`,
  );
  await q("DELETE FROM keyword WHERE site_id = ?");
  await q("DELETE FROM site WHERE id = ?");
}

/** Sağlayıcıyı siler; ölçüm geçmişi `provider_id = NULL` ile korunur. */
export async function saglayiciSil(baglanti: PoolConnection, saglayiciId: number): Promise<void> {
  const q = (sql: string) => baglanti.query(sql, [saglayiciId]);

  // Geçmiş hit'ler kalır, yalnız sağlayıcı bağı kopar. `profile` ve
  // `provider_geo` sağlayıcıya FK ile bağlıdır, ikisi silinir. `cookie` ve
  // `cookie_profil` sağlayıcıya değil dosyaya bağlı olduğu için dokunulmaz.
  await q("UPDATE hit SET provider_id = NULL WHERE provider_id = ?");
  // Profiller silinmeden once hit'teki profil bagi da koparilir; yoksa
  // hit satirlari silinmis profil kimligi tasir (hit.profile_id FK'siz).
  await q(
    `UPDATE hit h JOIN profile p ON p.id = h.profile_id
        SET h.profile_id = NULL
      WHERE p.provider_id = ?`,
  );
  await q("DELETE FROM profile WHERE provider_id = ?");
  await q("DELETE FROM provider_geo WHERE provider_id = ?");
  await q("DELETE FROM provider WHERE id = ?");
}
