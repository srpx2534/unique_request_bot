-- Devre kesici sayaclari saatlik pencerelidir; pencere baslangici tutulur.
-- Sayac sifirlanmadan oran seyreliyor ve karantina hic tetiklenmiyordu.
ALTER TABLE provider
  ADD COLUMN sayac_baslangic DATETIME(3) NULL;

ALTER TABLE provider_geo
  ADD COLUMN sayac_baslangic DATETIME(3) NULL;
