"""SERP anahtarını komut satırından ayar tablosuna yazar.

.env'den çıkarılan anahtarların tek seferlik taşınması ve elle güncelleme
için kullanılır. Panel Ayarlar ekranı aynı işi yapar; bu araç terminalden
çalışmak isteyenler içindir.

Kullanım:
    python tools/anahtar_tasima.py serp_decodo <anahtar>
    python tools/anahtar_tasima.py --liste
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

import pymysql  # noqa: E402

from worker import ayar  # noqa: E402

GECERLI = ("serp_decodo", "serp_serper", "serp_searchapi")


def baglan() -> pymysql.connections.Connection:
    """Ayar tablosuna yazacak bağlantıyı açar."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user=ayar.oku("MYSQL_USER", "request"),
        password=ayar.oku("MYSQL_PASSWORD"),
        database=ayar.oku("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        autocommit=True,
    )


def liste() -> int:
    """Kayıtlı anahtarları uzunluklarıyla yazar."""
    with baglan() as baglanti, baglanti.cursor() as imlec:
        imlec.execute("SELECT anahtar, CHAR_LENGTH(deger) FROM ayar WHERE anahtar LIKE 'serp%' ORDER BY anahtar")
        for anahtar, uzunluk in imlec.fetchall():
            print(f"{anahtar}: {uzunluk} karakter")
    return 0


def yaz(anahtar: str, deger: str) -> int:
    """Anahtarı yazar; varsa üzerine gider."""
    if anahtar not in GECERLI:
        print(f"HATA: geçersiz anahtar. Seçenekler: {', '.join(GECERLI)}")
        return 1
    with baglan() as baglanti, baglanti.cursor() as imlec:
        imlec.execute(
            "INSERT INTO ayar (anahtar, deger) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE deger = VALUES(deger)",
            (anahtar, deger),
        )
    print(f"[OK] {anahtar} yazıldı ({len(deger)} karakter)")
    return 0


def main() -> int:
    """Komut satırını çözer."""
    ayristirici = argparse.ArgumentParser(description="SERP anahtarı yaz")
    ayristirici.add_argument("anahtar", nargs="?", help="serp_decodo, serp_serper, serp_searchapi")
    ayristirici.add_argument("deger", nargs="?", help="anahtar değeri")
    ayristirici.add_argument("--liste", action="store_true", help="kayıtlı anahtarları göster")
    secim = ayristirici.parse_args()

    if secim.liste or not secim.anahtar:
        return liste()
    if not secim.deger:
        print("HATA: değer verilmedi.")
        return 1
    return yaz(secim.anahtar, secim.deger.strip())


if __name__ == "__main__":
    raise SystemExit(main())