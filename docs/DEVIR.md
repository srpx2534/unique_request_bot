# Devir — 2026-11-15

Bu dosya devralan ajan içindir. Önce tamamını oku, sonra "Sıradaki iş"in 1. adımından başla. Sözleşme `docs/CONTRACT.md` v1.8.7 kilitli, açık maddeler `docs/EKSIKLER.md`.

## Sıradaki iş — sağlayıcılar ekranında kaydet çalışmıyor

Kök neden bulundu, düzeltme yazılmadı: `src/server/panel_ayar.ts` satır 68 `if (anahtar.startsWith("oran_")) continue;` yüzünden genel `PATCH /ayar` ucu `oran_*` anahtarlarını sessizce atlıyor. Sağlayıcılar ekranı `src/web/sayfa/saglayicilar.tsx` satır 61'de `yaz.mutate(oranlar)` ile bu uca `{oran_residential, oran_mobil, oran_datacenter}` gönderiyor; istek 200 dönüyor, tabloya satır yazılmıyor. `ayar.oran_mobil` bu yüzden 0 kalıyor.

Yapılacak, sırayla:

1. `src/server/panel_ayar.ts` içine `yonlendirici.patch("/oran", ...)` ekle. Gövdeyi zod ile doğrula: `oran_residential`, `oran_mobil`, `oran_datacenter`, hepsi `z.coerce.number().int().min(0).max(100)`. Toplam 100 değilse 400 ve `{hata}` dön. Geçerliyse üçünü `INSERT INTO ayar (anahtar, deger) VALUES (?, ?) ON DUPLICATE KEY UPDATE deger = VALUES(deger)` ile yaz, `denetim(istek, "oran-guncelle", "ayar", null)` çağır, maskeli listeyi dön. Genel `PATCH /` içindeki `oran_` atlaması olduğu gibi kalır.
2. `src/web/lib/panel.ts` içine `oranYaz()` ekle: `PATCH /ayar/oran`, `onSuccess: tazele(istemci, "ayar")`.
3. `saglayicilar.tsx` satır 11'deki importta `ayarYaz` yerine `oranYaz`, satır 28'de `const yaz = oranYaz();`.
4. Kapılar: `npm.cmd run tip`, `npm.cmd test`, `.venv\Scripts\python.exe tools\lint_yol.py`, mojibake taraması (kod dosyalarında çift kodlama üçlüsü 0 olmalı; bu belgede literal geçmez).
5. Kullanıcı sağlayıcılar ekranından `oran_mobil` değerini 10'a çekecek. `SELECT deger FROM ayar WHERE anahtar='oran_mobil';` ile 10 yazdığını doğrula.
6. EKSIKLER 27: `SHOW COLUMNS FROM provider_geo;` ile kolonları gör (`tur` kolonu yok), mobil sağlayıcı sayısını `provider.kind='mobile'` üzerinden say, tek kelimeyle dar kapsamlı gerçek burst at, `hit` ve `burst` kayıtlarında mobil modalite oluştuğunu doğrula.

## Sonrası

EKSIKLER sırası geçerli. Ağ gerektirmeyen sıradaki maddeler: 60 (liste uçlarının dönüş zarfı), 61 (DURUM/EKSIKLER dışındaki belgeler), 58 (havuz.py ve saglik_db.py bölme). 47 (yedek/geri yükleme, metrik ucu) ve 62 (devir paketi) kapandı. Proxy ve kimlik bilgisi gelmeden kapanmayan 17 madde (16, 17, 19, 22, 24, 25, 26, 31, 32, 33, 34, 36, 38, 43, 63, 64) beklemede.

## Çalışma kuralları

- **Öncelik canlıya almadır.** Amaç kritik parçaları bitirip canlıya çıkmak. Canlıda etkisi olmayan düzenlemeler (kozmetik, belge süsü, bölme, isimlendirme) kritik madde varken bekletilir.
- Sıra: güvenlik/üretim → veri kaybı riski → devir paketi → API tutarlılığı → bakım borcu → kozmetik.

- Panel parametrelerini asistan değiştirmez; değeri kullanıcı girer.
- Kritik sayfa yapısı değişiklikleri önce onaya sunulur.
- Kod PowerShell copy-paste bloğu olarak verilir. Dosya yazımı `@'...'@` here-string + `[System.IO.File]::WriteAllText` + `New-Object System.Text.UTF8Encoding($false)` ile yapılır; `Set-Content`/`Out-File` Türkçe karakteri bozar.
- Sır değerler (parola, anahtar) kod içinde sabit tutulmaz; yalnız ortam değişkeninden okunur ve günlüğe yazılmaz. Bağlantı adresi ile parola ayrı taşınır.
- Yamalar `[regex]::Replace` veya `.Replace` ile, dosya satır sonuna dokunmadan. Her yamadan sonra `DEGISMEDI` kontrolü ve mojibake taraması.
- Yazma sonrası uzunluk kontrolü yap: bu oturumda `isci_durum.ts` bir kez 0 bayta düştü, `git checkout -- <yol>` ile HEAD'den kurtarıldı.
- `npm.ps1` execution policy'ye takılıyor, `npm.cmd` kullan.
- Çerezler site+kelime bazlıdır, aktif-önce ve canlı-önce sıralanır, hiç silinmez. Dosya adından il ataması yapılmaz.
- Dosya bölme proje bitene kadar yok; hedef 450 satır, tavan 800.
- Sözleşmedeki `kilit_suresi_dk` panel alanı ve çakışma listesi ekranı G4'tür, geliştirme aşamasında.

## Ortam

