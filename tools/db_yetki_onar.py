"""Veritabanı kullanıcısının yetkilerini denetler ve onarır.

Yerel bağlantı `localhost` soketinden gelir; kullanıcı yalnızca `%` için
tanımlıysa "Access denied" düşer. Bu araç iki host için yetkiyi eşitler.
Root şifresi .env'den okunur; boşsa boş denenir.

Kullanım:
    python tools/db_yetki_onar.py
"""

from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

import pymysql  # noqa: E402

from worker import ayar  # noqa: E402

KULLANICI = ayar.oku("MYSQL_USER", "request")
SIFRE = ayar.oku("MYSQL_PASSWORD")
VERITABANI = ayar.oku("MYSQL_DATABASE", "unique_request_bot")
HOSTLAR = ("localhost", "%")


def yonetici() -> pymysql.connections.Connection:
    """Root ile şema seçmeden bağlanır."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user="root",
        password=ayar.oku("MYSQL_ROOT_PASSWORD"),
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
        autocommit=True,
    )


def main() -> int:
    """Yetkileri gösterir, eksikse tanımlar ve doğrular."""
    baglanti = yonetici()
    imlec = baglanti.cursor()

    for host in HOSTLAR:
        try:
            imlec.execute(f"SHOW GRANTS FOR '{KULLANICI}'@'{host}'")
        except pymysql.err.OperationalError:
            print(f"[YOK] {KULLANICI}@{host} tanimli degil")
        else:
            print(f"[VAR] {KULLANICI}@{host}")

    for host in HOSTLAR:
        # Yuzde isareti pymysql formatinda kacis ister; yalnizca parametreli
        # cumlelerde ikilenir.
        guvenli = host.replace("%", "%%")
        imlec.execute(f"CREATE USER IF NOT EXISTS '{KULLANICI}'@'{guvenli}' IDENTIFIED BY %s", (SIFRE,))
        imlec.execute(f"ALTER USER '{KULLANICI}'@'{guvenli}' IDENTIFIED BY %s", (SIFRE,))
        imlec.execute(f"GRANT ALL PRIVILEGES ON `{VERITABANI}`.* TO '{KULLANICI}'@'{host}'")
    imlec.execute("FLUSH PRIVILEGES")

    for host in HOSTLAR:
        imlec.execute(f"SHOW GRANTS FOR '{KULLANICI}'@'{host}'")
        for satir in imlec.fetchall():
            print(f"  {satir[0]}")

    imlec.close()
    baglanti.close()

    deneme = pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user=KULLANICI,
        password=SIFRE,
        database=VERITABANI,
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
    )
    with deneme.cursor() as d:
        d.execute("SELECT COUNT(*) FROM geo")
        print(f"[OK] uygulama kullanicisi baglandi, geo satiri: {d.fetchone()[0]}")
    deneme.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())