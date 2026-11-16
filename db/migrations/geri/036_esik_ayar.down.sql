-- 036 geri: eşik varsayılan satırları silinir.
--
-- Satırlar panelden değiştirilmişse silme o değerleri de götürür; 036 geri
-- alınırken eşiklerin koddaki varsayılana dönmesi beklenen davranıştır.
DELETE FROM ayar WHERE anahtar IN ('esik_geo', 'asgari_ornek');
