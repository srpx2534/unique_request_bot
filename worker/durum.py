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
_onbellek: dict[tuple[str, str], tuple[float, bool]] = {}


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


def keyword_aktif_mi(kelime: str, site_domain: str | None = None) -> bool:
    """Kelime hala `active` mi.

    Args:
        kelime: Kelime metni.
        site_domain: Hedef alan adi. Ayni metin iki sitede olabildigi icin
            onbellek anahtari cifttir; verilmezse yalnizca metne bakilir.

    Returns:
        Aktifse True. Sorgu dusse bile True doner: durdurma suphesi burst'u
        kesmemeli.
    """
    anahtar = (kelime, (site_domain or "").strip().lower())
    simdi = time.monotonic()
    kayit = _onbellek.get(anahtar)
    if kayit and simdi - kayit[0] < ONBELLEK_SN:
        return kayit[1]

    sonuc = True
    baglanti = None
    try:
        baglanti = _baglan()
        with baglanti.cursor() as imlec:
            # Site verildiyse cift ile aranir: ayni metinli iki kayit karismasin.
            if anahtar[1]:
                imlec.execute(
                    "SELECT k.state FROM keyword k JOIN site s ON s.id = k.site_id"
                    " WHERE k.text = %s AND s.domain = %s LIMIT 1",
                    (kelime, anahtar[1]),
                )
            else:
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

    _onbellek[anahtar] = (simdi, sonuc)
    return sonuc