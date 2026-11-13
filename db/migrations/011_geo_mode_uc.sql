-- geo_mode üç değere çıkarılır.
--
-- city        : il IP'si kullanıldı
-- tr_fallback : il IP'si yoktu, rastgele TR IP kullanıldı
-- yabanci     : TR IP de yoktu, yabancı IP kullanıldı (son çare)
--
-- Eski 'national' değeri tr_fallback karşılığıdır, veri taşınır.

UPDATE hit SET geo_mode = 'tr_fallback' WHERE geo_mode = 'national';

ALTER TABLE hit MODIFY COLUMN geo_mode ENUM('city','tr_fallback','yabanci') NOT NULL DEFAULT 'yabanci';