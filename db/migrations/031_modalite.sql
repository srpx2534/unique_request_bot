-- Kelime bazli modalite: mobil kelime android profil ve mobil IP ister.
ALTER TABLE keyword
  ADD COLUMN mobil TINYINT(1) NOT NULL DEFAULT 0 AFTER volume;

-- Cerez profili de modalite tasir: mobil kelimede mobil cerezler once gelir.
ALTER TABLE cookie_profil
  ADD COLUMN mobil TINYINT(1) NOT NULL DEFAULT 0 AFTER parmak_izzi,
  ADD KEY idx_cp_mobil (durum, mobil);

-- Yukleme bazli modalite: dosyalar hangi moda ait olduguyla ice aktarilir.
ALTER TABLE cerez_yukleme
  ADD COLUMN modalite TINYINT(1) NOT NULL DEFAULT 0 AFTER klasor;