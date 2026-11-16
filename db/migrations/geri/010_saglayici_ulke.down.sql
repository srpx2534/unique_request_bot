-- 010 geri: sağlayıcı ülke kolonu düşer.
--
-- Ülke bilgisi kaybolur; tr_fallback adımı sağlayıcı ayırt edemez.
ALTER TABLE provider DROP KEY idx_ulke;
ALTER TABLE provider DROP COLUMN ulke;
