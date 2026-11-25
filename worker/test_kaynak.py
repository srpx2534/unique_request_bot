"""Alt kaynak ayirma ve cekme testleri."""

from worker import kaynak

TABAN = "https://hedef.test/sayfa"


def test_ayni_origin_kaynaklar_sec(liste=None):
    html = (
        '<link rel="stylesheet" href="/a.css">'
        '<script src="https://hedef.test/b.js"></script>'
        '<img src="/c.jpg">'
        '<img src="https://cdn.baska.com/d.jpg">'
    )
    kayitlar = kaynak.adresler(html, TABAN)
    adresler = [a for _, a in kayitlar]
    assert "https://hedef.test/a.css" in adresler
    assert "https://hedef.test/b.js" in adresler
    assert "https://hedef.test/c.jpg" in adresler
    assert all("baska.com" not in a for a in adresler)


def test_tur_etikete_gore():
    html = '<link rel="stylesheet" href="/a.css"><img src="/b.png">'
    turler = {t for t, _ in kaynak.adresler(html, TABAN)}
    assert turler == {"style", "image"}


def test_veri_ve_bos_adresler_atlanir():
    html = '<img src="data:image/png;base64,AAA"><img src=""><script src="#x"></script>'
    assert kaynak.adresler(html, TABAN) == []


def test_benzersiz_ve_sinirli():
    html = "".join(f'<img src="/{i}.png">' for i in range(40))
    kayitlar = kaynak.adresler(html, TABAN)
    assert len(kayitlar) == kaynak.AZAMI_KAYNAK
    assert len({a for _, a in kayitlar}) == len(kayitlar)


def test_basliklar_turu_tasir():
    basliklar = kaynak.basliklar("script")
    assert basliklar["Sec-Fetch-Dest"] == "script"
    assert basliklar["Sec-Fetch-Mode"] == "no-cors"
    assert basliklar["Sec-Fetch-Site"] == "same-origin"


class SahteOturum:
    def __init__(self, kod=200, patlat=()):
        self.kod = kod
        self.patlat = set(patlat)
        self.cagrilar = []

    def get(self, adres, **adli):
        if adres in self.patlat:
            raise RuntimeError("ag")
        self.cagrilar.append(adres)
        return type("Y", (), {"status_code": self.kod})()


def test_cek_basarili():
    oturum = SahteOturum()
    assert kaynak.cek(oturum, [("style", "https://hedef.test/a.css")]) == 1


def test_cek_hatali_kaynak_atlanir():
    oturum = SahteOturum(patlat={"https://hedef.test/a.css"})
    kayitlar = [("style", "https://hedef.test/a.css"), ("script", "https://hedef.test/b.js")]
    assert kaynak.cek(oturum, kayitlar) == 1


def test_cek_4xx_sayilmaz():
    oturum = SahteOturum(kod=404)
    assert kaynak.cek(oturum, [("image", "https://hedef.test/a.png")]) == 0