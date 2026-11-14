# SÖZLEŞME — Unique Request Bot

Sürüm: 1.6 (kilitli)
Kapsam: Çok sunuculu, panelden yönetilen, çoklu sağlayıcı üzerinden çalışan
        request-burst motoru
Veritabanı: MySQL 8.0.16+
Diller: Python 3.12 (fetch engine) + Node 20 / TypeScript (control plane)
Geliştirme: Windows 10/11
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

Worker kuralına üç istisna vardır:

- Sağlayıcı seçimi için `provider`, `provider_geo`, `geo` tabloları salt okunur.
- Ayar okuma için `ayar` tablosu salt okunur; SERP anahtarı ve pencere değerleri buradan gelir.
- Hit sonrası yalnızca `provider_geo` ve `alert` toplu tablolarına yazılır.
- Cookie havuzu için `cookie_profil`, `cookie` ve `cookie_kullanim` tabloları okunur; `cookie_profil` sahiplenme durumu ve `cookie_kullanim` çift kaydı worker tarafından yazılır (§26).

Bunun dışındaki tüm durum control plane'de kalır.

Ayar okuması `worker/ayar_db.py` üzerinden yapılır: 60 saniye önbellek, tablo okunamazsa `.env`, o da yoksa varsayılan. Panelde yapılan değişiklik en geç bir dakika içinde etkili olur.

## 4. Mimari

Akış: Panel (Node) → scheduler → Redis kuyruk → worker havuzu (Python, N sunucu) → SERP → tıklama → dwell → pogo → hit telemetrisi (JSON) → Node → MySQL.

Ölçüm hattı ayrıdır: SERP API → position (sadece ulusal, clean kanal).

Üç IP hattı birbirine karışmaz:

- Burst hattı: tıklama üretimi; residential/mobile, şehir hedefli öncelikli
- Ölçüm-A hattı: dünyanın gördüğü sıralama; SERP API (Decodo /search, Serper)
- Ölçüm-B hattı: tıklamış profilin gördüğü; ayrı küçük havuz + kalıcı cookie jar

Google, 2025'ten beri `/search` için JavaScript zorunlu kıldı. Düz HTTP istek sonuç yerine uygulama kabuğu döndürüyor (HTTP 200, ~94 KB, sıfır sonuç). Headless tarayıcı kapsam dışı olduğu için burst hattında sonuç listesi SERP API'sinden bir kez çözülür; izlenim ve tıklama proxy üzerinden doğrudan atılır. İzlenim isteği Google'a gerçek IP'den gider ve sunucu tarafında sayılır, yalnızca cevabı okunmaz. Böylece arama→tıklama zinciri aynı IP'de kalır.

Dağıtıcı işi düğüm kayıt defterinden seçer: yalnızca `durum='aktif'` ve kalbi 45 saniyeden taze düğümler arasından en az yüklüsü. Kayıt defteri tamamen boşsa yerel varsayılana (`127.0.0.1:WORKER_PORT`) düşer, böylece tek makine kurulumu bozulmaz. Uygun düğüm yoksa iş `aktif düğüm yok` ile geri bırakılır.

## 5. Geo çözümleme

`geo_mode` üç değerlidir: `city`, `tr_fallback`, `yabanci`. `province` kelimede her hit için sıra şudur:

1. İlde `city_capable=1`, `state='active'`, `exhausted_until` geçmiş sağlayıcı aranır. Varsa `geo_mode='city'` ve proxy kullanıcı adına `city-<slug>` eklenir.
2. Yoksa `geo_mode='tr_fallback'`, `geo.uule` kullanılır ve Türkiye IP'si veren herhangi bir aktif sağlayıcı seçilir. İş durmaz.
3. Türkiye IP'si veren sağlayıcı hiç yoksa `geo_mode='yabanci'` ve yabancı çıkış kullanılır; sıralama yine uule ile Türkiye'ye sabitlenir.
4. Sonuç `provider_geo` tablosuna ve `hit.geo_mode` alanına yazılır.
5. Aynı sağlayıcı ve il çiftinde CAPTCHA oranı %35'i geçerse o çift 60 dakika `exhausted_until` alır.

`national` kelimede il seçimi: `burst_count` 3'ün altındayken core tier (nüfusa göre ilk 10 il) ağırlıklı, sonrasında 81 il arasında ağırlıklı rastgele. Seçim A-Res ile yapılır:

```sql
ORDER BY -LOG(RAND()) / g.weight LIMIT 1
```

`weight` generated kolondur ve `ROUND(SQRT(population))` ile hesaplanır.

Ölçüm daima ulusaldır. İl sıralaması ölçülmez.

Sağlayıcı seed'i `005_provider.sql` ile yüklenir. `city_capable` yalnızca il hedeflemeyi tam destekleyende 1'dir; "kısmi" destek 0 sayılır ve §5 adım 2 gereği ulusal moda düşer.

