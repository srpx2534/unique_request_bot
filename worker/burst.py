"""Burst yürütücü: izlenim, tıklama, dwell, pogo.

Bir burst, aynı kelime için art arda atılan hit'lerden oluşur. Her hit'te
sıra şudur: SERP izlenimi (proxy üzerinden, doğrudan Google), hedefe
tıklama, dwell, pogo.

İzlenim neden proxy üzerinden: Google aramayı ve tıklamayı aynı IP'den
görmeli. SERP API'si kendi IP'sini kullanır, bu yüzden yalnızca hedef
adresi çözmek için bir kez çağrılır; sıralama bir burst içinde değişmez.

Her hit tek profil kullanır ve bu profil izlenim, tıklama ve pogoda aynı
kalır; tarayıcı oturumu bütünlüğü böyle korunur.

Kullanım: worker/app.py, tools/burst_dene.py.
"""

from __future__ import annotations

import random
import time
from typing import Callable
from urllib.parse import quote

from curl_cffi import requests

from worker import click, fingerprint, proxy, serp

AZAMI_HIT = 60  # sözleşme §9: basamak boyu en fazla 60
HIT_ARASI_MIN = 0.4  # saniye; art arda istekte insan ritmi
HIT_ARASI_MAX = 1.4  # saniye; jitter için üst sınır


def _sayaclar() -> dict:
    """Sonuç sayacı iskeletini üretir."""
    return {"ok": 0, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0}


def burst_yap(
    sorgu: str,
    hedef_domain: str,
    adet: int,
    proxy_secici: Callable[[], str | None] | None = None,
    uule: str | None = None,
    hedef_url: str | None = None,
    devam: Callable[[], bool] | None = None,
) -> dict:
    """Burst'ü yürütür.

    Args:
        sorgu: Aranacak kelime.
        hedef_domain: Tıklanacak alan adı.
        adet: Atılacak hit sayısı. AZAMI_HIT ile sınırlanır.
        proxy_secici: Her hit için proxy döndüren çağrılabilir. None ise
            doğrudan bağlantı kullanılır.
        uule: Konum parametresi; izlenim adresine eklenir.
        hedef_url: Hazır hedef adres. Verilirse API ile çözüm atlanır.
        devam: Her hit öncesi sorulan 'sürsün mü' geri çağrısı. False
            dönerse kalan hit atılmaz (C21).

    Returns:
        result, sayaçlar, elapsed_ms, hedef_url ve hits alanlarını taşıyan
        sözlük. result: ok, hedef_yok, anahtar_yok.
    """
    adet = max(1, min(adet, AZAMI_HIT))
    # Proxy seçici verilmediyse varsayılan üretici kullanılır; kimlik yoksa
    # üretici None döner ve hat doğrudan bağlantıya düşer.
    proxy_secici = proxy_secici or proxy.varsayilan_secici()
    basladi = time.perf_counter()

    sonuc = {"result": "ok", "hedef_url": None, "elapsed_ms": 0, "durduruldu": False,
             "hits": [], **_sayaclar()}

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
            return sonuc
        hedef_url = next(
            k["link"] for k in cozum["organik"] if k["position"] == cozum["position"]
        )
        serp_url = cozum["url"] or f"https://www.google.com/search?q={quote(sorgu)}"

    sonuc["hedef_url"] = hedef_url

    onceki_profil: str | None = None
    durduruldu = False
    for sira in range(1, adet + 1):
        # Durdurma her hit öncesi sorulur: uçan istek kesilmez, yenisi başlamaz.
        if devam is not None and not devam():
            durduruldu = True
            break
        proxy_adres = proxy_secici() if proxy_secici else None
        profil = fingerprint.profil_sec(haric=onceki_profil)
        onceki_profil = profil

        kayit = {"sira": sira, "profil": profil, "izlenim": None,
                 "tik": None, "pogo": None, "result": "error"}

        # Hit başına tek oturum: izlenimde doğan cookie tıklamaya taşınır ve
        # üç adım aynı istemci gibi görünür. Oturum hit sonunda kapanır.
        with requests.Session(impersonate=profil) as oturum:
            # 1. İzlenim: Google aramayı bu IP'den görsün.
            izlenim = serp.serp_getir_html(sorgu, uule=uule, proxy=proxy_adres,
                                           onceki_profil=profil, oturum=oturum)
            kayit["izlenim"] = izlenim["result"]
            if izlenim["result"] == "captcha":
                kayit["result"] = "captcha"
                sonuc["captcha"] += 1
                sonuc["hits"].append(kayit)
                continue

            # 2. Tıklama: aynı oturum, aynı proxy, referer SERP.
            tik = click.tikla(hedef_url, referer=serp_url, proxy=proxy_adres,
                              onceki_profil=profil, oturum=oturum)
            kayit["tik"] = tik["result"]
            if tik["result"] != "ok":
                kayit["result"] = tik["result"]
                sonuc[tik["result"]] += 1
                sonuc["hits"].append(kayit)
                continue

            # 3. Pogo: tıklama başarılıysa SERP'e dön.
            pog = click.pogo(serp_url, sorgu, proxy=proxy_adres,
                             onceki_profil=profil, oturum=oturum)
            kayit["pogo"] = pog["result"]

        kayit["result"] = "ok"
        sonuc["ok"] += 1
        sonuc["hits"].append(kayit)

        # Hit arası bekleme; son hit'ten sonra beklemek gereksiz.
        if sira < adet:
            time.sleep(random.uniform(HIT_ARASI_MIN, HIT_ARASI_MAX))

    sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
    sonuc["durduruldu"] = durduruldu
    return sonuc