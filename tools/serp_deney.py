"""SERP API sayfalama denemesi.

/search tek sayfada 10 sonuç veriyor. İlk 100 sıralamayı görebilmek için
hangi parametrenin sayfa açtığını bulmak gerekiyor. Her varyant denenir ve
dönen organik sayısı yazılır.

Kullanım:
    python tools/serp_deney.py --sorgu "veteriner"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from curl_cffi import requests  # noqa: E402

from worker import ayar  # noqa: E402

API = "https://data.decodo.com/v1/search"


def dene(etiket: str, ek: dict) -> None:
    """Tek varyantı dener ve sonucu yazar."""
    govde = {"query": secim.sorgu, "locale": "tr-TR", "geo": "tr", **ek}
    try:
        yanit = requests.post(
            API, json=govde,
            headers={"authorization": f"Bearer {ayar.serp_anahtari()}"},
            impersonate="chrome", timeout=30,
        )
    except Exception as hata:  # noqa: BLE001
        print(f"{etiket:10} HATA {hata}")
        return
    if yanit.status_code != 200:
        print(f"{etiket:10} http={yanit.status_code} {yanit.text[:120]}")
        return
    veri = yanit.json()
    organik = veri.get("organic") or veri.get("results", {}).get("organic") or []
    ilk = organik[0].get("link") if organik else "-"
    print(f"{etiket:10} adet={len(organik):3} ilk={ilk}")


def main() -> int:
    """Varyantları dener."""
    global secim
    ayar_p = argparse.ArgumentParser(description="Sayfalama denemesi")
    ayar_p.add_argument("--sorgu", required=True)
    secim = ayar_p.parse_args()

    dene("duz", {})
    dene("page2", {"page": 2})
    dene("start10", {"start": 10})
    dene("num100", {"num": 100})
    dene("limit100", {"limit": 100})
    dene("pages2", {"pages": 2})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())