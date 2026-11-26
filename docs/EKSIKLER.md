# Eksik maddeler

A (proxy kodu), B (worker testleri) ve C (oturum sürekliliği) kapandı; 173 worker + 49 UI test yeşil. Kalan maddeler sırayla kapatılır. Bir madde kapanınca buradan silinir, sonucu sözleşmedeki ilgili kritere işlenir.

## D. Gerçek tarayıcı cookie'leri
1. Format: Netscape `cookies.txt` (tercih) veya JSON dizi. Dosya basina tek profil. Dosya adi serbest, yalnizca uzanti (`.txt`/`.json`) denetlenir. (DUZELTILDI)
2. Havuz: tek cookie yüzlerce hit için yetmez. Dosyalar sırayla, hit başına bir kez kullanılacak; tükenince başa dönülecek. (DUZELTILDI)
3. Cografya: il seciminde tek dayanak proxy il IP'sidir; cerezde il eslesmesi aranmaz (C63). Cerez il eslestirmesi gelistirme asamasi (G3). (KISMI)
4. `SOCS` / `CONSENT` gerçek tarayıcıdan gelirse sabit değerlerden daha doğru; onay duvarı için bunlar yeğlenecek.
5. Oturum açmış hesap cookie'si (`SID`) güçlü sinyal ama tek hesaptan yüzlerce arama hesabı şüpheli gösterir. Önce oturumsuz cookie ile başlanacak, `SID` ayrı ölçülecek.
6. Tazelik: haftalar önce alınmış `NID`/`AEC` süresi geçmiş olur, Google yeniden üretir; fayda düşer, zarar yok.
7. Cookie dosyaları repoya girmez; `.gitignore`'a alınacak, hesap token'ı taşıyabilir. (DUZELTILDI)
8. `host_only` uretimi 199.229 gercek cerezde dogrulandi: 146.430 noktali alan adi (false), 52.799 noktasiz (true). Iki kol da dolu. (DUZELTILDI)
9. Modalite artik icerik ya da yol ipucundan okunur, ipucu yoksa yukleme bayragina duser; rastgele dosya adi tek basina kaynak degil. (DUZELTILDI)
10. Cerez canligi olculuyor: `cookie_profil.canli` (NULL olculmedi, 1 engellenmiyor, 0 engelli), `son_kontrol_at`, `olcum_proxy`. Olcum `tools/cerez_olcum.py` ile calisir; engelli cerez silinmez, siralamada sona duser. Havuz sayaclarinda canli/engelli/olculmemis gorunur. (DUZELTILDI)
11. `cerez_suresiz_kullan` kapatıldığında süresi geçmiş profillerin havuza dönüşü sınanmadı. (DUZELTILDI)
12. `havuz.cerez_sec()` SQL'inde ülke süzgeci sabit `TR`; yabancı profiller hiç devreye girmiyor. (DUZELTILDI)
13. Hatalı silme onay akışı ve `silinen` sayacı panelde uçtan uca görülmedi. Elle denendi: hatali kayitlar silindi, sayac dogru dondu. (DUZELTILDI)
14. `cerez_kendi` parametre degildi; ayarlar ekranindan, sunucudaki okumadan ve `ayar` tablosundan kaldirildi. Sayimlar suan ortak. (DUZELTILDI)
15. burst_dene.py adedi 60'lik basamaklara boluyor, sayaclari topluyor; AZAMI_HIT siniri korunuyor. (DUZELTILDI)
16. Kisiye ozel cerez gorunumu ileride kullanici yonetiminde admin izni olarak gelecek. `cerez.ts` icindeki `kendi` degiskeni ile `suzgec` ve `suzgecProfil` SQL'leri yerinde duruyor; eklenirken bunlar kullanilacak, yeni degisken uretilmeyecek.

### Sema hizalamasi (kapandi)
- `hit.geo_mode` varsayilani `tr_fallback`, `cerez_yukleme.durum` `aktarim`, `cookie_dosya.durum` `bekliyor`, `cookie_profil.durum` `tukendi` tasimiyor. Migration `040`. (DUZELTILDI)

