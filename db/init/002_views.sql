-- Rapor görünümü. Panel tek sorguda anlık sıralama, 7 günlük trafik
-- ve trend bilgisini alır; hit tablosu taranmaz.

CREATE VIEW v_live AS
SELECT k.id, k.text, k.geo_scope, COALESCE(g.name,'—') AS geo, k.state,
  (SELECT rank FROM position p WHERE p.keyword_id=k.id AND p.channel='clean'
    ORDER BY checked_at DESC LIMIT 1) AS rank_now,
  (SELECT rank FROM position p WHERE p.keyword_id=k.id AND p.channel='clean'
    AND checked_at < NOW()-INTERVAL 24 HOUR
    ORDER BY checked_at DESC LIMIT 1) AS rank_24h,
  COALESCE((SELECT SUM(hits_ok) FROM traffic_daily t WHERE t.keyword_geo_id IN
    (SELECT id FROM keyword_geo WHERE keyword_id=k.id) AND t.day>=CURDATE()-7),0) AS ok_7d,
  COALESCE((SELECT SUM(hits_fail) FROM traffic_daily t WHERE t.keyword_geo_id IN
    (SELECT id FROM keyword_geo WHERE keyword_id=k.id) AND t.day>=CURDATE()-7),0) AS fail_7d,
  COALESCE((SELECT SUM(fallback_count) FROM traffic_daily t WHERE t.keyword_geo_id IN
    (SELECT id FROM keyword_geo WHERE keyword_id=k.id) AND t.day>=CURDATE()-7),0) AS fb_7d,
  CASE WHEN rank_now IS NULL THEN 'yok' WHEN rank_24h IS NULL THEN 'yeni'
       WHEN rank_now < rank_24h THEN 'yukari' WHEN rank_now > rank_24h THEN 'asagi'
       ELSE 'sabit' END AS trend
FROM keyword k LEFT JOIN geo g ON g.code=k.home_geo
WHERE k.state IN ('active','paused');