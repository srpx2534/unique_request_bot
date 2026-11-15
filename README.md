# unique_request_bot

Çok sunuculu request-burst motoru: panelden site ve kelime girilir, start
verilen kelime Google SERP'inde gezdirilir, hedefe tıklanır, sıralama ayrı ve
temiz bir hattan ölçülür. Sözleşme docs/CONTRACT.md, açık işler
docs/EKSIKLER.md, devir notları docs/DEVIR.md.

## Kural: Windows'ta yaz, Linux'ta çalıştır

Kod Windows'ta yazılır, sunucuda Debian 12 üzerinde çalışır. Yol, satır sonu ve
kabuk kullanımı sözleşmenin §18 maddesine tabidir; depoda yalnızca LF bulunur
(.gitattributes), tools/lint_yol.py bunu denetler.

## Gerekenler

- Python 3.12 ve requirements.txt
- Node 20 (npm ci)
- MySQL 8 / MariaDB (utf8mb4_turkish_ci)
- Redis 7
- Üretimde Docker; yerelde Docker ya da XAMPP + Memurai

## Yerel kurulum — XAMPP + Memurai

1. XAMPP'ta MySQL'i, Memurai servisini başlat.
2. Memurai'de parola aç (bir kez, yönetici kabuk):

       $cli = "C:\Program Files\Memurai\memurai-cli.exe"
       & $cli CONFIG SET requirepass "SIFRE"
       & $cli -a "SIFRE" CONFIG REWRITE
       Restart-Service Memurai

3. .env dosyasını .env.example'dan kopyala, boş sırları doldur:
   MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD, REDIS_PASSWORD, SESSION_SECRET,
   WORKER_TOKEN. SESSION_SECRET en az 32 karakter olmalı (openssl rand -hex 32).
4. Şemayı kur, seed ve doğrulama yap:

       python -m venv .venv
       .venv\Scripts\pip install -r requirements.txt
       npm ci
       python tools/migrate.py
       python tools/seed.py
       python tools/verify.py
       npm run kullanici:ekle -- yonetici@ornek.com "PanelParola2026!"

verify.py "DOGRULAMA TAMAM" demeden panel açılmaz: eksik tablo, eksik görünüm
ya da eksik migration varsa 1 döner.

## Yerel kurulum — Docker

       copy .env.example .env
       python tools/gen_uule.py
       docker compose up -d

Konteynerlerde şema init klasöründen değil, tools/migrate.py ile kurulur.

## Çalıştırma

       npm run dev          # panel + worker birlikte
       npm run dev:server   # yalnız panel sunucusu
       npm run dev:web      # yalnız arayüz (Vite)

Panel http://127.0.0.1:8080, worker 8081. Panel varsayılan olarak yalnız yerel
arayüze bağlanır; üretimde TLS sonlandıran ters proxy arkasına alınır (17.3) ve
TRUST_PROXY ona göre verilir.

## Kapılar

       npm run tip
       npm test
       python -m pytest -q
       python tools/lint_yol.py
       python -m compileall -q worker tools
       python tools/verify.py

Veritabanı ve Redis isteyen testler (api, panel_*, silme) yalnızca CI'nin
veritabanı işinde koşar; platformdan bağımsız iş bunları --exclude ile atlar
(C27.1).

## Yedek ve geri yükleme

       python tools/yedek.py
       python tools/geri_yukle.py veri/yedek/X.sql

Geri yükleme root kimliğiyle koşar (dump görünümleri DEFINER=root taşır) ve
başarıdan sonra görünümleri migration tanımlarından yeniden kurar. Kimlik komut
satırında taşınmaz, geçici seçenek dosyası kullanılır (17.10, C71).

## Güvenlik notları

- hit tablosunda FK yoktur; site ve kelime silmek bağlı kayıtları tek işlemde
  götürür (C73, C74). Sağlayıcı silmek geçmiş hit'i korur, yalnız provider_id
  ve profile_id bağını koparır (C75).
- Redis parolası REDIS_PASSWORD ile ayrı verilir, URL'e gömülmez.
- Sır değerler kodda sabit tutulmaz; yalnız ortam değişkeninden okunur.
- .env, çerez klasörleri ve veri/yedek repoya girmez.
- SERP anahtarları ve oranlar ayar tablosundadır, panelden yönetilir; proxy
  kimlik bilgileri Sağlayıcılar ekranındadır.

## Belgeler

- docs/CONTRACT.md — bağlayıcı sözleşme ve kabul ölçütleri
- docs/EKSIKLER.md — açık maddeler
- docs/DURUM.md — durum özeti
- docs/DEVIR.md — devir notları ve çalışma kuralları
