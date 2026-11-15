"""Ayar onbellegi testleri.

Veritabani taklit edilir; onbellek, .env yedegi ve varsayilan zinciri
dogrulanir (C43).
"""

from __future__ import annotations

import pytest

from worker import ayar, ayar_db


class Imlec:
    """Sabit deger donduren imlec."""

    def __init__(self, deger: str | None) -> None:
        self.deger = deger

    def __enter__(self) -> "Imlec":
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def execute(self, *_a: object, **_k: object) -> None:
        return None

    def fetchone(self) -> tuple[str] | None:
        return None if self.deger is None else (self.deger,)


class Baglanti:
    """Baglanti yerine gecen sahte nesne."""

    def __init__(self, deger: str | None) -> None:
        self.deger = deger
        self.kapandi = False

    def cursor(self) -> Imlec:
        return Imlec(self.deger)

    def close(self) -> None:
        self.kapandi = True


@pytest.fixture(autouse=True)
def temiz() -> None:
    """Her testte onbellek bosaltilir."""
    ayar_db.temizle()


def test_tablodan_okur(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deger tablodan gelir."""
    monkeypatch.setattr(ayar_db, "_baglan", lambda: Baglanti("15"))
    assert ayar_db.oku("esik_captcha", "20") == "15"


def test_onbellek_ikinci_sorguyu_keser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Onbellek gecerliyken tabloya tekrar gidilmez."""
    sayac = {"n": 0}

    def baglan() -> Baglanti:
        sayac["n"] += 1
        return Baglanti("15")

    monkeypatch.setattr(ayar_db, "_baglan", baglan)
    ayar_db.oku("esik_captcha", "20")
    ayar_db.oku("esik_captcha", "20")
    assert sayac["n"] == 1


def test_tablo_hatasinda_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tablo okunamazsa .env devreye girer."""
    def patlat() -> None:
        raise RuntimeError("baglanti yok")

    monkeypatch.setattr(ayar_db, "_baglan", patlat)
    monkeypatch.setattr(ayar, "oku", lambda a, v="": "env-degeri")
    assert ayar_db.oku("esik_captcha", "20") == "env-degeri"


def test_env_de_yoksa_varsayilan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hicbir kaynak yoksa varsayilan doner."""
    def patlat() -> None:
        raise RuntimeError("baglanti yok")

    monkeypatch.setattr(ayar_db, "_baglan", patlat)
    monkeypatch.setattr(ayar, "oku", lambda a, v="": v)
    assert ayar_db.oku("esik_captcha", "20") == "20"


def test_bos_deger_env_e_duser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tablodaki bos deger .env okumasina birakilir."""
    monkeypatch.setattr(ayar_db, "_baglan", lambda: Baglanti(""))
    monkeypatch.setattr(ayar, "oku", lambda a, v="": "env-degeri")
    assert ayar_db.oku("esik_captcha", "20") == "env-degeri"


def test_baglanti_kapatilir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Okuma sonrasi baglanti kapatilir."""
    tutulan: list[Baglanti] = []

    def baglan() -> Baglanti:
        b = Baglanti("5")
        tutulan.append(b)
        return b

    monkeypatch.setattr(ayar_db, "_baglan", baglan)
    ayar_db.oku("esik_captcha", "20")
    assert tutulan[0].kapandi is True