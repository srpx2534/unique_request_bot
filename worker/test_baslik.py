"""Baslik secimi testleri.

Parmak izi basliklarini ezmemek kuraldir (C11): Accept profilden gelir,
Accept-Language ve Sec-Fetch-* bilincli olarak bizden gider.
"""

from __future__ import annotations

from worker import click, serp


def test_serp_accept_ezmez() -> None:
    """SERP istegi Accept basligini profilin birakir."""
    assert "Accept" not in serp.BASLIKLAR
    assert "Accept-Language" in serp.BASLIKLAR


def test_click_accept_ezmez() -> None:
    """Tiklama da Accept basligini ezmez."""
    assert "Accept" not in click.TIKLAMA_BASLIKLARI
    assert "Accept-Language" in click.TIKLAMA_BASLIKLARI


def test_click_gezinti_basliklari_dolu() -> None:
    """Gezinti sinyalleri korunur: Google tiklamayi bunlardan anlar."""
    for anahtar in ("Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site",
                    "Sec-Fetch-User", "Upgrade-Insecure-Requests"):
        assert anahtar in click.TIKLAMA_BASLIKLARI


def test_dwell_sinirlari_sozlesmeye_uygun() -> None:
    """Dwell 5-12 saniye araliginda (sozlesme §9)."""
    assert (click.DWELL_MIN, click.DWELL_MAX) == (5, 12)


def test_pogo_sinirlari_sozlesmeye_uygun() -> None:
    """Pogo 3-6 saniye sonra (sozlesme §9)."""
    assert (click.POGO_MIN, click.POGO_MAX) == (3, 6)