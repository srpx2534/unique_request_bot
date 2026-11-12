-- Sağlayıcı referansı (§8). Ağırlıklar sözleşmedeki değerlerdir.
-- city_capable yalnızca il hedeflemeyi tam destekleyende 1'dir; "kısmi"
-- olanlar 0 işaretlenir, §5 adım 2 gereği ulusal moda düşerler.
-- Kimlik bilgileri .env'de tutulur, burada yoktur.

INSERT INTO provider (id, name, kind, city_capable, weight, state)
VALUES
  (1, 'Decodo',      'residential', 0, 25, 'active'),
  (2, 'Bright Data', 'residential', 1, 20, 'active'),
  (3, 'Oxylabs',     'residential', 1, 15, 'active'),
  (4, 'Decodo',      'mobile',      0, 25, 'active'),
  (5, 'SOAX',        'mobile',      1, 10, 'active'),
  (6, 'IPRoyal',     'residential', 0,  5, 'active'),
  (7, 'Webshare',    'datacenter',  0,  1, 'disabled')
ON DUPLICATE KEY UPDATE
  name = VALUES(name), kind = VALUES(kind),
  city_capable = VALUES(city_capable), weight = VALUES(weight),
  state = VALUES(state);