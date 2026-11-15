-- Bolumleme uyarisi: hit esigi asildiginda panel gormeli (44, §105).
ALTER TABLE alert MODIFY COLUMN kind
  ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata','partition') NOT NULL;