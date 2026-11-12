# SÖZLEŞME — unique_request_bot

Sürüm: 1.2 (kilitli)
Kapsam: Çok sunuculu, panelden yönetilen, çoklu sağlayıcı üzerinden çalışan
        request-burst motoru
Veritabanı: MySQL 8.0.16+
Diller: Python 3.12 (fetch engine) + Node 20 / TypeScript (control plane)
Geliştirme: Windows 10/11 + WSL2
Çalışma: Debian 12 x86_64
Not: Bu sürümde markdown tablo kullanılmaz; tüm listeler madde işaretlidir.

## 1. Kapsam

Panelden site ve anahtar kelime kaydedilir. `start` verildiğinde sistem kelimeyi ve hedef URL'yi döngüde işler: Google SERP'inden geçer, hedefe tıklar, kısa dwell uygular, SERP'e döner. Trafik çoklu proxy sağlayıcısı üzerinden dağıtılır. Sıralama ayrı ve temiz bir ölçüm hattından düzenli aralıkla okunur. Panel; kelime başına başarı/başarısızlık oranını, yedek oranını, anlık ve geçmiş sıralamayı, trendi gösterir. Sistem `stop` gelene kadar çalışır, doğal bitiş yoktur.

## 2. Kapsam dışı

- Headless tarayıcı / gerçek click bot
- İçerik üretimi
- Backlink
- Google Search Console entegrasyonu
- Google Ads verisi
- Müşteriye dönük arayüz
- Bing / Yandex hedefleme

## 3. Dil ayrımı (bağlayıcı)

Fetch engine katmanı Python 3.12'dir; sorumluluğu SERP isteği, tıklama, dwell, pogo, JA3 ve proxy tüketimidir; sınırı HTTP/JSON servistir.

Control plane katmanı Node 20 + TypeScript'tir; sorumluluğu panel, orkestrasyon, kuyruk, sağlayıcı havuzu, ölçüm ve raporlamadır; veritabanı MySQL'dir.

Worker'lar durumsuzdur ve DB'ye yazmaz. Tüm durum control plane'de tutulur. Worker endpoint'i paylaşılan token ile kimlik doğrular ve dışarıya kapalıdır.

## 4. Mimari

Akış: Panel (Node) → scheduler → Redis kuyruk → worker havuzu (Python, N sunucu) → SERP → tıklama → dwell → pogo → hit telemetrisi (JSON) → Node → MySQL.

Ölçüm hattı ayrıdır: SERP API → position (sadece ulusal, clean kanal).

Üç IP hattı birbirine karışmaz:

- Burst hattı: tıklama üretimi; residential/mobile, şehir hedefli öncelikli
- Ölçüm-A hattı: dünyanın gördüğü sıralama; SERP API (Decodo /search, Serper)
- Ölçüm-B hattı: tıklamış profilin gördüğü; ayrı küçük havuz + kalıcı cookie jar

## 5. Geo çözümleme

`province` kelimede her hit için sıra şudur:

1. İlde `city_capable=1`, `state='active'`, `exhausted_until` geçmiş sağlayıcı aranır. Varsa `geo_mode='city'` ve proxy kullanıcı adına `city-<slug>` eklenir.
2. Yoksa `geo_mode='national'`, `geo.uule` kullanılır ve herhangi bir aktif sağlayıcı seçilir. İş durmaz.
3. Sonuç `provider_geo` tablosuna yazılır.
4. Aynı sağlayıcı ve il çiftinde CAPTCHA oranı %35'i geçerse o çift 60 dakika `exhausted_until` alır.

`national` kelimede il seçimi: `burst_count` 3'ün altındayken core tier (nüfusa göre ilk 10 il) ağırlıklı, sonrasında 81 il arasında ağırlıklı rastgele. Seçim A-Res ile yapılır:

```sql
ORDER BY -LOG(RAND()) / g.weight LIMIT 1
```

`weight` generated kolondur ve `ROUND(SQRT(population))` ile hesaplanır.

