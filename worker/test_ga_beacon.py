"""GA beacon testleri."""

import uuid

from worker import ga_beacon


def test_cid_profilden_turetilir_ve_kalicidir():
    assert ga_beacon.cid_uret(7) == ga_beacon.cid_uret(7)
    assert ga_beacon.cid_uret(7) != ga_beacon.cid_uret(8)
    uuid.UUID(ga_beacon.cid_uret(7))


def test_cid_profilsiz_rastgele():
    assert ga_beacon.cid_uret(None) != ga_beacon.cid_uret(None)


def test_govde_page_view_tasir():
    veri = ga_beacon.govde("cid", "https://a.com/x", "https://www.google.com/", 25_000, "ot")
    olay = veri["events"][0]
    assert olay["name"] == "page_view"
    assert olay["params"]["page_location"] == "https://a.com/x"
    assert olay["params"]["page_referrer"] == "https://www.google.com/"
    assert olay["params"]["engagement_time_msec"] == 25_000
    assert olay["params"]["session_id"] == "ot"


def test_govde_sifir_dwell_bire_cevrilir():
    veri = ga_beacon.govde("cid", "a", "", 0, "ot")
    assert veri["events"][0]["params"]["engagement_time_msec"] == 1


def test_kimlik_yoksa_kapali(monkeypatch):
    monkeypatch.setattr(ga_beacon, "ayar_bul", lambda _d: ("", ""))
    assert ga_beacon.gonder("a.com", "https://a.com", "", 1000)["result"] == "kapali"


def test_basariyla_gonderir(monkeypatch):
    cagri = {}

    class Yanit:
        status_code = 204

    def sahte(url, **adli):
        cagri["url"] = url
        cagri["params"] = adli.get("params")
        cagri["json"] = adli.get("json")
        return Yanit()

    monkeypatch.setattr(ga_beacon, "ayar_bul", lambda _d: ("G-1", "sir"))
    monkeypatch.setattr(ga_beacon.requests, "post", sahte)

    sonuc = ga_beacon.gonder("a.com", "https://a.com/x", "https://www.google.com/", 5000, 3)

    assert sonuc["result"] == "ok"
    assert cagri["params"]["measurement_id"] == "G-1"
    assert cagri["json"]["events"][0]["name"] == "page_view"


def test_http_hatasi_hata_doner(monkeypatch):
    class Yanit:
        status_code = 400

    monkeypatch.setattr(ga_beacon, "ayar_bul", lambda _d: ("G-1", "sir"))
    monkeypatch.setattr(ga_beacon.requests, "post", lambda *a, **k: Yanit())

    assert ga_beacon.gonder("a.com", "a", "", 1)["result"] == "error"


def test_ag_hatasi_hata_doner(monkeypatch):
    def patlat(*a, **k):
        raise RuntimeError("ag")

    monkeypatch.setattr(ga_beacon, "ayar_bul", lambda _d: ("G-1", "sir"))
    monkeypatch.setattr(ga_beacon.requests, "post", patlat)

    assert ga_beacon.gonder("a.com", "a", "", 1)["result"] == "error"