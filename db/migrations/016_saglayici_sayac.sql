-- Saglayici geneli hit sayaci.
--
-- Ulusal kelimede il kodu olmadigi icin provider_geo satiri yazilamiyordu ve
-- devre kesici ulusal trafigi hic gormuyordu. Sayaclar saglayici satirina
-- tasindi; provider_geo yalnizca il hedefli hit'lerde kullanilmaya devam eder.
-- Sayaclar karantina acilisinda sifirlanir.

ALTER TABLE provider
  ADD COLUMN hits_1h    INT UNSIGNED NOT NULL DEFAULT 0 AFTER captcha_pct,
  ADD COLUMN captcha_1h INT UNSIGNED NOT NULL DEFAULT 0 AFTER hits_1h;