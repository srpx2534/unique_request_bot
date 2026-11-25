"""Tarayici hattinda isinma sirasi.

Isinma aramadan once ve bir kez kosmali; kapaliyken ya da hata verdiginde
arama yine de yapilmali. Ag yok, sahte sayfa kullanilir.
"""

from __future__ import annotations

import pytest

from worker import tarayici


class SahteSayfa:
    """Playwright sayfasi yerine gecen, olay kaydeden sahte nesne."""

    def __init__(self, olaylar, patlat=()):
        self.olaylar = olaylar
        self.patlat = set(patlat)
        self.url = ""

    def goto(self, adres, **fazla):
        self.olaylar.append(("goto", adres))
        if adres in self.patlat:
            raise RuntimeError("gitmedi")
        self.url = adres
        return type("Yanit", (), {"status": 200})()

    def wait_for_timeout(self, ms):
        pass

    def wait_for_selector(self, *fazla, **adli):
        pass

    def wait_for_load_state(self, *fazla, **adli):
        pass

    def eval_on_selector_all(self, *fazla, **adli):
        return [{
            "cite": "https://hedef.com.tr",
            "href": "https://www.google.com/url?q=https://hedef.com.tr",
        }]


class SahteBaglam:
    """Yeni sayfa ureten sahte baglam."""

    def __init__(self, olaylar, patlat=()):
        self.olaylar = olaylar
        self.patlat = patlat

    def new_page(self):
        return SahteSayfa(self.olaylar, self.patlat)


@pytest.fixture
def isinma_kur(monkeypatch):
    """Isinmayi tek sayfaya ve kisa beklemeye sabitler."""

    def kur(acik=True, patlat=()):
        monkeypatch.setattr(tarayici.isinma, "acik", lambda: acik)
        monkeypatch.setattr(tarayici.isinma, "bekleme", lambda: (1_000, 1_000))
        monkeypatch.setattr(
            tarayici.isinma, "sayfa_sec",
            lambda rastgele=None: [tarayici.isinma.SAYFALAR[0]],
        )
        return tarayici.isinma.SAYFALAR[0]

    return kur


def _bos() -> dict:
    return {"result": "error", "organik": [], "url": "", "mesaj": ""}


def test_arama_once_isinir(isinma_kur):
    isinma_sayfasi = isinma_kur()
    olaylar: list = []
    sonuc = tarayici._tara(SahteBaglam(olaylar), "kelime", None, 1, _bos())

    assert sonuc["isinma"] == "ok"
    assert olaylar[0] == ("goto", isinma_sayfasi)
    assert "google" not in olaylar[0][1]
    assert "google.com/search" in olaylar[1][1]


def test_isinma_kapaliyken_dogrudan_aranir(isinma_kur):
    isinma_kur(acik=False)
    olaylar: list = []
    sonuc = tarayici._tara(SahteBaglam(olaylar), "kelime", None, 1, _bos())

    assert sonuc["isinma"] == "atlandi"
    assert "google.com/search" in olaylar[0][1]


def test_isinma_hatasi_aramayi_durdurmaz(isinma_kur):
    isinma_sayfasi = isinma_kur()
    olaylar: list = []
    sonuc = tarayici._tara(
        SahteBaglam(olaylar, patlat={isinma_sayfasi}), "kelime", None, 1, _bos()
    )

    assert sonuc["isinma"] == "error"
    assert sonuc["result"] == "ok"
    assert any("google.com/search" in adres for _, adres in olaylar)
class SahteBaglamKurucu:
    """Baglam yerine gecen, eklenen cerezleri kaydeden sahte nesne."""

    def __init__(self, kayit):
        self.kayit = kayit

    def add_init_script(self, js):
        pass

    def add_cookies(self, cerezler):
        self.kayit.extend(cerezler)


class SahteP:
    """Playwright yerine gecen sahte nesne; baglam acmayi taklit eder."""

    def __init__(self):
        self.eklenen = []
        self.chromium = self

    def launch_persistent_context(self, *fazla, **adli):
        return SahteBaglamKurucu(self.eklenen)


def _guven_kur(monkeypatch, tmp_path, cerez=None):
    monkeypatch.setattr(tarayici.guven, "DOSYA", tmp_path / "g.json")
    monkeypatch.setattr(tarayici.guven, "RED_DOSYA", tmp_path / "g.red")
    monkeypatch.setattr(tarayici.guven, "omur_dk", lambda: 60)
    if cerez:
        tarayici.guven.kaydet(cerez)


def test_guvenilen_set_onay_cerezlerinin_onune_gecer(monkeypatch, tmp_path):
    _guven_kur(monkeypatch, tmp_path, [
        {"name": "NID", "value": "x", "domain": ".google.com", "path": "/"},
    ])
    p = SahteP()
    tarayici._baglam_ac(p, True, None, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    adlar = [c["name"] for c in p.eklenen]
    assert "NID" in adlar
    assert "SOCS" not in adlar


def test_guven_yoksa_onay_cerezleri_eklenir(monkeypatch, tmp_path):
    _guven_kur(monkeypatch, tmp_path)
    p = SahteP()
    tarayici._baglam_ac(p, True, None, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    adlar = [c["name"] for c in p.eklenen]
    assert "SOCS" in adlar and "CONSENT" in adlar