Ölçüm daima ulusaldır. İl sıralaması ölçülmez.

## 6. Tablo şeması

```sql
SET NAMES utf8mb4;
SET time_zone = '+00:00';

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

CREATE TABLE site (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  domain     VARCHAR(191) NOT NULL UNIQUE,
  label      VARCHAR(191) NULL,
  active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB;

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

CREATE TABLE provider (
  id               SMALLINT UNSIGNED PRIMARY KEY,
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

CREATE TABLE serp_provider (
  id          SMALLINT UNSIGNED PRIMARY KEY,
  name        VARCHAR(64) NOT NULL,
  weight      SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  state       ENUM('active','quarantine','disabled') NOT NULL DEFAULT 'active',
  quota_month INT UNSIGNED NULL,
  used_month  INT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB;

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

CREATE TABLE campaign (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  keyword_id BIGINT UNSIGNED NOT NULL,
  started_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  stopped_at DATETIME(3) NULL,
  step_size  SMALLINT UNSIGNED NOT NULL DEFAULT 30,
  config     JSON NOT NULL,
  CONSTRAINT fk_cp_kw FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE
) ENGINE=InnoDB;

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

CREATE TABLE hit (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  burst_id    BIGINT UNSIGNED NOT NULL,
  provider_id SMALLINT UNSIGNED NOT NULL,
  profile_id  BIGINT UNSIGNED NULL,
  geo_code    TINYINT UNSIGNED NULL,
  geo_mode    ENUM('city','national') NOT NULL DEFAULT 'national',
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

CREATE TABLE position (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  keyword_id    BIGINT UNSIGNED NOT NULL,
  channel       ENUM('clean','post_click') NOT NULL,
  rank          SMALLINT UNSIGNED NULL,
  serp_provider SMALLINT UNSIGNED NULL,
  checked_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_read (keyword_id, channel, checked_at DESC),
  CONSTRAINT fk_ps_kw FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE
) ENGINE=InnoDB;

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

CREATE TABLE alert (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  kind         ENUM('captcha','provider_down','queue_lag','quota','fallback_high') NOT NULL,
  ref_id       BIGINT UNSIGNED NULL,
  message      VARCHAR(500) NOT NULL,
  acknowledged TINYINT(1) NOT NULL DEFAULT 0,
  created_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_open (acknowledged, created_at)
) ENGINE=InnoDB;

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
```

### 6.1 Tasarım gerekçeleri

- `keyword_geo` ölçüm birimi değil, rotasyon defteridir; il ölçümü yapılmadığı için sadece trafik dağıtımı ve cooldown takibi taşır.
- `position` tablosu `keyword_id` ile bağlanır; ölçüm kelime bazlıdır, iş birimi bazlı değildir.
- `chk_geo_consistency` kısıtı, `province` seçilip il verilmemesini veritabanı seviyesinde reddeder.
- `provider_geo` ayrı tablodur; şehir havuzunun tükendiğini sağlayıcı API'sine sormadan tespit etmenin tek yolu budur.
- `hit` tablosunda foreign key yoktur; hacim yüksektir, FK maliyeti gereksizdir.
- `position` append-only'dir; sıralama geçmişi korunur ve eğri çizilebilir.
- `rank` alanı NULL olabilir; "ilk 100'de yok" ile "ölçüm başarısız" ayrı durumlardır.
- `weight` generated kolondur; nüfus güncellenince otomatik yenilenir.

### 6.2 Seed zorunluluğu

`geo` tablosu 81 kayıtla seed edilir: `code`, `name`, `slug`, `population`, `lat`, `lon`. Core tier nüfusa göre ilk 10 ildir: 34, 6, 35, 16, 7, 42, 1, 63, 27, 41. `uule` her il için bir kez üretilip yazılır. Nüfus değerleri TÜİK güncel verisiyle değiştirilebilir, yaklaşık değer kabul edilir.

### 6.3 Saklama süreleri

