-- 049: alert.kind birlesik liste. 048 enum'u yeniden yazarken 047'nin
-- ekledigi dugum_olu degerini dusurdu; dugum_olu uyarilari sessizce
-- yazilamaz hale gelmisti. Iki tur birlikte tanimlanir.
SET NAMES utf8mb4;
ALTER TABLE alert
  MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota',
    'fallback_high','hedef_yok','failover','burst_hata','dugum_olu',
    'serp_hatasi') NOT NULL;