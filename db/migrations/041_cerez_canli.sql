-- Cerez canliligi: NULL olculmedi, 1 engellenmiyor, 0 engelleniyor.
-- Lyon cerez silinmez, havuz siralamasinda sona duser.
ALTER TABLE cookie_profil
  ADD COLUMN canli TINYINT(1) NULL,
  ADD COLUMN son_kontrol_at DATETIME(3) NULL,
  ADD COLUMN olcum_proxy TINYINT(1) NOT NULL DEFAULT 0,
  ADD KEY idx_cp_canli (durum, canli);