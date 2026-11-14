-- Cerezler tarayici uzerinden yuklenebilir; kaynak ve yukleyen izlenir.
ALTER TABLE cookie_dosya
  ADD COLUMN kaynak ENUM('yol','yukleme') NOT NULL DEFAULT 'yol' AFTER tur,
  ADD COLUMN yukleyen BIGINT UNSIGNED NULL AFTER kaynak,
  ADD KEY idx_yukleyen (yukleyen),
  ADD CONSTRAINT fk_cd_yukleyen FOREIGN KEY (yukleyen) REFERENCES kullanici(id) ON DELETE SET NULL;

CREATE TABLE cerez_yukleme (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  kullanici_id  BIGINT UNSIGNED NULL,
  klasor        VARCHAR(191) NOT NULL,
  dosya_sayisi  INT UNSIGNED NOT NULL DEFAULT 0,
  boyut         BIGINT UNSIGNED NOT NULL DEFAULT 0,
  durum         ENUM('yukleniyor','hazir','isleniyor','bitti','iptal') NOT NULL DEFAULT 'yukleniyor',
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_cy_durum (durum),
  KEY idx_cy_kullanici (kullanici_id),
  CONSTRAINT fk_cy_kullanici FOREIGN KEY (kullanici_id) REFERENCES kullanici(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;