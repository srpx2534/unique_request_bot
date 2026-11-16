-- 001 geri: tüm tablolar düşer.
--
-- Çocuktan ebeveyne sıra zorunlu; yabancı anahtarlar ters sırada 1217 verir.
-- Defter tablosu (schema_migration) migrate.py ye ait, burada düşmez.
DROP TABLE IF EXISTS hit;
DROP TABLE IF EXISTS traffic_daily;
DROP TABLE IF EXISTS position;
DROP TABLE IF EXISTS burst;
DROP TABLE IF EXISTS campaign;
DROP TABLE IF EXISTS keyword_geo;
DROP TABLE IF EXISTS cookie_kullanim;
DROP TABLE IF EXISTS cookie;
DROP TABLE IF EXISTS cookie_profil;
DROP TABLE IF EXISTS cerez_yukleme;
DROP TABLE IF EXISTS cookie_dosya;
DROP TABLE IF EXISTS alert;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS dugum_olay;
DROP TABLE IF EXISTS dugum;
DROP TABLE IF EXISTS keyword;
DROP TABLE IF EXISTS profile;
DROP TABLE IF EXISTS provider_geo;
DROP TABLE IF EXISTS provider;
DROP TABLE IF EXISTS serp_provider;
DROP TABLE IF EXISTS site;
DROP TABLE IF EXISTS geo;
DROP TABLE IF EXISTS ayar;
