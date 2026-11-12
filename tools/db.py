"""Veritabanı bağlantısı ve SQL dosyası yardımcıları.

Tüm yollar pathlib ile kurulur; Windows'ta da Linux'ta da aynı çalışır.
Bağlantı ayarları .env üzerinden okunur, kodda sabit değer yoktur.
"""

from __future__ import annotations

import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

# Proje kökü: bu dosyanın bir üst dizini.
KOK = Path(__file__).resolve().parents[1]
MIGRATION_DIZINI = KOK / "db" / "migrations"

# .env varsa yüklenir; yoksa ortam değişkenleri olduğu gibi kullanılır.
load_dotenv(KOK / ".env")


def baglan(veritabani: str | None = None) -> pymysql.connections.Connection:
    """MySQL bağlantısı açar.

    Args:
        veritabani: Hedef şema adı. None ise .env'deki ad kullanılır.

    Returns:
        Açık bağlantı. Çağıran taraf kapatmakla yükümlüdür.
    """
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "urb"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=veritabani or os.getenv("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        autocommit=True,
        # Sürücü tarafında tarih dönüşümü yapılmaz, metin olarak taşınır.
        cursorclass=pymysql.cursors.Cursor,
    )


def sema_olustur() -> None:
    """Hedef şemayı yoksa oluşturur. Var olan şemaya dokunmaz."""
    ad = os.getenv("MYSQL_DATABASE", "unique_request_bot")
    # Şema seçmeden bağlanılır, çünkü hedef henüz yok olabilir.
    baglanti = baglan(veritabani=None) if False else pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "urb"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                f"CREATE DATABASE IF NOT EXISTS `{ad}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
    finally:
        baglanti.close()


def sql_dosyasini_ayristir(yol: Path) -> list[str]:
    """SQL dosyasını tek tek çalıştırılabilir ifadelere böler.

    Yorum satırları (`--`) atılır, noktalı virgülden bölünür, boşlar süzülür.

    Args:
        yol: Okunacak .sql dosyası.

    Returns:
        Çalıştırılabilir ifade listesi.
    """
    ham = yol.read_text(encoding="utf-8")
    # Yorum satırlarını temizle; içerikteki -- korunur çünkü satır başı aranır.
    satirlar = [s for s in ham.splitlines() if not s.lstrip().startswith("--")]
    ifadeler = []
    for parca in "\n".join(satirlar).split(";"):
        temiz = parca.strip()
        if temiz:
            ifadeler.append(temiz)
    return ifadeler