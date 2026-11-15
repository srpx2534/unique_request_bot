-- provider.hata_sayac: ardisik basarisiz hit sayaci.
--
-- Saglayici "active" gorunup her hit'i error/timeout ile bitirdiginde havuz
-- onu secmeye devam ediyor, kelime de bosuna donuyordu. Esikte saglayici
-- kapatilir ve provider_down uyarisi duser; basarili hit sayaci sifirlar.
ALTER TABLE provider ADD COLUMN hata_sayac TINYINT UNSIGNED NOT NULL DEFAULT 0;