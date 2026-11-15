-- Sozlesme §6/§26.1 ile semayi hizalar.
ALTER TABLE hit MODIFY COLUMN geo_mode ENUM('city','tr_fallback','yabanci') NOT NULL DEFAULT 'tr_fallback';

-- cerez_yukleme: isleniyor -> aktarim. Iki degeri birlikte tutan ara adim,
-- yoksa mevcut satirlar daraltmada bos kalir.
ALTER TABLE cerez_yukleme MODIFY COLUMN durum ENUM('yukleniyor','hazir','isleniyor','aktarim','bitti','iptal') NOT NULL DEFAULT 'yukleniyor';
UPDATE cerez_yukleme SET durum = 'aktarim' WHERE durum = 'isleniyor';
ALTER TABLE cerez_yukleme MODIFY COLUMN durum ENUM('yukleniyor','hazir','aktarim','bitti','iptal') NOT NULL DEFAULT 'yukleniyor';

-- cookie_dosya: yeni -> bekliyor, ayni iki adimli yaklasim.
ALTER TABLE cookie_dosya MODIFY COLUMN durum ENUM('yeni','bekliyor','isleniyor','aktarildi','mukerrer','gecersiz') NOT NULL DEFAULT 'bekliyor';
UPDATE cookie_dosya SET durum = 'bekliyor' WHERE durum = 'yeni';
ALTER TABLE cookie_dosya MODIFY COLUMN durum ENUM('bekliyor','isleniyor','aktarildi','mukerrer','gecersiz') NOT NULL DEFAULT 'bekliyor';

-- cookie_profil: kullanilmayan tukendi degeri kaldirilir.
UPDATE cookie_profil SET durum = 'hazir' WHERE durum = 'tukendi';
ALTER TABLE cookie_profil MODIFY COLUMN durum ENUM('hazir','kullaniliyor','bozuk') NOT NULL DEFAULT 'hazir';