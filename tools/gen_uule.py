"""geo koordinatlarindan uule degeri uretir ve SQL dosyasi yazar.

uule, Google'a "su noktadan aranmis" demenin yoludur. Sehir hedefleyen proxy
bulunamadiginda SERP'in dogru ili gostermesi icin kullanilir; tiklama IP'sini
degistirmez.

Girdi artik SQL metni degil, seed CSV'sidir: 003 dosyasi yeniden uretilse de
kolon sirasi degisse de ayristirma bozulmaz.

Girdi : db/seeds/geo.csv
Cikti : db/migrations/004_uule.sql

Kullanim: python tools/gen_uule.py
"""

from __future__ import annotations

import base64
import csv
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
GEO_CSV = KOK / "db" / "seeds" / "geo.csv"
CIKTI_SQL = KOK / "db" / "migrations" / "004_uule.sql"

YARICAP_M = 65_000  # metre; il merkezini ve cevresini kapsar
BEKLENEN_IL = 81


def uule_uret(lat: str, lon: str) -> str:
    """Verilen koordinat icin uule dizesi dondurur.

    Bicim Google'in koordinat varyantidir: cozulen metin
    `latlng{ latitude_e7:... longitude_e7:... }` olur ve koordinat 10^7 ile
    carpilir. Onceki `latlng:lat,lon` yazimi ile urlsafe alfabe Google
    tarafindan cozulmuyordu; bozuk uule sessizce yok sayiliyor, il olcumu
    konumsuz kaliyordu.

    Args:
        lat: Enlem, ondalik metin.
        lon: Boylam, ondalik metin.

    Returns:
        Google'in bekledigi w+CAIQICI onekli kodlanmis dize.
    """
    # Zaman damgasi milisaniye; Google tazelik kontrolunde kullanir.
    zaman = int(time.time() * 1000)
    enlem = int(round(float(lat) * 10_000_000))
    boylam = int(round(float(lon) * 10_000_000))
    govde = (
        f"role:1 producer:12 provenance:6 timestamp:{zaman} "
        f"latlng{{ latitude_e7:{enlem} longitude_e7:{boylam} }} radius:{YARICAP_M}"
    )
    # Standart base64: Google "+" ve "/" bekler, urlsafe alfabeyi cozmez.
    kodlu = base64.b64encode(govde.encode("utf-8")).decode().rstrip("=")
    return "w+CAIQICI" + kodlu


def satirlari_oku() -> list[tuple[int, str, str]]:
    """CSV'den kod ve koordinatlari okur.

    Returns:
        (kod, lat, lon) demetleri.

    Raises:
        FileNotFoundError: CSV yoksa.
        ValueError: Satir sayisi 81 degilse.
    """
    if not GEO_CSV.exists():
        raise FileNotFoundError(f"seed dosyasi yok: {GEO_CSV}")

    kayitlar: list[tuple[int, str, str]] = []
    with GEO_CSV.open(encoding="utf-8", newline="") as dosya:
        for satir in csv.DictReader(dosya):
            kayitlar.append((int(satir["code"]), satir["lat"], satir["lon"]))

    if len(kayitlar) != BEKLENEN_IL:
        raise ValueError(f"{BEKLENEN_IL} il bekleniyordu, {len(kayitlar)} bulundu.")
    return kayitlar


def main() -> int:
    """uule SQL'ini uretir. Hata varsa 1 doner."""
    try:
        kayitlar = satirlari_oku()
    except (FileNotFoundError, ValueError) as hata:
        print(f"HATA: {hata}")
        return 1

    parcalar = [
        "-- Uretilmis dosya. Elle duzenlenmez.",
        "-- Kaynak: tools/gen_uule.py, girdi: db/seeds/geo.csv",
        "SET NAMES utf8mb4;",
    ]
    for kod, lat, lon in kayitlar:
        parcalar.append(f"UPDATE geo SET uule='{uule_uret(lat, lon)}' WHERE code={kod};")

    CIKTI_SQL.write_text("\n".join(parcalar) + "\n", encoding="utf-8", newline="\n")
    print(f"OK: {len(kayitlar)} il icin uule yazildi -> {CIKTI_SQL.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())