## E. Burst ve kabul
15. burst_dene.py adedi 60'lik basamaklara boluyor, sayaclari topluyor; AZAMI_HIT siniri korunuyor. (DUZELTILDI)
16. 100 hit testi sürüyor (60 + 40); proxy hattı bağlanınca proxy üzerinden yeniden koşulacak.
17. CAPTCHA oranı, `not_found` oranı ve tamamlanma oranı ölçülmedi (C7, C8, C9, C10).
18. devam False donunce dongu kiriliyor ve fazladan hit atilmiyor; test_burst bunu sabitliyor (C21). (DUZELTILDI)
20. Ust uste 3 burst hedefsizse kelime paused oluyor, kampanya kapaniyor, hedef_yok uyarisi dusuyor; burst bazinda sayiliyor (A3). (DUZELTILDI)
21. Özet ekranı ölçüm verisi biriktikten sonra denenmedi; `-` ve `100+` durumları kontrol edilmedi.

## F. Sağlayıcı havuzu — M3
22. Sağlayıcı seçimi ağırlıklı ve devre kesicili hale getirilecek.
23. Oranlar `ayar` tablosundan okunur ve yalniz panelden yazilir (C65); `.env` oran anahtari yok. Satir yoksa varsayilan 100/0/0 gecerli, mobil orani 0 mobil turu kapatir. (DUZELTILDI)
24. Failover 10 saniye altında tamamlanacak (C6).
27. Oranlar panelden yazılıyor (`ayar` satırı, `PATCH /api/ayar/oran`, C65) ve `oran_mobil` 10. `hit.tur` kolonu eklendi (045), worker seçilen türü yazıyor. Kalan: mobil sağlayıcılarda (id 4, 5) gateway ve kimlik yok (madde 33); kimlik girilince dar kapsamlı tek burst ile mobil hit doğrulanacak. (KISMI)
28. Oran 0 ya da mobil pencere kapaliyken tur_sec mobile hic dusmuyor; test_havuz iki durumu da tarayarak sabitliyor. (DUZELTILDI)
29. Esikler panelden ayarlanir: esik_captcha, esik_geo, asgari_ornek. kaydet ve karantina_kontrol degerleri ayar_db uzerinden okur, okunamazsa sozlesme degeri gecerli. (DUZELTILDI)
30. Saglayicilar ekraninda oran toplami canli gosterilir; 100 degilse kirmizi ve kaydetme engelli. (DUZELTILDI)
33. Proxy ve SERP kimlik bilgileri (Decodo, SOAX vb.) henüz yok; sağlayıcı biçimleri gerçek anahtarla doğrulanmadı.

## G. Ölçüm hattı — M5
35. B kanali yazildi: worker/olcum_b.py kucuk profil havuzu, kalici cookie jar, HTML izlenim, hedefe tikla, post_click pozisyonu, 3 kullanimda yakma; /worker/olcum_b ucu imzali ve 15 dk turdan cagriliyor. Canli dogrulandi. (DUZELTILDI)
36. Ölçüm-B hattı (`post_click`) gerçekten çalışıyor mu doğrulanmadı.
37. aralikDk 15 dk tavaniyla kirpiyor, olcumYap her dakika deniyor; dort kirpma durumu test edildi (C12). (DUZELTILDI)
38. `olcum.ts` ve `serp.py` yedek sağlayıcı sırasını kullanıyor ama gerçek anahtarla sınanmadı; Decodo kotası doluyken Serper ile bir ölçüm turu koşulmalı.

## H. CI ve kalite kapıları
39. CI matrisi kurulu: `windows-latest` + `ubuntu-22.04`, iki is. Is akisi henuz kosmadi, yesil gorulmedi (C26, C27).
40. `python tools/tls_check.py --all` hiç çalıştırılmadı (C5 kanıtı).
41. `.gitattributes` dolu; 5 bayat CRLF/karma dosya LF'e cevrildi, `git ls-files --eol` temiz (C28). (DUZELTILDI)
42. `tools/lint_yol.py` kurallari `shell=True`, `datetime.utcnow()` ve elle `/` birlestirmeyi de yakaliyor; lint `worker/test_yol.py` ile pytest'e bagli, ihlal 0 (§20, C29). (DUZELTILDI)
43. `v_live` p95 400 ms ölçümü 3.300 iş birimiyle yapılmadı (C15).
44. Bolumleme kodu yazildi: `bolum.ts` esigi asinca gunluk bolumleri kurar ya da ileri gunleri acar, `partition` uyarisi duser, bakim turuna bagli. Canli deneme 10 milyon satirda yapilacak. (KISMI)

