-- Esik ayarlari.
--
-- CAPTCHA esigi ve gunluk tavan panelden duzenlenebilir olmali; sabit kod
-- deger degistikce dagitim gerektirir. Ikisi de calisma aninda okunur.

INSERT INTO ayar (anahtar, deger) VALUES
  ('esik_captcha', '20'),
  ('gunluk_tavan', '0')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);