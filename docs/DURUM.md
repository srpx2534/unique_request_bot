# DURUM — 2026-11-15

Devralan ajan için tek gerçek durum dosyası. Tamamını oku, sonra "Açık işler"in en üstünden başla. Sözleşme `docs/CONTRACT.md` v1.8.7 kilitli; açık maddeler `docs/EKSIKLER.md`.

## 1. Amaç ve başarı ölçütü

unique_request_bot: panelden yönetilen Google istek patlatma motoru. Node/TS kontrol düzlemi + Python fetch worker + MariaDB. Hedef Debian 12.

Tek başarı ölçütü gerçek Google isteklerinde kabul oranı. Ölçülmeyen iş bitmiş sayılmaz. Kullanıcı açıkça onaylamadan yeni maddeye başlama ve commit atma.

## 2. Değişmez kurallar

- **Tüm proxy trafiği TR IP'lerden.** Her site Türkiye'de konumlu. Yabancı IP + TR çerez çelişki üretir; `gl`/`hl` her zaman `tr`/`tr`.
- **Commit atma.** Commitleri kullanıcı gönderir; sen sadece kod bırak.
- **Her PowerShell bloğu tek yapıştırma birimi.** Uzun heredoc'lar kullanıcının kabuğunda kesiliyor; blok kısa ve kendi kendine yetsin.
- **Sunucu tarafından dosya seçtirme yok.** Yükleme tarayıcıdan; çok kullanıcılı kurulumda sunucu yolu paylaşılamıyor.
- **Madde başlamadan önce gereken tüm kod toplanır**, kullanıcı tek dosya olarak verir, sonra düzenleme yapılır.
- Kullanıcı Türkçe yazar, Türkçe cevap ver. Emoji yok. Yorum ve arayüz metni Türkçe, SQL ve tanımlayıcılar ASCII.

## 3. Ortam

- Proje kökü: `C:\Users\developer\Desktop\App\unique_request_bot`
- Python: `.venv\Scripts\python.exe` (sistemde `python` ve `mysql` CLI yok)
- `npx` asılı kalıyor; `node_modules\.bin\tsc.cmd`, `esbuild.cmd`, `vitest.cmd` doğrudan çağrılır
- DB erişimi: `tools/db.py` kütüphanedir, CLI değil. Sorgu için: `.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'tools'); import db; c=db.baglan(); cur=c.cursor(); cur.execute('SELECT ...'); [print(r) for r in cur.fetchall()]"`
- Migration: `.venv\Scripts\python.exe tools\migrate.py` · Doğrulama: `tools\verify.py`
- Panel: `http://127.0.0.1:8080` — `/saglik` oturumsuz, `/api/*` oturum + CSRF
- Giriş akışı: `GET /api/token` → `{"token"}`; `POST /api/giris` gövde `{"eposta":"...","sifre":"..."}` başlık `x-csrf-token`; yanıttaki `token` yenilenir. Yanlış alan adı 400, eksik token 403.
- XAMPP sadece test ortamı, MariaDB. `FOR UPDATE SKIP LOCKED` yok. Docker yok. Decodo ve SERP kimlikleri şu an yok; proxy'siz maddeler öncelikli.
- Compose dosyası hazır (`docker-compose.yml`); Docker kurulu değil. Sırlar `.env` içinde: `MYSQL_ROOT_PASSWORD`, `SESSION_SECRET`, `REDIS_PASSWORD` zorunlu, `TRUST_PROXY` ve `CEREZ_YUKLEME_KOK` isteğe bağlı.
- DB kurulumu kullanıcının işi; `my.ini`'ye dokunulmuyor.

## 4. Mevcut durum (2026-11-15 ölçümü)

- `verify.py`: 25 tablo, 0 eksik, 2 view, geo 81, uule 81, migration 46 — temiz.
- Testler: **184 pytest, 80 vitest, iki `tsc` configi sessiz.** Yeşil olmayan tek şey yok.
- `cookie_profil`: 3.523 profil, **hepsinde `il_kodu` NULL** (il ataması bilerek kapalı, D-15).
- `host_only` ölçümü gerçek 199k çerezle yapıldı: 146.430 noktalı, 52.799 host-only.
- `cerez_kendi` ayar tablosundan ve ayarlar ekranından çıkarıldı; yönetim ekranında admin izni olarak geri gelecek (D-16, mevcut SQL yeniden kullanılacak).
- Ölçüm kanalı B (`worker/olcum_b.py`, imzalı `/worker/olcum_b`) kurulu; canlı Google yanıtı gerektiren ölçümler (D-4/D-5/D-6/D-10) proxy gelene kadar beklemede.
- Değişiklikler çalışma ağacında, commit atılmadı.