## I. Altyapı ve dağıtım
45. Docker imajları digest ile pinlenmedi (17.2). Docker kurulu değil; `docker-compose.yml` yalnızca üretim için duruyor.
46. `read_only`, `cap_drop`, root olmayan kullanıcı doğrulanmadı (17.3).
47. Kapandı: yedek/geri yükleme araçları yazıldı, geri yükleme canlı koştu (1227 sonrası root koşulsuz, görünümler yeniden kuruluyor), `verify.py` tamam döndü. Metrik ucu `GET /api/metrik` (C72). Boş kurulum 46 migration ile sınandı; 001 ile migration kolon çakışması `tools/test_sema_cakisma.py` ile bekçiye alındı. Metrik ekranı G5'te. (DUZELTILDI)
- Kelime bazlı kilit yazıldı: `keyword_geo.kilit_dugum/kilit_at` (042), sahiplenme, süre aşımında devralma, çakışma uyarısı ve bayat temizleme; `kilit_cakismasi` uyarı türü panelde. (DUZELTILDI)
48. Kod tarafı bitti ve yerel Memurai'de `requirepass` açıldı: parolasız `NOAUTH`, parolayla `PONG`, uyarı kalktı. HSTS, `secure: "auto"` çerez, sır uzunluğu uyarısı yerinde; Redis parolası URL'den ayrı taşınıyor. Kalan: TLS sonlandırma ters proxy yapılandırması (49 ile birlikte, üretim sunucusunda). (KISMI)
49. Sunucu tarafı veritabanı kurulumu ve ayarların oraya taşınması (kullanıcının işi).
50. `mysql.db` bir kez CRC hatası verdi ve onarıldı; tekrarı halinde `aria_chk --repair` gerekecek.
51. XAMPP `my.ini`: `innodb_buffer_pool_size=256M` ve `innodb_lock_wait_timeout=20` henüz uygulanmadı (kullanıcı sonra ele alacak).

## J. Uyarı takibi
52. Uyari ekrani var: /uyarilar, liste, aralik/tur/durum/site/kelime suzgeci, tek ve toplu kapatma, rehber penceresi; ust cubukta acik uyari rozeti. (DUZELTILDI)
53. Uyari saklama suresi 90 gun; saklama turu parcali siliyor, acik/kapali ayrimi yapmiyor. (DUZELTILDI)
54. queue_lag esik asilinca yaziliyor (varsayilan 200, kuyruk_esik ayari), 30 dakika sessizlik var. (DUZELTILDI)
55. Dokuz uyari turunun hepsi kodda uretiliyor; worker/test_uyari.py kaynagi tarayip eksik turu yakaliyor. (DUZELTILDI)

## K. Kod borcu (250 satır sınırı, §23.2)
56. cerez.ts 841 satirdan src/server/cerez/ altinda yedi dosyaya bolundu (yollar, ortak, ayristir, aktarim, sayfa, silme, yukleme, index); en buyugu 223 satir. worker/test_boyut.py 250 sinirini izliyor. (DUZELTILDI)
57. `panel.ts` 454, `kelime.ts` 389, `isci.ts` 264 satır. (DUZELTILDI)
58. `havuz.py` 542 satır ve tek dosyada dört iş yapıyor (oran, sağlayıcı seçimi, çerez seçimi, kuyruk). (KISMI: havuz.py ve saglik_db.py bolunmedi)
59. serp.py 242 ve burst.py 196 satira indi; serp_ortak.py, serp_html.py, burst_hit.py ayrildi, testlerin eristigi adlar korundu. (DUZELTILDI)

## L. Sözleşme ve belge
60. Liste uçlarının dönüş zarfı sözleşmede tek biçime bağlanmadı: sayfalı uçlar `{satirlar, toplam, sayfa, adet}`, kısa listeler düz dizi dönüyor.
61. `docs/DURUM.md` ve `docs/EKSIKLER.md` dışındaki belgeler (`CONTRACT.md` dışında) gözden geçirilmedi.
62. README, `.env.example`, docker-compose ve `.gitattributes` devir paketi kontrolü. (DUZELTILDI)
Devir paketi tamam: README, `.env.example`, `docker-compose.yml`, `.gitattributes`, `.gitignore` yazıldı; DEVIR/DURUM aynı duruma çekildi. Parola artık kodda geçmiyor, `REDIS_PASSWORD` ayrı taşınıyor, yedekler `yedek` volume'unda.

