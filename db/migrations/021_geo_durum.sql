-- Durum sozlugu sadeleşti.
--
-- cooldown diye bir durum hic yazilmiyordu; bekleme suresi cooldown_until
-- sutununda tutuluyor. Enum'dan cikarilir, iki deger kalir.

UPDATE keyword_geo SET state = 'pending' WHERE state = 'cooldown';

ALTER TABLE keyword_geo
  MODIFY COLUMN state ENUM('pending','running') NOT NULL DEFAULT 'pending';