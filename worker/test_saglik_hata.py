"""saglik_db ardisik hata sayaci testleri.

Veritabanina cikmaz; esik davranisi sahte baglantiyla sinanir.
"""

from __future__ import annotations

from worker import saglik_db


def _hazirla(monkeypatch, sayac: int, durum: str = "active"):
    kayit: dict = {"sql": [], "uyari": []}

    class Imlec:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql, parametre=None):
            kayit["sql"].append(sql)

        def fetchone(self):
            return (sayac, durum)

    class Baglanti:
        def cursor(self):
            return Imlec()

        def close(self):
            pass

    monkeypatch.setattr(saglik_db, "_baglan", lambda: Baglanti())
    monkeypatch.setattr(saglik_db, "uyari", lambda *a, **k: kayit["uyari"].append(a))
    return kayit


def test_hata_isle_esikte_kapatir(monkeypatch) -> None:
    kayit = _hazirla(monkeypatch, saglik_db.HATA_ESIGI)

    saglik_db.hata_isle(7)

    assert any("disabled" in s for s in kayit["sql"])
    assert kayit["uyari"] and kayit["uyari"][0][0] == "provider_down"


def test_hata_isle_esik_altinda_kapatmaz(monkeypatch) -> None:
    kayit = _hazirla(monkeypatch, saglik_db.HATA_ESIGI - 1)

    saglik_db.hata_isle(7)

    assert not any("disabled" in s for s in kayit["sql"])
    assert kayit["uyari"] == []


def test_hata_isle_zaten_kapaliysa_uyarmaz(monkeypatch) -> None:
    kayit = _hazirla(monkeypatch, saglik_db.HATA_ESIGI, durum="disabled")

    saglik_db.hata_isle(7)

    assert kayit["uyari"] == []


def test_hata_sifirla_sayaci_sifirlar(monkeypatch) -> None:
    kayit = _hazirla(monkeypatch, 2)

    saglik_db.hata_sifirla(7)

    assert any("hata_sayac = 0" in s for s in kayit["sql"])