-- Karantinaya alınan sağlayıcının ağırlığı sıfırlanırken eski değeri saklanır.
-- Böylece karantina bitince sağlayıcı sabit bir değere değil, kendi
-- ağırlığına döner.

ALTER TABLE provider ADD COLUMN weight_yedek SMALLINT UNSIGNED NULL AFTER weight;