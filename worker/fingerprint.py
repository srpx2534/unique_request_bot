"""Tarayici parmak izi profilleri.

curl_cffi'nin impersonate degerlerini tasir. Cerez varsa parmak izi cerezin
tarayici ailesine sabitlenir (cookie_profil.parmak_izzi) ve oturumun uc
adiminda da ayni profil kullanilir; cerez yoksa rastgele secilir.

Guncel Chrome surumleri tutulur: eski profiller TLS'te ayirt edilebilir.
Safari ve Edge yalnizca cerezsiz durumda havuza girer.
"""

from __future__ import annotations

import random

CHROME: tuple[str, ...] = ("chrome124", "chrome123", "chrome120", "chrome119", "chrome116")
SAFARI: tuple[str, ...] = ("safari17_0",)
EDGE: tuple[str, ...] = ("edge101",)
# Mobil pencerede tek android profil; curl_cffi 0.7.4 icindeki tek android deger.
ANDROID: tuple[str, ...] = ("chrome99_android",)

PROFILLER: tuple[str, ...] = CHROME + SAFARI + EDGE + ANDROID

BEKLENEN_UA: dict[str, str] = {
    "chrome124": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "chrome123": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "chrome120": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "chrome119": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "chrome116": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "safari17_0": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                  "Safari/605.1.15",
    "edge101": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36 "
               "Edg/101.0.1210.47",
    "chrome99_android": "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.58 "
                        "Mobile Safari/537.36",
}


def profil_sec(
    haric: str | None = None, aile: str | None = None, mobil: bool = False
) -> str:
    """Profil secer.

    Args:
        haric: Bir onceki istekte kullanilan profil; tekrar onlenir.
        aile: Cerezin tarayici ailesi (chrome, firefox, safari, bilinmiyor).
            None ise cerez yoktur ve genis havuzdan secilir. firefox icin
            curl_cffi 0.7.4'te profil yok, Chrome havuzuna duser.
        mobil: Mobil pencerede android profil secilir.

    Returns:
        Profil adi. Havuz bosalmaz.
    """
    if mobil:
        havuz = list(ANDROID)
    elif aile is None:
        havuz = list(CHROME) + list(SAFARI) + list(EDGE)
    elif aile == "safari":
        havuz = list(SAFARI)
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
