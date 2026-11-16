-- 021 geri: `cooldown` durumu geri gelir.
--
-- Beklemedeki satırlar pending kalır; cooldown verisi geri gelmez.
ALTER TABLE keyword_geo MODIFY COLUMN state ENUM('pending','running','cooldown') NOT NULL DEFAULT 'pending';
