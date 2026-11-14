# DURUM

Bu dosya projenin o anki hâlini ve devir notlarını tutar. İşi devralan ajan önce burayı, sonra `docs/EKSIKLER.md` içindeki 83 maddelik listeyi okur. Liste sırayla kapatılır.

## Proje

- Yol: `C:\Users\developer\Desktop\App\unique_request_bot`
- Ne: Google SERP burst/ölçüm botu. TS panel (Node 20) + Python worker (3.12), MySQL/MariaDB.
- Sözleşme: `docs/CONTRACT.md`, sürüm 1.7, 26 bölüm, 60 kabul kriteri. Kodla hizalandı.
- Son commit: `92f4e9b Genel Düzenleme`. Çalışma ağacında kod tarafı temiz.
- Yerel veritabanı XAMPP üzerinde. **XAMPP ayarlarına dokunulmayacak**; kullanıcı sonra ele alacak.

## Bu oturumda kapatılan işler

- `isci.ts` sahiplenmesi `last_burst_at` damgasına bağlandı; sistem hiç hit atmıyordu, sebep buydu.
- `FOR UPDATE SKIP LOCKED` kaldırıldı. MariaDB bu sözdizimini bilmiyor; koşullu `UPDATE ... WHERE id=? AND durum='yeni'` + `affectedRows` kontrolüne geçildi.
- Çerez silme partili hâle getirildi: 400 profil / 1000 dosya partisi, önce çocuk satır, her parti ayrı işlem. 5,4 milyon satır 1206 (kilit tablosu) hatası vermeden silindi, dört sayaç sıfırlandı.
- `docker-compose.yml`: `innodb_buffer_pool_size=256M`, `innodb_lock_wait_timeout=20`, `max-connections=300`, `stop_grace_period: 60s`.
- Sözleşmeye işlendi: `sayac_baslangic`, `host_only`, seed anahtarları, `GET /kelime/:id/ozet`, `DELETE /cerez/hatali`, `cerez_kendi`, modalite çıkarımı, C50-C60, §7.3, §8.1, §23.4, §17.8, §18.5.
- `docs/EKSIKLER.md` 83 maddelik öncelik listesine çevrildi.

## Kritik kararlar — değiştirmeden önce düşün

- Çerez modalitesi yüklemede **sorulmaz**; dosyadaki `userAgent` ve yol segmentinden çıkarılır.
- `host_only` bayrağı çerez satırında saklanır; host-only çerezde baştaki nokta düşürülür, alan adı çerezi yazıldığı gibi kalır.
- `cerez_kendi` açıkken yalnızca sayım süzülür; havuz ortak kalır, hit'ler tüm havuzdan beslenir.
- Özet ucu ölçüm yoksa `-`, ilk 100'de yoksa `100+` döner.
- Kuyruk sahiplenmesi `SKIP LOCKED` kullanmaz.
- Çerez silmede tek ifadeyle toplu `DELETE` yazılmaz; kilit tablosu taşar.

## Bilinen kırıklar — ilk bunlar

- `proxy.dize()` ülke parametresi almıyor, `country-tr` sabit yazıyor. Yabancı sağlayıcı seçildiğinde IP Türkiye'den çıkar, `hit.geo_mode` yalan söyler (C40).
- Sağlayıcı kullanıcı adı biçimi tek sağlayıcıya (Decodo) özgü; diğer dört sağlayıcı bu biçimi kabul etmez.
- `GET /health` token istiyor ve sürüm/doluluk yerine `{"durum":"ayakta"}` dönüyor; §7.2 ile çelişiyor.

## PowerShell ile çalışma kuralları

- Betikleri **tek blok** hâlinde ver; kullanıcı tek seferde yapıştırıyor.
- Dosya yazarken `New-Object System.Text.UTF8Encoding($false)`; BOM ekleme.
- `$A` ile `$a` aynı değişkendir; yol için `$Yol`, metin için `$Metin` kullan.
- `String.Replace` üç argüman almaz; ilk geçiş için `IndexOf` + `Substring`.
- `elseif` satır başında kalırsa kopar; `} elseif` aynı satırda yazılmalı.
- Metin çapaları harfle başlamalı. `-`, `#`, ters tik ile başlayan çapalar tutmuyor; öyleyse `IndexOf` ile bul, satır başına `LastIndexOf("`n")` ile geri sar.
- Dosyaya yazmadan önce geçici dosyaya yaz, satır sayısı eşik altındaysa iptal et, sonra `Move-Item -Force`.
- Uzun belgelerde **iç içe kod çiti kullanma**: dış blok ` ```markdown ` içinde iç ` ```sql ` olursa dış blok orada kapanır. SQL'i düz satır yaz.
- Tek mesaja uzun çıktı sığmıyor; parçalı vermek gerekiyor.

## Yapılmayacaklar

- Kullanıcı onayı olmadan commit atılmaz.
- Onay olmadan yeni maddeye geçilmez.
- XAMPP ayarları ve `my.ini` elle değiştirilmez.
- `docs/CONTRACT.md` içine `SKIP LOCKED` geri getirilmez.
- Sözleşmeye karşılığı olmayan özellik eklenmez; önce sözleşme, sonra kod.

## Doğrulama komutları
npx tsc --noEmit
python -m pytest worker -q
git status --short
git diff --stat
Çerez silme sonrası dört sayaç da sıfır olmalı:
SELECT 'cookie' t, COUNT() c FROM cookie
UNION ALL SELECT 'cookie_profil', COUNT() FROM cookie_profil
UNION ALL SELECT 'cookie_dosya', COUNT() FROM cookie_dosya
UNION ALL SELECT 'cerez_yukleme', COUNT() FROM cerez_yukleme;
## Dosya haritası

- `docs/CONTRACT.md` — bağlayıcı sözleşme, 26 bölüm, 60 kriter.
- `docs/EKSIKLER.md` — 83 maddelik liste, sırayla kapatılır.
- `src/server/` — panel API. `cerez.ts` partili silme, `kelime.ts` özet ucu, `panel.ts` ayar uçları.
- `worker/` — fetch engine. `havuz.py` seçim, `proxy.py` dize kurma, `burst.py` hit akışı, `saglik_db.py` sayaç ve uyarı.
- `db/migrations/001-033` — şema geçmişi. `033_cerez_kendi.sql` sonuncusu.
- `tools/` — kurulum, onarım, ölçüm ve kanıt betikleri.

## Sonraki adım

`docs/EKSIKLER.md` maddesi 1: `proxy.dize()` imzasına ülke parametresi ekle, `sec_mod()` çağrısında `ulke` geçir, `yabanci` modda `country-tr` yazılmasın. Ardından madde 2: sağlayıcı başına kullanıcı adı biçimi.
Bu docs/DURUM.md içine, mevcut içeriğin altına eklenir. Yeni ajan buradan devam edebilir.