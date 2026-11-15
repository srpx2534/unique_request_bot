"""Kalp atisi testleri.

Ag ve zamanlayici taklit edilir; durdurma bayragi ve kaynak okuma denenir.
"""

from __future__ import annotations

import pytest

from worker import kalp


@pytest.fixture(autouse=True)
def temiz(monkeypatch: pytest.MonkeyPatch) -> None:
    """Her testte durum ve zamanlayici sifirlanir."""
    monkeypatch.setattr(kalp, "_durum", "aktif")
    monkeypatch.setattr(kalp, "_zaman", None)
    monkeypatch.setattr(kalp.threading, "Timer", lambda *a, **k: type(
        "T", (), {"daemon": True, "start": lambda self: None, "cancel": lambda self: None}
    )())


def test_duraklatildi_false() -> None:
    """Baslangicta is alinir."""
    assert kalp.duraklatildi() is False


def test_duraklatildi_true() -> None:
    """Panel durdurunca is alinmaz (C38)."""
    kalp._durum = "durduruldu"
    assert kalp.duraklatildi() is True


def test_kaynak_psutil_yoksa_sifir() -> None:
    """psutil yoksa cpu/ram sifir doner, patlamaz."""
    kalp._psutil = None
    assert kalp._kaynak() == (0.0, 0.0)


def test_ip_tanimliysa_onu_verir(monkeypatch: pytest.MonkeyPatch) -> None:
    """DUGUM_IP tanimliysa soket acilmaz."""
    monkeypatch.setattr(kalp.ayar, "oku", lambda a, v="": "10.0.0.5" if a == "DUGUM_IP" else v)
    assert kalp._ip() == "10.0.0.5"


def test_at_durum_cevabini_okur(monkeypatch: pytest.MonkeyPatch) -> None:
    """Panel 'durduruldu' derse bayrak doner."""
    class Yanit:
        def read(self) -> bytes:
            return b'{"durum":"durduruldu"}'

        def __enter__(self) -> "Yanit":
            return self

        def __exit__(self, *a: object) -> None:
            return None

    monkeypatch.setattr(kalp.urllib.request, "urlopen", lambda *a, **k: Yanit())
    kalp._at()
    assert kalp.duraklatildi() is True


def test_at_401_sessiz_kalir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Imza reddedilirse dongu kopmaz."""
    import urllib.error

    def patlat(*_a: object, **_k: object) -> None:
        raise urllib.error.HTTPError("u", 401, "yetkisiz", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(kalp.urllib.request, "urlopen", patlat)
    kalp._at()
    assert kalp.duraklatildi() is False