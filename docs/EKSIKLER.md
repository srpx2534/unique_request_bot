# Eksik maddeler

Bu dosya, ertelenen doğrulamaları ve açık işleri tutar. Bir madde
kapatıldığında buradan silinir ve sonucu sözleşmedeki ilgili kritere
işlenir.

## Proxy hattı — ücretli plana geçince

Ücretsiz katmanda Decodo residential kimlik bilgileri alınamadığı için
aşağıdakiler doğrulanmadı. Kod, ücretli sürümde çalışacak varsayımıyla
yazıldı; sağlayıcı gelince sırayla sınanacak.

- `DECODO_USER` / `DECODO_PASS` / `DECODO_GATEWAY` gerçek değerlerle doldurulacak.
- `tools/proxy_dene.py` ile çıkış IP'si ve Türkiye konumu doğrulanacak.
- Aynı oturum kimliğinin aynı IP'yi koruduğu, farklı oturumun farklı IP verdiği ölçülecek.
- `city-<slug>` hedefleme biçiminin gerçekten il bazlı IP döndürdüğü doğrulanacak; dönmüyorsa `city_capable=0` işaretlenip ulusal moda düşülecek (§5, C17).
- `provider_geo.exhausted_until` davranışı gerçek CAPTCHA oranıyla sınanacak (C18).
- Sağlayıcı başına eşzamanlı oturum sınırı ve kota tüketimi ölçülecek.
- Ücretsiz herkese açık listelerde TR adayı bulunamadı; yalnızca yerel dinleyici ile parametre geçişi kanıtlandı, gerçek çıkış IP'si görülmedi.

## Oturum sürekliliği

- Hit başına tek `Session` kullanılacak: izlenim, tıklama ve pogo aynı oturumdan
  geçecek. Bugün üçü ayrı oturum açıyor, Google'ın izlenimde verdiği `AEC`/`NID`
  tıklamaya taşınmıyor ve istemci aynı kişi gibi görünmüyor.
- Başlık sırası profile uyacak: kendi `Accept` / `Accept-Language` override'ları
  curl_cffi'nin sırasını bozuyor olabilir, ölçülecek.
- Aynı hit içinde çıkış IP'si sabit kalacak; proxy hit başına bir kez üretiliyor,
  bu korunacak.

## Gerçek tarayıcı cookie'leri

Kullanıcı gerçek tarayıcıdan alınmış cookie dosyası sağlayabilir. Kullanılacak,
ama şu koşullarla:

- Format: Netscape `cookies.txt` (tercih) veya JSON dizi. Dosya başına tek
  profil; dosya adında il kodu taşınacak (ör. `34.txt`).
- Havuz: tek cookie yüzlerce hit için yetmez. Dosyalar sırayla, hit başına bir
  kez kullanılacak; tükenince başa dönülecek.
- Coğrafya: cookie hangi ilden alındıysa o ilin IP'siyle eşleşmeli. TR cookie +
  yabancı IP çelişki üretir.
- `SOCS` / `CONSENT` gerçek tarayıcıdan gelirse bizim sabit değerlerden daha
  doğru; onay duvarı için bunlar yeğlenecek.
- Oturum açmış hesap cookie'si (`SID`) güçlü sinyaldir ama tek hesaptan yüzlerce
  arama hesabı şüpheli gösterebilir. Önce oturumsuz cookie ile başlanacak,
  `SID` ayrı ölçülecek.
- Tazelik: haftalar önce alınmış `NID`/`AEC` süresi geçmiş olur, Google yeniden
  üretir. Fayda düşer, zarar yok.
- Cookie dosyaları repoya girmez; `.gitignore`'a alınacak, hesap token'ı
  taşıyabilir.
- Cookie'ler JS duvarını aşmaz; sonuç listesi yine API'den gelecek.

## Burst ve kabul

- `AZAMI_HIT = 60` olduğu için 100 hit'lik test iki basamağa bölünecek (§9).
- 100 hit testi sürüyor (60 + 40); proxy hattı bağlanınca proxy üzerinden
  yeniden koşulacak.
- CAPTCHA oranı, `not_found` oranı ve tamamlanma oranı henüz ölçülmedi (C7, C8, C9, C10).
- `stop` sonrası yeni hit atılmadığı doğrulanmadı (C21).
- Aynı `keyword_geo` üzerinde çakışan burst sayısı ölçülmedi (C16).

## Sağlayıcı havuzu — M3

- Sağlayıcı seçimi ağırlıklı ve devre kesicili hale getirilecek.
- Mobil / residential / datacenter oranı `.env` üzerinden ayarlanabilir olacak;
  `PROXY_MOBIL_ORAN=0` mobil'i tamamen kapatacak.
- Failover 10 saniye altında tamamlanacak (C6).
- Sağlayıcı genel CAPTCHA oranı %20'yi geçince 2 saat karantina uygulanacak (§8).
- `provider` ve `provider_geo` tabloları henüz boş; seed yazılmadı.

## Ölçüm hattı — M5

- Ölçüm-A kanalı SERP API'sinden, `clean` kanaldan, daima ulusal yapılacak (C20).
- Ölçüm-B kanalı ayrı küçük havuz ve kalıcı cookie jar ile kurulacak; `profile` tablosu boş.
- Ölçüm boşluğu 15 dakikayı geçmeyecek şekilde zamanlayıcı yazılacak (C12).

## Ortam

- Docker kurulu değil; `docker-compose.yml` yalnızca üretim için duruyor.
- `mysql.db` bir kez CRC hatası verdi ve onarıldı; tekrarı halinde `aria_chk --repair` gerekecek.
- Birim testleri yazıldı (`worker/test_serp.py`, `worker/test_proxy.py`, 13 test geçiyor).
- CI matrisi `windows-latest` ve `ubuntu-22.04`; iş akışı henüz koşmadı, CI yeşil değil (C26, C27).
- `.gitattributes` boş; CRLF kontrolü bu yüzden anlamsız (C28).

## Sözleşme

- Sözleşme toplu güncellenecek; M2 sonunda tek blok halinde verilecek.
- Google'ın JavaScript zorunluluğu §4'e işlenecek: burst hattında SERP listesi API'den, tıklama proxy'den.
- Cookie havuzu ve oturum sürekliliği §9'a işlenecek.

## Uyarı takibi

- Uyarılar `alert` tablosuna yazılıyor: `hedef_yok`, `failover`, `burst_hata`,
  `captcha`, `quota`, `provider_down`. Okuma için `v_alert` view'i ve
  `tools/alert_liste.py` var.
- Panelde uyarı ekranı M4'te yapılacak: liste, yaş, kapatma, filtre.
- Kapatılmayan uyarı birikimi için saklama süresi belirlenecek (`audit_log` 1 yıl,
  `alert` için süre yok).
- `queue_lag` türü henüz hiç yazılmıyor; kuyruk M4'te gelince bağlanacak.
- Oran eşikleri (`GEO_ESIK=35`, `GENEL_ESIK=20`, `ASGARI_ORNEK=10`) sabit;
  panelden ayarlanabilir hale getirilecek.

## Sağlayıcı oranları

- Oranlar `ayar` tablosunda, panelden düzenlenecek (M4).
- `oran_mobil=0` mobil havuzunu tamamen kapatır; doğrulanacak.
- Oranların toplamı 100 değilse okurken normalize edilir; panelde toplam uyarısı
  gösterilecek.
