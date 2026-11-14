"""Tarayici parmak izi profilleri.

curl_cffi'nin impersonate degerlerini tasir. Cerez varsa parmak izi cerezin
tarayici ailesine sabitlenir (cookie_profil.parmak_izzi) ve oturumun uc
adiminda da ayni profil kullanilir; cerez yoksa rastgele secilir.

Surumler guncel tutulur (curl_cffi 0.17.0): eski profiller TLS'te ayirt
edilebilir. Safari, Firefox ve Edge yalnizca cerezsiz durumda havuza girer;
Edge icin curl_cffi'de guncel deger yok, o yuzden cerezsiz havuzda tutulur.
"""

from __future__ import annotations

import random

CHROME: tuple[str, ...] = (
    "chrome152",
    "chrome151",
    "chrome150",
    "chrome146",
    "chrome145",
    "chrome142",
)
FIREFOX: tuple[str, ...] = ("firefox155", "firefox154", "firefox153")
SAFARI: tuple[str, ...] = ("safari270", "safari260")
EDGE: tuple[str, ...] = ("edge101",)
# Mobil pencerede tek android profil; masaustu TLS'i mobil trafikte ayirt edilir.
ANDROID: tuple[str, ...] = ("chrome131_android",)

PROFILLER: tuple[str, ...] = CHROME + FIREFOX + SAFARI + EDGE + ANDROID

BEKLENEN_UA: dict[str, str] = {
    "chrome152": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "chrome151": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "chrome150": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "chrome146": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "chrome145": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "chrome142": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "firefox155": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) "
                  "Gecko/20100101 Firefox/155.0",
    "firefox154": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:154.0) "
                  "Gecko/20100101 Firefox/154.0",
    "firefox153": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) "
                  "Gecko/20100101 Firefox/153.0",
    "safari270": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0 Safari/605.1.15",
    "safari260": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15",
    "edge101": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36 "
               "Edg/101.0.1210.47",
    "chrome131_android": "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 "
                         "Mobile Safari/537.36",
}


def profil_sec(
    haric: str | None = None, aile: str | None = None, mobil: bool = False
) -> str:
    """Profil secer.

    Args:
        haric: Bir onceki istekte kullanilan profil; tekrar onlenir.
        aile: Cerezin tarayici ailesi (chrome, firefox, safari, bilinmiyor).
            None ise cerez yoktur ve genis havuzdan secilir.
        mobil: Mobil pencerede android profil secilir.

    Returns:
        Profil adi. Havuz bosalmaz.
    """
    if mobil:
        havuz = list(ANDROID)
    elif aile is None:
        havuz = list(CHROME) + list(FIREFOX) + list(SAFARI) + list(EDGE)
    elif aile == "safari":
        havuz = list(SAFARI)
    elif aile == "firefox":
        havuz = list(FIREFOX)
    else:
        havuz = list(CHROME)
    if len(havuz) > 1:
        havuz = [p for p in havuz if p != haric] or havuz
    return random.choice(havuz)


def ua(profil: str) -> str:
    """Profilin beklenen User-Agent degerini dondurur; taninmayan icin bos."""
    return BEKLENEN_UA.get(profil, "")


def dogrula(profil: str) -> None:
    """Profil adi tanimli mi diye bakar, degilse ValueError yukseltir."""
    if profil not in PROFILLER:
        raise ValueError(f"tanimsiz profil: {profil} - gecerli: {', '.join(PROFILLER)}")