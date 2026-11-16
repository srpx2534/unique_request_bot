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


def test_webshare_bicimi_duz_kullanici() -> None:
    """Webshare hedefleme parametresi kullanmaz, kullanıcı adı düz yazılır."""
    adres = proxy.dize("host:1", "kullanici", "gizli", ulke="TR", oturum="abc", bicim="webshare")
    assert adres == "http://kullanici:gizli@host:1"


def test_bicim_bul_webshare() -> None:
    """Webshare adı kendi biçimine çözülür."""
    assert proxy.bicim_bul("Webshare") == "webshare"


def test_brightdata_bicimi_musteri_onekli() -> None:
    """Bright Data brd-customer- öneki ister."""
    adres = proxy.dize("host:1", "musteri", "gizli", oturum="abc", bicim="brightdata")


def test_geonode_kullanici_adi_bicimi() -> None:
    """Geonode `user-` oneki almaz, ulke tekrarlanmaz, il eklenir."""
    d = proxy.dize("proxy.geonode.io:9000", "geonode_abc-country-tr", "p", "TR",
                   "istanbul", oturum="aabb", bicim=proxy.bicim_bul("Geonode"))
    assert d == "http://geonode_abc-country-tr-city-istanbul-type-residential-session-aabb:p@proxy.geonode.io:10000"


def test_gateway_sema_ve_kuyruk_ayraci_atilir() -> None:
    """Gateway`e yazilmis sema ve sondaki iki nokta dizeye ikinci kez girmez."""
    d = proxy.dize("http://proxy.geonode.io:9000:", "geonode_abc-country-tr", "p",
                   "TR", None, oturum="aabb", bicim="geonode")
    assert d.startswith("http://geonode_abc-country-tr-type-residential-session-aabb:p@proxy.geonode.io:10000")
    assert d.count("http://") == 1
    assert not d.endswith(":")


def test_ulke_kullanici_adinda_varsa_tekrarlanmaz() -> None:
    """`-country-tr` iki kez yazilmaz."""
    d = proxy.dize("h:1", "kullanici-country-tr", "p", "TR", None, oturum="a", bicim="decodo")
    assert d.count("-country-tr") == 1


def test_cekirdek() -> None:
    """Sema, bolu ve sondaki iki nokta temizlenir."""
    assert proxy.cekirdek("http://a:1:") == "a:1"
    assert proxy.cekirdek("https://a:1/") == "a:1"
    assert proxy.cekirdek("a:1") == "a:1"


def test_geonode_onek_siz_ve_tip_yazar() -> None:
    """Geonode user- oneki almaz, tip parametresi yazar."""
    adres = proxy.dize("proxy.geonode.io:9000", "geonode_abc", "g", oturum="abc12345", bicim="geonode")
    assert adres.startswith("http://geonode_abc-country-tr-type-residential-session-abc12345:g@")
    assert "user-" not in adres


def test_geonode_oturum_sticky_porta_gecer() -> None:
    """Oturum eki sticky porta kaydirilir; rotasyonlu portta 403 veriyordu."""
    adres = proxy.dize("proxy.geonode.io:9000", "geonode_abc", "g", oturum="abc12345", bicim="geonode")
    assert "@proxy.geonode.io:10000" in adres


def test_geonode_sticky_port_korunur() -> None:
    """Zaten sticky olan port kaydirilmaz."""
    adres = proxy.dize("proxy.geonode.io:10000", "geonode_abc", "g", oturum="a", bicim="geonode")
    assert "@proxy.geonode.io:10000" in adres


def test_geonode_ulke_tekrari_yazilmaz() -> None:
    """Taban kullanici adi ulke tasiyorsa ikinci kez eklenmez."""
    adres = proxy.dize("h:9000", "geonode_abc-country-tr", "g", oturum="a", bicim="geonode")
    assert adres.count("-country-tr") == 1


def test_geonode_il_eklenir() -> None:
    """Il slug'i city parametresi olarak tip ve oturumun onune yazilir."""
    adres = proxy.dize("h:9000", "geonode_abc", "g", geo_slug="istanbul", oturum="a", bicim="geonode")
    assert "-city-istanbul-type-residential" in adres


def test_cekirdek_semayi_ve_artigi_atar() -> None:
    """Gecit metni host:port'a indirilir, bozuk yazim temizlenir."""
    assert proxy.cekirdek("http://proxy.geonode.io:9000:") == "proxy.geonode.io:9000"
    assert proxy.cekirdek(" proxy.geonode.io:9000/ ") == "proxy.geonode.io:9000"
    assert proxy.cekirdek(None) == ""


def test_bicim_bul_geonode() -> None:
    """Geonode adi kendi bicimine cozulur."""
    assert proxy.bicim_bul("Geonode residential") == "geonode"
