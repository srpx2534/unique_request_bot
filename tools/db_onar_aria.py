"""MariaDB sistem tablolarını denetler ve onarır.

GRANT yazımı `mysql.db` tablosuna düşer; Aria sayfa sağlama toplamı
bozulduğunda 1030/176 hatası verir. Bu araç ilgili tabloları sırayla
denetler ve onarır. Yalnızca root ile çalışır.

Kullanım:
    python tools/db_onar_aria.py
"""

from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

import pymysql  # noqa: E402

from worker import ayar  # noqa: E402

TABLOLAR = (
    "mysql.db",
    "mysql.global_priv",
    "mysql.tables_priv",
    "mysql.procs_priv",
    "mysql.columns_priv",
)


def baglan() -> pymysql.connections.Connection:
    """Root ile bağlanır."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user="root",
        password=ayar.oku("MYSQL_ROOT_PASSWORD"),
        charset="utf8mb4",
        autocommit=True,
    )


def main() -> int:
    """Her tabloyu denetler, ardından onarır."""
    baglanti = baglan()
    imlec = baglanti.cursor()

    for tablo in TABLOLAR:
        imlec.execute(f"CHECK TABLE {tablo}")
        print(f"[CHECK] {tablo}: {imlec.fetchall()}")

    for tablo in TABLOLAR:
        imlec.execute(f"REPAIR TABLE {tablo}")
        print(f"[REPAIR] {tablo}: {imlec.fetchall()}")

    imlec.execute("FLUSH PRIVILEGES")
    print("[OK] yetkiler tazelendi")
    imlec.close()
    baglanti.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())