-- Kota muhasebesi: aylik bayt sayaci ve ay devri (31, 32).
-- bytes_ay, sayacin hangi aya ait oldugunu tutar; ay degince sayac sifirlanir.
-- quota_bytes NULL ise saglayici kotasiz sayilir, secimde hep uygun kalir.
ALTER TABLE provider ADD COLUMN bytes_ay CHAR(7) NULL AFTER bytes_month;