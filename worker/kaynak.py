"""Sayfa alt kaynaklarini ceker: CSS, JS, gorsel.

Tek HTML istegi sunucuda tek satir birakir; gercek sayfa acilisinda tarayici
ayni origin'den onlarca alt kaynak ister. Bunlar cekilmeden hit, "sayfa
yuklenmesi" degil "tek istek" gibi durur ve ucuncu taraf etiketleri hic
ateslenmez.

Yalnizca sayfanin kendi origin'ine gidilir; disaridan gelen CDN adresleri
atlanir (onlar ayri bir oturum ve cerez isterdi). Adet sinirlidir: amac
gercekci bir yukleme izlenimi, sayfayi bastan sona indirmek degil.

Kullanim: worker/click.py.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

AZAMI_KAYNAK = 12
ZAMAN_ASIMI = 10  # saniye; alt kaynak hit'i bekletmemeli

ETIKET = re.compile(r"<(link|script|img)\b[^>]*>", re.I)
ADRES = re.compile(r"(?:href|src)=[\"']([^\"']+)[\"']", re.I)
# Etikete gore istek turu; `Sec-Fetch-Dest` bu degeri bekler.
TUR = {"link": "style", "script": "script", "img": "image"}


def adresler(html: str, taban: str) -> list[tuple[str, str]]:
    """Gövdeden ayni origin'li alt kaynak adreslerini cikarir.

    Args:
        html: Sayfa govdesi.
        taban: Sayfanin tam adresi; goreli adresler buna gore cozulur.

    Returns:
        (istek turu, tam adres) demetleri; benzersiz ve sirayla.
    """
    kok = urlparse(taban).netloc.lower()
    gorulen: set[str] = set()
    sonuc: list[tuple[str, str]] = []
    for etiket in ETIKET.finditer(html or ""):
        tur = TUR.get(etiket.group(1).lower())
        if not tur:
            continue
        eslesme = ADRES.search(etiket.group(0))
        if not eslesme:
            continue
        ham = eslesme.group(1).strip()
        if not ham or ham.startswith(("data:", "javascript:", "#")):
            continue
        tam = urljoin(taban, ham)
        if urlparse(tam).netloc.lower() != kok:
            continue
        if tam in gorulen:
            continue
        gorulen.add(tam)
        sonuc.append((tur, tam))
        if len(sonuc) >= AZAMI_KAYNAK:
            break
    return sonuc


def basliklar(tur: str) -> dict:
    """Alt kaynak istegi icin tarayici basliklarini kurar.

    Args:
        tur: style, script ya da image.

    Returns:
        Baslik sozlugu.
    """
    return {
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Sec-Fetch-Dest": tur,
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }


def cek(oturum, kayitlar: list[tuple[str, str]], proxy: str | None = None) -> int:
    """Alt kaynaklari sirayla ceker; hatalar hit'i durdurmaz.

    Args:
        oturum: Acik curl_cffi oturumu.
        kayitlar: (tur, adres) demetleri.
        proxy: Hit ile ayni proxy.

    Returns:
        Basariyla cekilen kaynak sayisi.
    """
    cekilen = 0
    for tur, adres in kayitlar:
        try:
            yanit = oturum.get(
                adres, headers=basliklar(tur), timeout=ZAMAN_ASIMI,
                proxies={"https": proxy, "http": proxy} if proxy else None,
                allow_redirects=True,
            )
        except Exception:  # noqa: BLE001
            continue
        if yanit.status_code < 400:
            cekilen += 1
    return cekilen