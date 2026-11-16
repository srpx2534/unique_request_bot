-- 041 geri: çerez canlılık alanları düşer.
--
-- İndeks kolonlardan önce düşer. Ölçüm sonucu kaybolur; bir sonraki ölçüm
-- turu alanlar geri gelene kadar çalışmaz.
ALTER TABLE cookie_profil DROP KEY idx_cp_canli;
ALTER TABLE cookie_profil DROP COLUMN canli, DROP COLUMN son_kontrol_at, DROP COLUMN olcum_proxy;