## 5. Bu turda kapatılanlar

- Bölüm D: `bicimBul`/`jsonParcalari` çıplak JSON dizisini kabul ediyor; uzantı dışında dosya adı kuralı yok; il ataması kaldırıldı ve yanlış değerler NULL'landı (2.931 satır).
- Bölüm D-2/D-3: çerez havuzu sıralı ve tek kullanımlık, `_secim_sorgusu` ile ülke eşleşmesi.
- D-8/D-9: `host_only` uçtan uca; modalite içerik/yol kaynaklı, yükleme bayrağı yedek.
- D-7 `.gitignore`, D-11/D-13 ölçüm ve elle doğrulama.
- 31/32: `bytes_ay`, `bayt_ekle` (%90 kota uyarısı), aday sorgusunda kota süzgeci, hit'te bayt yazımı.
- 23/29/30: oranlar `.env` anahtarlarından, eşikler panelden (`esik_captcha`, `esik_geo`, `asgari_ornek`).
- 15/18/20/28: burst toplu yazım, durdurma davranışı, A3 otomatik durdurma (`hedefYokDenetle`).
- 35/37: ölçüm kanalı B, kalıcı jar, imzalı uç, `aralikDk` 15 dakika tavanı.
- 44: `bolum.ts` bölümleme + migration 035 (D-65: 10M satırda canlı doğrulama beklemede).
- 41/42/39: lint kuralları genişletildi, 5 bayat CRLF dosyası LF'e çevrildi, lint pytest'e bağlandı.
- 52–55: uyarı saklama doğrulandı, `test_uyari.py` dokuz uyarı türünü tarıyor.
- 56/59: `cerez.ts`, `serp.py`, `burst.py`, `kelime.ts`, `isci.ts`, `panel.ts` bölündü; `worker/test_boyut.py` 250 satır sınırını izliyor. `panel.ts` 130, `panel_saglayici.ts` 129 satır.

## 6. Açık işler (öncelik sırası)

Tam liste `docs/EKSIKLER.md`; orada 39 madde açık. Sıra:

