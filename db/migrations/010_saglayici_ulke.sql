-- Saglayici ulkesi ve il ulke indeksi.
--
-- ulke: havuz sirasi city > TR rastgele > yabanci biciminde kurulur; TR
-- disi saglayici yabanci adiminda kullanilir. Varsayilan TR'dir.
-- geo_mode sutunu 001'de tanimlidir, deger listesi 011'de uc degere cikar.
--
-- Bu dosya gercek DDL'dir; sifirdan kurulumda sutun ve indeks burada acilir.

ALTER TABLE provider
  ADD COLUMN ulke CHAR(2) NOT NULL DEFAULT 'TR' AFTER kind,
  ADD KEY idx_ulke (ulke);