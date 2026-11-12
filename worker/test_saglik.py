"""saglik.py eşik testleri.

Ağa ve veritabanına çıkmaz; oran hesabı ile eşik kararının doğruluğu
doğrulanır. Eşik yanlış çalışırsa sağlayıcı erken tükenir ya da hiç
karantinaya girmez.
"""

from __future__ import annotations

from worker import saglik


def test_oran_hesabi() -> None:
    """Oran yüzde olarak hesaplanır."""
    assert saglik.oran_hesapla(3, 10) == 30.0


def test_sifir_toplamda_oran_sifir() -> None:
    """Toplam yoksa oran sıfırdır."""
    assert saglik.oran_hesapla(0, 0) == 0.0


def test_az_ornekte_esik_asilmaz() -> None:
    """Örnek sayısı yetersizken yüksek oran bile tüketmez."""
    assert saglik.esik_asildi_mi(80.0, 4, saglik.GEO_ESIK) is False


def test_ornek_yeterli_ve_oran_yuksekse_asilir() -> None:
    """Örnek yeterliyse ve oran eşiği geçtiyse tüketim uygulanır."""
    assert saglik.esik_asildi_mi(40.0, 20, saglik.GEO_ESIK) is True


def test_esitlikte_asilmaz() -> None:
    """Oran eşiğe eşitse tüketim uygulanmaz."""
    assert saglik.esik_asildi_mi(35.0, 20, saglik.GEO_ESIK) is False

def test_esikte_karantina_karari() -> None:
    """Eşik aşıldığında karantina kararı verilir."""
    assert saglik.karantina_karari(25.0, "active", False) == "karantina"


def test_esik_altinda_karar_yok() -> None:
    """Eşik altında karar çıkmaz."""
    assert saglik.karantina_karari(10.0, "active", False) == "yok"


def test_sure_dolunca_acilir() -> None:
    """Karantinadaki sağlayıcı süre dolunca açılır."""
    assert saglik.karantina_karari(30.0, "quarantine", True) == "ac"


def test_sure_dolmadan_acilmaz() -> None:
    """Süre dolmadan karantina kalkmaz."""
    assert saglik.karantina_karari(30.0, "quarantine", False) == "yok"