- Kök: `C:\Users\developer\Desktop\App\unique_request_bot`
- Python yalnızca `.venv\Scripts\python.exe` altında, PATH'te yok.
- MySQL: `C:\xampp\mysql\bin\mysql.exe`, kullanıcı `request`, şifre `.env` içinde `MYSQL_PASSWORD`, veritabanı `unique_request_bot`.
- Worker testleri `worker\test_*.py`, `.venv\Scripts\python.exe -m pytest worker`.
- UI testleri `src\server\*.test.ts`, `npm.cmd test`.
- Migration: `.venv\Scripts\python.exe tools\migrate.py`, dosyalar `db\migrations`, sıradaki numara 047. Son uygulanan 046.
- Worker veritabanına yazmaz (§3); DB işleri control plane'de.

## Doğrulanmış davranışlar

- Kilit (C64): beş ayrı süreç aynı satırı sahiplenmeye çalıştığında tam biri kazanıyor, taze yabancı kilitte beşi de kaybediyor, süresi geçmiş kilitte biri devralıyor, uyarı satırdaki sahibi adıyla yazılıyor, 30 dakika sessizlik tutuyor. Araç: `tools/kilit_cakisma_dene.ts` (`npx.cmd tsx tools\kilit_cakisma_dene.ts <id> [sahip|devral|uyari]`).
- hedef_yok: üst üste 3 hedefsiz burstte kelime `paused`, kampanya kapanıyor, `hedef_yok` uyarısı düşüyor.
- Havuz boşken iş başlamıyor: satır beklemede kalıyor, 30 dakikada bir tek `provider_down` uyarısı düşüyor (C69).
- Üst üste 3 error/timeout sağlayıcıyı `disabled` yapıyor; burst tamamen başarısızsa (ok=0) kelime duruyor (C70). `worker/test_saglik_hata.py`.
- Kapılar son hâlde yeşil: 184 pytest, 80 vitest, lint 0, tip 0, ağaç temiz.
- Zarif boşaltma (E4): sinyalde yeni burst 503 + `Retry-After: 30`, uçan iş bitene kadar kapanmaz, ikinci sinyal zorla çıkar; kontrol düzlemi 503'ü hata saymaz. `worker/test_bosaltma.py` dört test.
- Migration geri alma (E5): `tools/migrate.py --geri <n>` plan basar, `--uygula` ile koşar. 46 migration'ın tamamı için `db/migrations/geri/` altında geri dosyası var; tam geri-ileri turu ve `verify` temiz. `tools/test_migrate_geri.py` yedi test.
- Tek örnek kilidi (E7): panel `veri/panel.pid` almadan dinlemez; canlı sahipte ikinci süreç 1 ile çıkar, ölü sahipte devralır. `src/server/tek_ornek.test.ts` altı test, canlı iki süreç denemesi geçti.
- Test giriş kimliği kodda sabit değil: `TEST_EPOSTA` / `TEST_PAROLA` ortamdan okunur (`src/server/test_kimlik.ts`), `.env` ve CI adım env bloğu taşır. Geçici yönetici silinirse yalnız `kullanici:ekle` ile yeniden kurulur, kod değişmez.
- Yapılandırılmış günlük (E2): `gunluk.ts` tek satır JSON yazar, `console` başka modülde yasak (lint). Seviye `GUNLUK_SEVIYE` ile. `gunluk.test.ts` altı test.

## Açık altyapı notları

- Yerel Memurai'de `requirepass` 2026-11-16'da açıldı; yapılandırma yedeği `memurai.conf.bak-20261116-000806`. Parola `REDIS_PASSWORD`'de, URL'e gömülmüyor. Yedek dosyası Program Files'ta, repoda değil.
- `docker-compose.yml` içinde Redis adresi `redis://redis:6379/0`; parola ayrı `REDIS_PASSWORD` değişkeniyle veriliyor. Yedekler `yedek` volume'una `/app/veri/yedek` olarak bağlanıyor.
- `.env.example` zorunlu sırları listeler: `MYSQL_ROOT_PASSWORD`, `SESSION_SECRET`, `REDIS_PASSWORD`. İsteğe bağlı: `TRUST_PROXY`, `CEREZ_YUKLEME_KOK`.
- `.env`, `veri/` ve `*.bak` repoya girmez; `.gitignore` ile `.gitattributes` bunları kapsıyor.

- Hiçbir sağlayıcıda `gateway` yok (hepsi örnek satır); C69 devrede, burst başlamıyor. Gerçek gateway girilmeden hiçbir ağ maddesi kapanmaz.
- `.env` içinde proxy ya da oran anahtarı yok: proxy kimliği `provider` satırında, oranlar `ayar` tablosunda.
- `provider_geo` tablosunda `tur` kolonu yok; tür artık `hit.tur` içinde tutuluyor (045).
- EKSIKLER 27 kısmi: oran yazımı ve `hit.tur` tamam, mobil sağlayıcı kimliği yok, canlı doğrulama bekliyor.
- Diakritiksizleştirilmiş yorumlar 38 dosyada duruyor (kullanıcı kararı: şimdilik dokunulmuyor). EKSIKLER bitince 5-6 dosyalık partiler hâlinde, yalnız yorum satırları düzeltilecek.
- `src/server/bolum.ts` başlığında `§105` yazıyor; sözleşmede karşılığı yok, `§10.5` olabilir. Ayrı madde.
- Decodo SERP kotası dolu, proxy sağlayıcıları pasif; ağ gerektiren maddeler bu yüzden bekliyor.
- 22.704 çerez canlılık ölçümünden geçmedi; `tools/cerez_olcum.py` proxy açılınca `olcum_proxy=1` ile koşulacak.