- `hit`: 30 gün, sonra silinir
- `burst`: 90 gün
- `position`: süresiz
- `traffic_daily`: süresiz
- `audit_log`: 1 yıl

Partition, `hit` tablosu 10 milyon satırı geçince eklenir.

## 7. API sözleşmesi

```
POST /api/sites                    { domain, label }
POST /api/keywords                 { site_id, text, geo_scope, home_geo?, volume? }
POST /api/keywords/:id/start       → 202 { campaign_id }
POST /api/keywords/:id/stop        → 204
GET  /api/keywords/:id/curve?h=24  → [{ t, channel, rank }]
GET  /api/live                     → v_live

POST /worker/burst   Authorization: Bearer <worker_token>
  { keyword, target_url, geo_code?, geo_mode, uule?, size }
  → { ok, captcha, not_found, timeout, elapsed_ms }
```

`keyword` oluşturulunca `keyword_geo` otomatik üretilir. `province` için 1 satır (`core`), `national` için 81 satır (10 core, 30 normal, 41 passive).

## 8. Sağlayıcı politikası

Proxy sağlayıcıları, ağırlık ve şehir hedefleme durumu:

- Decodo, residential, ağırlık 25, şehir hedefleme kısmi
- Bright Data, residential, ağırlık 20, şehir hedefleme var
- Oxylabs, residential, ağırlık 15, şehir hedefleme var
- Decodo, mobile, ağırlık 25, şehir hedefleme kısmi
- SOAX, mobile, ağırlık 10, şehir hedefleme var
- IPRoyal, residential, ağırlık 5, şehir hedefleme kısmi
- Webshare, datacenter, sadece smoke test

SERP API sağlayıcıları: Decodo /search birincil, Serper yedek, SearchApi.io yedek.

Mobil IP'ler burst'ün ilk 8 saniyesinde tüketilir. Sağlayıcı genel CAPTCHA oranı %20'yi geçerse 2 saat karantina alır ve ağırlığı sıfırlanır. Sağlayıcı anahtarları kullanıcıya aittir, yazılım yalnızca tüketir.

## 9. Hız sabitleri

- Dwell: 5-12 saniye
- Pogo: 1 istek, 3-6 saniye sonra
- Alt kaynak: yok
- Eşzamanlılık: sunucu başına 12
- Tur aralığı: 25-40 dakika
- `keyword_geo` cooldown: 20-35 dakika rastgele
- Ölçüm aralığı: kelime başına 30 dakika
- Basamak boyu: en fazla 60 hit

## 10. Raporlama

```sql
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
```

Panel kelime başına şunları gösterir: başarı oranı, yedek oranı, sıralama eğrisi, trend. Yedek oranı %30'u geçerse uyarı üretilir.

## 11. Kabul kriterleri

