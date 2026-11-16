-- 035 geri: `partition` uyarı türü düşer.
--
-- Tür silinmeden daraltma 1265 verir; önce satırlar gider.
DELETE FROM alert WHERE kind = 'partition';
ALTER TABLE alert MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata') NOT NULL;
