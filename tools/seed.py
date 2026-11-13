"""Referans verisini yeniden yukler.

Iki kaynak sirayla uygulanir: 003_geo.sql (81 il) ve 004_uule.sql (uule).
Ikisi de ON DUPLICATE KEY UPDATE ile yazdigi icin tekrar calistirmak guvenlidir.
uule dosyasi once uretilir, elle guncel tutulmaz.

Kullanim: python tools/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "tools")

import gen_uule  # noqa: E402
from db import MIGRATION_DIZINI, baglan, sql_dosyasini_ayristir  # noqa: E402

SIRA = ("003_geo.sql", "004_uule.sql")
BEKLENEN_IL = 81


def _uygula(baglanti, ad: str) -> None:
    """Tek SQL dosyasini uygular."""
    for ifade in sql_dosyasini_ayristir(MIGRATION_DIZINI / ad):
        with baglanti.cursor() as imlec:
            imlec.execute(ifade)


def main() -> int:
    """Seed'i uygular ve dogrular. Hata varsa 1 doner."""
    if gen_uule.main() != 0:
        return 1

    baglanti = baglan()
    try:
        for ad in SIRA:
            _uygula(baglanti, ad)

        with baglanti.cursor() as imlec:
            imlec.execute("SELECT COUNT(*), COUNT(uule) FROM geo")
            toplam, dolu = imlec.fetchone()

        print(f"geo: {toplam} satir, {dolu} uule dolu.")
        if toplam != BEKLENEN_IL or dolu != BEKLENEN_IL:
            print("HATA: dogrulama tutmadi.")
            return 1
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    sys.exit(main())