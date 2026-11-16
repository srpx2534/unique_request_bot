-- 028 geri: dosya-yükleme bağı düşer.
--
-- Yabancı anahtar kolondan önce düşer; yoksa 1553 alınır.
ALTER TABLE cookie_dosya DROP FOREIGN KEY fk_cd_yukleme;
ALTER TABLE cookie_dosya DROP KEY idx_cd_yukleme;
ALTER TABLE cookie_dosya DROP COLUMN yukleme_id;
