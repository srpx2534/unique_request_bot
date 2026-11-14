-- Cerez defteri.
--
-- Dosyalar toplu aktarilir; ayni icerik iki kez aktarilmaz (ozet tekil).
-- Profil bir dosyaya karsilik gelir; cerezler profilde tutulur ve profil
-- kullanildikca tukenir. Birden fazla dugum ayni havuzdan beslenir, bu yuzden
-- sahiplenme atomik yapilir (durum + dugum_id + alindi_at).

CREATE TABLE cookie_dosya (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  yol          VARCHAR(512) NOT NULL,
  ad           VARCHAR(191) NOT NULL,
  tur          ENUM('json','netscape') NOT NULL,
  boyut        INT UNSIGNED NOT NULL,
  ozet         CHAR(64) NOT NULL,
  satir_sayisi SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  il_kodu      TINYINT UNSIGNED NULL,
  durum        ENUM('yeni','aktarildi','mukerrer','gecersiz') NOT NULL DEFAULT 'yeni',
  hata         VARCHAR(255) NULL,
  created_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE KEY uq_ozet (ozet),
  KEY idx_durum (durum),
  CONSTRAINT fk_cd_geo FOREIGN KEY (il_kodu) REFERENCES geo(code) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;

CREATE TABLE cookie_profil (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dosya_id     BIGINT UNSIGNED NOT NULL,
  ad           VARCHAR(191) NOT NULL,
  il_kodu      TINYINT UNSIGNED NULL,
  sona_erme    DATETIME(3) NULL,
  suresi_gecmis TINYINT(1) NOT NULL DEFAULT 0,
  durum        ENUM('hazir','kullaniliyor','tukendi','bozuk') NOT NULL DEFAULT 'hazir',
  kullanim     INT UNSIGNED NOT NULL DEFAULT 0,
  dugum_id     SMALLINT UNSIGNED NULL,
  alindi_at    DATETIME(3) NULL,
  created_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_secim (durum, suresi_gecmis, il_kodu, kullanim),
  KEY idx_dosya (dosya_id),
  CONSTRAINT fk_cp_dosya FOREIGN KEY (dosya_id) REFERENCES cookie_dosya(id) ON DELETE CASCADE,
  CONSTRAINT fk_cp_geo   FOREIGN KEY (il_kodu)  REFERENCES geo(code) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;

CREATE TABLE cookie (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  profil_id     BIGINT UNSIGNED NOT NULL,
  domain        VARCHAR(191) NOT NULL,
  ad            VARCHAR(191) NOT NULL,
  deger         TEXT NOT NULL,
  yol           VARCHAR(255) NOT NULL DEFAULT '/',
  sona_erme     DATETIME(3) NULL,
  guvenli       TINYINT(1) NOT NULL DEFAULT 0,
  http_only     TINYINT(1) NOT NULL DEFAULT 0,
  same_site     VARCHAR(8) NULL,
  oncelik       VARCHAR(8) NULL,
  oturumluk     TINYINT(1) NOT NULL DEFAULT 0,
  boyut         SMALLINT UNSIGNED NULL,
  kaynak_port   SMALLINT UNSIGNED NULL,
  kaynak_sema   VARCHAR(16) NULL,
  same_party    TINYINT(1) NOT NULL DEFAULT 0,
  partition_ust VARCHAR(191) NULL,
  partition_ata TINYINT(1) NULL,
  host_only     TINYINT(1) NOT NULL DEFAULT 0,
  KEY idx_profil (profil_id),
  CONSTRAINT fk_ck_profil FOREIGN KEY (profil_id) REFERENCES cookie_profil(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;