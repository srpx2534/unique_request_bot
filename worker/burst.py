"""Burst yürütücü: izlenim, tıklama, dwell, pogo.

Bir burst, aynı kelime için art arda atılan hit'lerden oluşur. Her hit'te
sıra şudur: SERP izlenimi (proxy üzerinden, doğrudan Google), hedefe
tıklama, dwell, pogo.

İzlenim neden proxy üzerinden: Google aramayı ve tıklamayı aynı IP'den
görmeli. SERP API'si kendi IP'sini kullanır, bu yüzden yalnızca hedef
adresi çözmek için bir kez çağrılır; sıralama bir burst içinde değişmez.

Her hit tek oturum ve tek profil kullanır; oturum üç adım boyunca açık
kalır, böylece cookie sürekliliği korunur.

Sağlayıcı düşerse hit bir kez, yeni sağlayıcı ve yeni profille tekrarlanır
(C6). Mobil IP yalnızca ilk hit'lerde kullanılır (§8).

Kullanım: worker/app.py, tools/burst_dene.py.
"""

from __future__ import annotations

import random
import time
from typing import Callable
from urllib.parse import quote

from curl_cffi import requests

from worker import cookie, fingerprint, havuz, saglik, saglik_db, serp
from worker.burst_hit import sayaclar, tek_hit

AZAMI_HIT = 60  # sözleşme §9: basamak boyu en fazla 60
HIT_ARASI_MIN = 0.4  # saniye; art arda istekte insan ritmi
HIT_ARASI_MAX = 1.4  # saniye; jitter için üst sınır
MOBIL_HIT_SAYISI = 2  # hit; mobil IP yalnızca ilk hit'lerde kullanılır (§8)
BASARI_ESIGI = 0.95  # C10; altında kalırsa burst_hata uyarısı düşer
DENEME = 2  # sağlayıcı düşerse toplam kaç kez denenir


