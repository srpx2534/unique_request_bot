-- Oran anahtarlarinin varsayilan satirlari (sozlesme 6.2).
--
-- Degerler ayar tablosunda SATIR olarak durur; arayuzu Saglayicilar ekranidir.
-- Satirlar yoksa ekran bos aciliyor, toplam 0 kaliyor ve kaydetme hic acilmiyordu.
-- ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar) mevcut degeri ezmez.
INSERT INTO ayar (anahtar, deger) VALUES
  ('oran_residential', '60'),
  ('oran_mobil', '30'),
  ('oran_datacenter', '10')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);