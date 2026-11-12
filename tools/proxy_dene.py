"""Proxy üretimini ve çıkış IP'sini dener.

İki kip vardır:
  - varsayılan: .env'deki Decodo bilgileriyle proxy üretir
  - --serbest : herkese açık ücretsiz listeden çalışan proxy arar

Serbest kip yalnızca kod yolunu sınamak içindir; ücretsiz proxy'ler
datacenter olduğu için CAPTCHA oranı yüksek çıkar, kalite ölçütü değildir.

Kullanım:
    python tools/proxy_dene.py
    python tools/proxy_dene.py --serbest --adet 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from curl_cffi import requests  # noqa: E402

from worker import proxy  # noqa: E402

KONTROL_URL = "https://ip.decodo.com/json?provider=IPinfo"
SERBEST_LISTE = ("https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main"
                 "/proxies/all/data.txt")
SERBEST_HAVUZ = 40  # denenecek en fazla aday
SERBEST_ASGARI = 3  # bulununca durulacak çalışan sayısı


def _duzelt(adres: str) -> str:
    """Proxy önekini http:// yapar.

    Liste https:// önekli geliyor; curl_cffi o zaman proxy'yi TLS olarak
    kuruyor ve sertifika adı eşleşmiyor. Düz CONNECT için http:// gerekir.
    """
    return "http://" + adres.split("://", 1)[1] if "://" in adres else "http://" + adres


def dene(adres: str, etiket: str) -> bool:
    """Proxy'yi kontrol adresine karşı dener.

    İlk deneme sertifika doğrulamalı, düşerse doğrulamasız tekrar denenir.
    Ücretsiz proxy'ler sık sık kendi sertifikasını araya sokuyor.
    """
    adres = _duzelt(adres)
    for dogrula in (True, False):
        try:
            yanit = requests.get(
                KONTROL_URL, proxies={"https": adres, "http": adres},
                impersonate="chrome", timeout=12, verify=dogrula,
            )
        except Exception as hata:  # noqa: BLE001
            if dogrula:
                continue  # sertifika hatası olabilir, doğrulamasız dene
            print(f"{etiket} HATA {str(hata)[:90]}")
            return False
        if yanit.status_code != 200:
            print(f"{etiket} http={yanit.status_code}")
            return False
        print(f"{etiket} OK {yanit.text[:120]}")
        return True
    return False


def serbest_ara(adet: int) -> int:
    """Ücretsiz listeden çalışan proxy arar. Bulunan sayısını döndürür."""
    try:
        liste = requests.get(SERBEST_LISTE, timeout=30).text
    except Exception as hata:  # noqa: BLE001
        print(f"HATA liste alınamadı: {hata}")
        return 0

    adaylar = [s.strip() for s in liste.splitlines() if s.strip().startswith("http")]
    print(f"listede {len(adaylar)} aday, ilk {SERBEST_HAVUZ} tanesi denenecek.")

    bulunan = 0
    for sira, adres in enumerate(adaylar[:SERBEST_HAVUZ], start=1):
        if dene(adres, f"{sira:2}."):
            bulunan += 1
            if bulunan >= adet:
                break
    return bulunan


def main() -> int:
    """Seçilen kipe göre dener."""
    ayar = argparse.ArgumentParser(description="Proxy denemesi")
    ayar.add_argument("--geo", help="il slug'ı")
    ayar.add_argument("--adet", type=int, default=2)
    ayar.add_argument("--serbest", action="store_true", help="ücretsiz liste kullan")
    secim = ayar.parse_args()

    if secim.serbest:
        bulunan = serbest_ara(secim.adet)
        print(f"çalışan: {bulunan}")
        return 0 if bulunan else 1

    if not proxy.var_mi():
        print("HATA: .env içinde DECODO_USER / DECODO_PASS boş.")
        return 1

    for sira in range(1, secim.adet + 1):
        adres = proxy.proxy_uret(secim.geo)
        print(f"{sira}. proxy: {proxy.maskele(adres)}")
        dene(adres, "   ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())