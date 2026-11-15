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
def test_bicim_bul_tanir() -> None:
    """Sağlayıcı adı biçime çözülür, boşluklu yazım da yakalanır."""
    assert proxy.bicim_bul("Bright Data") == "brightdata"
    assert proxy.bicim_bul("SOAX") == "soax"
    assert proxy.bicim_bul("Decodo residential") == "decodo"


def test_bicim_bul_tanınmayan_decodo() -> None:
    """Tanınmayan ad Decodo sayılır."""
    assert proxy.bicim_bul("bilinmeyen saglayici") == "decodo"
    assert proxy.bicim_bul(None) == "decodo"


def test_yabanci_ulke_yazilir() -> None:
    """Yabancı sağlayıcıda kendi ülkesi yazılır, TR zorlanmaz."""
    adres = proxy.dize("host:10001", "deneme", "gizli", ulke="US", oturum="abc")
    assert "-country-us-" in adres
    assert "-country-tr-" not in adres


def test_ulke_none_parametre_yazilmaz() -> None:
    """Ülke bilinmiyorsa country parametresi hiç yazılmaz."""
    adres = proxy.dize("host:10001", "deneme", "gizli", ulke=None, oturum="abc")
    assert "-country-" not in adres


def test_soax_bicimi_onek_siz() -> None:
    """SOAX paket adıyla çalışır, user- öneki almaz."""
    adres = proxy.dize("host:1", "paket", "gizli", ulke="TR", oturum="abc", bicim="soax")
    assert adres == "http://paket-country-tr-session-abc:gizli@host:1"


def test_brightdata_bicimi_musteri_onekli() -> None:
    """Bright Data brd-customer- öneki ister."""
    adres = proxy.dize("host:1", "musteri", "gizli", oturum="abc", bicim="brightdata")
    assert adres.startswith("http://brd-customer-musteri")