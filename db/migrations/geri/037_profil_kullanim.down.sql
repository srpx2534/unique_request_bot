-- 037 geri: profil kullanım sayacı düşer.
--
-- Sayaç yalnız profil yakma kararını taşır; düşmesi veri kaybı değildir.
-- Profillerin yakılmış olması `burned_at` alanında kalır.
ALTER TABLE profile DROP COLUMN kullanim;
