-- Cerez kullanimi.
--
-- cerez_kullan: kapaliysa hicbir hit'e cerez yuklenmez, sistem cerezsiz calisir.
-- cerez_suresiz_kullan: acikken suresi gecmis cerez de kullanilir; once aktif
-- olanlar tercih edilir.

INSERT INTO ayar (anahtar, deger) VALUES
  ('cerez_kullan', '1'),
  ('cerez_suresiz_kullan', '1')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);