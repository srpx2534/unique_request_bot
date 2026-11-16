-- 004 geri: il uule değerleri boşaltılır.
--
-- Uule yokken coğrafya sabitlemesi yapılamaz; ulusal sıralama bozulur.
UPDATE geo SET uule = NULL;
