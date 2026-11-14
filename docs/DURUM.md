$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\developer\Desktop\App\unique_request_bot'
$utf8 = New-Object System.Text.UTF8Encoding($false)

$rapor = @'
# DEVIR — 2026-11-14

Bu dosya, işi devralan ajan içindir. Önce tamamını oku, sonra "Açık işler" bölümünün
en üstünden başla. Her adımda "Doğrulama" bölümündeki kapıları çalıştır.

## 1. Amaç ve başarı ölçütü

unique_request_bot: panelden yönetilen Google istek patlatma motoru. Node/TS kontrol
düzlemi + Python fetch worker + MySQL. Hedef Debian 12.

Başarı ölçütü tek: gerçek Google isteklerinde kabul oranı. Ölçülmeyen iş bitmiş sayılmaz.
Kural: kullanıcı açıkça onaylamadan yeni backlog maddesine başlama; doğrudan soruları
kodlamadan önce cevapla.

## 2. Kurallar (ihlal edilirse iş çöpe gider)

- **Commit atma.** Commitleri kullanıcı gönderir. Sadece kod bırak.
- **Her PowerShell bloğu tek yapıştırma birimi olacak.** Dosya referansı verilecekse
  blok kendi kendine yetsin.
- **Sunucu tarafından dosya seçtirme yok.** Yüklemeler tarayıcıdan; çok kullanıcılı
  kurulumda sunucu yolu paylaşılamıyor.
- Kullanıcı Türkçe yazar, Türkçe cevap ver. Emoji yok.

## 3. Ortam

- Proje kökü: `C:\Users\developer\Desktop\App\unique_request_bot`
- Python: `.venv\Scripts\python.exe` (sistemde python/mysql CLI yok)
- DB erişimi: `tools/db.py` bir kütüphanedir, CLI değil. Sorgu için:
  `.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'tools'); import db; c=db.baglan(); cur=c.cursor(); cur.execute('SELECT ...'); [print(r) for r in cur.fetchall()]"`
- Migration: `.venv\Scripts\python.exe tools\migrate.py`
- Şema doğrulama: `.venv\Scripts\python.exe tools\verify.py` (beklenen: 25 tablo, migration 31)
- Panel: `http://127.0.0.1:8080` — `/saglik` (oturumsuz), `/api/*` (oturum + CSRF)
- Giriş akışı (API testleri için): `GET /api/token` → `{"token"}`; `POST /api/giris`
  gövde `{"eposta":"...","sifre":"..."}` başlık `x-csrf-token`; yanıttaki `token` yenilenir.
  Yanlış alan adı 400, eksik token 403 verir.
- XAMPP sadece test ortamı. Docker yok. Decodo kotası dolu.

## 4. Mevcut durum (son ölçüm)

- 25 tablo, migration 31, 81-81 geo+uule. `verify.py` temiz.
- `cookie_dosya`: 57.443 satır — 57.443 aktarıldı, 8.769 mükerrer, 232 geçersiz.
- `cookie_profil`: 57.443 toplam; 22.704 aktif, 34.739 süresi geçmiş, 39.961 TR,
  10.090 yabancı, 7.507 il eşleşen. Parmak izi: 50.741 chrome, 5.295 firefox, 1.407 bilinmiyor.
- Testler: 67 worker, 23 arayüz. `tsc` iki configte sessiz, `npm run build` geçiyor.
- curl_cffi 0.17.0; `tools/tls_check.py --all` 13 profil / 0 hata / 0 sapma.
- Son commitler: `9fac375`, `1f57c6f` (parmak izi + havuz).

## 5. Son turda yapılanlar

Mobil/web ayrımı uçtan uca kuruldu:
- `db/migrations/031_modalite.sql`: `keyword.mobil`, `cookie_profil.mobil` + `idx_cp_mobil`,
  `cerez_yukleme.modalite`.
- `src/server/cerez.ts`: yükleme `modalite` alıyor, içe aktarımda `cookie_profil.mobil`'e
  taşınıyor; özet sayacında `mobil`/`web`.
- `src/server/kelime.ts`: `mobil` ekleme ve PATCH şemalarında, INSERT/UPDATE'te, liste ve
  yanıt seçimlerinde.
- `worker/havuz.py`: `cerez_sec(..., mobil)` mobil çerezleri öne alır; `sec_mod(...,
  zorunlu_tur)` önce `mobile` sağlayıcıyı dener, yoksa normal sıraya düşer; `kelime_mobil()`.
- `worker/burst.py`: `mobil_hedef` sağlayıcı ve çerez seçimine geçer, mobil kelimede android
  profil zorlanır.
- `src/web/sayfa/cerezler.tsx`: Web/Mobil seçimi + sayaç.
- `src/web/sayfa/kelimeler.tsx`: Mod sütunu, satır anahtarı, düzenleme modalında Mod alanı.

## 6. Açık işler (öncelik sırası)

