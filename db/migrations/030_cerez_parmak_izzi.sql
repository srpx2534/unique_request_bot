-- Cerez profilinin tarayici ailesi. Ice aktarimda bir kez atanir ve oturumun
-- uc adiminda da ayni parmak izi kullanilir; cerez yoksa rastgele secilir.
ALTER TABLE cookie_profil
  ADD COLUMN parmak_izzi VARCHAR(16) NULL AFTER ulke;

-- Eski profiller cerez adlarindan geri doldurulur. Isaret yoksa bilinmiyor:
-- bilinmeyen aile Chrome profilleriyle eslesir, Safari'ye dusmez.
UPDATE cookie_profil p
  JOIN (
    SELECT profil_id,
           MAX(CASE
                 WHEN ad = '__Secure-BUCKET' THEN 'firefox'
                 WHEN ad IN ('SIDCC', '__Host-GAPS', 'SEARCH_SAMESITE', 'AEC') THEN 'chrome'
               END) AS aile
      FROM cookie GROUP BY profil_id
  ) x ON x.profil_id = p.id
   SET p.parmak_izzi = COALESCE(x.aile, 'bilinmiyor');