- C1 — Panelde site ve kelime CRUD, start/stop, canlı log çalışır.
- C2 — `start` verildikten sonra ilk hit 30 saniyenin altında atılır.
- C3 — Worker `/burst` p95 süresi 45 saniyenin altındadır.
- C4 — Her hit yeni UA, yeni IP, taze cookie ve Chrome JA3 ile gider; oran %100'dür.
- C5 — JA3 çıktısı gerçek Chrome hash'iyle birebir eşleşir.
- C6 — Sağlayıcı failover 10 saniyenin altında tamamlanır.
- C7 — CAPTCHA oranı pilotta %12'nin altındadır.
- C8 — CAPTCHA oranı tam kapasitede %8'in altındadır.
- C9 — `not_found` oranı %5'in altındadır.
- C10 — Burst tamamlanma oranı %95'in üstündedir.
- C11 — Veri kaybı sıfırdır.
- C12 — Ölçüm boşluğu 15 dakikayı geçmez.
- C13 — `province` kelime, il verilmeden kaydedilemez; veritabanı reddeder.
- C14 — `national` kelime kaydı 81 `keyword_geo` satırı üretir; tier dağılımı 10/30/41'dir.
- C15 — `v_live` görünümü 3.300 iş biriminde p95 400 ms'nin altında yanıt verir.
- C16 — Aynı `keyword_geo` üzerinde çakışan burst sayısı sıfırdır.
- C17 — Şehir hedefleyen sağlayıcı yokken iş durmaz, `national` moduna düşer.
- C18 — Sağlayıcı ve il çiftinde CAPTCHA %35'i geçerse 60 dakika `exhausted_until` uygulanır.
- C19 — `burst_count` 3'ün altındayken core tier, sonrasında broad faz kullanılır.
- C20 — Ölçüm daima ulusal ve `clean` kanaldan yapılır; oran %100'dür.
- C21 — `stop` sonrası yeni hit atılmaz.
- C22 — Tüm `DATETIME` değerleri UTC'dir; oran %100'dür.
- C23 — `uule` 81 ilin tamamında doludur.
- C24 — Sırlar repoda değil, ortam değişkenindedir; oran %100'dür.
- C25 — Aynı burst'ün tekrar işlenmesi idempotenttir, aynı sonucu verir.
- C26 — `pytest` ve `vitest` hem Windows hem Linux'ta geçer.
- C27 — CI matrisi `windows-latest` ve `ubuntu-22.04` içerir; ikisi de yeşildir.
- C28 — Depoda CRLF yoktur; `git ls-files --eol` temiz döner.
- C29 — Hiçbir modülde sabit `os.sep` veya `\\` yolu yoktur; lint kuralı geçer.
- C30 — Docker imajı `linux/amd64` üzerinde Debian 12'dir.

C7, C8, C9, C10, C11, C12 ve C15 pilot kabulünde ölçülür.

## 12. Kilometre taşları

- M1 — Migration seti, `geo` seed, uule üretici, CI iskeleti (3 gün)
- M2 — Python worker, curl_cffi, JA3 doğrulama, 100 hit testi (1 hafta)
- M3 — Sağlayıcı havuzu, circuit breaker, gözlemlenebilirlik (1 hafta)
- M4 — Node control plane, panel, kuyruk (1 hafta)
- M5 — Ölçüm A/B hattı, rapor (1 hafta)
- M6 — 5 sunucu pilot, 20 kelime, 2 hafta saha testi (2 hafta)
- M7 — 20 sunucuya ölçekleme ve devir (1 hafta)

## 13. Devir kriteri

M6 sonunda C7, C8, C9, C10, C11, C12, C15 ve C26-C30 sağlanıyorsa proje kabul edilir. Sağlanmıyorsa M3-M5 iyileştirme turu tekrarlanır. Devir kapsamı: kod, migration dosyaları, seed scripti, `README`, `.env.example`, `docker-compose`, `.gitattributes`.

## 14. Bakım

`not_found` oranı %5'i geçerse 24 saat içinde SERP regex revizyonu yapılır. `curl_cffi` sürüm takibi aylıktır. Sağlayıcı anahtar ve ağırlık güncellemesi süreklidir.

## 15. Varsayımlar

Kullanıcıda hazır bileşen yoktur; `geo` seed, uule üretici, migration seti, `docker-compose` ve `README` yüklenici tarafından üretilir. Hedef kelime sayısı 100'ü geçmez. Şehir hedefleme sağlayıcı sözleşmelerine bağlıdır; sağlanamazsa C17 devreye girer, sistem çalışır ancak il bazlı IP sinyali üretmez.

## 16. Değişiklik kontrolü

§3, §4, §5, §6, §11 ve §18 maddeleri M4 tamamlandıktan sonra değişirse ayrı kapsam sayılır. Diğer maddeler mutabakatla güncellenir.

## 17. Altyapı

