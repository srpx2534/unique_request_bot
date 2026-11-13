-- Saglayicisiz hit de yazilir.
--
-- Havuz bos oldugunda (dogrudan baglanti) hit satiri hic yazilmiyordu; olcum ve
-- rapor gercek trafigi gormuyordu. provider_id artik NULL olabilir.

ALTER TABLE hit
  MODIFY COLUMN provider_id SMALLINT UNSIGNED NULL;