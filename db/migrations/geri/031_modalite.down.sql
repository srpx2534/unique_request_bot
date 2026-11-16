-- 031 geri: modalite alanları düşer.
--
-- İndeks kolonla birlikte gider; önce indeks.
ALTER TABLE keyword DROP COLUMN mobil;
ALTER TABLE cookie_profil DROP KEY idx_cp_mobil;
ALTER TABLE cookie_profil DROP COLUMN mobil;
ALTER TABLE cerez_yukleme DROP COLUMN modalite;
