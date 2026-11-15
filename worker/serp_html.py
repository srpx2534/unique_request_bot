"""Yedek yol: Google'a dogrudan HTML istegi.

Bugun kabuk dondugu icin genelde not_found verir, ama istek Google'a gercek
IP'den gider ve izlenim sayilir. Oturum verilirse cerezler cagiran tarafta
korunur ve tiklamaya tasinir.
"""

from __future__ import annotations

import re
import time
from urllib.parse import unquote

from curl_cffi import requests

from worker import fingerprint
from worker.serp_ortak import bos_sonuc, kok

ZAMAN_ASIMI = 25  # saniye
ARAMA_URL = "https://www.google.com/search"
CEREZLER = {
    "SOCS": "CAISNQgQEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMzE5LjA4X3AxGgJlbiACGgYIgLC_rwY",
    "CONSENT": "YES+cb.20240101-00-p0.tr+FX+111",
}
# Accept bilerek yazilmaz: curl_cffi profilin kendi Accept basligini ve
# sirasini uygular, ezmek parmak izini bozar (C11).
BASLIKLAR = {"Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}

ELENEN = ("google.", "gstatic.", "googleusercontent.", "policies.google")
DESEN_YONLENDIRME = re.compile(r"/url\?q=([^&\"']+)")
DESEN_DUZ = re.compile(r"<a[^>]+href=\"(https?://[^\"]+)\"")


def sonuclari_ayikla(html: str) -> list[str]:
    """HTML'den benzersiz kok alan adlarini sirayla cikarir."""
    adresler = [unquote(m) for m in DESEN_YONLENDIRME.findall(html)]
    adresler += DESEN_DUZ.findall(html)
    gorulen: set[str] = set()
    sira: list[str] = []
    for adres in adresler:
        if any(e in adres for e in ELENEN):
            continue
        k = kok(adres)
        if k and k not in gorulen:
            gorulen.add(k)
            sira.append(k)
    return sira


def captcha_mi(son_url: str, html: str) -> bool:
    """Yanitin CAPTCHA duvari olup olmadigini soyler."""
    if "/sorry/" in son_url:
        return True
    kucuk = html[:4000].lower()
    return "recaptcha" in kucuk or "unusual traffic" in kucuk


def serp_getir_html(
    sorgu: str,
    hedef_domain: str | None = None,
    uule: str | None = None,
    proxy: str | None = None,
    onceki_profil: str | None = None,
    oturum: requests.Session | None = None,
) -> dict:
    """Google'a dogrudan HTML istegi yapar.

    Args:
        sorgu: Aranacak kelime.
        hedef_domain: Sirasi aranacak alan adi.
        uule: Konum parametresi.
        proxy: http://kullanici:sifre@host:port biciminde proxy.
        onceki_profil: Kullanilacak profil.
        oturum: Acik oturum. None ise yenisi acilir ve kapatilir.

    Returns:
        Sonuc sozlugu. result: ok, captcha, not_found, timeout, error.
    """
    sonuc = bos_sonuc()
    sonuc["kaynak"] = "html"
    profil = onceki_profil or fingerprint.profil_sec()
    sonuc["profil"] = profil

    parametreler = {"q": sorgu, "num": "100", "hl": "tr", "gl": "tr"}
    if uule:
        parametreler["uule"] = uule

    kendi = oturum is None
    oturum = oturum or requests.Session(impersonate=profil)

    basladi = time.perf_counter()
    try:
        yanit = oturum.get(
            ARAMA_URL, params=parametreler, headers=BASLIKLAR,
            cookies=CEREZLER, timeout=ZAMAN_ASIMI,
            proxies={"https": proxy, "http": proxy} if proxy else None,
        )
    except Exception as hata:  # noqa: BLE001
        sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
        sonuc["result"] = "timeout" if "timed out" in str(hata).lower() else "error"
        sonuc["mesaj"] = str(hata)[:200]
        return sonuc
    finally:
        if kendi:
            oturum.close()

    html = yanit.content.decode("utf-8", "replace")
    sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
    sonuc["http_status"] = yanit.status_code
    sonuc["bytes"] = len(yanit.content)
    sonuc["url"] = str(yanit.url)

    if yanit.status_code != 200:
        sonuc["result"] = "error"
        return sonuc
    if captcha_mi(sonuc["url"], html):
        sonuc["result"] = "captcha"
        return sonuc

    hostlar = sonuclari_ayikla(html)
    if not hostlar:
        sonuc["result"] = "not_found"
        return sonuc
    sonuc["result"] = "ok"
    if hedef_domain and kok(hedef_domain) in hostlar:
        sonuc["position"] = hostlar.index(kok(hedef_domain)) + 1
    return sonuc