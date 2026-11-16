-- 034 geri: bayt ayı kolonu düşer.
--
-- Kolon yalnız ay devri bilgisidir; düşmesi veri kaybı değildir.
ALTER TABLE provider DROP COLUMN bytes_ay;
