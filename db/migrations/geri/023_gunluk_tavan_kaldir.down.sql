-- 023 geri: günlük tavan ayarı geri gelir.
--
-- Değer 0 = tavan yok; 022 ile aynı varsayılan.
INSERT INTO ayar (anahtar, deger) VALUES ('gunluk_tavan', '0')
  ON DUPLICATE KEY UPDATE deger = deger;
