# Eksik maddeler

A (proxy kodu), B (worker testleri) ve C (oturum sürekliliği) kapandı; 112 test yeşil. Kalan maddeler sırayla kapatılır. Bir madde kapanınca buradan silinir, sonucu sözleşmedeki ilgili kritere işlenir.

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
19. Aynı `keyword_geo` üzerinde çakışan burst sayısı ölçülmedi (C16).
20. Ust uste 3 burst hedefsizse kelime paused oluyor, kampanya kapaniyor, hedef_yok uyarisi dusuyor; burst bazinda sayiliyor (A3). (DUZELTILDI)
21. Özet ekranı ölçüm verisi biriktikten sonra denenmedi; `-` ve `100+` durumları kontrol edilmedi.

## F. Sağlayıcı havuzu — M3

22. Sağlayıcı seçimi ağırlıklı ve devre kesicili hale getirilecek.
23. Oranlar `.env` ile ayarlanir: PROXY_RESIDENTIAL_ORAN, PROXY_MOBIL_ORAN, PROXY_DATACENTER_ORAN. Tablo degeri varsa o kazanir, yoksa env, yoksa varsayilan. PROXY_MOBIL_ORAN=0 mobil turu kapatir. (DUZELTILDI)
24. Failover 10 saniye altında tamamlanacak (C6).
25. Sağlayıcı genel CAPTCHA oranı %20'yi geçince 2 saat karantina uygulanacak (§8).
26. `provider` ve `provider_geo` tabloları henüz boş; seed yazılmadı.
27. `oran_mobil` hâlâ 0; açılmadan android profil hiç çıkmaz. Mobil yol canlı istekle doğrulanmalı.
28. Oran 0 ya da mobil pencere kapaliyken tur_sec mobile hic dusmuyor; test_havuz iki durumu da tarayarak sabitliyor. (DUZELTILDI)
29. Esikler panelden ayarlanir: esik_captcha, esik_geo, asgari_ornek. kaydet ve karantina_kontrol degerleri ayar_db uzerinden okur, okunamazsa sozlesme degeri gecerli. (DUZELTILDI)
30. Saglayicilar ekraninda oran toplami canli gosterilir; 100 degilse kirmizi ve kaydetme engelli. (DUZELTILDI)
31. `provider.bytes_month` ve `quota_bytes` hiçbir yerde yazılmıyor; kota muhasebesi fiilen yok.
32. Kota uyarısı yalnızca SERP 429'una bağlı; proxy bayt kotası için uyarı yok.
33. Proxy ve SERP kimlik bilgileri (Decodo, SOAX vb.) henüz yok; sağlayıcı biçimleri gerçek anahtarla doğrulanmadı.

## G. Ölçüm hattı — M5

34. Ölçüm-A kanalı SERP API'sinden, `clean` kanaldan, daima ulusal yapılacak (C20).
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
47. `mysqldump` yedek ve geri yükleme testi yok (17.6). Yedek/geri yükleme, metrik ucu, tek örnek kilidi (E1-E7) yok.
48. HTTPS/HSTS, Redis `requirepass`, sır saklama (B6/B8/B9) üretim öncesi.
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
62. README, `.env.example`, docker-compose ve `.gitattributes` devir paketi kontrolü.

## M. Pilot ve devir

63. M6 pilotu: 5 sunucu, 20 kelime, 2 hafta saha testi.
64. Pilot kabul ölçümleri: C7, C8, C9, C10, C11, C12, C15.
65. Bolumleme 10 milyon satir esigiyle canli denenecek: esik asilinca gunluk bolumler kuruluyor mu, ileri gunler aciliyor mu, `partition` uyarisi dusuyor mu, saklama eski bolumleri dusuruyor mu.

## N. Gelistirme asamasi (hayata gecmeden yapilmaz)

- G1 — Araclar menusu acilacak; bakim ve toplu islem araclari orada toplanacak.
- G2 — Cerez canlilik olcumu araci bu menuden tetiklenecek.
- G3 — Cerez il eslestirmesi (klasor yapisi ya da yukleme aninda il secimi).