Sağlayıcı seçimi tür oranına göre yapılır. Oranlar ayar tablosundadır (`oran_residential`, `oran_mobil`, `oran_datacenter`) ve panelden düzenlenir. Toplam 100 değilse okurken normalize edilir. Önce tür kurası çekilir, sonra o türde `state='active'`, karantinası geçmiş, kimlik bilgisi dolu sağlayıcılar arasından A-Res ile seçim yapılır. Tür boş kalırsa sırayla residential ve datacenter denenir, hiçbiri yoksa doğrudan bağlantıya düşülür (C17). Mobil IP yalnızca burst'ün ilk 8 saniyesinde devreye girer.
Çerez seçimi kelimenin modalitesine göre yapılır. Mobil işaretli kelimede önce `mobile` türü sağlayıcı denenir, yoksa normal sıraya düşülür ve android profil kullanılır (C48). Çerez önceliği sabittir: aktif+il, aktif TR, diğer aktifler; aktifler bittiğinde süresi geçmişler aynı iç sırayla (C45). Mobil kelimede aynı sıra mobil çerezler öne alınarak uygulanır.

Sağlayıcı satırı `ulke` taşır; Türkiye IP'si veren sağlayıcılar `ulke='TR'` ile işaretlenir ve `tr_fallback` adımında yalnızca bunlar aranır.

Decodo residential ve mobile ayrı ürünlerdir; kimlik bilgileri sağlayıcı satırında tutulur, `.env`'de tek değer yetmez.

## 6. Şema

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
  mobil      TINYINT(1) NOT NULL DEFAULT 0,
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
  ulke             CHAR(2) NOT NULL DEFAULT 'TR',
  gateway          VARCHAR(128) NULL,
  kullanici        VARCHAR(128) NULL,
  sifre            VARCHAR(128) NULL,
  city_capable     TINYINT(1) NOT NULL DEFAULT 0,
  weight           SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  weight_yedek     SMALLINT UNSIGNED NULL,
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
  provider_id SMALLINT UNSIGNED NULL,
  profile_id  BIGINT UNSIGNED NULL,
  geo_code    TINYINT UNSIGNED NULL,
  geo_mode    ENUM('city','tr_fallback','yabanci') NOT NULL DEFAULT 'tr_fallback',
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
  kind         ENUM('captcha','provider_down','queue_lag','quota','fallback_high',
                    'hedef_yok','failover','burst_hata') NOT NULL,
  ref_id       BIGINT UNSIGNED NULL,
  keyword_id   BIGINT UNSIGNED NULL,
  site_id      BIGINT UNSIGNED NULL,
  message      VARCHAR(500) NOT NULL,
  acknowledged TINYINT(1) NOT NULL DEFAULT 0,
  created_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_open (acknowledged, created_at),
  KEY idx_kw (keyword_id, created_at),
  KEY idx_site (site_id, created_at),
  CONSTRAINT fk_al_kw   FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE SET NULL,
  CONSTRAINT fk_al_site FOREIGN KEY (site_id)    REFERENCES site(id)    ON DELETE SET NULL
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

CREATE TABLE dugum (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ad          VARCHAR(64) NOT NULL,
  ip          VARCHAR(45) NOT NULL UNIQUE,
  durum       ENUM('aktif','durduruldu') NOT NULL DEFAULT 'aktif',
  yuk         SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  cpu         DECIMAL(5,2) NOT NULL DEFAULT 0,
  ram         DECIMAL(5,2) NOT NULL DEFAULT 0,
  surum       VARCHAR(32) NULL,
  son_kalp_at DATETIME(3) NULL,
  kayit_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_secim (durum, son_kalp_at)
) ENGINE=InnoDB;

