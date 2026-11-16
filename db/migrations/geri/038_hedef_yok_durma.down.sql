-- 038 geri: hedef yok sayacı ve eşiği kalkar.
--
-- Sayaç kelime satırındadır; düşmesi veri kaybı değildir, durdurma kararı
-- artık üst üste deneme sayılmadan verilir.
ALTER TABLE keyword DROP COLUMN hedef_yok_sayac;
DELETE FROM ayar WHERE anahtar = 'hedef_yok_durma';
