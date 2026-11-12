-- Uyarı türleri genişletilir: hedef bulunamaması, failover ve burst hatası
-- da izlenebilir olsun. Panelde takip ekranı bunları okuyacak.
-- Mevcut değerler korunur, yalnızca liste büyür.

ALTER TABLE alert MODIFY COLUMN kind
  ENUM('captcha','provider_down','queue_lag','quota','fallback_high',
       'hedef_yok','failover','burst_hata') NOT NULL;

-- Okunur liste: açılmamışlar önce, her satırda yaş (dakika).
CREATE OR REPLACE VIEW v_alert AS
SELECT id, kind, ref_id, message, acknowledged, created_at,
       TIMESTAMPDIFF(MINUTE, created_at, NOW(3)) AS yas_dk
FROM alert
ORDER BY acknowledged ASC, created_at DESC;