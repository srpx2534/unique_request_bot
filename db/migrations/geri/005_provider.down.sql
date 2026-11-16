-- 005 geri: seed sağlayıcı satırları silinir.
--
-- Kimlikler 001-007 sabittir; silme provider_geo ve profile satırlarını da
-- yabancı anahtar üzerinden götürür.
DELETE FROM provider WHERE id BETWEEN 1 AND 7;
