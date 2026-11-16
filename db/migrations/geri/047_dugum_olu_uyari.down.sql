-- 047 geri: `dugum_olu` uyari turu duser.
--
-- Tur silinmeden daraltma 1265 verir; once satirlar gider.
DELETE FROM alert WHERE kind = 'dugum_olu';
ALTER TABLE alert MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata','partition','hedef_yok_durdu','kilit_cakismasi') NOT NULL;
