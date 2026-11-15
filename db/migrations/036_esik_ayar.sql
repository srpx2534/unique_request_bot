-- Esiklerin panelden ayarlanabilmesi icin varsayilan satirlar (29).
INSERT INTO ayar (anahtar, deger) VALUES ('esik_geo', '35') ON DUPLICATE KEY UPDATE deger = deger;
INSERT INTO ayar (anahtar, deger) VALUES ('asgari_ornek', '10') ON DUPLICATE KEY UPDATE deger = deger;