def burst_yap(
    sorgu: str,
    hedef_domain: str,
    adet: int,
    proxy_secici: Callable[[], str | None] | None = None,
    uule: str | None = None,
    hedef_url: str | None = None,
    geo_slug: str | None = None,
    devam: Callable[[], bool] | None = None,
) -> dict:
    """Burst'ü yürütür.

    Args:
        sorgu: Aranacak kelime.
        hedef_domain: Tıklanacak alan adı.
        adet: Atılacak hit sayısı. AZAMI_HIT ile sınırlanır.
        proxy_secici: Her hit için proxy döndüren çağrılabilir. None ise
            havuzdan seçilir.
        uule: Konum parametresi; izlenim adresine eklenir.
        hedef_url: Hazır hedef adres. Verilirse API ile çözüm atlanır.
        geo_slug: İl slug'ı; verilirse il hedefli sağlayıcı aranır.
        devam: Her hit öncesi sorulan 'sürsün mü' geri çağrısı. False
            dönerse kalan hit atılmaz (C21).

    Returns:
        result, sayaçlar, elapsed_ms, hedef_url, durduruldu ve hits
        alanlarını taşıyan sözlük. result: ok, hedef_yok, anahtar_yok.
    """
    adet = max(1, min(adet, AZAMI_HIT))
    basladi = time.perf_counter()

    sonuc = {"result": "ok", "hedef_url": None, "elapsed_ms": 0,
             "durduruldu": False, "hits": [], **sayaclar()}

    if hedef_url:
        # Adres dışarıdan geldiyse API'ye hiç gidilmez; burst daha hızlı başlar.
        serp_url = f"https://www.google.com/search?q={quote(sorgu)}"
    else:
        # Hedef adres bir kez çözülür: 100 hit için 1000 API isteği gitmesin.
        cozum = serp.serp_getir(sorgu, hedef_domain=hedef_domain, uule=uule)
        if cozum["result"] == "anahtar_yok":
            sonuc["result"] = "anahtar_yok"
            return sonuc
        if cozum["result"] not in ("ok", "not_found"):
            # Geçici API hatası (timeout, 429, 5xx): hedef yok sayılmaz ve
            # sayaç artmaz; yoksa tek bir 429 kelimeyi durdurabilirdi.
            sonuc["result"] = "serp_hata"
            sonuc["hata"] = cozum.get("mesaj", "")
            return sonuc
        if cozum["result"] == "not_found" or not cozum["position"]:
            sonuc["result"] = "hedef_yok"
            # Hic hit atilmadi: kayip sayisi adet degil, hedef_yok olarak yazilir.
            sonuc["hedef_yok"] = adet
            # Hedef ilk 100'de yok: sayaç artar, eşikte kelime durur.
            sayac, durdu = saglik_db.hedef_yok_islet(sorgu, hedef_domain)
            sonuc["hedef_yok_sayac"] = sayac
            if not durdu:
                saglik_db.uyari("hedef_yok", None, f"'{sorgu}' ilk 100'de bulunamadı", kelime=sorgu, domain=hedef_domain)
            return sonuc
        saglik_db.hedef_yok_sifirla(sorgu, hedef_domain)
        hedef_url = next(
            k["link"] for k in cozum["organik"] if k["position"] == cozum["position"]
        )
        serp_url = cozum["url"] or f"https://www.google.com/search?q={quote(sorgu)}"

    sonuc["hedef_url"] = hedef_url

    onceki_profil: str | None = None
    durduruldu = False
    failover_uyarildi = False
    # İl kodu bir kez çözülür; her hit'te sorgu açmamak için.
    geo_kodu = havuz.kod_bul(geo_slug) if geo_slug else None
    # Kelime mobil isaretliyse mobil IP ve android profil zorlanir.
    mobil_hedef = havuz.kelime_mobil(sorgu)
    mobil_hit_siniri = max(1, min(3, MOBIL_HIT_SAYISI))
    for sira in range(1, adet + 1):
        # Durdurma her hit öncesi sorulur: uçan istek kesilmez, yenisi başlamaz.
        if devam is not None and not devam():
            durduruldu = True
            break

        # Mobil IP pahalı ve çabuk tükeniyor; yalnızca ilk hit'lerde
        # kullanılır, sonra residential'a düşülür (§8).
        mobil_acik = sira <= mobil_hit_siniri

        kayit: dict = {}
        failover_oldu = False
        saglayici_id: int | None = None
        for deneme in range(1, DENEME + 1):
            geo_mod: str | None = None
            tur: str | None = None
            if proxy_secici:
                proxy_adres = proxy_secici()
            else:
                # sec_mod ucuncu eleman olarak hangi yoldan gidildigini verir.
                # Paylasilan son_mod globali eszamanli burst'te karisirdi.
                secim = havuz.sec_mod(geo_slug, mobil_acik, "mobile" if mobil_hedef else None)
                proxy_adres = secim[1] if secim else None
                saglayici_id = secim[0] if secim else None
                geo_mod = secim[2] if secim else None
                tur = secim[3] if secim else None

            # Cerez yalnizca ayni ulke IP'siyle anlamli: yabanci hitte yuklenmez.
            cerez_profil: int | None = None
            cerezler: list[dict] = []
            aile: str | None = None
            if geo_mod in ("city", "tr_fallback"):
                secilen = havuz.cerez_sec(geo_kodu, hedef_domain, sorgu, mobil_hedef, ulke="TR")
                if secilen is not None:
                    cerez_profil, aile = secilen
                    cerezler = cookie.suz(havuz.cerez_al(cerez_profil), hedef_domain)

            # Cerez varsa parmak izi o cerezin ailesine sabit; yoksa rastgele.
            mobil_profil = bool(mobil_hedef or (mobil_acik and tur == "mobile"))
            profil = fingerprint.profil_sec(haric=onceki_profil, aile=aile, mobil=mobil_profil)
            onceki_profil = profil
            kayit = tek_hit(sorgu, hedef_url, serp_url, proxy_adres, profil, uule, cerezler)
            # Telemetri secimle birlikte tamamlanir; hit tablosu bunlari bekler.
            kayit["saglayici_id"] = saglayici_id
            kayit["geo_mode"] = geo_mod
            kayit["tur"] = tur
            kayit["cerez"] = bool(cerezler)
            # Cerezle basarili hit, cerezi canli isaretler; olcum turu esas
            # kanal olarak kalir, bu ikinci kanal sayaci calisirken de artirir.
            if cerez_profil is not None and kayit["result"] == "ok":
                havuz.cerez_canli(cerez_profil)
            if cerez_profil is not None:
                havuz.cerez_birak(cerez_profil)
            if kayit["result"] == "ok" or kayit["result"] == "captcha":
                break
            # Sağlayıcı kaynaklı düşüşte yeni sağlayıcıyla bir kez daha
            # denenir; aynı sağlayıcıda ısrar etmek zaman kaybıdır (C6).
            if deneme < DENEME:
                failover_oldu = True
                # Burst başına tek uyarı yeter; her hit'te tekrar yazılmasın.
                if not failover_uyarildi:
                    saglik_db.uyari("failover", saglayici_id, f"'{sorgu}' sağlayıcı değişimi", kelime=sorgu, domain=hedef_domain)
                    failover_uyarildi = True

        # Bayrak deneme döngüsünde kaybolmasın diye burada işaretlenir.
        if failover_oldu:
            kayit["failover"] = True

        # Sağlayıcı sağlığı yalnızca gerçek bir sağlayıcı kullanıldıysa işlenir.
        if saglayici_id:
            if kayit["result"] == "ok":
                saglik_db.hata_sifirla(saglayici_id)
            elif kayit["result"] in ("error", "timeout"):
                # Kota bir ariza degil plan meselesidir: karantina degil,
                # kota isaretlenir ve saglayici yeni hit almaz (C81).
                if saglik.kota_mi(kayit.get("mesaj")):
                    saglik_db.kota_isle(saglayici_id)
                else:
                    saglik_db.hata_isle(saglayici_id)
            # İl çifti yalnızca gerçekten il hedefli çıkışta işlenir; ulusal ya
            # da yabancı çıkış kodu il çiftine yazarsa eşik yanlış çiftte dolar.
            saglik_db.kaydet(
                saglayici_id,
                geo_kodu if kayit.get("geo_mode") == "city" else None,
                kayit["result"],
            )
            saglik_db.bayt_ekle(saglayici_id, kayit["bytes"])
            saglik_db.karantina_kontrol(saglayici_id)

        kayit["sira"] = sira
        sonuc["hits"].append(kayit)
        sonuc[kayit["result"]] = sonuc.get(kayit["result"], 0) + 1

        # Hit arası bekleme; son hit'ten sonra beklemek gereksiz.
        if sira < adet:
            time.sleep(random.uniform(HIT_ARASI_MIN, HIT_ARASI_MAX))

    sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
    sonuc["durduruldu"] = durduruldu

    # Kapanış değerlendirmesi: oran eşiğin altındaysa uyarı düşülür.
    # Payda atılan hit'tir: erken durdurulan burst tam adetle bölününce
    # sağlıklı iş yanlışlıkla burst_hata yazıyordu.
    atilan = len(sonuc["hits"])
    # Hic basarili hit yoksa saglayici calismiyor demektir: kelime durur.
    if atilan and sonuc["ok"] == 0:
        saglik_db.saglayici_yok_dur(sorgu, hedef_domain)
    if atilan and sonuc["ok"] / atilan < BASARI_ESIGI:
        saglik_db.uyari(
            "burst_hata", None,
            f"'{sorgu}' tamamlanma %{round(sonuc['ok'] * 100 / atilan)} "
                        f"(ok={sonuc['ok']} captcha={sonuc['captcha']} hata={sonuc['error']})",
            kelime=sorgu, domain=hedef_domain,
        )
    if sonuc["captcha"]:
        saglik_db.uyari("captcha", None, f"'{sorgu}' captcha={sonuc['captcha']}", kelime=sorgu, domain=hedef_domain)
    return sonuc
