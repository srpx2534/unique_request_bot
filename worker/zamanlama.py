"""Gun icindeki saat agirligi.

Gercek trafik her saat ayni degil: aksam saatlerinde taban yuksek, gece
neredeyse yok. Hepsini ayni hizda gondermek, gece 04:00'te tepe trafik
varmis gibi gorunur.

Agirlik 0.2-1.0 arasindadir ve hit adedini olceklendirmek icin kullanilir.

Kullanim: worker/burst.py, src/server/olcum.ts.
"""

from __future__ import annotations

from datetime import datetime

# Saat -> agirlik. 20-23 aksam tepesi, 00-07 gece dibi.
SAAT_AGIRLIK = {
    0: 0.3, 1: 0.25, 2: 0.2, 3: 0.2, 4: 0.2, 5: 0.2, 6: 0.25,
    7: 0.35, 8: 0.45, 9: 0.5, 10: 0.55, 11: 0.55,
    12: 0.5, 13: 0.5, 14: 0.5, 15: 0.55, 16: 0.6, 17: 0.65,
    18: 0.7, 19: 0.8, 20: 0.95, 21: 1.0, 22: 0.95, 23: 0.7,
}


def agirlik(saat: int | None = None) -> float:
    """Verilen saatin agirligini dondurur.

    Args:
        saat: 0-23; verilmezse yerel saat.

    Returns:
        0.2 ile 1.0 arasi agirlik.
    """
    if saat is None:
        saat = datetime.now().hour
    return SAAT_AGIRLIK.get(int(saat) % 24, 0.5)


def uygun_mu(esik: float = 0.45, saat: int | None = None) -> bool:
    """Burst baslatmak icin saat uygun mu.

    Args:
        esik: Bu agirligin altinda burst baslatilmaz.
        saat: 0-23; verilmezse yerel saat.

    Returns:
        Agirlik esigin altinda degilse True.
    """
    return agirlik(saat) >= esik


def olcekle(adet: int, saat: int | None = None) -> int:
    """Hit adedini saatin agirligina gore olcekler.

    Args:
        adet: Istenen hit sayisi.
        saat: 0-23; verilmezse yerel saat.

    Returns:
        En az 1 olacak sekilde olceklenmis adet.
    """
    return max(1, int(round(adet * agirlik(saat))))