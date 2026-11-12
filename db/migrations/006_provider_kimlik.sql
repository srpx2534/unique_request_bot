-- Sağlayıcı kimlik bilgileri ve oran ayarları.
-- Decodo residential ve mobile ayrı ürünlerdir, kimlikleri de ayrıdır;
-- bu yüzden bilgi sağlayıcı satırında tutulur, .env'de tek değer yetmez.
-- Şifreler düz metindir; repoda değil veritabanında durur (C24).

ALTER TABLE provider
  ADD COLUMN gateway   VARCHAR(128) NULL AFTER kind,
  ADD COLUMN kullanici VARCHAR(128) NULL AFTER gateway,
  ADD COLUMN sifre     VARCHAR(128) NULL AFTER kullanici;

CREATE TABLE IF NOT EXISTS ayar (
  anahtar       VARCHAR(64)  NOT NULL PRIMARY KEY,
  deger         VARCHAR(255) NOT NULL,
  guncellendi_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                ON UPDATE CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;

-- Oranlar yüzde olarak tutulur; toplam 100 değilse okurken normalize edilir.
INSERT INTO ayar (anahtar, deger) VALUES
  ('oran_residential', '100'),
  ('oran_mobil',       '0'),
  ('oran_datacenter',  '0'),
  ('mobil_pencere_sn', '8')
ON DUPLICATE KEY UPDATE anahtar = VALUES(anahtar);