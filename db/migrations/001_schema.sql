-- Şema kurulumu. Sıra 001'dir; view ve seed bunun ardından gelir.
-- Tüm zaman damgaları UTC'dir; oturum saat dilimi burada sabitlenir.
-- Motor daima InnoDB, karakter seti utf8mb4.

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- İl referansı: 81 kayıt, plaka kodu anahtar.
-- weight nüfustan türetilir, ağırlıklı seçimde kullanılır.
CREATE TABLE geo (
  code        TINYINT UNSIGNED PRIMARY KEY,
  name        VARCHAR(64)  NOT NULL UNIQUE,
  slug        VARCHAR(64)  NOT NULL UNIQUE,
  population  INT UNSIGNED NOT NULL,
  weight      SMALLINT UNSIGNED AS (ROUND(SQRT(population))) STORED,
  lat         DECIMAL(9,6),
  lon         DECIMAL(9,6),
  uule        VARCHAR(255) NULL,
  CONSTRAINT chk_geo_code CHECK (code BETWEEN 1 AND 81)
) ENGINE=InnoDB;

-- Site: burst hedefi olan domain.
CREATE TABLE site (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  domain     VARCHAR(191) NOT NULL UNIQUE,
  label      VARCHAR(191) NULL,
  active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB;

-- Kelime: geo_scope zorunlu.
-- province ise home_geo şart, national ise boş olmak zorunda (CHECK).
CREATE TABLE keyword (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  site_id    BIGINT UNSIGNED NOT NULL,
  text       VARCHAR(191) NOT NULL,
  geo_scope  ENUM('national','province') NOT NULL,
  home_geo   TINYINT UNSIGNED NULL,
  volume     INT UNSIGNED NULL,
  tier       TINYINT UNSIGNED NULL,
  state      ENUM('idle','active','paused','retired') NOT NULL DEFAULT 'idle',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE KEY uq_site_text (site_id, text),
  KEY idx_state (state),
  CONSTRAINT fk_kw_site FOREIGN KEY (site_id) REFERENCES site(id) ON DELETE CASCADE,
  CONSTRAINT fk_kw_geo  FOREIGN KEY (home_geo) REFERENCES geo(code),
  CONSTRAINT chk_geo_consistency CHECK (
    (geo_scope='province' AND home_geo IS NOT NULL) OR
    (geo_scope='national' AND home_geo IS NULL)
  )
) ENGINE=InnoDB;

-- Rotasyon defteri: kelime x il.
-- Ölçüm birimi değil; sadece trafik dağıtımı ve cooldown takibi taşır.
CREATE TABLE keyword_geo (
  id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  keyword_id     BIGINT UNSIGNED NOT NULL,
  geo_code       TINYINT UNSIGNED NOT NULL,
  tier           ENUM('core','normal','passive') NOT NULL DEFAULT 'normal',
  state          ENUM('pending','running','cooldown') NOT NULL DEFAULT 'pending',
  burst_count    SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  last_burst_at  DATETIME(3) NULL,
  cooldown_until DATETIME(3) NULL,
  UNIQUE KEY uq_kw_geo (keyword_id, geo_code),
  KEY idx_pick (keyword_id, tier, cooldown_until),
  CONSTRAINT fk_kg_kw  FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE,
  CONSTRAINT fk_kg_geo FOREIGN KEY (geo_code)   REFERENCES geo(code)
) ENGINE=InnoDB;

-- Proxy sağlayıcı. city_capable=1 olanlar il hedefleyebilir.
CREATE TABLE provider (
  id               SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name             VARCHAR(64) NOT NULL,
  kind             ENUM('residential','mobile','datacenter') NOT NULL,
  city_capable     TINYINT(1) NOT NULL DEFAULT 0,
  weight           SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  state            ENUM('active','quarantine','disabled') NOT NULL DEFAULT 'active',
  captcha_pct      DECIMAL(5,2) NOT NULL DEFAULT 0,
  bytes_month      BIGINT UNSIGNED NOT NULL DEFAULT 0,
  quota_bytes      BIGINT UNSIGNED NULL,
  quarantine_until DATETIME(3) NULL
) ENGINE=InnoDB;

-- Sağlayıcı x il sağlığı. Şehir havuzunun tükendiğini buradan anlarız.
CREATE TABLE provider_geo (
  provider_id     SMALLINT UNSIGNED NOT NULL,
  geo_code        TINYINT UNSIGNED NOT NULL,
  hits_1h         INT UNSIGNED NOT NULL DEFAULT 0,
  captcha_1h      INT UNSIGNED NOT NULL DEFAULT 0,
  captcha_pct     DECIMAL(5,2) NOT NULL DEFAULT 0,
  exhausted_until DATETIME(3) NULL,
  updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                  ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (provider_id, geo_code),
  CONSTRAINT fk_pg_prov FOREIGN KEY (provider_id) REFERENCES provider(id) ON DELETE CASCADE,
  CONSTRAINT fk_pg_geo  FOREIGN KEY (geo_code)    REFERENCES geo(code)
) ENGINE=InnoDB;

-- SERP API sağlayıcı: sadece ölçüm hattında kullanılır.
CREATE TABLE serp_provider (
  id          SMALLINT UNSIGNED PRIMARY KEY,
  name        VARCHAR(64) NOT NULL,
  weight      SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  state       ENUM('active','quarantine','disabled') NOT NULL DEFAULT 'active',
  quota_month INT UNSIGNED NULL,
  used_month  INT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB;

-- Profil: kalıcı cookie jar, ölçüm-B kanalı için.
CREATE TABLE profile (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ua          VARCHAR(255) NOT NULL,
  ja3_profile VARCHAR(64)  NOT NULL,
  cookie_jar  JSON         NOT NULL,
  provider_id SMALLINT UNSIGNED NOT NULL,
  geo_code    TINYINT UNSIGNED NULL,
  burned_at   DATETIME(3) NULL,
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_live (geo_code, burned_at),
  CONSTRAINT fk_pf_prov FOREIGN KEY (provider_id) REFERENCES provider(id)
) ENGINE=InnoDB;

-- Kampanya: start/stop kaydı, hangi ayarla çalıştığı saklanır.
CREATE TABLE campaign (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  keyword_id BIGINT UNSIGNED NOT NULL,
  started_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  stopped_at DATETIME(3) NULL,
  step_size  SMALLINT UNSIGNED NOT NULL DEFAULT 30,
  config     JSON NOT NULL,
  CONSTRAINT fk_cp_kw FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Burst: tek bir basamak. phase core ise büyük iller, broad ise yayılmış.
CREATE TABLE burst (
  id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  campaign_id    BIGINT UNSIGNED NOT NULL,
  keyword_geo_id BIGINT UNSIGNED NOT NULL,
  step           SMALLINT UNSIGNED NOT NULL,
  target_count   SMALLINT UNSIGNED NOT NULL,
  phase          ENUM('core','broad') NOT NULL,
  started_at     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  ended_at       DATETIME(3) NULL,
  stats          JSON NOT NULL,
  KEY idx_bs_time (started_at),
  CONSTRAINT fk_bs_cp FOREIGN KEY (campaign_id)    REFERENCES campaign(id) ON DELETE CASCADE,
  CONSTRAINT fk_bs_kg FOREIGN KEY (keyword_geo_id) REFERENCES keyword_geo(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Hit: tek istek telemetrisi. Hacim yüksek olduğu için FK konmaz.
CREATE TABLE hit (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  burst_id    BIGINT UNSIGNED NOT NULL,
  provider_id SMALLINT UNSIGNED NOT NULL,
  profile_id  BIGINT UNSIGNED NULL,
  geo_code    TINYINT UNSIGNED NULL,
  geo_mode    ENUM('city','national') NOT NULL DEFAULT 'national',
  tur         ENUM('residential','mobile','datacenter') NULL,
  result      ENUM('ok','captcha','not_found','timeout','error') NOT NULL,
  http_status SMALLINT UNSIGNED NULL,
  latency_ms  INT UNSIGNED NULL,
  bytes       INT UNSIGNED NULL,
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_burst (burst_id),
  KEY idx_day (created_at),
  KEY idx_prov_day (provider_id, created_at),
  KEY idx_mode_day (geo_mode, created_at)
) ENGINE=InnoDB;

-- Pozisyon: append-only. rank NULL ise "ilk 100'de yok".
CREATE TABLE position (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  keyword_id    BIGINT UNSIGNED NOT NULL,
  channel       ENUM('clean','post_click') NOT NULL,
  `rank`          SMALLINT UNSIGNED NULL,
  serp_provider SMALLINT UNSIGNED NULL,
  checked_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_read (keyword_id, channel, checked_at DESC),
  CONSTRAINT fk_ps_kw FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Günlük trafik özeti: rapor hit taramasın diye.
CREATE TABLE traffic_daily (
  day            DATE NOT NULL,
  keyword_geo_id BIGINT UNSIGNED NOT NULL,
  hits_ok        INT UNSIGNED NOT NULL DEFAULT 0,
  hits_fail      INT UNSIGNED NOT NULL DEFAULT 0,
  fallback_count INT UNSIGNED NOT NULL DEFAULT 0,
  bytes          BIGINT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (day, keyword_geo_id),
  CONSTRAINT fk_td_kg FOREIGN KEY (keyword_geo_id) REFERENCES keyword_geo(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Uyarı kaydı.
CREATE TABLE alert (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  kind         ENUM('captcha','provider_down','queue_lag','quota','fallback_high') NOT NULL,
  ref_id       BIGINT UNSIGNED NULL,
  message      VARCHAR(500) NOT NULL,
  acknowledged TINYINT(1) NOT NULL DEFAULT 0,
  created_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_open (acknowledged, created_at)
) ENGINE=InnoDB;

-- Denetim izi.
CREATE TABLE audit_log (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  actor      VARCHAR(64) NOT NULL,
  action     VARCHAR(64) NOT NULL,
  entity     VARCHAR(64) NOT NULL,
  entity_id  BIGINT UNSIGNED NULL,
  payload    JSON NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_ent (entity, entity_id)
) ENGINE=InnoDB;