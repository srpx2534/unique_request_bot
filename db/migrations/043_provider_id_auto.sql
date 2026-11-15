-- provider.id AUTO_INCREMENT olur (panel sağlayıcı ekleme, §8).
--
-- Kimlik şimdiye kadar dışarıdan yazılıyordu. Panel INSERT'i kimlik
-- göndermediği için strict modda 1364 (Field 'id' doesn't have a default
-- value), gevşek modda id = 0 yazılıp ikinci eklemede ER_DUP_ENTRY alınıyordu.
--
-- Açık kimlik yazan araçlar (005_provider.sql, tools/proxy_ice.py,
-- tools/saglik_dene.py) etkilenmez: açık değer sayacı kendiliğinden ileri
-- taşır, dolayısıyla çakışma doğmaz.
ALTER TABLE provider MODIFY COLUMN id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT;

-- Sayaç en büyük kimliğin ardından başlar (alt değer verilirse InnoDB yukarı çeker).
ALTER TABLE provider AUTO_INCREMENT = 1;