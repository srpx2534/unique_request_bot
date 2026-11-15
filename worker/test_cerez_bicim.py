"""Bicim tanima ve il kodu cikarma testleri (D-1).

Modul worker paketinden ice aktarilir. Stdlib de ayni adli bir modul
bulundurdugu icin paket yolu acikca yazilir; golgeleme riski kalmaz.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from worker import cookie

_DEPO = Path(cookie.__file__).resolve().parent.parent

bicim_bul = cookie.bicim_bul
coz = cookie.coz
il_bul = cookie.il_bul


def _dizi() -> str:
    return json.dumps([{"name": "SID", "domain": ".google.com", "value": "v", "path": "/"}])


def test_citali_dizi_json_sayilir() -> None:
    assert bicim_bul(_dizi()) == "json"


def test_nesne_json_sayilir() -> None:
    assert bicim_bul(json.dumps({"cookies": []})) == "json"


def test_bastaki_bosluk_diziyi_bozmaz() -> None:
    assert bicim_bul("\r\n\t  " + _dizi()) == "json"


def test_netscape_hala_taninir() -> None:
    assert bicim_bul(".google.com\tTRUE\t/\tFALSE\t0\tSID\tx") == "netscape"


def test_http_only_satiri_netscape() -> None:
    assert bicim_bul("#HttpOnly_.google.com\tTRUE\t/\tFALSE\t0\tSID\tx") == "netscape"


def test_yorum_satiri_atlanip_sonraki_satira_bakilir() -> None:
    metin = "# Netscape HTTP Cookie File\n.google.com\tTRUE\t/\tFALSE\t0\tSID\tx"
    assert bicim_bul(metin) == "netscape"


@pytest.mark.parametrize("metin", ["", "   ", "merhaba dunya", "<html></html>"])
def test_taninmayan_icerik_none(metin: str) -> None:
    assert bicim_bul(metin) is None


def test_citali_dizi_cozulur() -> None:
    cerezler = coz(_dizi(), "json")
    assert len(cerezler) == 1
    assert cerezler[0]["ad"] == "SID"
    assert cerezler[0]["domain"] == "google.com"
    assert cerezler[0]["host_only"] is False


def test_noktasiz_alan_host_only_olur() -> None:
    ham = json.dumps([{"name": "A", "domain": "google.com", "value": "1"}])
    assert coz(ham, "json")[0]["host_only"] is True


@pytest.mark.parametrize(
    ("ad", "beklenen"),
    [
        ("34_cerez.json", 34),
        ("cerez_06.txt", 6),
        ("81/alt/a.json", 81),
        ("cerez.json", None),
        ("82_cerez.json", None),
        ("34\\alt\\b.json", 34),
    ],
)
def test_il_kodu_dosya_adindan(ad: str, beklenen: int | None) -> None:
    assert il_bul(ad) == beklenen


def test_ts_ayristirici_diziyi_kabul_eder_il_zorunlu_degil() -> None:
    kaynak = (_DEPO / "src" / "server" / "cerez.ts").read_text(encoding="utf-8")
    assert 'bas === "{" || bas === "["' in kaynak
    assert 'karakter === "{" || karakter === "["' in kaynak
    assert 'karakter === "}" || karakter === "]"' in kaynak
    assert "const il: number | null = null;" in kaynak
    assert "ipucuMobil" in kaynak
    assert "JOIN cerez_yukleme y ON y.id = d.yukleme_id" in kaynak