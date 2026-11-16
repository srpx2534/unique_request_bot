-- 033 geri: `cerez_kendi` ayarı silinir.
--
-- Ayar kapalı davranışa döner: sayımlar ortak havuzdan yapılır.
DELETE FROM ayar WHERE anahtar = 'cerez_kendi';
