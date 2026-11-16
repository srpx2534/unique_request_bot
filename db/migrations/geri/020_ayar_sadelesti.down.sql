-- 020 geri: sadeleştirmede silinen iki ayar geri gelir.
--
-- Değerler 006 ve 019 varsayılanlarıdır.
INSERT INTO ayar (anahtar, deger) VALUES ('mobil_pencere_sn', '8'), ('gunluk_tavan', '0')
  ON DUPLICATE KEY UPDATE deger = deger;
