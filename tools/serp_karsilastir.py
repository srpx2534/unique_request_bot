"""Tarayici ve SERP API'sinin ilk 20 kumesini karsilastirir (80).

Olcum dogrulugunun kapanis olcusu budur: ayni kelime, ayni dakika, ayni TR
residential IP sinifi. Tarayici yolu gercek kullaniciyi temsil eder; API
sonucu ondan uzaksa olcum guvenilir degildir.

Kullanim: python tools/serp_karsilastir.py "erzurum escort" [--adet 20]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker import serp, tarayici  # noqa: E402
from worker.serp_ortak import kok  # noqa: E402

ADET = 20
ESIK = 0.90


def kume(organik: list[dict], adet: int) -> list[str]:
    """Organik kayitlardan benzersiz kok listesi cikarir."""
    gorulen: list[str] = []
    for kayit in organik:
        k = kok(str(kayit.get("link") or ""))
        if k and k not in gorulen:
            gorulen.append(k)
        if len(gorulen) >= adet:
            break
    return gorulen


def oran(a: list[str], b: list[str]) -> float:
    """Iki kumenin ortusme oranini verir; payda kisa kumedir."""
    if not a or not b:
        return 0.0
    return len(set(a) & set(b)) / min(len(a), len(b))


def main() -> int:
    """Iki yolu kosar, ortusmeyi yazar."""
    ayar = argparse.ArgumentParser(description="SERP yolu karsilastirmasi")
    ayar.add_argument("kelime")
    ayar.add_argument("--adet", type=int, default=ADET)
    secim = ayar.parse_args()

    if not tarayici.kullanilabilir():
        print("tarayici yok: playwright kurulu degil")
        return 1

    tarayici_cevap = tarayici.serp_oku(secim.kelime)
    if tarayici_cevap["result"] not in ("ok", "not_found"):
        print(f"tarayici dustu: {tarayici_cevap['result']} · {tarayici_cevap['mesaj']}")
        return 1
    api_cevap = serp.serp_getir(secim.kelime)
    if api_cevap["result"] not in ("ok", "not_found"):
        print(f"api dustu: {api_cevap['result']} · {api_cevap.get('mesaj', '')}")
        return 1

    tarayici_kume = kume(tarayici_cevap["organik"], secim.adet)
    api_kume = kume(api_cevap["organik"], secim.adet)

    print(f"kelime: {secim.kelime}")
    print(f"tarayici: {len(tarayici_kume)} sonuc · api: {len(api_kume)} sonuc")
    for i, ad in enumerate(tarayici_kume, 1):
        print(f"  T{i:02d} {ad}")
    print("---")
    for i, ad in enumerate(api_kume, 1):
        print(f"  A{i:02d} {ad}")

    yuzde = oran(tarayici_kume, api_kume)
    print(f"ortusme: %{round(yuzde * 100, 1)} (esik %{round(ESIK * 100)})")
    return 0 if yuzde >= ESIK else 2


if __name__ == "__main__":
    raise SystemExit(main())