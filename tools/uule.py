"""uule üretimi.

uule, Google'a "şu koordinattan aranmış" demenin yoludur. Şehir hedefleyen
proxy bulunamadığında SERP'in doğru ili göstermesi için kullanılır.
Tıklama IP'sini değiştirmez, sadece sonuç sayfasını yerelleştirir.
Format Google tarafından belgelenmemiştir; değerler ampirik doğrulanır.
"""

from __future__ import annotations

import base64
import time

# Şehir yarıçapı metre. 65 km il merkezini ve çevresini kapsar.
YARICAP_M = 65_000

# Google'ın beklediği sabit önek.
ONEK = "w+CAIQICI"


def uret(lat: str, lon: str) -> str:
    """Koordinat için uule dizesi üretir.

    Args:
        lat: Enlem, ondalık metin.
        lon: Boylam, ondalık metin.

    Returns:
        Önekli ve base64 kodlu uule dizesi.
    """
    # Zaman damgası milisaniye cinsinden; Google tazelik kontrolünde kullanır.
    zaman = int(time.time() * 1000)
    govde = (
        f"role:1 producer:12 provenance:6 timestamp:{zaman} "
        f"latlng:{lat},{lon} radius:{YARICAP_M}"
    )
    # URL güvenli base64, dolgu karakterleri atılır.
    kodlu = base64.urlsafe_b64encode(govde.encode("utf-8")).decode().rstrip("=")
    return ONEK + kodlu