-- 049 geri: serp_hatasi kalkar, dugum_olu korunur.
-- Geri almadan once serp_hatasi satirlari silinmeli.
SET NAMES utf8mb4;
ALTER TABLE alert
  MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota',
    'fallback_high','hedef_yok','failover','burst_hata','dugum_olu') NOT NULL;