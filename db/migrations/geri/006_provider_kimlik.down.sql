-- 006 geri: sağlayıcı kimlik kolonları ve ayar tablosu düşer.
--
-- Ayar tablosu düşünce oranlar ve eşikler kaybolur; kod varsayılanı kullanılır.
ALTER TABLE provider DROP COLUMN gateway;
ALTER TABLE provider DROP COLUMN kullanici;
ALTER TABLE provider DROP COLUMN sifre;
DROP TABLE IF EXISTS ayar;