1. **Sözleşme v1.6.** `docs/CONTRACT.md` v1.5 kilitli; şu alanlar ve kural yazılmalı:
   `keyword.mobil`, `cookie_profil.mobil`, `cerez_yukleme.modalite`, mobil öncelik kuralı
   (mobil kelimede önce mobil çerez + mobile sağlayıcı, yoksa normal). C5 metni hâlâ
   `edge101`/`safari17_0` sabit diyor; güncel havuzla değiştir.
2. **Mobil modu gerçek istekle dene.** `mobile` sağlayıcı yokken residential'a düşüş ve
   mobil SERP ayrıştırması. Decodo kotası dolu; kota yenilenince ilk iş bu.
3. **Çerez canlılığını ölç.** 22.704 "aktif" canlı demek değil. Örneklem al, gerçek kabul
   oranını çıkar. Ölçmeden başarı varsayma.
4. **`oran_mobil` şu an 0.** Android profil ancak sağlayıcı `mobile` ise çıkar; oran
   açılmadan mobil yol hiç çalışmaz. Panelden açılmalı.
5. A3 — kelime üst üste N kez `hedef_yok` dönerse otomatik durdur.
6. A5 — `sahiplen === 0` dalı `keyword_geo` satırını `running` bırakabiliyor.
7. A10 — ölçümü tur sonuna al, kelime başına sayfa sayısını kıs.
8. A11 — partition oluşturma/silme ve saklama işlerini zamanla (hit 30g, alert 90g, audit 1y).
9. A12 — `sahte_veri.py` ve tools betiklerini yeni UTC oturumu altında gözden geçir.
10. A13 — `hedefDenetle` gerçek hit yerine `target_count` topluyor.
11. C1/C2 — `burst.stats` JSON, `dugum_olay.dugum_id` tipini `dugum.id` ile doğrula.
12. C3-C7 — kalan sözleşme güncellemeleri (dugum şeması, hits gövdesi, result alanı,
    burst imzası, nullable provider_id, iki durumlu keyword_geo, gunluk_tavan kaldırma).
13. D1-D3, D6 — `isci.ts`, uyarı filtresi, `hedef_yok` eşiği, `app.py` imza tarafı testleri.
14. D4/D5 — CI'ı yeniden çalıştır, `verify.py`/`lint_yol.py` kapsamını kontrol et.
15. B6/B8/B9/B12 — HTTPS/HSTS, sır saklama, Redis requirepass, eşik sınır doğrulaması.
16. E1-E7 — yedek, loglama, worker healthcheck, zarif boşaltma, migration geri alma,
    metrik ucu, tek örnek kilidi.
17. F1/F4/F5 — Decodo TR kimlik/çıkış IP doğrulama, click/pogo uçtan uca, 100'lük hit bölme.
18. G1-G5 — önbellek notu, `olcum_araligi` üst sınırı, NOW/UTC taraması, `verify.py`
    taban kayması, `pytest.ini` temizliği.
19. Geçici `docs/*.py` ve `docs/yedek` temizliği.
20. `cookie_kullanim` yetim satır temizliği; `temizle` sırasında çalışan yüklemenin iptali
    ve geçici klasör silme.
21. 232 geçersiz dosya yeniden yüklenmeli (ayrıştırıcı düzeltildi, geçici kopyalar silindi).

## 7. Bilinen tuzaklar

- **Satır sonu:** bazı dosyalar CRLF. Çok satırlı çapa CRLF dosyada tutmaz. Her düzenlemede
  içeriği `-replace "`r`n", "`n"` ile normalize et.
- **Kodlama:** `Get-Content -Raw` ANSI okur, Türkçe karakterli çapa tutmaz ve dosyayı
  bozar. Daima `[System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)` ve
  `WriteAllText(..., New-Object System.Text.UTF8Encoding($false))` kullan.
- **BOM:** SQL dosyasına BOM yazılırsa MariaDB 1064 verir. UTF8Encoding($false) şart.
- **`Resolve-Path`** var olmayan dosyada patlar; yeni dosya yazarken `"$PWD\..."` kullan.
- **`Set-Content -Encoding utf8`** BOM ekler ve ANSI okuma ile çift kodlama yapar.
- **JSX:** tablo hücrelerini regex ile değiştirirken iç içe `<td>` bırakmak kolay. Sonrasında
  `([regex]::Matches($k,'<td')).Count` ile `</td>` sayısını karşılaştır ve `npm run build` koş.
- **`havuz.cerez_sec`** artık demet döndürür `(profil_id, parmak_izzi)`; `sec_mod` 4'lü demet.
  Tek eleman bekleyen çağrıları bozarsın.
- Node süreçlerini öldürüp yeniden başlatmak gerekir; sağlık için 15 sn bekle.

## 8. Kararlar ve gerekçeleri

- **`gl`/`hl` = `tr`/`tr` sabit.** Hedef TR sıralaması; yabancı IP'den `gl=tr` ile Türkçe
  sonuç almak istenen davranış. `gl`'yi IP ülkesine bağlamak TR sıralamasını bozar.
