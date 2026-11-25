"""Guvenilen cerez seti testleri."""

import os
import time

import pytest

from worker import guven


@pytest.fixture(autouse=True)
def gecici_dosyalar(tmp_path, monkeypatch):
    monkeypatch.setattr(guven, "DOSYA", tmp_path / "gerez.json")
    monkeypatch.setattr(guven, "RED_DOSYA", tmp_path / "gerez.red")
    monkeypatch.setattr(guven, "omur_dk", lambda: 60)


def _cerez(ad="NID", alan=".google.com"):
    return {"name": ad, "value": "x", "domain": alan, "path": "/"}


class SahteBaglam:
    def __init__(self):
        self.eklenen = None

    def add_cookies(self, cerezler):
        self.eklenen = cerezler


class SahteOturum:
    def __init__(self):
        self.cerezler = []
        self.cookies = self

    def set(self, ad, deger, domain=None, path=None):
        self.cerezler.append((ad, domain))


def test_google_disi_cerez_atilir():
    assert guven.kaydet([_cerez(), _cerez("PHPSESSID", "site.com")]) == 1
    assert [c["name"] for c in guven.oku()] == ["NID"]


def test_kaydet_red_sayacini_sifirlar():
    guven.reddet()
    guven.kaydet([_cerez()])
    assert guven.red_sayisi() == 0


def test_bos_liste_dosya_yazmaz():
    assert guven.kaydet([]) == 0
    assert guven.oku() == []


def test_yeni_set_taze():
    guven.kaydet([_cerez()])
    assert guven.taze_mi() is True


def test_suresi_gecmis_set_bayat():
    guven.kaydet([_cerez()])
    eski = time.time() - 61 * 60
    os.utime(guven.DOSYA, (eski, eski))
    assert guven.taze_mi() is False


def test_ust_uste_red_seti_bayatlatir():
    guven.kaydet([_cerez()])
    guven.reddet()
    assert guven.taze_mi() is True
    guven.reddet()
    assert guven.taze_mi() is False


def test_bayat_set_uygulanmaz():
    baglam = SahteBaglam()
    assert guven.uygula(baglam) == 0
    assert baglam.eklenen is None


def test_taze_set_baglama_eklenir():
    guven.kaydet([_cerez()])
    baglam = SahteBaglam()
    assert guven.uygula(baglam) == 1
    assert baglam.eklenen[0]["name"] == "NID"


def test_taze_set_kavanoza_yuklenir():
    guven.kaydet([_cerez()])
    oturum = SahteOturum()
    assert guven.kavanoza(oturum) == 1
    assert oturum.cerezler[0][0] == "NID"