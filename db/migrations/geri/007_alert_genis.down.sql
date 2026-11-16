-- 007 geri: uyarı türleri 001 kümesine iner, v_alert düşer.
--
-- Yeni türlerin satırları silinir, yoksa daraltma 1265 verir.
DELETE FROM alert WHERE kind IN ('hedef_yok', 'failover', 'burst_hata');
ALTER TABLE alert MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high') NOT NULL;
DROP VIEW IF EXISTS v_alert;