- **Safari/Firefox/Edge çerezli yolda yok.** Çerez varsa yalnız Chrome (veya aile firefox ise
  Firefox) profili; geniş havuz yalnız çerezsiz. Safari işareti güvenilir olmadığı için
  hiçbir profil safari atanmıyor.
- **`bilinmiyor` aile Chrome'a düşer.** Güvenli varsayılan.
- **Süresi geçmiş çerezler kullanılır** (`cerez_suresiz_kullan`), aktifler bitmeden devreye
  girmez.
- **Çerez site+kelime çiftinde bir kez kullanılır**, farklı sitede tekrar kullanılabilir.
- **Öncelik:** aktif+il → aktif TR → diğer aktifler → süresi geçmiş aynı iç sırayla.

## 9. Doğrulama

.venv\Scripts\python.exe -m pytest worker -q
npx vitest run
npx tsc -p tsconfig.server.json --noEmit
npx tsc --noEmit
npm run build
.venv\Scripts\python.exe tools\verify.py
.venv\Scripts\python.exe tools\tls_check.py --all

Beklenen: 67+ worker testi, 23 arayüz testi, iki tsc sessiz, build yeşil, verify 25 tablo /
migration 31, tls 0 hata 0 sapma.
'@ -replace "`r`n", "`n"

[System.IO.File]::WriteAllText("$PWD\docs\DEVIR.md", $rapor, $utf8)
'--- yazildi ---'
(Get-Item 'docs\DEVIR.md').Length

## Düzeltme turu — 2026-11-14

Kod okuması sonucu çıkan 53 maddelik kaydın kritik ve yüksek grubu kapatıldı.

### Sistem davranışı

- `isci.ts` sahiplenmesi `last_burst_at` damgasına bağlandı; `affectedRows` artık gerçek sahiplenmeyi gösteriyor. Sistem burst'leri silmiyor, satır `running` kilitlenmiyor.
- Burst kimliği `insertId`'den alınıyor; eşzamanlı burst'te yanlış satıra bağlanma kapandı.
- Hacim hedefi gerçek `hit` satırlarından (`result='ok'`) sayılıyor; `target_count` planı artık hedefi şişirmiyor.
- `burst.py` mobil penceresi hit sayısına çevrildi; mobil yol artık ilk hit'te kapanmıyor.
- `not_found` izleniminde tıklama yapılmıyor, pogo sonucu hit sonucuna yansıyor.

### Veritabanı ve CI

- `028` üç ayrı `ALTER`'a bölündü, sonuna LF eklendi.
- `029` içindeki FK adı `fk_ck_kullanim_profil` yapıldı; `026` ile ad çakışması giderildi. `veritabani` CI işi bu yüzden yeşile döndü.
- `032_saglik_pencere.sql` eklendi: devre kesici sayaçları saatlik pencereli.
- `kurulum_dene.py` zorunlu tablo listesini `verify.py`'den alıyor; `verify` eşiği 32 migration.
- Sıfırdan kurulum denemesi tam zincirle geçti (32 migration, 24 tablo, geo/uule 81).

### Çerez alt sistemi

- `host_only` yazma, okuma ve yükleme zincirinde taşınıyor.
- C46 ülke filtresi `cerez_sec` sorgusuna eklendi.
- Docker'da `CEREZ_YUKLEME_KOK` için volume açıldı; `read_only` kökfs altında yazma çalışıyor.
- `guvenliYol` il kodunu koruyor; `delete /cerez` yükleme defterini ve geçici klasörleri de siliyor.
- Ölü uçlar (`/cerez/tara`, `/cerez/aktar`, `/cerez/ilerleme`, `/cerez/gozat`, `klasorSec`) kaldırıldı.

### Panel ve worker

- `provider` kimliği DB'den üretiliyor; karantina ağırlığı yedeğe yazılıyor.
- PATCH uçlarında 404 kararı varlık kontrolüne bağlandı; aynı değerle güncelleme artık 404 vermiyor.
- `baslat` önceki kampanyayı kapatıyor, `durdur` 204 dönüyor; kelime metni değişince geo satırları yenileniyor.
- `/ayar` `oran_*` anahtarlarını atlıyor; oranlar tek uçtan yönetiliyor.
- `app.py` `/durum` token istiyor; `ayar_db` önbelleği C43 sırasına uyuyor; `durum.py` çift anahtar kullanıyor; `son_mod` globali kırılganlıktan çıkarıldı.
- SPA derin bağlantısı `index.html`'e düşüyor; saklama sorgusu MariaDB uyumlu.
- `serp.py` ve `olcum.ts` anahtar sırasını (decodo → serper → searchapi) ve sağlayıcı uçlarını kullanıyor.

### Doğrulama

69 worker testi, 23 arayüz testi, iki `tsc` configi ve `verify.py` temiz. Commit atılmadı; değişiklikler çalışma ağacında.