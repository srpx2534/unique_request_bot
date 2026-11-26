-- 85: `cerez_sec` her hit'te durum suzgeciyle toplu UPDATE calistiriyor;
-- durum indeksi olmadan tarama tam tabloya donuyordu.
CREATE INDEX idx_cookie_profil_durum ON cookie_profil (durum);