- 17.1 — Tüm sunucular Debian 12 x86_64'dir. Windows yalnızca geliştirme makinesidir.
- 17.2 — Her bileşen Docker imajıdır. İmajlar digest ile pinlenir. `curl-impersonate` sürümü imaj içinde sabittir, host'a kurulmaz.
- 17.3 — Sertleştirme: root olmayan kullanıcı, `read_only` rootfs, `cap_drop: ALL`, `restart: always`.
- 17.4 — Bulut bağımsızlığı: kod hiçbir bulut sağlayıcısının API'sine bağlı değildir.
- 17.5 — Worker'lar public alt ağda çalışır; NAT Gateway maliyeti doğmaz.
- 17.6 — MySQL günlük `mysqldump` ile yedeklenir, 7 gün saklanır, offsite kopya alınır. Geri yükleme aylık test edilir.
- 17.7 — Sırlar ortam değişkeninde veya secret store'da tutulur; repoda düz metin yoktur.

## 18. Geliştirme ortamı — Windows'ta yaz, Linux'ta çalıştır

Kod Windows'ta yazılır, Linux'ta çalışır. Aşağıdaki maddeler bağlayıcıdır.

### 18.1 Yol ve dosya adları

- Tüm dosya yolları Python'da `pathlib.Path`, Node'da `node:path` ile kurulur. Sabit `/` veya `\\` yazılmaz.
- Dosya adlarında `: * ? " < > |` karakterleri kullanılmaz.
- Windows rezerve adları (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) kullanılmaz.
- Yol uzunluğu 260 karakteri geçmez.
- Symlink kullanılmaz.
- Dosya ve klasör adlarında büyük-küçük harf karışıksa `import` ve `require` birebir eşleşmek zorundadır; Windows toleranslıdır, Linux değildir.

### 18.2 Satır sonu

- Depoda yalnızca LF kullanılır. `core.autocrlf=false` ve `.gitattributes` zorunludur (Ek A).
- `.sh` dosyaları LF ve `#!/usr/bin/env bash` ile yazılır.

### 18.3 Kabuk ve süreç

- Kabuk çağrısı minimumdur. Gerektiğinde Python'da `subprocess` ve `shell=False`, Node'da `execFile` kullanılır.
- `&&`, `;`, `$VAR` içeren tek satır komutlar kullanılmaz; mantık dile taşınır.
- Node script'lerinde `cross-env` kullanılır, `FOO=bar cmd` biçimi kullanılmaz.
- `os.fork` ve `fcntl` kullanılmaz. Dosya kilidi için `filelock` veya `portalocker` kullanılır.

### 18.4 Ortam değişkenleri ve zaman

- Ayarlar `.env` ve `python-dotenv` / `dotenv` ile yüklenir. `export` kullanılmaz.
- Saat dilimi her yerde UTC'dir. Yerel saat varsayımı yapılmaz. `tzdata` imaja dahildir.
- Python `venv` Windows'ta `Scripts`, Linux'ta `bin` altındadır; betiklerde ikisi de aranmaz, `python -m` kullanılır.

### 18.5 Yerel servisler

- MySQL ve Redis yerelde WSL2 içinde Docker ile çalışır. Windows kurulumları (Memurai, MySQL MSI) desteklenmez.
- Geliştirme ortamı `docker compose up` ile ayağa kalkar; host'ta servis kurulumu yapılmaz.

### 18.6 Test ve CI

- Tüm testler iki platformda geçmek zorundadır. CI matrisi `windows-latest` ve `ubuntu-22.04` içerir.
- Platforma özel dallanma gerekiyorsa `sys.platform` veya `process.platform` ile tek noktada ve yorumla yapılır.

### 18.7 Parmak izi

- `curl_cffi` Windows'ta çalışır ancak JA3 doğrulaması iki platformda da koşar (C5). Yalnızca Windows'ta doğrulanmış parmak izi kabul edilmez.
- Docker imajı `linux/amd64` üzerinde Debian 12'dir.

## 19. Ek A — `.gitattributes`

```
* text=auto eol=lf
*.png binary
*.jpg binary
*.webp binary
*.woff2 binary
*.sh text eol=lf
*.bat text eol=crlf
*.ps1 text eol=crlf
```

## 20. Ek B — Yasak yapılar (lint ile zorlanır)

