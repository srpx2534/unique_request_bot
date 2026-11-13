-- Sağlayıcı ülkesi ve IP düşüş kaydı.
--
-- ulke: havuz sırası city > TR rastgele > yabancı biçiminde kurulur.
-- geo_mode: hit'in hangi yoldan geldiğini tutar; 'city' il IP'si,
-- 'tr_fallback' il bulunamadığı için rastgele TR IP, 'yabanci' son çare.
--
-- Her iki sütun da bu dosya yazılmadan önce elle eklendiği için dosya
-- yalnızca doğrulama yapar; tekrar koşulduğunda hata vermez.

SELECT COUNT(*) AS ulke_var FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'provider' AND COLUMN_NAME = 'ulke';

SELECT COUNT(*) AS geo_mode_var FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit' AND COLUMN_NAME = 'geo_mode';

SELECT COUNT(*) AS idx_var FROM information_schema.STATISTICS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'provider' AND INDEX_NAME = 'idx_ulke';