"""Hedef URL'ye tıklama, dwell ve pogo.

Burst hattının ikinci ve üçüncü adımı. Çağıran taraf bir `Session` verirse
tıklama ve pogo aynı oturumdan geçer; böylece SERP izleniminde doğan
cookie'ler tıklamaya taşınır ve istemci aynı kişi gibi görünür. Oturum
verilmezse kendi oturumunu açar ve kapatır.

Tıklama, SERP isteğini atan proxy üzerinden ve `Referer` SERP adresi olacak
şekilde yapılır; Google böylece tıklamayı bir arama sonucundan gelmiş sayar.
Dwell boyunca bağlantı açık tutulmaz, yalnızca beklenir; pogo ise SERP'e
geri dönüştür.

Süreler sözleşme §9'dan gelir: dwell 5-12 saniye, pogo 3-6 saniye sonra.

Kullanım: worker/burst.py, tools/click_dene.py.
"""

from __future__ import annotations

import random
import time
from urllib.parse import urlparse

from curl_cffi import requests

from worker import fingerprint, ga_beacon

ZAMAN_ASIMI = 25  # saniye; hedef site yavaşsa tıklamayı bırak
DWELL_MIN = 5  # saniye; tık sayılsın yeter, hız öncelikli (§9)
DWELL_MAX = 12  # saniye; üstü burst'ü gereksiz uzatır
POGO_MIN = 3  # saniye; hemen dönmek bot gibi görünür
POGO_MAX = 6  # saniye; üstü pogo penceresini kaçırır

# Tıklama sırasında gönderilen, tarayıcının gezinti isteğine benzeyen başlıklar.
# Accept burada da yazilmaz: profilin kendi basligi ve sirasi korunur (C11).
TIKLAMA_BASLIKLARI = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _temel_sonuc() -> dict:
    """Ortak sonuç iskeletini üretir."""
    return {
        "result": "error",
        "url": None,
        "http_status": None,
        "elapsed_ms": 0,
        "bytes": 0,
        "dwell_ms": 0,
        "pogo": False,
        "ga": None,
        "profil": None,
        "mesaj": "",
    }


def _origin(adres: str) -> str:
    """Adresi origin'e indirger.

    Google sonuc sayfasinda `referrer-policy: origin-when-cross-origin`
    gonderiyor: baska siteye gecerken tarayici yalniz origin'i yollar, arama
    kelimesi Referer'da hic gorunmez. Tam adres gondermek kendi basina bot izi.

    Args:
        adres: Tam adres.

    Returns:
        Sema ve host; cozulemezse adres oldugu gibi.
    """
    if not adres:
        return ""
    parca = urlparse(adres)
    if not parca.scheme or not parca.netloc:
        return adres
    return f"{parca.scheme}://{parca.netloc}/"


def _proxy_sozlugu(proxy: str | None) -> dict | None:
    """Proxy metnini curl_cffi biçimine çevirir."""
    if not proxy:
        return None
    return {"https": proxy, "http": proxy}


