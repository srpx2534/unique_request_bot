-- hit.tur: bir hit'in hangi saglayici turunden ciktigi (residential/mobile/datacenter).
--
-- Modalite bugune kadar yalniz profil seciminde kullaniliyor, hicbir yere
-- yazilmiyordu; mobil yolun calistigi kayittan dogrulanamiyordu (EKSIKLER 27).
-- NULL olabilir: saglayicisiz (dogrudan baglanti) hit'te tur yoktur.
ALTER TABLE hit ADD COLUMN tur ENUM('residential','mobile','datacenter') NULL AFTER geo_mode;
ALTER TABLE hit ADD KEY idx_tur_day (tur, created_at);