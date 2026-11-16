-- 015 geri: SERP anahtar ve ölçüm aralığı ayarları silinir.
--
-- Anahtarlar panelden yeniden girilene kadar ölçüm turu atlanır.
DELETE FROM ayar WHERE anahtar IN ('serp_decodo', 'serp_serper', 'serp_searchapi', 'olcum_araligi_dk');
