-- 029 geri: kullanım çifti tablosu ve ülke kolonu düşer.
--
-- Tablo çocuk olduğu için önce o gider; sonra 029 un eklediği
-- indeks ve kolonlar. `tukendi` durumu geri gelmez, 029 onu hazir yapti.
DROP TABLE cookie_kullanim;
ALTER TABLE cookie_profil DROP KEY idx_cp_secim;
ALTER TABLE cookie_profil DROP COLUMN ulke;
ALTER TABLE cookie_dosya DROP KEY idx_cd_durum;
ALTER TABLE cookie_dosya DROP COLUMN isleniyor_at;
