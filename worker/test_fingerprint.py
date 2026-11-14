"""Parmak izi secimi: cerez ailesi, mobil pencere ve tekrar onleme."""

from __future__ import annotations

from worker import fingerprint


def test_cerez_ailesi_chrome_havuzundan_secer() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(aile="chrome") in fingerprint.CHROME


def test_bilinmeyen_aile_chrome_havuzuna_duser() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(aile="bilinmiyor") in fingerprint.CHROME


def test_firefox_ailesi_firefox_secer() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(aile="firefox") in fingerprint.FIREFOX


def test_safari_ailesi_safari_secer() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(aile="safari") in fingerprint.SAFARI


def test_cerezsiz_havuz_tum_alleleri_icerir() -> None:
    secilen = {fingerprint.profil_sec() for _ in range(600)}
    izinli = set(fingerprint.CHROME + fingerprint.FIREFOX + fingerprint.SAFARI + fingerprint.EDGE)
    assert secilen <= izinli
    assert "safari270" in secilen or "safari260" in secilen
    assert "firefox155" in secilen or "firefox154" in secilen or "firefox153" in secilen


def test_cerezli_havuzda_safari_firefox_edge_yok() -> None:
    secilen = {fingerprint.profil_sec(aile="chrome") for _ in range(600)}
    assert secilen <= set(fingerprint.CHROME)


def test_mobil_pencere_android_secer() -> None:
    assert fingerprint.profil_sec(mobil=True) == "chrome131_android"


def test_onceki_profil_tekrarlanmaz() -> None:
    for _ in range(50):
        assert fingerprint.profil_sec(haric="chrome152", aile="chrome") != "chrome152"


def test_eski_chrome_profili_havuzda_yok() -> None:
    assert "chrome110" not in fingerprint.PROFILLER
    assert "chrome124" not in fingerprint.PROFILLER
    assert "chrome152" in fingerprint.CHROME


def test_her_profilin_ua_degeri_var() -> None:
    for p in fingerprint.PROFILLER:
        assert fingerprint.ua(p).startswith("Mozilla/5.0")