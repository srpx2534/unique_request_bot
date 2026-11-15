"""Burst'ü elle dener.

Küçük bir adetle uçtan uca akışı çalıştırır ve sayaçları yazar. Proxy
verilmezse doğrudan bağlantı kullanılır.

Kullanım:
    python tools/burst_dene.py --sorgu "veteriner" --domain armut.com --adet 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from worker import burst  # noqa: E402


def main() -> int:
    """Burst'ü çalıştırır. Başarısızsa 1 döner."""
    ayar = argparse.ArgumentParser(description="Burst denemesi")
    ayar.add_argument("--sorgu", required=True)
    ayar.add_argument("--domain", required=True)
    ayar.add_argument("--adet", type=int, default=3)
    ayar.add_argument("--proxy")
    ayar.add_argument("--uule")
    ayar.add_argument("--geo", help="il slug'ı")
    secim = ayar.parse_args()

    proxy_secici = (lambda: secim.proxy) if secim.proxy else None
    # Basamak boyu en fazla AZAMI_HIT'tir (§9); büyük adet basamaklara bölünür.
    kalan = secim.adet
    toplam = {"ok": 0, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0}
    sonuc = None
    while kalan > 0:
        parca = min(kalan, burst.AZAMI_HIT)
        kalan -= parca
        sonuc = burst.burst_yap(
            secim.sorgu, secim.domain, parca,
            proxy_secici=proxy_secici, uule=secim.uule,
            geo_slug=secim.geo,
        )
        for anahtar in toplam:
            toplam[anahtar] += sonuc[anahtar]
        if sonuc["result"] != "ok":
            break
    assert sonuc is not None
    sonuc.update(toplam)

    print(f"result={sonuc['result']} hedef={sonuc['hedef_url']} "
          f"ms={sonuc['elapsed_ms']}")
    print(f"ok={sonuc['ok']} captcha={sonuc['captcha']} "
          f"not_found={sonuc['not_found']} timeout={sonuc['timeout']} "
          f"error={sonuc['error']}")
    for kayit in sonuc["hits"]:
        print(f"  {kayit['sira']}. izlenim={kayit['izlenim']} "
              f"tik={kayit['tik']} pogo={kayit['pogo']} -> {kayit['result']}")

    return 0 if sonuc["result"] == "ok" and sonuc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())