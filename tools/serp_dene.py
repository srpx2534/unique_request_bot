"""SERP isteğini elle dener.

API yolunu ve HTML yedeğini ayrı ayrı çalıştırır, sonuç sayısını ve ilk
bes adresi yazar. Anahtar ayar tablosundaki serp_decodo alanindan okunur.

Kullanım:
    python tools/serp_dene.py --sorgu "veteriner" --domain petlebi.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from worker import serp  # noqa: E402


def yaz(etiket: str, sonuc: dict) -> None:
    """Bir sonucu okunur biçimde yazar."""
    print(f"--- {etiket} ---")
    print(f"result={sonuc['result']} position={sonuc['position']} "
          f"http={sonuc['http_status']} ms={sonuc['elapsed_ms']} "
          f"bytes={sonuc['bytes']} organik={len(sonuc['organik'])}")
    if sonuc["mesaj"]:
        print(f"mesaj: {sonuc['mesaj']}")
    for kayit in sonuc["organik"][:5]:
        print(f"  {kayit['position']}. {kayit['link']}")


def main() -> int:
    """Her iki yolu dener. API başarısızsa 1 döner."""
    ayar = argparse.ArgumentParser(description="SERP denemesi")
    ayar.add_argument("--sorgu", required=True)
    ayar.add_argument("--domain")
    ayar.add_argument("--uule")
    ayar.add_argument("--proxy")
    secim = ayar.parse_args()

    api = serp.serp_getir(
        secim.sorgu, hedef_domain=secim.domain, uule=secim.uule
    )
    yaz("api", api)

    html = serp.serp_getir_html(
        secim.sorgu, hedef_domain=secim.domain, uule=secim.uule, proxy=secim.proxy
    )
    yaz("html yedek", html)

    return 0 if api["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())