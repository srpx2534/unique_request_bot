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
(C6). Mobil IP yalnızca ilk saniyelerde kullanılır (§8).

Kullanım: worker/app.py, tools/burst_dene.py.
"""

from __future__ import annotations

import random
import time
from typing import Callable
from urllib.parse import quote

from curl_cffi import requests

from worker import click, fingerprint, havuz, saglik, serp

AZAMI_HIT = 60  # sözleşme §9: basamak boyu en fazla 60
HIT_ARASI_MIN = 0.4  # saniye; art arda istekte insan ritmi
HIT_ARASI_MAX = 1.4  # saniye; jitter için üst sınır
MOBIL_PENCERE_SN = 8  # saniye; mobil IP yalnızca bu pencerede kullanılır (§8)
BASARI_ESIGI = 0.95  # C10; altında kalırsa burst_hata uyarısı düşer
DENEME = 2  # sağlayıcı düşerse toplam kaç kez denenir


def _sayaclar() -> dict:
    """Sonuç sayacı iskeletini üretir."""
    return {"ok": 0, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0}


def _tek_hit(
    sorgu: str,
    hedef_url: str,
    serp_url: str,
    proxy_adres: str | None,
    profil: str,
    uule: str | None,
) -> dict:
    """Bir hit'i uçtan uca dener.

    Returns:
        sira dışındaki alanları taşıyan kayıt sözlüğü.
    """
    kayit = {"profil": profil, "izlenim": None, "tik": None, "pogo": None,
             "result": "error"}

    with requests.Session(impersonate=profil) as oturum:
        izlenim = serp.serp_getir_html(sorgu, uule=uule, proxy=proxy_adres,
                                       onceki_profil=profil, oturum=oturum)
        kayit["izlenim"] = izlenim["result"]
        if izlenim["result"] == "captcha":
            kayit["result"] = "captcha"
            return kayit

        tik = click.tikla(hedef_url, referer=serp_url, proxy=proxy_adres,
                          onceki_profil=profil, oturum=oturum)
        kayit["tik"] = tik["result"]
        if tik["result"] != "ok":
            kayit["result"] = tik["result"]
            return kayit

        pog = click.pogo(serp_url, sorgu, proxy=proxy_adres,
                         onceki_profil=profil, oturum=oturum)
        kayit["pogo"] = pog["result"]

    kayit["result"] = "ok"
    return kayit


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
             "durduruldu": False, "hits": [], **_sayaclar()}

    if hedef_url:
        # Adres dışarıdan geldiyse API'ye hiç gidilmez; burst daha hızlı başlar.
        serp_url = f"https://www.google.com/search?q={quote(sorgu)}"
    else:
        # Hedef adres bir kez çözülür: 100 hit için 1000 API isteği gitmesin.
        cozum = serp.serp_getir(sorgu, hedef_domain=hedef_domain, uule=uule)
        if cozum["result"] == "anahtar_yok":
            sonuc["result"] = "anahtar_yok"
            return sonuc
        if cozum["result"] != "ok" or not cozum["position"]:
            sonuc["result"] = "hedef_yok"
            sonuc["not_found"] = adet
            # Hedef ilk 100'de yok: panelde görülsün, sessizce geçmesin.
            saglik.uyari("hedef_yok", None, f"'{sorgu}' ilk 100'de bulunamadı")
            return sonuc
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
    for sira in range(1, adet + 1):
        # Durdurma her hit öncesi sorulur: uçan istek kesilmez, yenisi başlamaz.
        if devam is not None and not devam():
            durduruldu = True
            break

        # Mobil IP pahalı ve çabuk tükeniyor; yalnızca ilk saniyelerde
        # kullanılır, sonra residential'a düşülür (§8).
        mobil_acik = (time.perf_counter() - basladi) < MOBIL_PENCERE_SN

        kayit: dict = {}
        failover_oldu = False
        saglayici_id: int | None = None
        for deneme in range(1, DENEME + 1):
            if proxy_secici:
                proxy_adres = proxy_secici()
            else:
                secim = havuz.sec(geo_slug, mobil_acik)
                proxy_adres = secim[1] if secim else None
                saglayici_id = secim[0] if secim else None

            profil = fingerprint.profil_sec(haric=onceki_profil)
            onceki_profil = profil
            kayit = _tek_hit(sorgu, hedef_url, serp_url, proxy_adres, profil, uule)

            if kayit["result"] == "ok" or kayit["result"] == "captcha":
                break
            # Sağlayıcı kaynaklı düşüşte yeni sağlayıcıyla bir kez daha
            # denenir; aynı sağlayıcıda ısrar etmek zaman kaybıdır (C6).
            if deneme < DENEME:
                failover_oldu = True
                # Burst başına tek uyarı yeter; her hit'te tekrar yazılmasın.
                if not failover_uyarildi:
                    saglik.uyari("failover", saglayici_id, f"'{sorgu}' sağlayıcı değişimi")
                    failover_uyarildi = True

        # Bayrak deneme döngüsünde kaybolmasın diye burada işaretlenir.
        if failover_oldu:
            kayit["failover"] = True

        # Sağlayıcı sağlığı yalnızca gerçek bir sağlayıcı kullanıldıysa işlenir.
        if saglayici_id:
            saglik.kaydet(saglayici_id, geo_kodu, kayit["result"])
            saglik.karantina_kontrol(saglayici_id)

        kayit["sira"] = sira
        sonuc["hits"].append(kayit)
        sonuc[kayit["result"]] = sonuc.get(kayit["result"], 0) + 1

        # Hit arası bekleme; son hit'ten sonra beklemek gereksiz.
        if sira < adet:
            time.sleep(random.uniform(HIT_ARASI_MIN, HIT_ARASI_MAX))

    sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
    sonuc["durduruldu"] = durduruldu

    # Kapanış değerlendirmesi: oran eşiğin altındaysa uyarı düşülür.
    if sonuc["ok"] / adet < BASARI_ESIGI:
        saglik.uyari(
            "burst_hata", None,
            f"'{sorgu}' tamamlanma %{round(sonuc['ok'] * 100 / adet)} "
            f"(ok={sonuc['ok']} captcha={sonuc['captcha']} hata={sonuc['error']})",
        )
    if sonuc["captcha"]:
        saglik.uyari("captcha", None, f"'{sorgu}' captcha={sonuc['captcha']}")
    return sonuc