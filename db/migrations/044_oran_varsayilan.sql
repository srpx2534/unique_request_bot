-- Oran anahtarlarinin varsayilan satirlari (sozlesme 6.2).
--
-- Degerler ayar tablosunda SATIR olarak durur; arayuzu Saglayicilar ekranidir.
-- Satirlar yoksa ekran bos aciliyor, toplam 0 kaliyor ve kaydetme hic acilmiyordu.
-- Varsayilan 100/0/0'dir (EKSIKLER 23): mobil orani 0 mobil turu kapatir.
-- ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar) mevcut degeri ezmez.
INSERT INTO ayar (anahtar, deger) VALUES
  ('oran_residential', '100'),
  ('oran_mobil', '0'),
  ('oran_datacenter', '0')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);