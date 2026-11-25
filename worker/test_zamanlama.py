"""Saat agirligi testleri."""

from worker import zamanlama


def test_aksam_tepesi_geceden_yuksek():
    assert zamanlama.agirlik(21) > zamanlama.agirlik(3)
    assert zamanlama.agirlik(21) == 1.0


def test_uygunluk_esige_bakar():
    assert zamanlama.uygun_mu(0.45, 21) is True
    assert zamanlama.uygun_mu(0.45, 4) is False


def test_olcekleme_en_az_bir():
    assert zamanlama.olcekle(100, 21) == 100
    assert zamanlama.olcekle(100, 4) == 20
    assert zamanlama.olcekle(1, 4) == 1


def test_bilinmeyen_saat_varsayilan():
    assert zamanlama.agirlik(30) == zamanlama.agirlik(6)