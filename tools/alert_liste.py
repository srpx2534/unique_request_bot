"""Uyarıları listeler ve kapatır.

Panel gelene kadar uyarıları görmenin yolu. Varsayılan olarak yalnızca
açılmamışları gösterir; --tumu ile hepsi listelenir.

Kullanım:
    python tools/alert_liste.py
    python tools/alert_liste.py --tumu --adet 50
    python tools/alert_liste.py --kapat 12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "tools"))

from db import baglan  # noqa: E402


def listele(tumu: bool, adet: int) -> int:
    """Uyarıları yazar. Açık uyarı sayısını döndürür."""
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            kosul = "" if tumu else " WHERE acknowledged = 0"
            imlec.execute(
                "SELECT id, kind, message, yas_dk, acknowledged FROM v_alert"
                + kosul + " LIMIT %s",
                (adet,),
            )
            satirlar = imlec.fetchall()
            imlec.execute("SELECT COUNT(*) FROM alert WHERE acknowledged = 0")
            acik = imlec.fetchone()[0]
    finally:
        baglanti.close()

    print(f"açık uyarı: {acik}")
    for kimlik, tur, mesaj, yas, kapandi in satirlar:
        im = "kapalı" if kapandi else "AÇIK"
        print(f"  [{kimlik}] {im} {tur} · {yas} dk · {mesaj}")
    return acik


def kapat(kimlik: int) -> int:
    """Uyarıyı kapatır. Etkilenen satır sayısını döndürür."""
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE alert SET acknowledged = 1 WHERE id = %s", (kimlik,)
            )
            return imlec.rowcount
    finally:
        baglanti.close()


def main() -> int:
    """Komut satırını işler."""
    ayar = argparse.ArgumentParser(description="Uyarı listesi")
    ayar.add_argument("--tumu", action="store_true", help="kapalıları da göster")
    ayar.add_argument("--adet", type=int, default=20)
    ayar.add_argument("--kapat", type=int, help="uyarı kimliği")
    secim = ayar.parse_args()

    if secim.kapat:
        print(f"kapatılan: {kapat(secim.kapat)}")
        return 0
    listele(secim.tumu, secim.adet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())