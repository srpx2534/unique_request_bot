-- SERP anahtarları ve ölçüm aralığı artık .env yerine ayar tablosunda.
-- Değerler boş başlar; Ayarlar ekranından doldurulur. Mevcut değer korunur.
-- 0 ölçüm aralığı = yalnızca cooldown sırası geçerli.

INSERT INTO ayar (anahtar, deger) VALUES
  ('serp_decodo',      ''),
  ('serp_serper',      ''),
  ('serp_searchapi',   ''),
  ('olcum_araligi_dk', '0')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);