-- Hedefi ilk 100'de bulunamayan kelime, panelden ayarlanan sayida ust uste
-- denemeden sonra durdurulur. Sayac keyword satirinda tutulur; baslat'ta sifirlanir.
ALTER TABLE keyword ADD COLUMN hedef_yok_sayac INT NOT NULL DEFAULT 0;
INSERT INTO ayar (anahtar, deger) VALUES ('hedef_yok_durma', '3') ON DUPLICATE KEY UPDATE deger = deger;