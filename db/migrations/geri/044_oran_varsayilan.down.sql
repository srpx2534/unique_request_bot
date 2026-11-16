-- 044 geri: oran varsayılan satırları silinir.
--
-- Üç anahtar tek işlemde gider. Satırlar sonradan panelden değiştirilmişse
-- silme o değerleri de götürür; 044 geri alınırken oranların varsayılana
-- dönmesi beklenen davranıştır.
DELETE FROM ayar WHERE anahtar IN ('oran_residential', 'oran_mobil', 'oran_datacenter');
