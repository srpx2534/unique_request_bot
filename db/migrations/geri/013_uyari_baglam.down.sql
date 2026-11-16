-- 013 geri: uyarı bağlam kolonları düşer.
--
-- Uyarı hangi site ve kelimeden çıktığını kaybeder; satırlar kalır.
ALTER TABLE alert DROP KEY idx_kw;
ALTER TABLE alert DROP KEY idx_site;
ALTER TABLE alert DROP COLUMN keyword_id;
ALTER TABLE alert DROP COLUMN site_id;
