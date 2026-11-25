-- 048 geri: kume/saglayici kolonlari duser, serp_hatasi turu kalkar.
-- Geri almadan once serp_hatasi satirlari silinmeli ya da tur korunmali.
SET NAMES utf8mb4;
ALTER TABLE position DROP COLUMN kume, DROP COLUMN saglayici;
ALTER TABLE alert
  MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota',
    'fallback_high','hedef_yok','failover','burst_hata') NOT NULL;