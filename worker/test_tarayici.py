"""Tarayici hattinda isinma sirasi.

Isinma aramadan once ve bir kez kosmali; kapaliyken ya da hata verdiginde
arama yine de yapilmali. Ag yok, sahte sayfa kullanilir.
"""

from __future__ import annotations

import pytest

from worker import tarayici


class SahteSayfa:
    """Playwright sayfasi yerine gecen, olay kaydeden sahte nesne."""

    def __init__(self, olaylar, patlat=()):
        self.olaylar = olaylar
        self.patlat = set(patlat)
        self.url = ""

    def goto(self, adres, **fazla):
        self.olaylar.append(("goto", adres))
        if adres in self.patlat:
            raise RuntimeError("gitmedi")
        self.url = adres
        return type("Yanit", (), {"status": 200})()

    def wait_for_timeout(self, ms):
        pass

    def wait_for_selector(self, *fazla, **adli):
        pass

    def wait_for_load_state(self, *fazla, **adli):
        pass

    def eval_on_selector_all(self, *fazla, **adli):
        return [{
            "cite": "https://hedef.com.tr",
            "href": "https://www.google.com/url?q=https://hedef.com.tr",
        }]


class SahteBaglam:
    """Yeni sayfa ureten sahte baglam."""

    def __init__(self, olaylar, patlat=()):
        self.olaylar = olaylar
        self.patlat = patlat

    def new_page(self):
        return SahteSayfa(self.olaylar, self.patlat)


@pytest.fixture
def isinma_kur(monkeypatch):
    """Isinmayi tek sayfaya ve kisa beklemeye sabitler."""

    def kur(acik=True, patlat=()):
        monkeypatch.setattr(tarayici.isinma, "acik", lambda: acik)
        monkeypatch.setattr(tarayici.isinma, "bekleme", lambda: (1_000, 1_000))
        monkeypatch.setattr(
            tarayici.isinma, "sayfa_sec",
            lambda rastgele=None: [tarayici.isinma.SAYFALAR[0]],
        )
        return tarayici.isinma.SAYFALAR[0]

    return kur


def _bos() -> dict:
    return {"result": "error", "organik": [], "url": "", "mesaj": ""}


def test_arama_once_isinir(isinma_kur):
    isinma_sayfasi = isinma_kur()
    olaylar: list = []
    sonuc = tarayici._tara(SahteBaglam(olaylar), "kelime", None, 1, _bos())

    assert sonuc["isinma"] == "ok"
    assert olaylar[0] == ("goto", isinma_sayfasi)
    assert "google" not in olaylar[0][1]
    assert "google.com/search" in olaylar[1][1]


def test_isinma_kapaliyken_dogrudan_aranir(isinma_kur):
    isinma_kur(acik=False)
    olaylar: list = []
    sonuc = tarayici._tara(SahteBaglam(olaylar), "kelime", None, 1, _bos())

    assert sonuc["isinma"] == "atlandi"
    assert "google.com/search" in olaylar[0][1]


def test_isinma_hatasi_aramayi_durdurmaz(isinma_kur):
    isinma_sayfasi = isinma_kur()
    olaylar: list = []
    sonuc = tarayici._tara(
        SahteBaglam(olaylar, patlat={isinma_sayfasi}), "kelime", None, 1, _bos()
    )

    assert sonuc["isinma"] == "error"
    assert sonuc["result"] == "ok"
    assert any("google.com/search" in adres for _, adres in olaylar)
class SahteSayfaHata(SahteSayfa):
    """HTTP 500 donen sayfa; govdede sonuc listesi yok."""

    def goto(self, adres, **fazla):
        self.olaylar.append(("goto", adres))
        self.url = adres
        return type("Yanit", (), {"status": 500})()


class HataliBaglam(SahteBaglam):
    """Her yeni sayfada HTTP 500 ureten baglam."""

    def new_page(self):
        return SahteSayfaHata(self.olaylar, self.patlat)


def test_adres_uule_tasimaz(isinma_kur):
    """Ulusal olcumde uule gonderilmez, gl/hl kalir (66)."""
    isinma_kur()
    olaylar: list = []
    tarayici._tara(SahteBaglam(olaylar), "kelime", None, 1, _bos())

    arama = olaylar[-1][1]
    assert "uule=" not in arama
    assert "gl=tr" in arama and "hl=tr" in arama


def test_http_500_olcum_sayilmaz(isinma_kur):
    """5xx yanit "ilk 100'de yok" sayilmaz, hata doner (77)."""
    isinma_kur()
    olaylar: list = []
    sonuc = tarayici._tara(HataliBaglam(olaylar), "kelime", None, 1, _bos())

    assert sonuc["result"] == "error"
    assert sonuc["mesaj"] == "http 500"


