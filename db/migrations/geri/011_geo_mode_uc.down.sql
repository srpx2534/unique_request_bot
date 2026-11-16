-- 011 geri: geo_mode iki değere iner.
--
-- Üç değerin tamamı national karşılığıdır; veri taşınır, sonra daraltılır.
UPDATE hit SET geo_mode = 'national' WHERE geo_mode IN ('tr_fallback', 'yabanci');
ALTER TABLE hit MODIFY COLUMN geo_mode ENUM('city','national') NOT NULL DEFAULT 'national';
