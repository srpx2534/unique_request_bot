-- cerez_kendi: acikken panelde yalnizca kullanicinin kendi yukledigi dosyalar
-- sayilir; havuz ortak kaldigi icin hit'ler yine tum havuzdan beslenir.
INSERT INTO ayar (anahtar, deger) VALUES ('cerez_kendi', '0')
  ON DUPLICATE KEY UPDATE deger = deger;