class SahteBaglamKurucu:
    """Baglam yerine gecen, eklenen cerezleri kaydeden sahte nesne."""

    def __init__(self, kayit):
        self.kayit = kayit

    def add_init_script(self, js):
        pass

    def add_cookies(self, cerezler):
        self.kayit.extend(cerezler)


class SahteP:
    """Playwright yerine gecen sahte nesne; baglam acmayi taklit eder."""

    def __init__(self):
        self.eklenen = []
        self.chromium = self

    def launch_persistent_context(self, *fazla, **adli):
        return SahteBaglamKurucu(self.eklenen)


def _guven_kur(monkeypatch, tmp_path, cerez=None):
    monkeypatch.setattr(tarayici.guven, "DOSYA", tmp_path / "g.json")
    monkeypatch.setattr(tarayici.guven, "RED_DOSYA", tmp_path / "g.red")
    monkeypatch.setattr(tarayici.guven, "omur_dk", lambda: 60)
    if cerez:
        tarayici.guven.kaydet(cerez)


def test_guvenilen_set_onay_cerezlerinin_onune_gecer(monkeypatch, tmp_path):
    _guven_kur(monkeypatch, tmp_path, [
        {"name": "NID", "value": "x", "domain": ".google.com", "path": "/"},
    ])
    p = SahteP()
    tarayici._baglam_ac(p, True, None, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    adlar = [c["name"] for c in p.eklenen]
    assert "NID" in adlar
    assert "SOCS" not in adlar


def test_guven_yoksa_onay_cerezleri_eklenir(monkeypatch, tmp_path):
    _guven_kur(monkeypatch, tmp_path)
    p = SahteP()
    tarayici._baglam_ac(p, True, None, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    adlar = [c["name"] for c in p.eklenen]
    assert "SOCS" in adlar and "CONSENT" in adlar


class SahteIstek:
    """Baglam istek tasiyicisi yerine gecen sahte nesne."""

    def __init__(self, sonuc=""):
        self.sonuc = sonuc

    def get(self, adres, **fazla):
        if isinstance(self.sonuc, Exception):
            raise self.sonuc
        return type("Yanit", (), {"url": self.sonuc})()


class BaglamIstek:
    def __init__(self, sonuc=""):
        self.request = SahteIstek(sonuc)


def test_goto_gercek_adrese_cozulur():
    b = BaglamIstek("https://hedef.com.tr/derin")
    assert tarayici._goto_coz(b, "https://www.google.com/goto?url=X") == "https://hedef.com.tr/derin"


def test_goto_google_kalirsa_bos_doner():
    b = BaglamIstek("https://www.google.com/sorry/index")
    assert tarayici._goto_coz(b, "https://www.google.com/goto?url=X") == ""


def test_goto_hatasinda_bos_doner():
    b = BaglamIstek(RuntimeError("ag"))
    assert tarayici._goto_coz(b, "https://www.google.com/goto?url=X") == ""


def test_cite_yol_izinden_host_cikarilir():
    """`cite` yol izi olsa da kok alan adi dogru cikar."""
    assert tarayici._cite_kok("www.site.com.tr › alt › sayfa") == "site.com.tr"
    assert tarayici._cite_kok("erzurumescortr.com") == "erzurumescortr.com"
    assert tarayici._cite_kok("com › . › escort") == ""
    assert tarayici._cite_kok("") == ""


def test_temizle_cite_host_verir():
    """Goto cozulemezse gorunen adresin host'u kullanilir, `com` degil."""
    adresler = [{"cite": "www.hedef.com.tr › alt", "baslik": "a",
                 "href": "https://www.google.com/goto?url=X"}]
    kayitlar = tarayici._temizle(adresler, lambda h: "")
    assert kayitlar[0]["link"] == "https://hedef.com.tr"


def test_temizle_cozucuyu_kullanir():
    adresler = [{"cite": "https://hedef.com.tr", "baslik": "a", "href": "https://www.google.com/goto?url=X"}]
    kayitlar = tarayici._temizle(adresler, lambda h: "https://hedef.com.tr/derin/sayfa")
    assert kayitlar[0]["link"] == "https://hedef.com.tr/derin/sayfa"


def test_temizle_cozemezse_cite_kalir():
    adresler = [{"cite": "https://hedef.com.tr", "baslik": "a", "href": "https://www.google.com/goto?url=X"}]
    kayitlar = tarayici._temizle(adresler, lambda h: "")
    assert kayitlar[0]["link"] == "https://hedef.com.tr"
