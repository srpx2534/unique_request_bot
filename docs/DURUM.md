cd C:\Users\developer\Desktop\App\unique_request_bot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$m = @'
# DURUM — devir notu

Son güncelleme: 2026-11-13

## Proje

unique_request_bot. Panelden yönetilen, çoklu proxy sağlayıcısı üzerinden çalışan
request-burst motoru. Sözleşme: `docs/CONTRACT.md` v1.5 (kilitli).

Windows geliştirme, Debian 12 çalışma. Python 3.12 fetch motoru, Node 20 + TS
kontrol düzlemi, MySQL. Proje kökü: `C:\Users\developer\Desktop\App\unique_request_bot`.

## Ortam

- MySQL XAMPP içinde (`C:\xampp\mysql\bin\my.ini`). `aria_page_checksum=0` yazıldı, yedek `my.ini.yedek`.
- Redis: Memurai servisi.
- Panel: `npm.cmd run dev:server` (ayrı pencere), 127.0.0.1:8080.
- Worker: `python -m worker.app`, 127.0.0.1:8081.
- Panel kullanıcısı: yonetici@ornek.com / PanelParola2026!
- Giriş alanları: `eposta`, `sifre`. CSRF başlığı `x-csrf-token`, token `GET /api/token`.
- DB kullanıcısı `request`, iki host için de yetkili. Onarım araçları: `tools/db_onar_aria.py`, `tools/db_db_sifirla.py`, `tools/db_yetki_onar.py`.

## Biten işler (son turlar)

- `.env` sadeleşti: yalnızca MYSQL_*, REDIS_URL, SESSION_SECRET, WORKER_TOKEN. Proxy kimliği `provider` satırında, SERP anahtarları `ayar` tablosunda.
- SERP anahtarı `ayar` tablosuna taşındı (migration 015), `worker/ayar_db.py` 60 sn önbellekli okuma, panelde maskeleme + Temizle + Dene düğmesi.
- `olcum_araligi_dk` ayarı zamanlayıcıya bağlandı.
- Düğüm kayıt defteri, kalp atışı, dağıtıcıda düğüm seçimi.
- Uyarılar/Loglar sayfalaması, 404 ekranı, onay diyalogları, CSV.
- Marka "Unique Request Bot".
- 45 pytest yeşil, tsc temiz.

## Açık maddeler (sırayla)

1. `hit` tablosu doldurulmuyor. `worker/burst.py` kayıt sözlüğüne `saglayici_id`, `geo_mode`, `http_status`, `latency_ms`, `bytes` eklenecek; `worker/app.py` `hits` dizisini geçirecek; `src/server/isci.ts` toplu INSERT yazacak.
2. `traffic_daily` toparlayıcı yok (günlük ok/fail/yedek).
3. `GET /api/site` düz dizi dönüyor, sözleşme `{ satirlar }` diyor.
4. `tools/sahte_veri.py` bazı satırlarda `ended_at < started_at`; rapor ortalaması eksi.
5. `dugum_olay` yazımı ve zaman çizelgesi ekranı yok.
6. Kalp HMAC yok.
7. `position` ölçüm hattı yok (SERP API → position).
8. Vitest seti eksik: oran normalizasyonu, tier, stop, token, dugumSec.
9. `alert` türlerinden queue_lag, quota, fallback_high hiç üretilmiyor.
10. `hit` için partition ve saklama işi yok.
11. Decodo TR kimlikleri yok; 100'lük ölçüm ve şehir oranı doğrulaması bekliyor.

## Bilinen tuzaklar

- PowerShell'de çift tırnak içinde backtick kaçışı; dosya yamalarında tek tırnaklı desen kullan.
- pymysql parametreli sorguda literal `%` → `%%`.
- Türkçe karakterli desenler bazı dosyalarda mojibake yüzünden tutmaz; ASCII desen seç.
- `mysql.user` görünümdür, onarım hedefi `mysql.global_priv`.
- Worker `python worker\app.py` ile çalışmaz, `python -m worker.app`.

## Çalışma kuralları

- Kullanıcı onayı olmadan kod yazılmaz.
- Sözleşme güncellemeleri toplu yapılır.
- Git commit'lerini kullanıcı atar.
- Dosyalar Türkçe yorum taşır, 250 satırı geçmez.
- Cevaplar kısa; sandbox yok, düz metin.
'@
[System.IO.File]::WriteAllText((Join-Path (Get-Location) "docs\DURUM.md"), ($m -replace "`r`n","`n"), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "[YAZILDI] docs\DURUM.md"
(Get-Content "docs\DURUM.md").Count