"""Isinma modulu testleri."""

import random

import pytest

from worker import isinma


class SahteSayfa:
    """Playwright sayfasi yerine gecen sahte nesne."""

    def __init__(self, patlat=()):
        self.gidilen = []
        self.beklenen = []
        self.patlat = set(patlat)

    def goto(self, adres, **fazla):
        if adres in self.patlat:
            raise RuntimeError("gitmedi")
        self.gidilen.append(adres)

    def wait_for_timeout(self, ms):
        self.beklenen.append(ms)


class SahteOturum:
    """curl_cffi oturumu yerine gecen sahte nesne."""

    def __init__(self, patlat=()):
        self.gidilen = []
        self.patlat = set(patlat)

    def get(self, adres, **fazla):
        if adres in self.patlat:
            raise RuntimeError("ag hatasi")
        self.gidilen.append(adres)
        return object()


@pytest.fixture
def ayar_kur(monkeypatch):
    """ayar_db.oku yerine sabit deger donduren kurucu."""

    def kur(**deger):
        def sahte(anahtar, varsayilan=""):
            return str(deger.get(anahtar, varsayilan))

        monkeypatch.setattr(isinma.ayar_db, "oku", sahte)

    return kur


def test_kapaliyken_atlanir(ayar_kur):
    ayar_kur(isinma_acik="0")
    assert isinma.tarayicida(SahteSayfa())["result"] == "atlandi"


def test_sayfa_sayisi_sinirlanir(ayar_kur):
    ayar_kur(isinma_sayfa="99")
    assert isinma.sayfa_sayisi() == isinma.AZAMI_SAYFA
    ayar_kur(isinma_sayfa="0")
    assert isinma.sayfa_sayisi() == 1


def test_sayfa_sec_benzersiz_ve_google_disi():
    secilen = isinma.sayfa_sec(random.Random(7))
    assert len(secilen) == len(set(secilen))
    assert all("google" not in adres for adres in secilen)


def test_bekleme_araligi_bozuksa_varsayilana_doner(ayar_kur):
    ayar_kur(isinma_bekleme_min="abc", isinma_bekleme_max="xyz")
    assert isinma.bekleme() == isinma.VARSAYILAN_BEKLEME_MS


def test_tarayicida_sayfalari_acar(ayar_kur):
    ayar_kur(isinma_sayfa="2")
    sayfa = SahteSayfa()
    sonuc = isinma.tarayicida(sayfa, random.Random(1), aralik=(1_000, 1_000))
    assert sonuc["result"] == "ok"
    assert sonuc["sayfa"] == 2
    assert len(sayfa.gidilen) == 2
    assert sayfa.beklenen == [1_000, 1_000]


def test_tarayicida_hata_veren_sayfayi_atlar(ayar_kur, monkeypatch):
    ayar_kur(isinma_sayfa="3")
    secili = list(isinma.SAYFALAR[:3])
    monkeypatch.setattr(isinma, "sayfa_sec", lambda rastgele=None: list(secili))
    sayfa = SahteSayfa(patlat=set(secili))
    sonuc = isinma.tarayicida(sayfa, random.Random(2), aralik=(1_000, 1_000))
    assert sonuc["result"] == "error"
    assert sonuc["sayfa"] == 0


def test_http_basarili(ayar_kur):
    ayar_kur(isinma_sayfa="1")
    oturum = SahteOturum()
    sonuc = isinma.http(oturum, random.Random(3), aralik=(1_000, 1_000))
    assert sonuc["result"] == "ok"
    assert sonuc["sayfa"] == 1


def test_http_hatali_sayfayi_atlar(ayar_kur):
    ayar_kur(isinma_sayfa="5")
    oturum = SahteOturum(patlat=set(isinma.SAYFALAR))
    sonuc = isinma.http(oturum, random.Random(4), aralik=(1_000, 1_000))
    assert sonuc["result"] == "error"