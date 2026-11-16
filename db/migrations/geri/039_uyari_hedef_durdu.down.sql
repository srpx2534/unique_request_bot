-- 039 geri: `hedef_yok_durdu` uyarı türü düşer.
--
-- Tür ENUM sonundan çıkarıldığı için kalan türlerin indeksi değişmez.
-- Önce bu türün satırları silinir, yoksa daraltma 1265 verir.
DELETE FROM alert WHERE kind = 'hedef_yok_durdu';
ALTER TABLE alert MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata','partition') NOT NULL;
