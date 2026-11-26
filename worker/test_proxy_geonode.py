"""Geonode kullanici adi: il slug'i temizlenir (88)."""

from __future__ import annotations

from worker import proxy


def test_il_slug_temizlenir() -> None:
    """Bosluk ve buyuk harf kullanici adini bozmaz."""
    dize = proxy._geonode("geo.geonode.io:9000", "kullanici", "sifre", "tr",
                          "Afyon Karahisar", "abc12345")
    assert "-city-afyonkarahisar" in dize
    assert " " not in dize


def test_bos_slug_il_eklemez() -> None:
    """Slug bossa city hedeflemesi yazilmaz."""
    dize = proxy._geonode("geo.geonode.io:9000", "kullanici", "sifre", "tr",
                          "", "abc12345")
    assert "-city-" not in dize
    assert "-country-tr" in dize