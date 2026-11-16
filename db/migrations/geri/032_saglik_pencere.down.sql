-- 032 geri: saatlik sayaç pencere damgaları düşer.
--
-- Damga düşünce pencere sıfırlama durur, sayaçlar birikir.
ALTER TABLE provider DROP COLUMN sayac_baslangic;
ALTER TABLE provider_geo DROP COLUMN sayac_baslangic;
