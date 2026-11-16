-- 040 geri: şema sözleşme öncesi hâline döner.
--
-- Üç tablo iki adımlı geri alınır: önce eski değer ENUM'a geri eklenir,
-- veri taşınır, sonra daraltılır. Tek adımda daraltmak 1265 verir.
-- `tukendi` verisi geri gelmez; 040 onu `hazir`a taşımıştı.
ALTER TABLE hit MODIFY COLUMN geo_mode ENUM('city','tr_fallback','yabanci') NOT NULL DEFAULT 'yabanci';
ALTER TABLE cerez_yukleme MODIFY COLUMN durum ENUM('yukleniyor','hazir','isleniyor','aktarim','bitti','iptal') NOT NULL DEFAULT 'yukleniyor';
UPDATE cerez_yukleme SET durum = 'isleniyor' WHERE durum = 'aktarim';
ALTER TABLE cerez_yukleme MODIFY COLUMN durum ENUM('yukleniyor','hazir','isleniyor','bitti','iptal') NOT NULL DEFAULT 'yukleniyor';
ALTER TABLE cookie_dosya MODIFY COLUMN durum ENUM('yeni','bekliyor','isleniyor','aktarildi','mukerrer','gecersiz') NOT NULL DEFAULT 'bekliyor';
UPDATE cookie_dosya SET durum = 'yeni' WHERE durum = 'bekliyor';
ALTER TABLE cookie_profil MODIFY COLUMN durum ENUM('hazir','kullaniliyor','tukendi','bozuk') NOT NULL DEFAULT 'hazir';
