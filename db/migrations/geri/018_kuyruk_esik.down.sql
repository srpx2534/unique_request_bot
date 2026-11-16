-- 018 geri: kuyruk eşiği silinir.
--
-- Eşik yokken kuyruk uyarısı üretilmez.
DELETE FROM ayar WHERE anahtar = 'kuyruk_esik';
