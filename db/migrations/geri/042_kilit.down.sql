-- 042 geri: kilit kolonları ve `kilit_cakismasi` uyarı türü düşer.
--
-- Kilit kolonları düşünce eşzamanlı iki control plane aynı satırı işleyebilir;
-- kilit süresi ayarı `ayar` tablosunda kalır.
ALTER TABLE keyword_geo DROP KEY ix_kilit;
ALTER TABLE keyword_geo DROP COLUMN kilit_dugum, DROP COLUMN kilit_at;
DELETE FROM alert WHERE kind = 'kilit_cakismasi';
ALTER TABLE alert MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata','partition','hedef_yok_durdu') NOT NULL;
