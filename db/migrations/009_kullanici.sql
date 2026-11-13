-- Panel kullanıcısı. Şimdilik tek kullanıcı kullanılacak, şema çoklu
-- kullanıcıya hazır: her satır kendi parola özetini taşır.
-- Rol alanı bugün yalnızca 'admin' değerini alır, sonra genişletilir.

CREATE TABLE kullanici (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  eposta      VARCHAR(191) NOT NULL UNIQUE,
  sifre_hash  VARCHAR(72)  NOT NULL,
  rol         ENUM('admin') NOT NULL DEFAULT 'admin',
  aktif       TINYINT(1)   NOT NULL DEFAULT 1,
  son_giris_at DATETIME(3) NULL,
  created_at  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;