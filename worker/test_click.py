"""Tiklama, dwell ve pogo testleri.

Aga cikmaz: oturum ve uyku taklit edilir. Dwell yalnizca basarili yanitta
uygulanmali, Referer her iki adimda da tasinmali, verilen oturum
kapatilmamalidir.
"""

from __future__ import annotations

import pytest

from worker import click


class SahteYanit:
    """Sabit kodlu yanit."""

    def __init__(self, kod: int = 200) -> None:
        self.status_code = kod
        self.content = b"0123456789"


class SahteOturum:
    """Oturum yerine gecen sahte nesne; cagrilari kaydeder."""

    def __init__(self, kod: int = 200, **_k: object) -> None:
        self.kod = kod
        self.cagrilar: list[tuple[str, dict]] = []
        self.kapandi = False

    def get(self, url: str, **kw: object) -> SahteYanit:
        self.cagrilar.append((url, kw))
        return SahteYanit(self.kod)

    def close(self) -> None:
        self.kapandi = True


@pytest.fixture()
def ortam(monkeypatch: pytest.MonkeyPatch) -> list:
    """Uyku ve rastgele secimi kaydeder, oturumu taklit eder."""
    kayit: list = []
    monkeypatch.setattr(click.time, "sleep", lambda s: kayit.append(("sleep", s)))
    monkeypatch.setattr(
        click.random, "uniform",
        lambda a, b: (kayit.append(("uniform", a, b)), (a + b) / 2)[1],
    )
    monkeypatch.setattr(click.requests, "Session", SahteOturum)
    return kayit


def test_dwell_uygulanir(ortam: list) -> None:
    """Basarili yanitta dwell uygulanir ve sinirlar §9'dan gelir."""
    sonuc = click.tikla("https://hedef.test", referer="https://google.com/search?q=x")
    assert sonuc["result"] == "ok"
    assert sonuc["dwell_ms"] > 0
    assert ("uniform", click.DWELL_MIN, click.DWELL_MAX) in ortam


def test_dwell_kapaliyken_uyumaz(ortam: list) -> None:
    """dwell=False iken uyunmaz."""
    click.tikla("https://hedef.test", dwell=False)
    assert not [k for k in ortam if k[0] == "sleep"]


def test_4xx_dwell_uygulanmaz(ortam: list, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hata kodunda beklemek anlamsiz."""
    monkeypatch.setattr(click.requests, "Session", lambda **_: SahteOturum(404))
    sonuc = click.tikla("https://hedef.test")
    assert sonuc["result"] == "error"
    assert sonuc["dwell_ms"] == 0


def test_referer_origine_indirgenir(ortam: list) -> None:
    """Gercek trafikte Referer origin'den oteye gitmez."""
    oturum = SahteOturum()
    click.tikla("https://hedef.test", referer="https://www.google.com/search?q=x", oturum=oturum)
    basliklar = oturum.cagrilar[0][1]["headers"]
    assert basliklar["Referer"] == "https://www.google.com/"


def test_pogo_refereri_hedef_origin(ortam: list) -> None:
    """Geri donuste Referer, terk edilen sayfanin origin'i olur."""
    oturum = SahteOturum()
    click.pogo("https://www.google.com/search?q=x", "x", oturum=oturum,
               hedef_url="https://hedef.test/sayfa")
    assert oturum.cagrilar[0][1]["headers"]["Referer"] == "https://hedef.test/"


def test_verilen_oturum_kapatilmaz(ortam: list) -> None:
    """Cagiran oturumu kendi kapatir (C10)."""
    oturum = SahteOturum()
    click.tikla("https://hedef.test", oturum=oturum)
    assert oturum.kapandi is False


def test_kendi_oturumunu_kapatir(ortam: list) -> None:
    """Oturum verilmezse acilan oturum kapatilir."""
    sonuc = click.tikla("https://hedef.test")
    assert sonuc["result"] == "ok"


def test_pogo_bekleme_siniri(ortam: list) -> None:
    """Pogo 3-6 saniye araliginda bekler ve Referer tasir."""
    sonuc = click.pogo("https://google.com/search?q=x", "x")
    assert sonuc["result"] == "ok"
    assert ("uniform", click.POGO_MIN, click.POGO_MAX) in ortam
    assert 3000 <= sonuc["bekleme_ms"] <= 6000


def test_pogo_adres_yoksa_kurar(ortam: list, monkeypatch: pytest.MonkeyPatch) -> None:
    """SERP adresi bossa sorgudan adres kurulur."""
    oturum = SahteOturum()
    click.pogo("", "deneme kelime", oturum=oturum)
    assert "q=deneme" in oturum.cagrilar[0][0]


def test_proxy_sozlugu() -> None:
    """Proxy yoksa None, varsa http/https anahtarlari doner."""
    assert click._proxy_sozlugu(None) is None
    assert click._proxy_sozlugu("http://a:b@h:1") == {
        "https": "http://a:b@h:1", "http": "http://a:b@h:1"
    }

def test_ga_beacon_basariyla_gonderilir(ortam: list, monkeypatch: pytest.MonkeyPatch) -> None:
    """Basarili tikta page_view Google'a iletilir."""
    cagri: list = []
    monkeypatch.setattr(
        click.ga_beacon, "gonder",
        lambda *a: (cagri.append(a), {"result": "ok", "mesaj": ""})[1],
    )
    sonuc = click.tikla("https://hedef.test/x", referer="https://www.google.com/", profil_id=5)
    assert sonuc["ga"] == "ok"
    assert cagri[0][0] == "hedef.test"
    assert cagri[0][4] == 5


def test_ga_4xx_te_gonderilmez(ortam: list, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sayfa acilmadiysa beacon da atilmaz."""
    cagri: list = []
    monkeypatch.setattr(click.requests, "Session", lambda **_: SahteOturum(404))
    monkeypatch.setattr(
        click.ga_beacon, "gonder",
        lambda *a: (cagri.append(a), {"result": "ok", "mesaj": ""})[1],
    )
    sonuc = click.tikla("https://hedef.test")
    assert sonuc["ga"] is None
    assert not cagri
