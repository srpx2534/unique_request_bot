-- Kuyruk gecikme esigi.
--
-- Kuyrukta bekleyen is sayisi bu degeri asarsa queue_lag uyarisi duser.
-- Isci hizi dusunce panel bunu gormeli; sabit kod yerine ayar tutuldu.

INSERT INTO ayar (anahtar, deger) VALUES ('kuyruk_esik', '200')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);