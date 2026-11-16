-- 012 geri: il adları ASCII biçime döner.
--
-- Ad, slug'ın ilk harfi büyütülmüş hâlidir; Türkçe karakterler kaybolur.
UPDATE geo SET name = CONCAT(UPPER(LEFT(slug, 1)), SUBSTRING(slug, 2)) WHERE code BETWEEN 1 AND 81;