def tikla(
    hedef_url: str,
    referer: str | None = None,
    proxy: str | None = None,
    onceki_profil: str | None = None,
    dwell: bool = True,
    oturum: requests.Session | None = None,
    profil_id: int | None = None,
) -> dict:
    """Hedef URL'ye tıklar ve dwell uygular.

    Args:
        hedef_url: Açılacak adres.
        referer: SERP adresi. Google tıklamayı bu başlıkla eşler.
        proxy: http://kullanici:sifre@host:port biçiminde proxy.
        onceki_profil: Bir önceki istekte kullanılan profil.
        dwell: False ise bekleme yapılmaz (hızlı duman testi).
        oturum: Kullanılacak açık oturum. None ise yenisi açılır.
        profil_id: Çerez profil kimliği; GA istemci kimliği bundan türetilir.

    Returns:
        result, url, http_status, elapsed_ms, bytes, dwell_ms, profil ve
        mesaj alanlarını taşıyan sözlük. result: ok, timeout, error.
    """
    sonuc = _temel_sonuc()
    profil = onceki_profil or fingerprint.profil_sec()
    sonuc["profil"] = profil
    sonuc["url"] = hedef_url

    basliklar = dict(TIKLAMA_BASLIKLARI)
    if referer:
        # Gercek trafikte Referer origin'den oteye gitmez.
        basliklar["Referer"] = _origin(referer)

    kendi = oturum is None
    oturum = oturum or requests.Session(impersonate=profil)

    basladi = time.perf_counter()
    try:
        yanit = oturum.get(
            hedef_url,
            headers=basliklar,
            proxies=_proxy_sozlugu(proxy),
            timeout=ZAMAN_ASIMI,
            allow_redirects=True,
        )
        sonuc["http_status"] = yanit.status_code
        sonuc["bytes"] = len(yanit.content)

        # Dwell yalnızca sayfa açıldıysa uygulanır; 4xx/5xx'te beklemek
        # gereksiz, Google'a "girip çıktı" sinyali vermenin anlamı yok.
        if dwell and yanit.status_code < 400:
            sure = random.uniform(DWELL_MIN, DWELL_MAX)
            time.sleep(sure)
            sonuc["dwell_ms"] = int(sure * 1000)
            # Google Analytics ancak burada gorunur: JS calismadigi icin sitenin
            # kendi etiketi ateslenmiyor, page_view dogrudan gonderilir.
            sonuc["ga"] = ga_beacon.gonder(
                urlparse(hedef_url).netloc, hedef_url, referer or "",
                sonuc["dwell_ms"], profil_id, proxy,
            )["result"]
    except Exception as hata:  # noqa: BLE001
        sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
        sonuc["result"] = "timeout" if "timed out" in str(hata).lower() else "error"
        sonuc["mesaj"] = str(hata)[:200]
        return sonuc
    finally:
        if kendi:
            oturum.close()

    sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
    sonuc["result"] = "ok" if sonuc["http_status"] and sonuc["http_status"] < 400 else "error"
    return sonuc


def pogo(
    serp_url: str,
    sorgu: str,
    proxy: str | None = None,
    onceki_profil: str | None = None,
    oturum: requests.Session | None = None,
    hedef_url: str | None = None,
) -> dict:
    """SERP'e geri döner.

    Args:
        serp_url: Dönülecek SERP adresi.
        sorgu: Arama kelimesi; adres boşsa adres kurmak için kullanılır.
        proxy: Tıklamayla aynı proxy olmalı, yoksa IP değişir.
        onceki_profil: Tıklamada kullanılan profil.
        oturum: Tıklamayla aynı oturum. None ise yenisi açılır.
        hedef_url: Terk edilen sayfa; Referer onun origin'i olur.

    Returns:
        result, http_status, elapsed_ms, bekleme_ms ve mesaj alanları.
    """
    sonuc = {"result": "error", "http_status": None, "elapsed_ms": 0,
             "bekleme_ms": 0, "mesaj": ""}

    # Pogo öncesi bekleme: hemen dönmek insan davranışına uymaz.
    bekleme = random.uniform(POGO_MIN, POGO_MAX)
    time.sleep(bekleme)
    sonuc["bekleme_ms"] = int(bekleme * 1000)

    adres = serp_url or f"https://www.google.com/search?q={sorgu}"
    basliklar = {
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        # Geri donuste Referer, terk edilen sayfanin origin'idir.
        "Referer": _origin(hedef_url or "") or _origin(adres),
        "Sec-Fetch-Mode": "navigate",
    }

    kendi = oturum is None
    oturum = oturum or requests.Session(impersonate=onceki_profil or fingerprint.profil_sec())

    basladi = time.perf_counter()
    try:
        yanit = oturum.get(
            adres, headers=basliklar, proxies=_proxy_sozlugu(proxy),
            timeout=ZAMAN_ASIMI,
        )
        sonuc["http_status"] = yanit.status_code
    except Exception as hata:  # noqa: BLE001
        sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
        sonuc["result"] = "timeout" if "timed out" in str(hata).lower() else "error"
        sonuc["mesaj"] = str(hata)[:200]
        return sonuc
    finally:
        if kendi:
            oturum.close()

    sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
    sonuc["result"] = "ok" if sonuc["http_status"] < 400 else "error"
    return sonuc