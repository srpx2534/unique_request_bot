"""Oturum sürekliliği testleri.

Ağa çıkmaz. Üç adımın da (izlenim, tıklama, pogo) dışarıdan verilen aynı
oturumu kullandığı ve yeni oturum açmadığı doğrulanır. Bu kopukluk geri
gelirse Google istemciyi ayrı kişi sayar.
"""

from __future__ import annotations

import pytest

from worker import click, serp


class SahteYanit:
    """curl_cffi yanıtını taklit eder."""

    def __init__(self, html: str = "") -> None:
        self.status_code = 200
        self.content = html.encode("utf-8")
        self.url = "https://www.google.com/search?q=a"


class SahteOturum:
    """Çağrıları kaydeden sahte oturum."""

    def __init__(self, html: str = "") -> None:
        self.cagrilar: list[str] = []
        self._html = html
        self.kapandi = False

    def get(self, adres: str, **_kw) -> SahteYanit:
        """İsteği kaydeder ve sahte yanıt döndürür."""
        self.cagrilar.append(adres)
        return SahteYanit(self._html)

    def close(self) -> None:
        """Kapanışı işaretler."""
        self.kapandi = True


@pytest.fixture(autouse=True)
def yeni_oturum_yasak(monkeypatch):
    """Testlerde yeni oturum açılmasını yasaklar."""

    def patlat(*_a, **_k):
        raise AssertionError("yeni oturum açıldı, oysa dışarıdan verilmişti")

    monkeypatch.setattr(click.requests, "Session", patlat)
    monkeypatch.setattr(serp.requests, "Session", patlat)


def test_izlenim_verilen_oturumu_kullanir() -> None:
    """İzlenim adımı dışarıdan verilen oturumdan geçer."""
    oturum = SahteOturum('<a href="https://a.com/">a</a>')
    sonuc = serp.serp_getir_html("a", oturum=oturum)
    assert oturum.cagrilar, "oturum hiç kullanılmadı"
    assert sonuc["result"] == "ok"


def test_tiklama_verilen_oturumu_kullanir() -> None:
    """Tıklama dışarıdan verilen oturumdan geçer."""
    oturum = SahteOturum()
    sonuc = click.tikla("https://a.com/", oturum=oturum, dwell=False)
    assert oturum.cagrilar == ["https://a.com/"]
    assert sonuc["result"] == "ok"


def test_pogo_verilen_oturumu_kullanir(monkeypatch) -> None:
    """Pogo dışarıdan verilen oturumdan geçer, bekleme sıfırlanır."""
    monkeypatch.setattr(click, "POGO_MIN", 0)
    monkeypatch.setattr(click, "POGO_MAX", 0)
    oturum = SahteOturum()
    sonuc = click.pogo("https://www.google.com/search?q=a", "a", oturum=oturum)
    assert oturum.cagrilar
    assert sonuc["result"] == "ok"


def test_verilen_oturum_kapatilmaz() -> None:
    """Oturumu çağıran açtığı için adımlar onu kapatmaz."""
    oturum = SahteOturum()
    click.tikla("https://a.com/", oturum=oturum, dwell=False)
    assert oturum.kapandi is False