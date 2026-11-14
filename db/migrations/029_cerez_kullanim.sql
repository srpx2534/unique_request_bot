-- Cerez bir site-kelime ciftinde bir kez kullanilir; ulke etiketi eklenir.
ALTER TABLE cookie_profil
  ADD COLUMN ulke CHAR(2) NULL AFTER il_kodu,
  ADD KEY idx_cp_secim (durum, suresi_gecmis, ulke);

CREATE TABLE cookie_kullanim (
  profil_id  BIGINT UNSIGNED NOT NULL,
  site_id    BIGINT UNSIGNED NOT NULL,
  keyword_id BIGINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (profil_id, site_id, keyword_id),
  KEY idx_ck_cift (site_id, keyword_id),
  CONSTRAINT fk_ck_profil FOREIGN KEY (profil_id) REFERENCES cookie_profil(id) ON DELETE CASCADE,
  CONSTRAINT fk_ck_site FOREIGN KEY (site_id) REFERENCES site(id) ON DELETE CASCADE,
  CONSTRAINT fk_ck_kelime FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Eski profillerin ulkesi cerez alan adlarindan geri doldurulur.
UPDATE cookie_profil p
  JOIN (
    SELECT profil_id,
           MAX(CASE WHEN SUBSTRING_INDEX(domain, '.', -1) = 'tr' THEN 'TR' END) AS tr,
           MAX(CASE WHEN CHAR_LENGTH(SUBSTRING_INDEX(domain, '.', -1)) = 2
                    THEN UPPER(SUBSTRING_INDEX(domain, '.', -1)) END) AS cc
      FROM cookie GROUP BY profil_id
  ) x ON x.profil_id = p.id
   SET p.ulke = COALESCE(x.tr, x.cc);

-- Tukenen durumu kalkti: harcanmis profiller yeniden havuza doner.
UPDATE cookie_profil SET durum = 'hazir', dugum_id = NULL WHERE durum = 'tukendi';

-- Kuyruk sahiplenmesi kiralanir; coken dugumun satiri geri alinir.
ALTER TABLE cookie_dosya
  ADD COLUMN isleniyor_at DATETIME(3) NULL AFTER durum,
  ADD KEY idx_cd_durum (durum, isleniyor_at);