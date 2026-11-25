"""serp.py ayrıştırıcı testleri.

Ağa çıkmaz; sabit HTML parçaları üzerinden sıralama, eleme ve CAPTCHA
tespiti doğrulanır. Ayrıştırıcı bozulursa not_found oranı yükselir,
bu yüzden davranış burada kilitlenir.
"""

from __future__ import annotations

import pytest

from worker import serp, serp_html


def test_kok_www_atar() -> None:
    """www. öneki kökten düşer."""
    assert serp._kok("https://www.Armut.com/veteriner") == "armut.com"


def test_kok_alt_alan_adini_koke_indirger() -> None:
    """Alt alan adı ayrı sonuç sayılmaz, kök döner."""
    assert serp._kok("blog.example.com/x") == "example.com"


def test_ayikla_sirayi_korur_ve_tekrari_atar() -> None:
    """İlk görülme sırası korunur, tekrar eden host bir kez sayılır."""
    html = (
        '<a href="https://a.com/x">1</a>'
        '<a href="https://b.com/y">2</a>'
        '<a href="https://www.a.com/z">3</a>'
    )
    assert serp._sonuclari_ayikla(html) == ["a.com", "b.com"]


def test_ayikla_google_alan_adlarini_eler() -> None:
    """Google'a ait adresler sonuç sayılmaz."""
    html = '<a href="https://support.google.com/x">s</a><a href="https://a.com/">a</a>'
    assert serp._sonuclari_ayikla(html) == ["a.com"]


def test_ayikla_yonlendirme_bicimini_cozer() -> None:
    """Eski /url?q= biçimi de ayrıştırılır."""
    html = '<a href="/url?q=https://a.com/x&amp;sa=U">a</a>'
    assert serp._sonuclari_ayikla(html) == ["a.com"]


def test_captcha_yol_ile_anlasilir() -> None:
    """CAPTCHA duvarı adresten tespit edilir."""
    assert serp._captcha_mi("https://www.google.com/sorry/index?x=1", "") is True


def test_captcha_govdeden_anlasilir() -> None:
    """Gövdedeki recaptcha izi de yeter."""
    assert serp._captcha_mi("https://www.google.com/search", "recaptcha") is True


def test_temiz_serp_captcha_degil() -> None:
    """Normal sonuç sayfası CAPTCHA sayılmaz."""
    assert serp._captcha_mi("https://www.google.com/search?q=a", "<h3>a</h3>") is False


class _Yanit:
    """Sabit yanit; govde uzunlugu testten gelir."""

    status_code = 200
    url = "https://www.google.com/search?q=haber"

    def __init__(self, boy: int, on: str = "<html><title>Google Search</title>") -> None:
        self.content = on.encode("utf-8") + b"x" * boy


class _Oturum:
    def __init__(self, boy: int, on: str = "<html><title>Google Search</title>") -> None:
        self.boy = boy
        self.on = on

    def get(self, *_a, **_k):
        return _Yanit(self.boy, self.on)

    def close(self) -> None:
        pass


def test_kabuk_govde_izlenim_sayilir() -> None:
    """Sonuc baglantisi olmayan uzun kabuk govde ok sayilir, tiklama surer."""
    sonuc = serp_html.serp_getir_html("haber", oturum=_Oturum(90_000))
    assert sonuc["result"] == "ok"
    assert sonuc["position"] is None
    assert "kabuk" in sonuc["mesaj"]


def test_taninmayan_kisa_govde_error() -> None:
    """Google izi tasimayan kisa govde not_found degil error sayilir."""
    sonuc = serp_html.serp_getir_html("haber", oturum=_Oturum(2_000, "<html>"))
    assert sonuc["result"] == "error"


def test_bes_baytlik_govde_error() -> None:
    """Gateway'in bes baytlik sahte govdesi basari sayilmaz."""
    sonuc = serp_html.serp_getir_html("haber", oturum=_Oturum(0, "false"))
    assert sonuc["result"] == "error"


def test_kok_iki_etiketli_uzanti_korunur() -> None:
    """com.tr uzanti kokun parcasi kalir, com.tr'ye inmez."""
    assert serp._kok("https://www.hurriyet.com.tr/x") == "hurriyet.com.tr"
    assert serp._kok("https://armut.com.tr") == "armut.com.tr"


def test_decodo_govdesi_ulke_ve_locale_tasir() -> None:
    """Decodo govdesi ulke adi ve kucuk harfli locale ister."""
    govde = serp._govde_kur("decodo", "haber", 1, "tr", "tr", None)
    assert govde["geo"] == "Turkey"
    assert govde["locale"] == "tr-tr"
    assert govde["proxy_pool"] == "premium"


def test_decodo_govdesi_uule_verilirse_ekler() -> None:
    """UULE verilirse govdeye girer."""
    govde = serp._govde_kur("decodo", "haber", 1, "tr", "tr", "abc")
    assert govde["uule"] == "abc"


def test_serper_govdesi_gl_hl_kullanir() -> None:
    """Serper ulke kodu ve dil kodu ile calisir, proxy_pool almaz."""
    govde = serp._govde_kur("serper", "haber", 1, "tr", "tr", None)
    assert govde["gl"] == "tr"
    assert govde["hl"] == "tr"
    assert "proxy_pool" not in govde

class _Tekrarli:
    """Sirayla verilen durum kodlarini doner."""

    url = "https://www.google.com/search?q=haber"

    def __init__(self, *kodlar: int) -> None:
        self.kodlar = list(kodlar)
        self.cagri = 0

    def get(self, *_a, **_k):
        kod = self.kodlar[min(self.cagri, len(self.kodlar) - 1)]
        self.cagri += 1
        yanit = _Yanit(90_000)
        yanit.status_code = kod
        return yanit

    def close(self) -> None:
        pass


def test_429_bir_kez_tekrar_denenir() -> None:
    """429 ilk denemede gelirse istek yinelenir, ikinci 200 ise ok doner."""
    oturum = _Tekrarli(429, 200)
    sonuc = serp_html.serp_getir_html("haber", oturum=oturum)
    assert sonuc["result"] == "ok"
    assert oturum.cagri == 2

@pytest.fixture(autouse=True)
def isinma_sus(monkeypatch):
    """Isinma ve cerez seti aga cikmasin; sayac arama isteklerini saysin."""
    monkeypatch.setattr(serp_html.isinma, "http", lambda *a, **k: {"result": "atlandi"})
    monkeypatch.setattr(serp_html.guven, "kavanoza", lambda *a: 0)
