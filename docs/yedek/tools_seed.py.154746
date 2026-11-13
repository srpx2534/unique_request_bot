"""Referans verisini veritabanına yazar.

Şu an tek iş yapar: 81 ili nüfus ve koordinatla ekler, uule değerini üretir.
Idempotenttir; tekrar çalıştırıldığında satırları günceller, çoğaltmaz.

Kullanım:
    python tools/seed.py
"""

from __future__ import annotations

import csv
import sys

import uule
from db import KOK, baglan

GEO_CSV = KOK / "db" / "seeds" / "geo.csv"

# Beklenen il sayısı. Eksik seed sessizce geçmesin.
BEKLENEN_IL = 81


def satirlari_oku() -> list[tuple]:
    """CSV'yi okur ve doğrular.

    Returns:
        (kod, ad, slug, nufus, lat, lon, uule) demetlerinden oluşan liste.
    """
    if not GEO_CSV.exists():
        raise FileNotFoundError(f"seed dosyası yok: {GEO_CSV}")

    kayitlar: list[tuple] = []
    with GEO_CSV.open(encoding="utf-8", newline="") as dosya:
        for satir in csv.DictReader(dosya):
            kod = int(satir["code"])
            # uule koordinattan burada üretilir, ayrı dosya gerekmez.
            kayitlar.append(
                (
                    kod,
                    satir["name"],
                    satir["slug"],
                    int(satir["population"]),
                    satir["lat"],
                    satir["lon"],
                    uule.uret(satir["lat"], satir["lon"]),
                )
            )

    if len(kayitlar) != BEKLENEN_IL:
        raise ValueError(f"{BEKLENEN_IL} il bekleniyordu, {len(kayitlar)} bulundu.")
    return kayitlar


def main() -> int:
    """Seed'i uygular. Hata varsa 1 döner."""
    try:
        kayitlar = satirlari_oku()
    except (FileNotFoundError, ValueError) as hata:
        print(f"HATA: {hata}")
        return 1

    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            # Çakışmada güncelle: seed tekrar çalıştırılabilir kalır.
            imlec.executemany(
                """
                INSERT INTO geo (code, name, slug, population, lat, lon, uule)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  name=VALUES(name), slug=VALUES(slug),
                  population=VALUES(population), lat=VALUES(lat),
                  lon=VALUES(lon), uule=VALUES(uule)
                """,
                kayitlar,
            )

        # Doğrulama: satır sayısı ve uule doluluğu yerinde mi.
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT COUNT(*), COUNT(uule) FROM geo")
            toplam, dolu = imlec.fetchone()

        print(f"geo: {toplam} satır, {dolu} uule dolu.")
        if toplam != BEKLENEN_IL or dolu != BEKLENEN_IL:
            print("HATA: doğrulama tutmadı.")
            return 1
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    sys.exit(main())