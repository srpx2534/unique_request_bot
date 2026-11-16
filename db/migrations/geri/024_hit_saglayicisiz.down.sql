-- 024 geri: hit.provider_id yeniden zorunlu olur.
--
-- Sağlayıcısız hit satırları NULL taşıdığı için daraltmadan önce 0 yazılır;
-- hit tablosunda FK yok, 0 geçerlidir.
UPDATE hit SET provider_id = 0 WHERE provider_id IS NULL;
ALTER TABLE hit MODIFY COLUMN provider_id SMALLINT UNSIGNED NOT NULL;
