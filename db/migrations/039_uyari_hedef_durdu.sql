-- Hedef yok nedeniyle durdurma, "bulunamadi" uyarisindan ayrilir.
-- Deger ENUM sonuna eklenir; mevcut kayitlarin indeksi degismez.
ALTER TABLE alert MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata','partition','hedef_yok_durdu') NOT NULL;