-- Gunluk tavan geri geldi.
--
-- Kelime hacmi bos birakilirsa hicbir ust sinir kalmiyordu; bu anahtar kelime
-- basina gunluk hit tavanini tutar. 0 = tavan yok.

INSERT INTO ayar (anahtar, deger) VALUES ('gunluk_tavan', '0')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);