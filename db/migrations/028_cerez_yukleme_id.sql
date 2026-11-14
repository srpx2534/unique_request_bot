-- Yukleme islemi ile dosya bagi; ilerleme bu sutundan sayilir.
ALTER TABLE cookie_dosya
  ADD COLUMN yukleme_id BIGINT UNSIGNED NULL AFTER yukleyen,
  ADD KEY idx_cd_yukleme (yukleme_id),
  ADD CONSTRAINT fk_cd_yukleme FOREIGN KEY (yukleme_id) REFERENCES cerez_yukleme(id) ON DELETE SET NULL;