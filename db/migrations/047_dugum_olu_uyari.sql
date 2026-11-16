-- Dugum olu uyarisi: kalbi kesilen dugum panelde gorunur olsun (E3).
--
-- Dagitici zaten 45 saniyeden eski kalpli dugume is vermiyor; eksik olan
-- panelin gormesiydi. Tur ENUM sonuna eklenir, mevcut kayitlarin indeksi
-- degismez. Uyari dugum basina 30 dakika sessizdir.
ALTER TABLE alert MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata','partition','hedef_yok_durdu','kilit_cakismasi','dugum_olu') NOT NULL;
