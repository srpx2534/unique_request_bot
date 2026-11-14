"""Ayar tablosundan okuma.

SERP anahtarları gibi yönetim verileri .env yerine veritabanında tutulur.
Değerler 60 saniye önbelleklenir: burst başına tek sorgu yapılır, panelde
yapılan değişiklik bir dakika içinde etkili olur.

Yalnızca SELECT çalışır; worker durumsuz kalır. Tablo okunamazsa .env'e,
o da yoksa varsayılana düşer.
"""

from __future__ import annotations

import time

import pymysql

from worker import ayar

ONBELLEK_SN = 60
_onbellek: dict[str, tuple[float, str]] = {}


def _baglan() -> pymysql.connections.Connection:
    """Salt okuma amaçlı bağlantı açar."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user=ayar.oku("MYSQL_USER", "request"),
        password=ayar.oku("MYSQL_PASSWORD"),
        database=ayar.oku("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
        autocommit=True,
    )


def oku(anahtar: str, varsayilan: str = "") -> str:
    """Ayarı okur.

    Args:
        anahtar: ayar.anahtar değeri.
        varsayilan: Hiçbir kaynakta değer yoksa dönecek değer.

    Returns:
        Önbellekten, tablodan veya .env'den gelen değer.
    """
    simdi = time.monotonic()
    kayit = _onbellek.get(anahtar)
    if kayit and simdi - kayit[0] < ONBELLEK_SN:
        # Tablodan gelen deger onbellekte; yoksa .env, o da yoksa varsayilan (C43).
        return kayit[1] or ayar.oku(anahtar, varsayilan)

    deger: str | None = None
    baglanti = None
    try:
        baglanti = _baglan()
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT deger FROM ayar WHERE anahtar = %s", (anahtar,))
            satir = imlec.fetchone()
        # Anahtar yoksa None kalir: "yok" ile "okunamadi" ayri dallardir.
        if satir:
            deger = str(satir[0]).strip()
    except Exception:  # noqa: BLE001
        deger = None
    finally:
        if baglanti is not None:
            baglanti.close()

    if deger is not None:
        # Yalnizca tablodan okunan deger onbelleklenir; tablo hatasi her turda
        # yeniden denenir, .env okumasi tekrar tekrar yapilmaz.
        _onbellek[anahtar] = (simdi, deger)
        return deger or ayar.oku(anahtar, varsayilan)
    return ayar.oku(anahtar, varsayilan)


def temizle() -> None:
    """Önbelleği boşaltır; elle doğrulama ve testler için."""
    _onbellek.clear()