-- Artik kullanilmayan iki ayar.
--
-- mobil_pencere_sn: burst motoru degeri sabit tutuyor, tablo degeri okunmuyor.
-- gunluk_tavan: kelime bazli hacim alani zaten tavani tasiyor (isci hacim
-- dolunca kelimeyi durduruyor).

DELETE FROM ayar WHERE anahtar IN ('mobil_pencere_sn', 'gunluk_tavan');