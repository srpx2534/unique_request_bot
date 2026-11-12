"""proxy.py biçimlendirme testleri.

Ağa çıkmaz; kullanıcı adının ülke, il ve oturum parametrelerini doğru
sırada taşıdığı, şifrenin maskelendiği doğrulanır.
"""

from __future__ import annotations

from worker import proxy


def test_dize_ulke_ve_oturum_tasir() -> None:
    """Dize ülke ve oturum parametrelerini içerir."""
    adres = proxy.dize("host:10001", "deneme", "gizli", oturum="abc123")
    assert adres == "http://user-deneme-country-tr-session-abc123:gizli@host:10001"


def test_dize_il_slug_ekler() -> None:
    """İl slug'ı city parametresi olarak eklenir."""
    adres = proxy.dize("host:10001", "deneme", "gizli", geo_slug="istanbul")
    assert "-city-istanbul-" in adres


def test_dize_oturum_verilmezse_uretir() -> None:
    """Oturum verilmezse rastgele üretilir, dize yine kurulur."""
    adres = proxy.dize("host:10001", "deneme", "gizli")
    assert "-session-" in adres
    assert adres.count("-session-") == 1


def test_maskele_sifreyi_gizler() -> None:
    """Maskeleme şifreyi yıldızlar, kullanıcı adını korur."""
    gizli = proxy.maskele("http://kullanici:sifre@host:10001")
    assert "sifre" not in gizli
    assert "kullanici" in gizli


def test_maskele_none() -> None:
    """Proxy yoksa okunur bir metin döner."""
    assert proxy.maskele(None) == "(yok)"