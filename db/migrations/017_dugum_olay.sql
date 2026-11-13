-- Dugum olay defteri.
--
-- Kayit, kalp kaybi, durdur/başlat ve silme burada tutulur; durum degisiminin
-- ne zaman oldugu sonradan okunabilmeli (§6.1). Dugum silinince olaylari da
-- gider, kayit defteri dugumun kendisine baglidir.

CREATE TABLE dugum_olay (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dugum_id   SMALLINT UNSIGNED NOT NULL,
  tur        ENUM('kayit','kalp_kaybi','durdur','baslat','sil') NOT NULL,
  message    VARCHAR(255) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_dugum (dugum_id, created_at),
  CONSTRAINT fk_do_dugum FOREIGN KEY (dugum_id) REFERENCES dugum(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;