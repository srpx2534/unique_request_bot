"""serp.py ayrıştırıcı testleri.

Ağa çıkmaz; sabit HTML parçaları üzerinden sıralama, eleme ve CAPTCHA
tespiti doğrulanır. Ayrıştırıcı bozulursa not_found oranı yükselir,
bu yüzden davranış burada kilitlenir.
"""

from __future__ import annotations

from worker import serp


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