CREATE TABLE dugum_olay (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dugum_id   BIGINT UNSIGNED NOT NULL,
  tur        ENUM('kayit','kalp_kaybi','durdur','baslat','sil') NOT NULL,
  message    VARCHAR(255) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_dugum (dugum_id, created_at),
  CONSTRAINT fk_do_dugum FOREIGN KEY (dugum_id) REFERENCES dugum(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE ayar (
  anahtar        VARCHAR(64)  NOT NULL PRIMARY KEY,
  deger          VARCHAR(255) NOT NULL,
  guncellendi_at DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                 ON UPDATE CURRENT_TIMESTAMP(3)
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
- `provider` kimlik bilgilerini taşır, çünkü Decodo residential ve mobile ayrı ürünlerdir ve tek `.env` değeri ikisini birlikte çalıştıramaz.
- `weight_yedek` karantina sırasında ağırlığı saklar; sağlayıcı sabit bir değere değil kendi ağırlığına döner.
- `ayar` tablosu oranları, pencereyi, ölçüm aralığını ve SERP anahtarlarını taşır; panelden düzenlendiği için `.env`'de tutulamaz.
- `alert` türleri geniştir; panelde takip ekranı bu türleri filtreleyerek gösterir.
- `alert` satırı `keyword_id` ve `site_id` taşır; uyarının hangi site ve kelimeden çıktığı görünmeden takip mümkün değildir.
- `dugum` ayrı tablodur; dağıtıcı `.env` listesine değil kayıt defterine bakar, ölü sunucuyu ayırt eder ve düğüm bazlı durdurma uygulanabilir.
- `dugum_olay` kalp kaybını ve durdur/başlat geçmişini tutar; durum değişiminin ne zaman olduğu sonradan okunabilmelidir.

### 6.2 Seed zorunluluğu

- `geo` tablosu 81 kayıtla seed edilir: code, name, slug, population, lat, lon. Core tier nüfusa göre ilk 10 ildir: 34, 6, 35, 16, 7, 42, 1, 63, 27, 41. `uule` her il için bir kez üretilip yazılır.
- Nüfus değerleri TÜİK güncel verisiyle değiştirilebilir, yaklaşık değer kabul edilir.
- `ayar` tablosu şu anahtarlarla seed edilir: `oran_residential`, `oran_mobil`, `oran_datacenter`, `olcum_araligi_dk`, `serp_decodo`, `serp_serper`, `serp_searchapi`. SERP anahtarları boş başlar, panelden doldurulur.

### 6.3 Saklama süreleri

- `hit`: 30 gün, sonra silinir
- `burst`: 90 gün
- `position`: süresiz
- `traffic_daily`: süresiz
- `audit_log`: 1 yıl
- `alert`: 90 gün
- `dugum_olay`: 90 gün
- Partition, `hit` tablosu 10 milyon satırı geçince eklenir.

## 7. API sözleşmesi

Kimlik: oturum cookie'si + CSRF token. Worker uçları paylaşılan token ile.

### 7.1 Panel uçları

- `POST /api/giris` `{ eposta, parola }` → 200, yeni CSRF token
- `POST /api/cikis` → 204
- `GET  /api/ben` → oturum sahibi
- `GET  /api/ozet` → sayaçlar
- `GET  /api/site?q=` → `{ satirlar }`, her satırda `kelime_adet`
- `POST /api/site` `{ domain, label }`
- `PATCH /api/site/:id` `{ domain?, label?, active? }`
- `DELETE /api/site/:id` → 204
- `GET  /api/kelime?...&sayfa=&adet=` → `{ satirlar, toplam, sayfa, adet }`
- `POST /api/kelime` `{ site_id, kelime, kapsam, il?, volume? }`
- `PATCH /api/kelime/:id`
- `DELETE /api/kelime/:id` → 204
- `POST /api/kelime/:id/geo-yenile` → `{ geo_adet }`
- `POST /api/kelime/:id/baslat` → `{ id, state }`
- `POST /api/kelime/:id/durdur` → 204
- `GET  /api/provider?q=` → sağlayıcı listesi
- `POST /api/provider` / `PATCH /api/provider/:id` / `DELETE /api/provider/:id`
- `GET  /api/geo` → 81 il
- `GET  /api/uyari?...&sayfa=&adet=` → `{ satirlar, ozet, toplam, sayfa, adet }`
- `POST /api/uyari/:id/kapat` → 204
- `POST /api/uyari/tumunu-kapat` → `{ kapatilan }`
- `GET  /api/log?...&sayfa=&adet=` → `{ satirlar, toplam, sayfa, adet }`
- `GET  /api/rapor?...` → özet, site ve kelime kırılımı, günlük seri
- `GET  /api/dugum?...&durum=&kalp=` → düğüm listesi
- `POST /api/dugum` `{ ad, ip }`
- `PATCH /api/dugum/:id` `{ ad?, durum? }`
- `DELETE /api/dugum/:id` → 204
- `GET  /api/ayar` → ayar listesi; `serp_*` değerleri `••••` + son 4 hane olarak maskelenir
- `PATCH /api/ayar` → gövdedeki anahtarları yazar; maskeli değer geri gönderilirse atlanır
- `POST /api/ayar/serp-dene` `{ anahtar }` → `{ ok, organik?, kod?, sure_ms }`

- `POST /api/cerez/yukleme` `{ modalite }` → `{ id, klasor }`; tarayıcıdan parti parti yükleme
- `POST /api/cerez/yukleme/:id/parti` multipart → parti alındı
- `POST /api/cerez/yukleme/:id/baslat` → içe aktarma kuyruğa girer
- `GET  /api/cerez/yukleme/:id` → ilerleme ve havuz sayaçları
- `DELETE /api/cerez/yukleme/:id` → iptal, geçici klasör silinir
- `GET  /api/cerez` → havuz sayımı, durum ve son hatalı dosyalar
- `DELETE /api/cerez` → havuzu boşalt

Liste uçlarında sayfa 1'den başlar, `adet` 1-500 arasıdır ve varsayılanı 50'dir.

### 7.2 Worker uçları

- `GET  /health` → sürüm ve doluluk
- `POST /worker/burst` `{ keyword, target_url, geo_code?, geo_slug?, geo_mode, uule?, size }` → `{ ok, captcha, not_found, timeout, error, elapsed_ms }`
- `POST /api/worker/kalp` `{ ip, yuk, cpu, ram, surum }` → `{ durum }`. CSRF ve oturum denetiminin dışındadır; düğüm kaydı IP ile eşleşir, eşleşmezse 404.
- `POST /api/worker/kalp` cevabındaki `durum`, worker'ın iş alıp almayacağını belirler; `durduruldu` iken burst ucu 503 döner.

`keyword` oluşturulunca `keyword_geo` otomatik üretilir. `province` için 1 satır (core), `national` için 81 satır (10 core, 30 normal, 41 passive).

## 8. Sağlayıcı politikası

Proxy sağlayıcıları, ağırlık ve şehir hedefleme durumu:

- Decodo, residential, ağırlık 25, şehir hedefleme kısmi
- Bright Data, residential, ağırlık 20, şehir hedefleme var
- Oxylabs, residential, ağırlık 15, şehir hedefleme var
- Decodo, mobile, ağırlık 25, şehir hedefleme kısmi
- SOAX, mobile, ağırlık 10, şehir hedefleme var
- IPRoyal, residential, ağırlık 5, şehir hedefleme kısmi
- Webshare, datacenter, sadece smoke test

SERP API sağlayıcıları: Decodo /search birincil, Serper yedek, SearchApi.io yedek. Anahtarlar `ayar` tablosundadır, panelden girilir ve maskeli gösterilir.

Mobil IP'ler burst'ün ilk 8 saniyesinde tüketilir. Sağlayıcı anahtarları kullanıcıya aittir, yazılım yalnızca tüketir.

Devre kesici iki seviyelidir. Sağlayıcı/il çiftinde CAPTCHA %35'i geçerse çift 60 dakika tükenir (C18). Sağlayıcı genelinde oran %20'yi geçerse sağlayıcı 2 saat karantinaya alınır, ağırlığı yedeğe alınıp sıfırlanır. Karantina dolunca ağırlık yedekten geri verilir ve oran sıfırlanır. Oranlar en az 10 örnek toplanmadan değerlendirilmez.

Sağlayıcı düşerse hit bir kez, yeni sağlayıcı ve yeni profille tekrarlanır (C6). Üçüncü deneme yapılmaz.

## 9. Hız sabitleri

- Dwell: 5-12 saniye
- Pogo: 1 istek, 3-6 saniye sonra
- Alt kaynak: yok
- Eşzamanlılık: sunucu başına 12
- Tur aralığı: 25-40 dakika
- `keyword_geo` cooldown: 20-35 dakika rastgele
- Ölçüm aralığı: `ayar.olcum_araligi_dk` (varsayılan 0 = yalnızca cooldown sırası)
- Basamak boyu: en fazla 60 hit
- Hit arası bekleme: 0,4-1,4 saniye, jitter'lı
- API sayfaları arası bekleme: 0,6-1,3 saniye
- Aynı hit içindeki izlenim, tıklama ve pogo tek oturumdan geçer; cookie sürekliliği korunur, oturum hit sonunda kapanır
- Mobil pencere: burst'ün ilk 8 saniyesi; pencere kapanınca mobil IP kullanılmaz

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

Panel kelime başına şunları gösterir: başarı oranı, yedek oranı, sıralama eğrisi, trend. Yedek oranı %30'u geçerse uyarı üretilir. Rapor ve log ekranları CSV indirir.

## 11. Kabul kriterleri

- C1 — Panelde site ve kelime CRUD, start/stop, canlı log çalışır.
- C2 — `start` verildikten sonra ilk hit 30 saniyenin altında atılır.
- C3 — Worker `/burst` p95 süresi 45 saniyenin altındadır.
- C4 — Her hit yeni IP ve taze cookie ile gider; parmak izi çerez profilinde sabittir ve oturumun üç adımında da aynı profil kullanılır. Oran %100'dür.
- C5 — Parmak izi gerçek tarayıcı ile birebir eşleşir. Ölçüt küme üyeliğidir: ölçülen ja4 ve ja3, `docs/tls_reference.json` içindeki profilin kümelerinde bulunmalıdır. Chromium 110+ uzantı sırasını karıştırdığı için ja3 bağlantı başına değişir, JA4 ise ALPN/SNI varyansıyla birden fazla değer alabilir. Havuz güncel Chrome (142-152), Firefox (153-155), Safari (260/270) ve mobil için `chrome131_android` taşır; Safari, Firefox ve Edge yalnızca çerezsiz durumda seçilir. Kanıt: `python tools/tls_check.py --all`.
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
- C17 — Şehir hedefleyen sağlayıcı yokken iş durmaz, ulusal moda düşer.
- C18 — Sağlayıcı ve il çiftinde CAPTCHA %35'i geçerse 60 dakika `exhausted_until` uygulanır.
- C19 — `burst_count` 3'ün altındayken core tier, sonrasında broad faz kullanılır.
- C20 — Ölçüm daima ulusal ve clean kanaldan yapılır; oran %100'dür.
- C21 — `stop` sonrası yeni hit atılmaz.
- C22 — Tüm `DATETIME` değerleri UTC'dir; oran %100'dür.
- C23 — `uule` 81 ilin tamamında doludur.
- C24 — Sırlar repoda değil, ortam değişkeninde veya veritabanındadır; repoda düz metin yoktur.
- C25 — Aynı burst'ün tekrar işlenmesi idempotenttir, aynı sonucu verir.
- C26 — pytest ve vitest hem Windows hem Linux'ta geçer.
- C27 — CI matrisi windows-latest ve ubuntu-22.04 içerir; ikisi de yeşildir.
- C28 — Depoda CRLF yoktur; `git ls-files --eol` temiz döner.
- C29 — Hiçbir modülde sabit `os.sep` veya `\\` yolu yoktur; lint kuralı geçer.
- C30 — Docker imajı linux/amd64 üzerinde Debian 12'dir.
- C31 — Aynı hit içindeki üç adım tek oturum kullanır; oran %100'dür. Kanıt: `pytest worker/test_oturum.py`.
- C32 — Sağlayıcı düşerse hit yeni sağlayıcıyla en fazla bir kez tekrarlanır. Kanıt: `pytest worker/test_burst.py`.
- C33 — Karantina ağırlığı yedekten geri verir, sabit değere dönmez. Kanıt: `python tools/saglik_dene.py`.
- C34 — Oranlar toplamı 100 değilse normalize edilir; `oran_mobil=0` mobil havuzunu tamamen kapatır. Kanıt: `pytest worker/test_havuz.py`.
- C35 — `.env` yalnızca önyükleme sırlarını taşır: `MYSQL_*`, `REDIS_URL`, `SESSION_SECRET`, `WORKER_TOKEN`. Proxy kimliği, SERP anahtarı ve ölçüm aralığı `.env`'de bulunmaz.
- C36 — SERP anahtarları veritabanındadır, panelde maskeli gösterilir ve maskeli değer geri yazıldığında gerçek değer korunur.
- C37 — Kayıtlı ve aktif düğüm varken dağıtıcı işi yalnızca kalbi 45 saniyeden taze düğüme atar.
- C38 — Panelde durdurulan düğüm yeni iş almaz, iş diğer düğüme kayar.
- C39 — Liste uçları `sayfa` ve `adet` alır, `toplam` döner; `adet` üst sınırı 500'dür.
- C40 — `geo_mode` üç değerlidir; `yabanci` yalnızca Türkiye IP'si veren sağlayıcı kalmadığında kullanılır.
- C41 — Her uyarı satırı `keyword_id` ve `site_id` taşır; liste site ve kelimeyi gösterir.
- C42 — Yıkıcı işlemler (silme, toplu kapatma) onay ister; bilinmeyen yol 404 ekranına düşer.
- C43 — `ayar` okuması worker'da önbelleklidir; tablo okunamazsa `.env`, o da yoksa varsayılan devreye girer ve iş durmaz.
- C44 — Çerez, site+kelime çiftinde bir kez kullanılır; farklı sitede aynı kelime için yeniden kullanılabilir. Çift kaydı `cookie_kullanim` ile tutulur.
- C45 — Çerez önceliği sabittir: aktif+il, aktif TR, diğer aktifler, sonra süresi geçmiş aynı iç sırayla. Süresi geçmişler aktifler bitmeden devreye girmez.
- C46 — Çerez ülkesi IP ülkesiyle eşleşmeden çerez yüklenmez; yabancı çıkışta çerez kullanılmaz.
- C47 — Çerez profili parmak izi ailesini (`chrome`, `firefox`, `safari`, `bilinmiyor`) taşır; istek o aileyle gider, çerez yoksa profil rastgele seçilir.
- C48 — Mobil işaretli kelimede önce mobil çerez ve `mobile` sağlayıcı denenir; mobil sağlayıcı yoksa iş durmaz, normal proxy'ye düşer ve android profil kullanılır.
- C49 — Havuz boşken veya çerez kapalıyken iş hiçbir yolda durmaz; çerez yüklenemezse istek çerezsiz devam eder.

C7, C8, C9, C10, C11, C12 ve C15 pilot kabulünde ölçülür.

## 12. Kilometre taşları

- M1 — Migration seti, geo seed, uule üretici, CI iskeleti (3 gün)
- M2 — Python worker, curl_cffi, JA3 doğrulama, 100 hit testi (1 hafta)
- M3 — Sağlayıcı havuzu, circuit breaker, gözlemlenebilirlik (1 hafta)
- M4 — Node control plane, panel, kuyruk (1 hafta)
- M5 — Ölçüm A/B hattı, rapor (1 hafta)
- M6 — 5 sunucu pilot, 20 kelime, 2 hafta saha testi (2 hafta)
- M7 — 20 sunucuya ölçekleme ve devir (1 hafta)

## 13. Devir kriteri

M6 sonunda C7, C8, C9, C10, C11, C12, C15 ve C26-C30 sağlanıyorsa proje kabul edilir. Sağlanmıyorsa M3-M5 iyileştirme turu tekrarlanır. Devir kapsamı: kod, migration dosyaları, seed scripti, README, `.env.example`, docker-compose, `.gitattributes`.

## 14. Bakım

`not_found` oranı %5'i geçerse 24 saat içinde SERP regex revizyonu yapılır. `curl_cffi` sürüm takibi aylıktır. Sağlayıcı anahtar ve ağırlık güncellemesi süreklidir. SERP anahtarı değişimi panelden yapılır, kod dağıtımı gerekmez.

## 15. Varsayımlar

Kullanıcıda hazır bileşen yoktur; geo seed, uule üretici, migration seti, docker-compose ve README yüklenici tarafından üretilir. Hedef kelime sayısı 100'ü geçmez. Şehir hedefleme sağlayıcı sözleşmelerine bağlıdır; sağlanamazsa C17 devreye girer, sistem çalışır ancak il bazlı IP sinyali üretmez.

## 16. Değişiklik kontrolü

§3, §4, §5, §6, §11 ve §18 maddeleri M4 tamamlandıktan sonra değişirse ayrı kapsam sayılır. Diğer maddeler mutabakatla güncellenir.

## 17. Altyapı

- 17.1 — Tüm sunucular Debian 12 x86_64'dir. Windows yalnızca geliştirme makinesidir.
- 17.2 — Her bileşen Docker imajıdır. İmajlar digest ile pinlenir. `curl-impersonate` sürümü imaj içinde sabittir, host'a kurulmaz.
- 17.3 — Sertleştirme: root olmayan kullanıcı, read_only rootfs, cap_drop: ALL, restart: always.
- 17.4 — Bulut bağımsızlığı: kod hiçbir bulut sağlayıcısının API'sine bağlı değildir.
- 17.5 — Worker'lar public alt ağda çalışır; NAT Gateway maliyeti doğmaz.
- 17.6 — MySQL günlük `mysqldump` ile yedeklenir, 7 gün saklanır, offsite kopya alınır. Geri yükleme aylık test edilir.
- 17.7 — Sırlar ortam değişkeninde veya secret store'da tutulur; repoda düz metin yoktur.

## 18. Geliştirme ortamı — Windows'ta yaz, Linux'ta çalıştır

Kod Windows'ta yazılır, Linux'ta çalışır. Aşağıdaki maddeler bağlayıcıdır.

### 18.1 Yol ve dosya adları

- Tüm dosya yolları Python'da `pathlib.Path`, Node'da `node:path` ile kurulur. Sabit `/` veya `\\` yazılmaz.
- Dosya adlarında `: * ? " < > |` karakterleri kullanılmaz.
- Windows rezerve adları (CON, PRN, AUX, NUL, COM1-9, LPT1-9) kullanılmaz.
- Yol uzunluğu 260 karakteri geçmez.
- Symlink kullanılmaz.
- Dosya ve klasör adlarında büyük-küçük harf karışıksa import ve require birebir eşleşmek zorundadır; Windows toleranslıdır, Linux değildir.

### 18.2 Satır sonu

- Depoda yalnızca LF kullanılır. `core.autocrlf=false` ve `.gitattributes` zorunludur (Ek A).
- `.sh` dosyaları LF ve `#!/usr/bin/env bash` ile yazılır.

### 18.3 Kabuk ve süreç

- Kabuk çağrısı minimumdur. Gerektiğinde Python'da `subprocess` ve `shell=False`, Node'da `execFile` kullanılır.
- `&&`, `;`, `$VAR` içeren tek satır komutlar kullanılmaz; mantık dile taşınır.
- Node script'lerinde `cross-env` kullanılır, `FOO=bar cmd` biçimi kullanılmaz.
- `os.fork` ve `fcntl` kullanılmaz. Dosya kilidi için `filelock` veya `portalocker` kullanılır.

### 18.4 Ortam değişkenleri ve zaman

- `.env` yalnızca önyükleme sırlarını taşır: `MYSQL_*`, `REDIS_URL`, `SESSION_SECRET`, `WORKER_TOKEN`.
- Kodla türetilebilen değerler `.env`'de tutulmaz: panel portu, worker portu, düğüm IP'si, worker adresi. Bunlar koddaki varsayılandan veya kayıt defterinden çözülür; isteğe bağlı olarak ortam değişkeniyle ezilebilir.
- Yönetim verisi `.env`'de tutulmaz: proxy kimliği `provider` satırında, SERP anahtarı ve ölçüm aralığı `ayar` tablosundadır.
- `.env.example` doldurulacak alanları yorumla açıklar, gerçek sır taşımaz.
- Saat dilimi her yerde UTC'dir. Yerel saat varsayımı yapılmaz. `tzdata` imaja dahildir.
- Python venv Windows'ta `Scripts`, Linux'ta `bin` altındadır; betiklerde ikisi de aranmaz, `python -m` kullanılır.

### 18.5 Yerel servisler

- MySQL ve Redis yerelde çalışır; geliştirme makinesinde yerel kurulum kabul edilir.
- Üretimde her bileşen konteynerdir.

### 18.6 Test ve CI

- Tüm testler iki platformda geçmek zorundadır. CI matrisi windows-latest ve ubuntu-22.04 içerir.
- Platforma özel dallanma gerekiyorsa `sys.platform` veya `process.platform` ile tek noktada ve yorumla yapılır.

### 18.7 Parmak izi

- `curl_cffi` Windows'ta çalışır ancak JA3 doğrulaması iki platformda da koşar (C5). Yalnızca Windows'ta doğrulanmış parmak izi kabul edilmez.
- Docker imajı linux/amd64 üzerinde Debian 12'dir.

## 19. Ek A — .gitattributes

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

## 22. Sürüm kaydı

- 1.2 — Tablosuz sözleşme; tüm listeler madde işaretine çevrildi.
- 1.3 — §18 Windows/Linux ayrımı, §19 `.gitattributes`, §20 yasak yapılar, §23 kodlama kuralları, §24 cookie politikası, C5 güncellendi. Google'ın JavaScript zorunluluğu §4'e işlendi.
- 1.4 — §3 worker yazma istisnası, §5 sağlayıcı seçimi ve tür oranları, §6 kimlik sütunları ve ayar tablosu, §8 iki seviyeli devre kesici, §11 C31-C34, alert türleri genişletildi.
- 1.6 — §3 cookie tablosu istisnası, §5 mobil öncelik, §6 `keyword.mobil` ve cookie tabloları, §7 cookie uçları, §9 mobil pencere, §11 C4/C5 güncellendi, C44-C49, §24 yeniden yazıldı, §26 cookie alt sistemi.
- 1.5 — §3 `ayar` okuma istisnası, §4 düğüm seçimi, §5 `geo_mode` üç değeri ve `provider.ulke`, §6 `dugum`, `dugum_olay`, `alert` bağlam sütunları, §7 panel ve worker uçlarının tamamı ile sayfalama, §8 SERP anahtarlarının veritabanında tutulması, §9 ölçüm aralığının ayara taşınması, §10 CSV, §11 C35-C43, §14 anahtar değişiminin panelden yapılması, §18.4 `.env` disiplini.

## 23. Kodlama kuralları (bağlayıcı)

### 23.1 Yorum zorunluluğu — Türkçe

- Her dosyanın başında, dosyanın ne işe yaradığını ve nerede kullanıldığını anlatan en az üç satırlık Türkçe blok bulunur.
- Her fonksiyon ve metot, Türkçe docstring taşır; ne yaptığını, parametrelerini, dönüş değerini ve fırlattığı hataları yazar.
- Her karmaşık blok (döngü, dallanma, retry, seçim mantığı) öncesinde "neden böyle" sorusunu yanıtlayan Türkçe yorum bulunur.
- Her sihirli sayı, birimi ve gerekçesiyle yorumlanır. Örnek: `DWELL_MIN = 5 saniye; tık sayılsın yeter, hız öncelikli`.
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
- Üretilmiş dosyalar (build çıktısı, node_modules, .venv, log, dist) repoya girmez.
- Test dosyası, test edilen modülün yanında ve aynı adla `*.test.ts` / `test_*.py` biçiminde durur.
- Kullanılmayan bağımlılık `package.json` / `requirements.txt` içinde bırakılmaz.

### 23.3 Ücretsiz servis önceliği

Geliştirme aşamasında (M1-M5) ücretsiz katmanlar kullanılır:

- SERP ölçümü: Decodo ücretsiz plan (10 bin istek) ve Serper ücretsiz kota (2.500).
- Yerel MySQL ve Redis: konteyner, ek ücret yok.
- CI: GitHub Actions ücretsiz dakikalar.
- İzleme: kendi Prometheus ve Grafana konteynerleri.
- Hata izleme: Sentry ücretsiz katman veya self-host.
- Test hedef sitesi: kullanıcının kendi domaininde ücretsiz alt alan adı.
- Proxy: M2-M5 için Decodo ücretsiz plan ve IPRoyal deneme kredisi.

Paralı kaynağa yalnızca şu üç durumda geçilir:

- Gerçek residential trafik hacmi (M6 pilot, kaçınılmaz).
- Şehir hedefleme doğrulaması için ücretli sağlayıcı teyidi.
- 20 sunucuya ölçekleme (M7).

Ücretsiz katman sınırına dayanan her yerde kod, kotayı aşınca uyarı üretir ve sessizce durmaz.

## 24. Cookie politikası

- Her istek taze oturumla başlar; SOCS ve CONSENT onay duvarını atlar.
- Aynı hit içinde oturum korunur, AEC/NID gibi cookie'ler tıklamaya taşınır.
- Statik NID yapıştırılmaz; Google'ın üretmesine izin verilir.
- Gerçek tarayıcıdan alınmış cookie dosyaları desteklenir: Netscape biçimi ve EditThisCookie JSON; dosya başına tek profil.
- Çerez, site+kelime çiftinde bir kez kullanılır; farklı sitede tekrar kullanılabilir. Kullanım `cookie_kullanim` ile kayıt altındadır.
- Çerez ülkesi cookie alan adlarından türetilir; yabancı çıkışta çerez yüklenmez.
- Süresi geçmiş çerezler silinmez; aktifler tükendiğinde `cerez_suresiz_kullan` açıksa kullanılır.
- İçe aktarımda profil parmak izi ailesi atanır ve istek boyunca değişmez.
- Yükleme tarayıcıdan yapılır: parti parti multipart, geçici klasör, canlı ilerleme, iptal. Sunucu yolu paylaşılmaz.
- Havuz boşken sistem çerezsiz çalışmaya devam eder; çerez yokluğu hata değildir.
- Cookie dosyaları repoya girmez.
- Cookie'ler JavaScript duvarını aşmaz; sonuç listesi yine API'den gelir.
## 25. Değişiklik özeti (1.6)

- §3: cookie tabloları için worker istisnası
- §5: mobil öncelik ve çerez önceliği sırası
- §6: `keyword.mobil`, `cookie_profil.mobil/ulke/parmak_izzi`, `cerez_yukleme.modalite`
- §7: cookie yükleme uçları
- §9: mobil pencere
- §11: C4/C5 güncellendi, C44-C49 eklendi
- §22: 1.6 kaydı
- §24: cookie politikası yeniden yazıldı
- §26: cookie alt sistemi

- §3: `ayar` salt okuma istisnası ve `ayar_db` önbelleği
- §4: düğüm kayıt defterinden seçim, boş defterde yerel varsayılan
- §5: `geo_mode` üç değeri, `provider.ulke`, `yabanci` son çare
- §6: `dugum`, `dugum_olay`, `alert.keyword_id/site_id`, `hit.geo_mode` üç değer, `provider.ulke`, `ayar` seed anahtarları, `dugum_olay` saklama
- §6.1: beş yeni gerekçe
- §7: tüm panel uçları, sayfalama parametreleri, `/api/worker/kalp`, `/api/ayar/serp-dene`, maskeleme kuralı
- §8: SERP anahtarlarının veritabanında tutulması
- §9: ölçüm aralığının `ayar` üzerinden gelmesi
- §10: CSV çıktısı
- §11: C35-C43
- §14: anahtar değişiminin panelden yapılması
- §18.4: `.env` disiplini, türetilebilir değerlerin dosyadan çıkarılması

## 26. Cookie alt sistemi

Çerez havuzu, gerçek tarayıcıdan alınmış dökümlerin panelden yüklenmesiyle beslenir. Panel dosyaları ayrıştırır ve MySQL'e yazar; worker yalnızca sahiplenir ve okur. Havuz boşken sistem çerezsiz çalışmaya devam eder.

### 26.1 Şema

```sql
CREATE TABLE cookie_dosya (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ad            VARCHAR(255) NOT NULL,
  tur           VARCHAR(16) NULL,
  boyut         INT UNSIGNED NULL,
  ozet          CHAR(64) NULL,
  satir_sayisi  INT UNSIGNED NULL,
  il_kodu       TINYINT UNSIGNED NULL,
  durum         ENUM('bekliyor','isleniyor','aktarildi','mukerrer','gecersiz') NOT NULL DEFAULT 'bekliyor',
  hata          VARCHAR(255) NULL,
  kaynak        VARCHAR(16) NOT NULL DEFAULT 'tarayici',
  yukleyen      BIGINT UNSIGNED NULL,
  yukleme_id    BIGINT UNSIGNED NULL,
  isleniyor_at  DATETIME(3) NULL,
  created_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_cd_durum (durum, isleniyor_at),
  KEY idx_cd_ozet (ozet)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cerez_yukleme (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  kullanici_id BIGINT UNSIGNED NULL,
  klasor       VARCHAR(255) NOT NULL,
  modalite     TINYINT(1) NOT NULL DEFAULT 0,
  durum        ENUM('yukleniyor','hazir','aktarim','bitti','iptal') NOT NULL DEFAULT 'yukleniyor',
  created_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cookie_profil (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dosya_id      BIGINT UNSIGNED NOT NULL,
  ad            VARCHAR(191) NOT NULL,
  il_kodu       TINYINT UNSIGNED NULL,
  ulke          CHAR(2) NULL,
  parmak_izzi   VARCHAR(16) NULL,
  mobil         TINYINT(1) NOT NULL DEFAULT 0,
  sona_erme     DATETIME(3) NULL,
  suresi_gecmis TINYINT(1) NOT NULL DEFAULT 0,
  durum         ENUM('hazir','kullaniliyor','bozuk') NOT NULL DEFAULT 'hazir',
  kullanim      INT UNSIGNED NOT NULL DEFAULT 0,
  dugum_id      SMALLINT UNSIGNED NULL,
  alindi_at     DATETIME(3) NULL,
  created_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_cp_secim (durum, suresi_gecmis, ulke),
  KEY idx_cp_mobil (durum, mobil),
  KEY idx_cd_dosya (dosya_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cookie (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  profil_id     BIGINT UNSIGNED NOT NULL,
  domain        VARCHAR(191) NOT NULL,
  ad            VARCHAR(191) NOT NULL,
  deger         TEXT NOT NULL,
  yol           VARCHAR(255) NOT NULL DEFAULT '/',
  sona_erme     DATETIME(3) NULL,
  guvenli       TINYINT(1) NOT NULL DEFAULT 0,
  http_only     TINYINT(1) NOT NULL DEFAULT 0,
  same_site     VARCHAR(8) NULL,
  oncelik       VARCHAR(8) NULL,
  oturumluk     TINYINT(1) NOT NULL DEFAULT 0,
  partition_ust VARCHAR(191) NULL,
  partition_ata TINYINT(1) NULL,
  same_party    TINYINT(1) NOT NULL DEFAULT 0,
  boyut         INT UNSIGNED NULL,
  kaynak_port   SMALLINT UNSIGNED NULL,
  kaynak_sema   VARCHAR(8) NULL,
  KEY idx_profil (profil_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cookie_kullanim (
  profil_id  BIGINT UNSIGNED NOT NULL,
  site_id    BIGINT UNSIGNED NOT NULL,
  keyword_id BIGINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (profil_id, site_id, keyword_id),
  KEY idx_ck_cift (site_id, keyword_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 26.2 Kurallar

- `tukendi` durumu yoktur; profil kullanımdan sonra `hazir`a döner, tükenme çift bazındadır.
- `cookie_kullanim` birincil anahtarı çifti taşır; aynı profil aynı çiftte ikinci kez seçilmez.
- Kuyruk kiralamalıdır: sahiplenme `durum` ve `isleniyor_at` ile yapılır, `FOR UPDATE SKIP LOCKED` kullanılır, çöken düğümün satırı geri alınır.
- İçe aktarım `parmak_izzi` ailesini cookie adlarından türetir: `__Secure-BUCKET` firefox; `SIDCC`, `__Host-GAPS`, `SEARCH_SAMESITE`, `AEC` chrome; işaret yoksa bilinmiyor.
- Ülke cookie alan adlarından türetilir; TR ve yabancı ayrımı IP eşleşmesinde kullanılır.
- `mobil` alanı yükleme kaydından gelir; mobil kelimede mobil çerezler öne alınır.
- Geçici klasör `CEREZ_YUKLEME_KOK` altındadır ve kalıcı birimde durur; düğüm kimliği `DUGUM_ADI` ile verilir.
- `temizle` globaldir ve geri alınamaz; onay ister.