1. **Commit.** Sözleşme v1.7, EKSIKLER, DURUM ve kod değişiklikleri çalışma ağacında; commit'i kullanıcı atar. Onay gelmeden commit denemesi yapma.
2. **`cerez_kendi` admin izni (D-16).** Kullanıcı yönetiminde izin olarak geri gelecek; mevcut SQL yeniden kullanılacak. Ayar tablosuna ve ayarlar ekranına geri konmaz.
3. **D-15 il ataması.** Şu an `il_kodu` tümüyle NULL. Doğrusu UULE koordinatından il çıkarmak ve il sınır poligonuyla eşlemek; dosya adına güvenilmiyor.
4. **D-65 bölümleme canlı testi.** 10 milyon hit satırı varken `hit` bölümlerinin oluşması/düşmesi ve sorgu planının bozulmaması doğrulanacak.
5. **58** `havuz.py` (542 satır) dörde bölünecek: oran, sağlayıcı seçimi, çerez seçimi, kuyruk. `saglik_db.py` de sınırı aşıyorsa bölünür.
6. **60–61** liste yanıt zarfı sözleşmede tekilleştirilecek; kalan belgeler gözden geçirilecek. **62** devir paketi (README, `.env.example`, compose, `.gitattributes`, `.gitignore`) kapandı.
7. **Proxy gelince (Decodo):** D-4/D-5/D-6/D-10 (SOCS/CONSENT, SID ölçümü, tazelik, canlılık), F1/F4/F5 (TR çıkış IP doğrulama, click/pogo, 100'lük hit bölme), mobil modun gerçek istekle denenmesi. Bunlar ölçüm olmadan kapatılmaz.
8. **B6/B8/B9/B12** HTTPS/HSTS, sır saklama, Redis `requirepass`, eşik sınır doğrulaması.
9. **E1–E7** yedek, loglama, worker healthcheck, zarif boşaltma, migration geri alma, metrik ucu, tek örnek kilidi. Yedek/geri yükleme, metrik ucu, E4, E5, E7 ve E2 yazıldı; yalnız E3 açık.
10. `cookie_kullanim` yetim satırları; `temizle` sırasında çalışan yüklemenin iptali ve geçici klasörün silinmesi.
11. Geçersiz sayılan çerez dosyalarının yeniden yüklenmesi (ayrıştırıcı düzeltildi).
12. `docs/*.py` ve `docs/yedek` temizliği.

## 7. Bilinen tuzaklar

- **Satır sonu:** bazı dosyalar CRLF. Çok satırlı çapa CRLF'de tutmaz; her düzenlemeden önce içeriği `[regex]::Replace($t, '\r\n', [string][char]10)` ile normalize et.
- **Kodlama:** `Get-Content -Raw` ANSI okur, Türkçe çapayı kaçırır ve dosyayı bozar. Daima `[System.IO.File]::ReadAllText` / `WriteAllText(..., New-Object System.Text.UTF8Encoding($false))`.
- **BOM:** SQL dosyasına BOM yazılırsa MariaDB 1064 verir.
- **`Set-Content -Encoding utf8`** BOM ekler; `Resolve-Path` var olmayan dosyada patlar.
- **Kabuk:** uzun heredoc kesiliyor. Blokları kısa tut; araya sohbet satırı yapışırsa blok baştan çalışmaz. `-replace` operatörü argümansız bırakılırsa hata verir. `New-Object List` yerine `New-Object 'System.Collections.Generic.List[string]'` kullan.
- **Türkçe çapa** yerine satır indeksiyle değiştir; çapa bulunamazsa indeks her zaman tutar.
- **Yer tutucu:** Node tarafı `?`, Python/pymysql tarafı `%s`. `profil_guncelle` bir kez `?` yüzünden sessizce jar yazmadı.
- **`cerez_sec`** demet döndürür `(profil_id, parmak_izzi)`, `sec_mod` 4'lü demet. Tek eleman bekleyen çağrı bozulur.
- **`il_kodu` NULL'ı bilerek anlamlı:** havuz süzgeci `il_kodu = ? OR il_kodu IS NULL`. NULL'ları doldurmak il süzgecini bozar.
- **`cerez.ts` artık klasör** (`src/server/cerez/`); `worker/test_boyut.py` iki dosyayı birleştirerek okuyor, tek dosya sanıp yol verme.
- **`test_boyut.py` IZINLI listesi:** 250 satırı geçen her dosya oraya yazılır, bölününce çıkarılır.
- MariaDB'de `FOR UPDATE SKIP LOCKED` yok; bölümleme `ALTER` ile tek tek yapılır.
- Node süreçlerini yeniden başlatmak gerekir; sağlık için 15 sn bekle. `npx` asılı kalır.

## 8. Kararlar ve gerekçeleri

- **`gl`/`hl` = `tr`/`tr` sabit.** Hedef TR sıralaması; `gl`'yi IP ülkesine bağlamak sıralamayı bozar. Proxy yalnız TR.
- **İl ataması kapalı.** Dosya adları rastgele hash; `ilBul` herhangi bir 1-81 sayısını yakalayıp 3000+ profili yanlış ile yazdı, bu yüzden değerler NULL'landı.
- **Dosya adı serbest**, yalnız `.txt`/`.json` uzantısı denetlenir.
- **Modalite içerikten/yoldan** çıkar, yükleme bayrağı yalnız yedek.
- **`cerez_kendi` parametre değil**, admin izni.
- **Süresi geçmiş çerezler kullanılır** (`cerez_suresiz_kullan`), aktifler bitmeden devreye girmez. Çerez site+kelime çiftinde bir kez kullanılır.
- **Öncelik:** aktif+il → aktif TR → diğer aktifler → süresi geçmiş, aynı iç sırayla.
- **Oranlar `ayar` tablosundan**, eşikler de aynı tablodan (`esik_captcha`, `esik_geo`, `asgari_ornek`); ikisi de yalnız panelden yazılır, `.env` anahtarı yok.
- **Ölçüm kanalı B ayrı** (`worker/olcum_b.py`): ölçüm trafiği burst IP'sini kirletmez.
- **Kota muhasebesi bayt üzerinden** (`bytes_ay`, `bayt_ekle`, %90 uyarısı).
- **Saklama `hit` için `DROP PARTITION`** ile yapılır; DELETE yükü metadata'ya döner.
- **`bilinmiyor` aile Chrome'a düşer**; Safari hiç atanmaz.
- **Yükleme tarayıcıdan**, sunucu yolu seçtirilmez.

## 9. Doğrulama

```
.venv\Scripts\python.exe -m pytest -q
node_modules\.bin\vitest.cmd run
node_modules\.bin\tsc.cmd --noEmit
node_modules\.bin\esbuild.cmd src/server/uygulama.ts --bundle --platform=node --outfile=NUL
.venv\Scripts\python.exe tools\verify.py
.venv\Scripts\python.exe tools\lint_yol.py
```

Beklenen: 179 pytest, 80 vitest, `tsc` sessiz, `verify` 25 tablo / 0 eksik / migration 46, lint temiz. Bu sayılar düşerse iş bitmemiştir. Proxy'siz hiçbir ölçüm maddesi kapatılmaz.






