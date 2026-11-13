-- Sunucu kayıt defteri.
--
-- Lisans zorlaması yok; amaç hangi makinenin ayakta olduğunu ve ne kadar
-- yüklü olduğunu görmek, gerektiğinde durdurmak. Canlılık son kalp atışından
-- hesaplanır, ayrı sütunda tutulmaz.

CREATE TABLE dugum (
  id           SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ad           VARCHAR(64)  NOT NULL,
  ip           VARCHAR(45)  NOT NULL,
  durum        ENUM('aktif','durduruldu') NOT NULL DEFAULT 'aktif',
  yuk          SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  cpu          DECIMAL(5,2) NOT NULL DEFAULT 0,
  ram          DECIMAL(5,2) NOT NULL DEFAULT 0,
  surum        VARCHAR(32)  NULL,
  son_kalp_at  DATETIME(3)  NULL,
  kayit_at     DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE KEY uq_ip (ip),
  KEY idx_kalp (son_kalp_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;