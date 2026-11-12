"""proxy.py dizesi testleri.

Ağa çıkmaz; kullanıcı adının hedefleme ve oturum parametrelerini doğru
taşıdığı, kimlik yokken None döndüğü doğrulanır.
"""

from __future__ import annotations

from worker import proxy


def test_kimlik_yoksa_none(monkeypatch) -> None:
    """Kimlik bilgisi boşsa proxy üretilmez, hat doğrudan bağlantıya düşer."""
    monkeypatch.setenv("DECODO_USER", "")
    monkeypatch.setenv("DECODO_PASS", "")
    assert proxy.proxy_uret() is None


def test_kullanici_adi_ulke_ve_oturum_tasir(monkeypatch) -> None:
    """Kullanıcı adı ülke ve oturum parametrelerini içerir."""
    monkeypatch.setenv("DECODO_USER", "deneme")
    monkeypatch.setenv("DECODO_PASS", "gizli")
    adres = proxy.proxy_uret()
    assert adres is not None
    assert "user-deneme-country-tr" in adres
    assert "-session-" in adres
    assert "@" in adres


def test_geo_slug_eklenir(monkeypatch) -> None:
    """İl slug'ı kullanıcı adına city parametresi olarak eklenir."""
    monkeypatch.setenv("DECODO_USER", "deneme")
    monkeypatch.setenv("DECODO_PASS", "gizli")
    adres = proxy.proxy_uret(geo_slug="istanbul")
    assert adres is not None
    assert "-city-istanbul-" in adres


def test_oturum_verilirse_kullanilir(monkeypatch) -> None:
    """Verilen oturum kimliği aynen geçer."""
    monkeypatch.setenv("DECODO_USER", "deneme")
    monkeypatch.setenv("DECODO_PASS", "gizli")
    adres = proxy.proxy_uret(oturum="abc123")
    assert adres is not None
    assert "-session-abc123:" in adres


def test_maskele_sifreyi_gizler() -> None:
    """Maskeleme şifreyi yıldızlar, kullanıcı adını korur."""
    gizli = proxy.maskele("http://kullanici:sifre@host:10001")
    assert "sifre" not in gizli
    assert "kullanici" in gizli