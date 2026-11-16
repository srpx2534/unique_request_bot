-- 045 geri: hit.tur kolonu ve indeksi düşer.
--
-- İndeks kolondan önce düşer; kolon indeksten önce düşseydi MariaDB
-- indeksi de kendiliğinden atardı ama ad açık kalsın.
-- Kolon NULL olabildiği için veri kaybı yalnız tur bilgisidir.
ALTER TABLE hit DROP KEY idx_tur_day;
ALTER TABLE hit DROP COLUMN tur;