- `"C:\\..."` veya `"/home/..."` yerine `Path(...)` / `path.join`
- `open("a/b.txt")` yerine `Path("a") / "b.txt"`
- `subprocess.run("a && b", shell=True)` yerine liste argümanı
- `os.system` yerine `subprocess.run`
- `os.fork` yerine `multiprocessing`
- `fcntl.flock` yerine `filelock`
- Naive `datetime.now()` yerine `datetime.now(timezone.utc)`
- `chmod` bağımlılığı yerine `python x.py` / `node x.js`
- CRLF commit yerine `.gitattributes`

## 21. Onay

İşveren — Ad, tarih, imza: ................................................

Yüklenici — Ad, tarih, imza: ................................................


## 23. Kodlama kuralları (bağlayıcı)

### 23.1 Yorum zorunluluğu — Türkçe

- Her dosyanın başında, dosyanın ne işe yaradığını ve nerede kullanıldığını
  anlatan en az üç satırlık Türkçe blok bulunur.
- Her fonksiyon ve metot, Türkçe docstring taşır; ne yaptığını, parametrelerini,
  dönüş değerini ve fırlattığı hataları yazar.
- Her karmaşık blok (döngü, dallanma, retry, seçim mantığı) öncesinde "neden
  böyle" sorusunu yanıtlayan Türkçe yorum bulunur.
- Her sihirli sayı, birimi ve gerekçesiyle yorumlanır. Örnek: `DWELL_MIN = 5
  # saniye; tık sayılsın yeter, hız öncelikli`.
- Yorum, kodu tekrar etmez; kodun neden öyle olduğunu açıklar.
- Değişken, fonksiyon ve tablo adları İngilizce olabilir. Açıklama dili Türkçedir.
- Ölü kod yorumla gizlenmez, silinir. Yerine yeni davranış yorumlanır.

### 23.2 Dosya disiplini

- Dosya başına tek sorumluluk. Bir dosyada iki farklı iş varsa bölünür.
- Dosya 250 satırı geçmez. Geçiyorsa sorumluluk ayrıştırılmamış demektir.
- Sınıf başına ayrı dosya açılmaz; ilgili küçük sınıflar tek dosyada toplanır.
- `index.ts` / `index.py` barrel zinciri kurulmaz; import doğrudan dosyaya gider.
- Boş klasör bırakılmaz.
- Aynı bilgi iki yerde tutulmaz; konfigürasyon tek kaynaktan okunur.
- Üretilmiş dosyalar (build çıktısı, `node_modules`, `.venv`, log, `dist`) repoya
  girmez.
- Test dosyası, test edilen modülün yanında ve aynı adla `*.test.ts` /
  `test_*.py` biçiminde durur.
- Kullanılmayan bağımlılık `package.json` / `requirements.txt` içinde bırakılmaz.

### 23.3 Ücretsiz servis önceliği

Geliştirme aşamasında (M1-M5) ücretsiz katmanlar kullanılır:

- SERP ölçümü: Decodo ücretsiz plan (10 bin istek) ve Serper ücretsiz kota (2.500).
- Yerel MySQL ve Redis: Docker konteyneri, ek ücret yok.
- CI: GitHub Actions ücretsiz dakikalar.
- İzleme: kendi Prometheus ve Grafana konteynerleri.
- Hata izleme: Sentry ücretsiz katman veya self-host.
- Test hedef sitesi: kullanıcının kendi domaininde ücretsiz alt alan adı.
- Proxy: M2-M5 için Decodo ücretsiz plan ve IPRoyal deneme kredisi.

Paralı kaynağa yalnızca şu üç durumda geçilir:

- Gerçek residential trafik hacmi (M6 pilot, kaçınılmaz).
- Şehir hedefleme doğrulaması için ücretli sağlayıcı teyidi.
- 20 sunucuya ölçekleme (M7).

Ücretsiz katman sınırına dayanan her yerde kod, kotayı aşınca uyarı üretir ve
sessizce durmaz.