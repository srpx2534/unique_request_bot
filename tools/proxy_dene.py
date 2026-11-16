"""Havuzdan proxy secimini ve cikis IP'sini dener.

Saglayici tablosundan secim yapar, maskeli dizeyi yazar ve kontrol
adresine giderek donen IP'yi gosterir. Ayni oturumun ayni IP'yi vermesi
beklenir; farkli oturumlar farkli IP vermelidir.

Proxy reddi kisaltilmadan yazilir: 407 kimlik, 466 kota, 403 bicim
reddidir ve ucunun cozumu farklidir. Kota gorulurse saglayici havuzda
tuketilir (C81), boylece sonraki secim onu atlar.

Kullanim:
    python tools/proxy_dene.py
    python tools/proxy_dene.py --geo istanbul --adet 3
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from curl_cffi import requests  # noqa: E402

from worker import havuz, proxy, saglik  # noqa: E402

KONTROL_URL = "https://ip.decodo.com/json?provider=IPinfo"
MESAJ_SINIRI = 300  # karakter; kodu ve sebebi kesmeden gostermek icin
DESEN_KOD = re.compile(r"response (\d{3})")


def red_kodu(mesaj: str) -> int | None:
    """Hata metnindeki proxy yanit kodunu cikarir.

    Args:
        mesaj: Istek hatasinin tam metni.

    Returns:
        Uc haneli kod ya da metinde yoksa None.
    """
    eslesme = DESEN_KOD.search(mesaj)
    return int(eslesme.group(1)) if eslesme else None


def dene(adres: str) -> bool:
    """Proxy'yi kontrol adresine karsi dener.

    Args:
        adres: Kimlikli proxy dizesi.

    Returns:
        Cikis alindiysa True.
    """
    try:
        yanit = requests.get(
            KONTROL_URL, proxies={"https": adres, "http": adres},
            impersonate="chrome", timeout=20,
        )
    except Exception as hata:  # noqa: BLE001
        mesaj = str(hata)[:MESAJ_SINIRI]
        kod = red_kodu(mesaj)
        if kod == saglik.KOTA_KODU:
            print(f"   KOTA {kod} · {mesaj}")
        elif kod:
            print(f"   RED {kod} · {mesaj}")
        else:
            print(f"   HATA · {mesaj}")
        return False
    if yanit.status_code != 200:
        print(f"   http={yanit.status_code} · {yanit.text[:MESAJ_SINIRI]}")
        return False
    print(f"   OK {yanit.text[:140]}")
    return True


def main() -> int:
    """Secimi ve cikisi dener. Kimse secilemezse 1 doner."""
    ayar = argparse.ArgumentParser(description="Proxy denemesi")
    ayar.add_argument("--geo", help="il slug")
    ayar.add_argument("--adet", type=int, default=2)
    secim = ayar.parse_args()

    print(f"oranlar: {havuz.oranlari_oku()}")
    basarili = 0
    for sira in range(1, secim.adet + 1):
        kayit = havuz.sec(secim.geo, mobil_acik=True)
        if not kayit:
            print(f"{sira}. saglayici secilemedi (kimlik ya da kota yok olabilir).")
            continue
        saglayici_id, adres = kayit
        print(f"{sira}. saglayici {saglayici_id} · {proxy.maskele(adres)}")
        if dene(adres):
            basarili += 1
    print(f"basarili: {basarili}/{secim.adet}")
    return 0 if basarili else 1


if __name__ == "__main__":
    raise SystemExit(main())