## M. Pilot ve devir
63. M6 pilotu: 5 sunucu, 20 kelime, 2 hafta saha testi.
64. Pilot kabul ölçümleri: C7, C8, C9, C10, C11, C12, C15.
65. Bolumleme 10 milyon satir esigiyle canli denenecek: esik asilinca gunluk bolumler kuruluyor mu, ileri gunler aciliyor mu, `partition` uyarisi dusuyor mu, saklama eski bolumleri dusuruyor mu.

## N. Gelistirme asamasi (hayata gecmeden yapilmaz)

- G1 — Araclar menusu acilacak; bakim ve toplu islem araclari orada toplanacak.
- G2 — Cerez canlilik olcumu araci bu menuden tetiklenecek.
- G3 — Cerez il eslestirmesi (klasor yapisi ya da yukleme aninda il secimi).
- G4 — Cakisma suresi ayari ve cakisma listesi Araclar menusunde; uyarilar orada kapatilacak.
- G5 — Yedek alma, yedek listesi, geri yukleme ve metrik ucu (E1-E7) Araclar menusunden tetiklenecek; gelistirme asamasinda yapilacak.

E1–E7 tamamlandı: yedek/geri yükleme, metrik ucu, E2 günlük, E3 düğüm sağlığı, E4 zarif boşaltma, E5 migration geri alma, E7 tek örnek kilidi.

## O. Olcum dogrulugu — EN ACIL (yerel arama ile ayni sonuc)

Bu bolumun kabul olcutu: ayni kelime, ayni dakika, ayni TR residential IP sinifi uzerinden API sonucu ile gercek tarayici sonucu ilk 20 sonuc kumesi en az %90 ortusur. Bu saglanmadan hicbir madde kapanmis sayilmaz ve proje ilerlemis sayilmaz.

Ulusal kelime kurali: il secilmemisse il ile alakali hicbir islem yapilmaz. Ne Decodo govdesinde il/uule-il, ne proxy kullanici adinda `-city-`. Buna karsilik ulke sabiti her ulusal olcumde vardir: `gl=tr`, `hl=tr`, TR residential cikis. Uule ulusalda gonderilmez (66). Il kapsamli kelimede ayni alanlar il uule'siyle doldurulur.

