"""Havuzdan proxy seçimini ve çıkış IP'sini dener.

Sağlayıcı tablosundan seçim yapar, maskeli dizeyi yazar ve kontrol
adresine giderek dönen IP'yi gösterir. Aynı oturumun aynı IP'yi vermesi
beklenir; farklı oturumlar farklı IP vermelidir.

Kullanım:
    python tools/proxy_dene.py
    python tools/proxy_dene.py --geo istanbul --adet 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from curl_cffi import requests  # noqa: E402

from worker import havuz, proxy  # noqa: E402

KONTROL_URL = "https://ip.decodo.com/json?provider=IPinfo"


def dene(adres: str) -> bool:
    """Proxy'yi kontrol adresine karşı dener."""
    try:
        yanit = requests.get(
            KONTROL_URL, proxies={"https": adres, "http": adres},
            impersonate="chrome", timeout=20,
        )
    except Exception as hata:  # noqa: BLE001
        print(f"   HATA {str(hata)[:110]}")
        return False
    if yanit.status_code != 200:
        print(f"   http={yanit.status_code}")
        return False
    print(f"   OK {yanit.text[:140]}")
    return True


def main() -> int:
    """Seçimi ve çıkışı dener. Kimse seçilemezse 1 döner."""
    ayar = argparse.ArgumentParser(description="Proxy denemesi")
    ayar.add_argument("--geo", help="il slug'ı")
    ayar.add_argument("--adet", type=int, default=2)
    secim = ayar.parse_args()

    print(f"oranlar: {havuz.oranlari_oku()}")
    basarili = 0
    for sira in range(1, secim.adet + 1):
        kayit = havuz.sec(secim.geo, mobil_acik=True)
        if not kayit:
            print(f"{sira}. sağlayıcı seçilemedi (kimlik bilgisi yok olabilir).")
            continue
        saglayici_id, adres = kayit
        print(f"{sira}. sağlayıcı {saglayici_id} · {proxy.maskele(adres)}")
        if dene(adres):
            basarili += 1
    print(f"başarılı: {basarili}/{secim.adet}")
    return 0 if basarili else 1


if __name__ == "__main__":
    raise SystemExit(main())