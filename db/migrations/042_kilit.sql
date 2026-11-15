-- Kelime bazli kilit: sahip dugum ve kilit zamani.
-- Kilit suresi dolunca satir kendiliginden baskasina gecer; cerez gibi silinmez.
ALTER TABLE keyword_geo
  ADD COLUMN kilit_dugum VARCHAR(64) NULL DEFAULT NULL,
  ADD COLUMN kilit_at DATETIME(3) NULL DEFAULT NULL,
  ADD KEY ix_kilit (state, kilit_at);

-- Cakisma uyari turu: ayni satiri iki control plane islemek istediginde yazilir.
ALTER TABLE alert
  MODIFY COLUMN kind ENUM('captcha','provider_down','queue_lag','quota','fallback_high','hedef_yok','failover','burst_hata','partition','hedef_yok_durdu','kilit_cakismasi') NOT NULL;