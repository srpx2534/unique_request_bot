-- 025 geri: çerez kullanım ayarları silinir.
--
-- Ayarlar yokken okuma varsayılana düşer; çerez kullanımı kapanır.
DELETE FROM ayar WHERE anahtar IN ('cerez_kullan', 'cerez_suresiz_kullan');
