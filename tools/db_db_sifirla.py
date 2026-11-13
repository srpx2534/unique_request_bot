"""mysql.db tablosunu checksum kapalıyken yeniden kurar.

Onarım sonrası tablo okunur ama yazılamaz durumda kalırsa (1030/176),
sayfalar farklı sağlama ayarıyla yazılmış demektir. Tablo boşaltılır;
veritabanı seviyesindeki yetkiler zaten kaybolmuştu, yeniden verilecek.

Kullanım:
    python tools/db_db_sifirla.py
"""

from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

import pymysql  # noqa: E402

from worker import ayar  # noqa: E402


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


def dene(imlec, cumle: str) -> None:
    """Cümleyi çalıştırır, sonucu yazar; hata olsa da devam eder."""
    try:
        imlec.execute(cumle)
        print(f"[OK] {cumle}")
    except Exception as hata:  # noqa: BLE001
        print(f"[HATA] {cumle} -> {hata}")


def main() -> int:
    """Checksum kapatılır, tablo yeniden kurulur ve boşaltılır."""
    baglanti = baglan()
    imlec = baglanti.cursor()

    dene(imlec, "SET GLOBAL aria_page_checksum = OFF")
    dene(imlec, "ALTER TABLE mysql.db ENGINE = Aria")
    dene(imlec, "CHECK TABLE mysql.db")
    dene(imlec, "TRUNCATE TABLE mysql.db")
    dene(imlec, "FLUSH PRIVILEGES")

    imlec.execute("CHECK TABLE mysql.db")
    print(f"[SON] {imlec.fetchall()}")

    imlec.close()
    baglanti.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())