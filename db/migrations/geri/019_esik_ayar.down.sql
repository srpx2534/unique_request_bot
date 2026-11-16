-- 019 geri: captcha eşiği ve günlük tavan silinir.
--
-- İkisi de 019 ile gelmişti; eşik yokken kod varsayılanı kullanılır.
DELETE FROM ayar WHERE anahtar IN ('esik_captcha', 'gunluk_tavan');
