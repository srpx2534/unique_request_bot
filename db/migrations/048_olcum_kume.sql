-- 048: olcum kumesi, saglayici izi ve supheli SERP uyari turu.
-- Kume, son temiz olcumle ortusme denetimi icin tutulur (71).
SET NAMES utf8mb4;
ALTER TABLE position
  ADD COLUMN kume JSON NULL,
  ADD COLUMN saglayici VARCHAR(16) NULL;
ALTER TABLE alert
  MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota',
    'fallback_high','hedef_yok','failover','burst_hata','serp_hatasi') NOT NULL;