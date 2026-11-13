"""Kelimenin hala calisip calismadigini ucuz yolla sorar.

Burst ortasinda `stop` verilirse kalan hit atilmamali (C21). Her hit icin
veritabani sorgusu pahali oldugu icin sonuc 3 saniye onbelleklenir: durdurma
en fazla 3 saniye gecikmeyle etkili olur, istek basina sorgu gitmez.

Yalnizca SELECT calisir; worker durumsuz kalir.

Kullanim: worker/app.py.
"""

from __future__ import annotations

import time

import pymysql

from worker import ayar

ONBELLEK_SN = 3  # saniye; durdurma gecikmesi ile sorgu yuku dengesi
_onbellek: dict[str, tuple[float, bool]] = {}


def _baglan() -> pymysql.connections.Connection:
    """Salt okuma amacli baglanti acar."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user=ayar.oku("MYSQL_USER", "request"),
        password=ayar.oku("MYSQL_PASSWORD"),
        database=ayar.oku("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        autocommit=True,
    )


def keyword_aktif_mi(kelime: str) -> bool:
    """Kelime hala `active` mi.

    Args:
        kelime: Kelime metni.

    Returns:
        Aktifse True. Sorgu dusse bile True doner: durdurma suphesi burst'u
        kesmemeli.
    """
    simdi = time.monotonic()
    kayit = _onbellek.get(kelime)
    if kayit and simdi - kayit[0] < ONBELLEK_SN:
        return kayit[1]

    sonuc = True
    baglanti = None
    try:
        baglanti = _baglan()
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT state FROM keyword WHERE text = %s LIMIT 1", (kelime,))
            satir = imlec.fetchone()
            if satir:
                sonuc = satir[0] == "active"
    except Exception:  # noqa: BLE001
        sonuc = True
    finally:
        if baglanti is not None:
            try:
                baglanti.close()
            except Exception:  # noqa: BLE001
                pass

    _onbellek[kelime] = (simdi, sonuc)
    return sonuc