"""cookie.py ayristirici testleri."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from worker import cookie

JSON_ORNEK = json.dumps({
    "cookies": [
        {
            "domain": ".google.com", "name": "NID", "value": "abc",
            "path": "/", "expires": 1775590865.4, "httpOnly": True,
            "secure": True, "sameSite": "None", "priority": "Medium",
            "session": False, "size": 209, "sourcePort": 443,
            "sourceScheme": "Secure", "sameParty": False,
        },
        {
            "domain": ".youtube.com", "name": "YSC", "value": "x",
            "path": "/", "expires": -1, "httpOnly": True, "secure": True,
            "session": True,
        },
    ]
})

NETSCAPE_ORNEK = (
    "# Netscape HTTP Cookie File\n"
    ".google.com\tTRUE\t/\tTRUE\t1775590865\tNID\tabc\n"
    "#HttpOnly_.google.com.tr\tTRUE\t/\tTRUE\t0\t__Secure-1PSID\tg.a000\n"
)


def test_json_coz_alanlari_tasir():
    cerezler = cookie.json_coz(JSON_ORNEK)
    assert len(cerezler) == 2
    nid = cerezler[0]
    assert nid["domain"] == "google.com"
    assert nid["ad"] == "NID"
    assert nid["guvenli"] is True
    assert nid["http_only"] is True
    assert nid["same_site"] == "none"
    assert nid["oncelik"] == "medium"
    assert nid["boyut"] == 209
    assert nid["kaynak_port"] == 443
    assert nid["host_only"] is False
    assert isinstance(nid["sona_erme"], datetime)


def test_json_suresiz_cerez_none():
    cerezler = cookie.json_coz(JSON_ORNEK)
    assert cerezler[1]["sona_erme"] is None
    assert cerezler[1]["oturumluk"] is True


def test_json_bozuk_atar():
    with pytest.raises(ValueError):
        cookie.json_coz("{bozuk")


def test_json_kok_taninmaz():
    with pytest.raises(ValueError):
        cookie.json_coz(json.dumps({"baska": 1}))


def test_netscape_coz_http_only_oneki():
    cerezler = cookie.netscape_coz(NETSCAPE_ORNEK)
    assert len(cerezler) == 2
    assert cerezler[0]["domain"] == "google.com"
    assert cerezler[1]["http_only"] is True
    assert cerezler[1]["domain"] == "google.com.tr"
    assert cerezler[1]["sona_erme"] is None


def test_netscape_bos_atar():
    with pytest.raises(ValueError):
        cookie.netscape_coz("# yalniz yorum\n")


def test_bicim_bul():
    assert cookie.bicim_bul(JSON_ORNEK) == "json"
    assert cookie.bicim_bul(NETSCAPE_ORNEK) == "netscape"
    assert cookie.bicim_bul("duz metin") is None


def test_il_bul():
    assert cookie.il_bul("adana_01.json") == 1
    assert cookie.il_bul("81_duzce.txt") == 81
    assert cookie.il_bul("cookie_34_2024.txt") == 34
    assert cookie.il_bul("cerezler.json") is None
    assert cookie.il_bul("kopya_82.txt") is None


def test_suz_google_ve_hedef_kalir():
    cerezler = cookie.json_coz(JSON_ORNEK) + [
        cookie._kayit(domain="armut.com", ad="a", deger="b"),
        cookie._kayit(domain="doubleclick.net", ad="IDE", deger="c"),
    ]
    kalan = cookie.suz(cerezler, "https://www.armut.com/veteriner")
    adlar = {c["ad"] for c in kalan}
    assert "NID" in adlar
    assert "a" in adlar
    assert "IDE" not in adlar


def test_oturuma_yukle_sayar():
    class Sahte:
        def __init__(self) -> None:
            self.kayitlar: list[tuple[str, str]] = []
            self.cookies = self

        def set(self, ad: str, deger: str, domain: str = "", path: str = "/") -> None:
            self.kayitlar.append((ad, domain))

    sahte = Sahte()
    yuklenen = cookie.oturuma_yukle(sahte, cookie.json_coz(JSON_ORNEK))
    assert yuklenen == 2
    assert sahte.kayitlar[0] == ("NID", "google.com")