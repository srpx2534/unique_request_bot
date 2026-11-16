-- 027 geri: yükleme tablosu ve dosya kaynak alanları düşer.
--
-- Yabancı anahtar önce düşer. Yükleme geçmişi kaybolur.
ALTER TABLE cookie_dosya DROP FOREIGN KEY fk_cd_yukleyen;
ALTER TABLE cookie_dosya DROP KEY idx_yukleyen;
ALTER TABLE cookie_dosya DROP COLUMN kaynak;
ALTER TABLE cookie_dosya DROP COLUMN yukleyen;
DROP TABLE cerez_yukleme;
