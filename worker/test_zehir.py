"""Zehir dedektoru testleri."""

from worker import zehir


def _kayit(baslik="", link="https://ornek.com/"):
    return {"baslik": baslik, "link": link}


def test_uygun_liste_temiz():
    kayitlar = [
        _kayit("Erzurum Escort Bayan"),
        _kayit("Samsun Escort Rehberi"),
    ]
    assert zehir.zehirli_mi("erzurum escort", kayitlar) is False


def test_alakasiz_liste_zehirli():
    kayitlar = [
        _kayit("Spotify Premium indir"),
        _kayit("Instagram takipci"),
    ]
    assert zehir.zehirli_mi("erzurum escort", kayitlar) is True


def test_adreste_gecmesi_yeter():
    kayitlar = [_kayit("Ana sayfa", "https://erzumescortr.com/")]
    assert zehir.zehirli_mi("erzurum escort", kayitlar) is False


def test_turkce_buyuk_harf_eslesir():
    kayitlar = [_kayit("İSTANBUL ESKORT")]
    assert zehir.zehirli_mi("istanbul escort", kayitlar) is False


def test_parca_yoksa_temiz_sayilir():
    assert zehir.zehirli_mi("ve ile", [_kayit("alakasiz")]) is False
    assert zehir.zehirli_mi("erzurum escort", []) is False


def test_durak_kelime_parca_olmaz():
    assert "ve" not in zehir.parcalar("erzurum ve escort")
    assert zehir.parcalar("erzurum escort") == ["erzurum", "escort"]


def test_ilk_on_disinda_kalan_bakilmaz():
    kayitlar = [_kayit("alakasiz") for _ in range(12)]
    kayitlar.append(_kayit("erzurum escort"))
    assert zehir.zehirli_mi("erzurum escort", kayitlar) is True