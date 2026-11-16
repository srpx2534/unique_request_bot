-- 022 geri: günlük tavan ayarı silinir.
--
-- 023 de aynı anahtarı siliyor; geri alma sırasında ikisi de düşer.
DELETE FROM ayar WHERE anahtar = 'gunluk_tavan';
