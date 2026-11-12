"""havuz.py oran ve seçim testleri.

Ağa ve veritabanına çıkmaz; oran normalizasyonu ile tür kurası doğrulanır.
Dağılım bozulursa mobil oranı panelden ne girilirse girsin tutmaz.
"""

from __future__ import annotations

from worker import havuz


def test_hepsi_sifirsa_residential_yuz() -> None:
    """Hiç oran girilmemişse residential %100 kabul edilir."""
    assert havuz.oranlari_normalize({}) == {
        "oran_residential": 100, "oran_mobil": 0, "oran_datacenter": 0
    }


def test_toplam_yuze_tamamlanir() -> None:
    """Toplam 100 değilse en büyük kalana fark yazılarak 100'e tamamlanır."""
    sonuc = havuz.oranlari_normalize(
        {"oran_residential": 60, "oran_mobil": 60, "oran_datacenter": 0}
    )
    assert sum(sonuc.values()) == 100
    assert sonuc["oran_residential"] == sonuc["oran_mobil"] == 50


def test_negatif_deger_sifira_kirpilir() -> None:
    """Negatif oran sıfır sayılır."""
    sonuc = havuz.oranlari_normalize(
        {"oran_residential": 100, "oran_mobil": -20, "oran_datacenter": 0}
    )
    assert sonuc["oran_mobil"] == 0


def test_mobil_sifirsa_hic_sec_mez() -> None:
    """Mobil oranı sıfırken kura mobile düşmez."""
    oranlar = {"oran_residential": 50, "oran_mobil": 50, "oran_datacenter": 0}
    for yuzde in range(0, 100, 5):
        assert havuz.tur_sec(oranlar, mobil_acik=False, rastgele=yuzde) == "residential"


def test_mobil_pencere_acikken_secilebilir() -> None:
    """Mobil açıkken yüksek dilim mobile düşer."""
    oranlar = {"oran_residential": 20, "oran_mobil": 80, "oran_datacenter": 0}
    assert havuz.tur_sec(oranlar, mobil_acik=True, rastgele=90) == "mobile"


def test_hic_uygun_tur_yoksa_none() -> None:
    """Tüm oranlar sıfırsa tür seçilemez."""
    sifir = {"oran_residential": 0, "oran_mobil": 0, "oran_datacenter": 0}
    assert havuz.tur_sec(sifir, mobil_acik=True) is None