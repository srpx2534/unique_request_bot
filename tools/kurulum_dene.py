"""Sifirdan kurulumu gecici semada dener.

Butun migration'lar bos bir semaya sirayla uygulanir, zorunlu tablolar ve seed
sayilari denetlenir, sonra sema silinir. Boylece "elle eklenmis sutun" gibi
gizli bagimliliklar ortaya cikar.

Kullanim: python tools/kurulum_dene.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymysql

sys.path.insert(0, "tools")

from db import COLLATION, MIGRATION_DIZINI, _yonetici_adaylari, ayar, sql_dosyasini_ayristir  # noqa: E402

SEMA = "unique_request_bot_kurulum_dene"
# Zorunlu tablo listesi verify.py'den alinir; iki kopya bayatliyordu.
from verify import ZORUNLU  # noqa: E402


def _baglan():
    """Sema secmeden yonetici baglantisi acar."""
    hatalar = []
    for kullanici, sifre in _yonetici_adaylari():
        try:
            return pymysql.connect(
                host=ayar("MYSQL_HOST", "127.0.0.1"),
                port=int(ayar("MYSQL_PORT", "3306")),
                user=kullanici, password=sifre, charset="utf8mb4", autocommit=True,
            )
        except Exception as hata:  # noqa: BLE001
            hatalar.append(str(hata))
    raise RuntimeError("baglanti kurulamadi: " + "; ".join(hatalar))


def main() -> int:
    """Kurulumu dener. Eksik varsa 1 doner."""
    baglanti = _baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(f"DROP DATABASE IF EXISTS `{SEMA}`")
            imlec.execute(f"CREATE DATABASE `{SEMA}` CHARACTER SET utf8mb4 COLLATE {COLLATION}")
            imlec.execute(f"USE `{SEMA}`")

            for dosya in sorted(MIGRATION_DIZINI.glob("*.sql")):
                for ifade in sql_dosyasini_ayristir(dosya):
                    imlec.execute(ifade)
                print(f"  uygulandi: {dosya.name}")

            imlec.execute(
                "SELECT table_name FROM information_schema.tables"
                " WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (SEMA,),
            )
            var = {s[0] for s in imlec.fetchall()}
            eksik = [t for t in ZORUNLU if t not in var]

            imlec.execute("SELECT COUNT(*), COUNT(uule) FROM geo")
            geo, uule = imlec.fetchone()

        print(f"tablo: {len(var)} · eksik: {len(eksik)} · geo: {geo} · uule: {uule}")
        for ad in eksik:
            print(f"  EKSIK {ad}")

        if eksik or geo != 81 or uule != 81:
            print("HATA: kurulum tutmadi.")
            return 1
        print("KURULUM TAMAM.")
        return 0
    finally:
        try:
            with baglanti.cursor() as imlec:
                imlec.execute(f"DROP DATABASE IF EXISTS `{SEMA}`")
        finally:
            baglanti.close()


if __name__ == "__main__":
    sys.exit(main())