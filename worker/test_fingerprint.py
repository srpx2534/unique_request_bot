"""Parmak izi secimi: cerez ailesi, mobil pencere ve tekrar onleme."""

from __future__ import annotations

from worker import fingerprint


def test_cerez_ailesi_chrome_havuzundan_secer() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(aile="chrome") in fingerprint.CHROME


def test_bilinmeyen_aile_chrome_havuzuna_duser() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(aile="bilinmiyor") in fingerprint.CHROME


def test_safari_ailesi_safari_secer() -> None:
    assert fingerprint.profil_sec(aile="safari") == "safari17_0"


def test_cerezsiz_havuz_safari_ve_edge_icerir() -> None:
    secilen = {fingerprint.profil_sec() for _ in range(400)}
    assert secilen <= set(fingerprint.CHROME + fingerprint.SAFARI + fingerprint.EDGE)
    assert "safari17_0" in secilen or "edge101" in secilen


def test_cerezli_havuzda_safari_ve_edge_yok() -> None:
    secilen = {fingerprint.profil_sec(aile="chrome") for _ in range(400)}
    assert "safari17_0" not in secilen
    assert "edge101" not in secilen


def test_mobil_pencere_android_secer() -> None:
    assert fingerprint.profil_sec(mobil=True) == "chrome99_android"


def test_onceki_profil_tekrarlanmaz() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(haric="chrome124", aile="chrome") != "chrome124"


def test_eski_chrome_profili_havuzda_yok() -> None:
    assert "chrome110" not in fingerprint.PROFILLER
    assert "chrome124" in fingerprint.CHROME