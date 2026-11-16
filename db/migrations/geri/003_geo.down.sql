-- 003 geri: 81 il seed satırı silinir.
--
-- `geo`ya bağlı satırlar önce boşaltılır: provider_geo ve keyword_geo silinir,
-- keyword.home_geo NULL lanır. Çerez tabloları bu aşamada zaten düşmüştür.
DELETE FROM provider_geo;
DELETE FROM keyword_geo;
UPDATE keyword SET home_geo = NULL;
DELETE FROM geo;
