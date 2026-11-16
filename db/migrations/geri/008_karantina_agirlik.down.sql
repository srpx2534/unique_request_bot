-- 008 geri: yedek ağırlık kolonu düşer.
--
-- Karantina çıkışı sabit değere döner, sağlayıcının kendi ağırlığına değil.
ALTER TABLE provider DROP COLUMN weight_yedek;
