-- 016 geri: sağlayıcı saatlik sayaçları düşer.
--
-- Sayaçlar düşünce karantina kararı oran yerine yalnız captcha_pct taşır.
ALTER TABLE provider DROP COLUMN hits_1h;
ALTER TABLE provider DROP COLUMN captcha_1h;
