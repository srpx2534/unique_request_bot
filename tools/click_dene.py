"""Tıklama, dwell ve pogo adımını elle dener.

SERP API'sinden hedef adresi bulur, tıklar, bekler ve SERP'e döner.
Proxy verilmezse doğrudan bağlantı kurulur.

Kullanım:
    python tools/click_dene.py --sorgu "veteriner" --domain armut.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from worker import click, serp  # noqa: E402


def main() -> int:
    """Akışı uçtan uca dener. Başarısızsa 1 döner."""
    ayar = argparse.ArgumentParser(description="Tıklama denemesi")
    ayar.add_argument("--sorgu", required=True)
    ayar.add_argument("--domain", required=True)
    ayar.add_argument("--proxy")
    ayar.add_argument("--dwellsiz", action="store_true", help="bekleme yapma")
    secim = ayar.parse_args()

    serp_sonuc = serp.serp_getir(secim.sorgu, hedef_domain=secim.domain)
    print(f"serp: result={serp_sonuc['result']} position={serp_sonuc['position']}")
    if serp_sonuc["result"] != "ok" or not serp_sonuc["position"]:
        print("hedef bulunamadı, tıklama atlanıyor.")
        return 1

    hedef = next(
        k["link"] for k in serp_sonuc["organik"]
        if k["position"] == serp_sonuc["position"]
    )
    print(f"hedef: {hedef}")

    tik = click.tikla(
        hedef, referer=serp_sonuc["url"], proxy=secim.proxy,
        onceki_profil=serp_sonuc["profil"], dwell=not secim.dwellsiz,
    )
    print(f"tik: result={tik['result']} http={tik['http_status']} "
          f"ms={tik['elapsed_ms']} bytes={tik['bytes']} dwell={tik['dwell_ms']}")

    if tik["result"] != "ok":
        return 1

    pog = click.pogo(serp_sonuc["url"], secim.sorgu, proxy=secim.proxy,
                     onceki_profil=tik["profil"])
    print(f"pogo: result={pog['result']} http={pog['http_status']} "
          f"ms={pog['elapsed_ms']} bekleme={pog['bekleme_ms']}")
    return 0 if pog["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())