66. **KAPANDI** — Ulusal kelimede uule hic gonderilmez. Once ulke uule'si eklendi, sonra zararli oldugu olculdu: ayni IP'de uule'li oylama %10, uule'siz oylama %100 (`tools/oylama_dene.py`). Uule listeyi ikinci kumeye dusuruyor, IP cografyasi zaten TR sinyali veriyor. `worker/olcum_a.py`, `worker/app.py`, `worker/test_app.py`, `src/server/olcum.ts` ve C20 guncellendi. Il kapsamli kelimede davranis degismez: il uule'si gonderilir. Ulusal hitte TR cikis zorunludur; yabanci cikisa dusen ulusal hit siralamayi kaydirir.
67. `tools/gen_uule.py` kanonik v2 bicimine cekilir: `latlng{ latitude_e7:<lat*1e7> longitude_e7:<lon*1e7> } radius:<m>`, standart base64 (`+` `/` korunur), kirpma yok. Bugunku `latlng:lat,lon` bicimi ve `urlsafe` alfabesi bozuk uule uretiyor; bozuk uule sessizce yok sayilir. 004 yeniden uretilir, `db/migrations/geri` dosyasi da guncellenir.
68. Ulusal kelimede il sizmasina karsi bekci test: Decodo govdesinde `uule` il uule'si olmamali, proxy dizesinde `-city-` gecmemeli. `worker/test_serp.py` ve `worker/test_proxy.py` bu iki durumu sabitler.
69. Olcum istegi control plane'in kendi IP'sinden degil, TR residential proxy uzerinden atilir; Decodo govdesine `proxy_pool: "premium"` yazilir. Bugun `olcum.ts` proxy kullanmiyor, datacenter IP'den gidiyor; cift SERP'in en guvenilir tetikleyicisi budur.
70. Decodo yanitindaki `search_parameters.gl` ile gonderilen `geo_location` karsilastirilir. Taninmayan `geo` sessizce US'e dusuyor ve 200 donuyor; uyusmazsa `position` yazilmaz, `serp_hatasi` uyarisi duser.
71. Supheli (zehirlenmis) SERP denetimi ve tek tekrar: sonuc listesi 10'dan kisa, kelimenin ana terimini icermiyor ya da son temiz olcumden kume olarak uzaksa kaydedilmez, tek kez yeniden sorulur. Ikinci deneme de supheli ise `rank = NULL` ve `serp_hatasi` uyarisi.
72. Olcum tek kod yoluna toplanir. Bugun `src/server/olcum.ts` ile `worker/serp.py` ayni isi iki ayri ve sapan bicimde yapiyor (`geo`, `locale`, `proxy_pool`, `uule`, sayfa beklemesi). Olcum de imzali worker ucundan (`/worker/olcum_a`) kosar; `olcum.ts` yalnizca orkestrasyon yapar.
73. `locale` degeri sozlesmeye uygun kucuk harf `tr-tr` olur; `panel_ayar.ts` icindeki `serp-dene` ucu da ayni bicime cekilir (bugun `tr-TR` ve `geo: "tr"`).
74. Mobil isaretli kelimede olcum mobil profil ve mobil cikisla yapilir. Decodo `/search` `device` parametresi almiyor; mobil kelime bugun masaustu sayfasindan olculuyor (C48 ile celisir). Karar: mobil kelimede mobil proxy + android profil zorunlu, olcum sonucu `hit.tur` gibi isaretlenir.
75. `kok()` alan adi cozumlemesi duzeltilir: son iki etiket yerine bilinen cok parcali uzantilar (`com.tr`, `net.tr`, `org.tr`, `gov.tr`, `edu.tr`, `co.uk`, `com.br`) korunur. Bugun `site.com.tr` -> `com.tr` oluyor ve o kelimede ilk `.com.tr` rakip hedef sanilip yanlis sira yaziliyor. Ayni duzeltme `worker/serp_ortak.py` ve `src/server/olcum.ts` icinde birlikte yapilir.
76. B kanali onarilir: `serp_getir_html` `organik` listesini doldurur, `olcum_b` bu listeyi kullanir. Bugun `organik` hic dolmadigi icin B kanali rank bulamiyor, tiklama yapmiyor ve `position`'a `post_click` + `NULL` yaziyor.
77. `position` yaziminda 200 disi yanit basarili olcum sayilmaz. Bugun yalnizca 429 turu kesiyor; 500/502 `rank = NULL` satiri yazip "ilk 100'de yok" gibi gorunuyor.
78. `position` satirina `serp_provider` yazilir; hangi saglayicidan geldigi sonradan gorulebilsin.
79. Olcumde sayfalar arasi bekleme ve tur butcesi: 10 sayfa tek nefeste gidiyor, hiz siniri riski var.
80. Kabul kaniti araci: `tools/serp_karsilastir.py`. Ayni kelimeyi API ile ve gercek tarayici yoluyla (TR residential + Chromium) ceker, ilk 20 kume ortusmesini yuzde olarak basar. Bu bolumun kapanis olcusu bu aracin ciktisidir.

## P. Veri butunlugu

81. `src/server/isci.ts`: `if (!yanit.ok) throw` satiri 503 dalindan once calistigi icin 503 blogu olu kod. Zarif bosaltmada burst hata istatistigiyle kapaniyor, sebep yazilmiyor (C76/E4). Once 503 kontrolu, sonra `!yanit.ok`.
82. `hitYaz` icinde `h.geo_mode ?? "tr_fallback"` yabanci cikista modu bozuyor; worker degeri ne ise o yazilir, null ise null.
83. `rapor.ts`: ulusal kelime `GROUP BY ... il.name` yuzunden 81 satir cikiyor; il yalniz `geo_scope = 'province'` iken gruplanir.
84. `rapor.ts`: hit sayisi `SUM(b.target_count)` yerine gercek `hit` sayimindan gelir; erken biten burst sayaci sisiriyor.
85. `havuz.cerez_sec` her hit'te iki toplu `UPDATE cookie_profil` calistiriyor; `durum` indeksi eklenir ve kilit dusurme turu seyreltilir.
86. `saglik_db.uyari` kelime-site eslesmesini metinle ve `LIMIT 1` ile yapiyor; ayni metin iki sitede varsa uyari yanlis siteye baglaniyor. Kimlik tasinir.
87. `veritabani.ts` `islem()` icinde `baglanti.query` yerine `baglanti.execute` kullanilir (parametre kacisi).
88. `proxy.py` `_geonode` il slug'ini dogrulamadan kullanici adina ekliyor; Geonode'un bekledigi deger (il adi/slug) teyit edilir, yanlissa 407 sessizce saglayiciyi kapatir.

