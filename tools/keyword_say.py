"""keyword_geo dağılımını sayar.

C14 doğrulaması için: kelime başına tier sayımı ve core diliminin gerçekten
nüfus sırasının ilk 10 ili olup olmadığı yazılır. Salt okunur.

Kullanım:
    python tools/keyword_say.py --kelime "veteriner"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "tools"))

from db import baglan  # noqa: E402

CORE_ILLER = (34, 6, 35, 16, 7, 42, 1, 63, 27, 41)


def main() -> int:
    """Sayımı yazar. Hata varsa 1 döner."""
    ayar = argparse.ArgumentParser(description="keyword_geo sayımı")
    ayar.add_argument("--kelime", required=True)
    secim = ayar.parse_args()

    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT kg.tier, COUNT(*) FROM keyword_geo kg "
                "JOIN keyword kw ON kw.id = kg.keyword_id "
                "WHERE kw.text = %s GROUP BY kg.tier ORDER BY kg.tier",
                (secim.kelime,),
            )
            satirlar = imlec.fetchall()

            imlec.execute(
                "SELECT COUNT(*) FROM keyword_geo kg "
                "JOIN keyword kw ON kw.id = kg.keyword_id "
                "WHERE kw.text = %s AND kg.tier = 'core' "
                "AND kg.geo_code NOT IN " + str(CORE_ILLER),
                (secim.kelime,),
            )
            core_disi = imlec.fetchone()[0]

            imlec.execute(
                "SELECT COUNT(*) FROM keyword_geo kg "
                "JOIN keyword kw ON kw.id = kg.keyword_id WHERE kw.text = %s",
                (secim.kelime,),
            )
            toplam = imlec.fetchone()[0]
    finally:
        baglanti.close()

    print(f"kelime: {secim.kelime} · toplam: {toplam}")
    for etiket, adet in satirlar:
        print(f"  {etiket}: {adet}")
    print(f"core disi il sayisi: {core_disi}")
    return 0 if core_disi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())