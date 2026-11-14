-- Yukleme islemi ile dosya bagi; ilerleme bu sutundan sayilir.
-- Sutun, anahtar ve kisit ayri ALTER'larda eklenir: MariaDB tek ALTER
-- icinde ADD KEY ile FK kurulmasini her surumde kabul etmiyor.
ALTER TABLE cookie_dosya
  ADD COLUMN yukleme_id BIGINT UNSIGNED NULL AFTER yukleyen;

ALTER TABLE cookie_dosya
  ADD KEY idx_cd_yukleme (yukleme_id);

ALTER TABLE cookie_dosya
  ADD CONSTRAINT fk_cd_yukleme FOREIGN KEY (yukleme_id)
    REFERENCES cerez_yukleme(id) ON DELETE SET NULL;