### P kapanislari (2026-11-26)

- 77 KAPANDI — `tarayici._tara` hic sonuc yokken gelen 5xx'i `error` dondurur, "ilk 100'de yok" yazilmaz. Kanit: `worker/test_tarayici.py::test_http_500_olcum_sayilmaz`.
- 78 KAPANDI — `position.saglayici` zaten yaziliyor (`tarayici`, saglayici adi); hangi kaynaktan geldigi gorunur.
- 79 KAPANDI — sayfa basina `BEKLEME_MS` (4 sn) ve `networkidle` beklemesi var; 10 sayfa tek nefeste gitmiyor.
- 80 KAPANDI — `tools/serp_karsilastir.py` tarayici ile API'nin ilk 20 kumesini karsilastirir, ortusme yuzdesini basar, esik %90.
- 82 KAPANDI — `hitYaz` saglayicisiz hitte `yabanci`, saglayicili hitte `tr_fallback` yazar; mod istatistigi bozulmuyor.
- 83 KAPANDI — `rapor.ts` il join'ini `k.geo_scope = 'province'` ile sinirlar; ulusal kelime 81 satir uretmez.
- 84 KAPANDI — rapor ve hacim denetimi gercek `hit` sayimindan okur, `target_count` yalniz planlanan olarak doner.
- 85 KAPANDI — `cookie_profil.durum` indeksi eklendi (migration 051 + geri dosyasi).
- 86 KAPANDI — `saglik_db.uyari` kimligi kelime + domain ile kurar; domain verilmezse site eslesmesi aranmaz.
- 87 KAPANDI — `islem()` icindeki yazmalar `baglanti.execute` (hazir ifade) kullanir.
- 88 KAPANDI — `proxy._geonode` il slug'ini kucuk harf/harf-rakam suzer, bos ya da uzun slug city hedeflemesini atlar. Kanit: `worker/test_proxy_geonode.py`.
- 69 KODDA TAMAM — `tarayici.serp_oku` deneme basina havuzdan yeni proxy secer; anahtar gelince canli dogrulanacak.
- Y1 KAPANDI — `uule` tarayici URL'sinden kaldirildi, `gl=tr`/`hl=tr` kaldi. Kanit: `worker/test_tarayici.py::test_adres_uule_tasimaz`.

## Q. Panel, arayuz ve yapi (otonom yapilir)

89. `saglayicilar.tsx` oran kaydinda `onError` yok; sunucu 400'u kullaniciya gorunmuyor.
90. `panel.ts` log suzgeci ile `rapor.ts` suzgeci ayni yardimcidan gecmez; iki yerde ayrisirsa silinen satir ekranda gorunene esit olmaz.
91. `serp_html.py` icindeki mukerrer satirlar (`sonuclari_ayikla` iki kez, `return sonuc` iki kez) ve kullanilmayan importlar temizlenir.
92. `olcum.ts` icindeki kaymis docstring'ler duzeltilir, imza uretimi tek yere toplanir.
93. DEVIR.md ve DURUM.md guncellenir: oran ucu bitti, siradaki is bu bolumdur; `hit.tur`/`olcum_b` durumu yazilir.
94. Sozlesmeye islenir: §5 ulusal/il uule ayrimi, §9 olcum bekleme sabitleri, C20 guncellemesi, C86 duzeltmesi, yeni C89 (olcum dogrulugu: API ile gercek tarayici ilk 20 ortusmesi >= %90) ve C90 (ulusal kelimede il sizmasi yok, ulke uule'si var). (Onay gerekir)

## R. Kabul olcutu — bu bolumun kapanisi

- `tools/serp_karsilastir.py` 20 kelimede kosar, ortalama ortusme >= %90.
- Ayni kelimede `position` ile gercek tarayici sirasi arasinda 2 farktan buyuk sapma kalmaz.
- `provider_geo`/`hit` kayitlarinda mod istatistigi dogru: ulusal hit `geo_code = NULL`, `geo_mode` gercek cikisi yansitir.
- Bozuk uule uretimi kalmaz: `tools/uule.py --dogrula` tum 81 ili cozer.