-- Uyarıya bağlam: hangi kelime, hangi site.
--
-- ref_id genel amaçlıydı; panelde "hangi kelimede sorun var" görülemiyordu.
-- Sütunlar doğrudan tutulur, liste bunları join eder.
-- Mevcut satırlar ref_id burst kimliği varsayılarak geriye doğru çözülür.

ALTER TABLE alert ADD COLUMN keyword_id BIGINT UNSIGNED NULL AFTER ref_id;
ALTER TABLE alert ADD COLUMN site_id BIGINT UNSIGNED NULL AFTER keyword_id;
ALTER TABLE alert ADD KEY idx_kw (keyword_id);
ALTER TABLE alert ADD KEY idx_site (site_id);

UPDATE alert a
  JOIN burst b ON b.id = a.ref_id
  JOIN keyword_geo g ON g.id = b.keyword_geo_id
   SET a.keyword_id = g.keyword_id
 WHERE a.keyword_id IS NULL;

UPDATE alert a
  JOIN keyword k ON k.id = a.keyword_id
   SET a.site_id = k.site_id
 WHERE a.site_id IS NULL;