-- İl adları iki kez kodlanmış (UTF-8 baytları latin1 sanılıp yeniden kodlanmış).
-- Değer ikili olarak latin1'e çevrilip utf8mb4 olarak geri okunur; ASCII adlar
-- bozulmadan geçer.

UPDATE geo
   SET name = CONVERT(BINARY(CONVERT(name USING latin1)) USING utf8mb4);