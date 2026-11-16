-- 043 geri: provider.id yeniden AUTO_INCREMENT olmaktan çıkar.
--
-- Kimlikler korunur; yalnız yeni eklemelerde kimlik dışarıdan yazılmak
-- zorunda kalır. AUTO_INCREMENT sayacı kolonla birlikte düşer.
ALTER TABLE provider MODIFY COLUMN id SMALLINT UNSIGNED NOT NULL;
