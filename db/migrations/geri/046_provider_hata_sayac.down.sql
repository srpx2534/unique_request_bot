-- 046 geri: hata_sayac kolonu düşer.
--
-- Kolon yalnız sayaç taşır; düşmesi veri kaybı değildir, sayaç sıfırdan
-- başlar. Sağlayıcı kapatma kararı sayaca bağlı olduğu için 046 geri
-- alındığında art arda hata koruması da devre dışı kalır.
ALTER TABLE provider DROP COLUMN hata_sayac;
