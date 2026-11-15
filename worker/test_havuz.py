"""havuz.py oran ve seçim testleri.

Ağa ve veritabanına çıkmaz; oran normalizasyonu ile tür kurası doğrulanır.
Dağılım bozulursa mobil oranı panelden ne girilirse girsin tutmaz.
"""

from __future__ import annotations

import pytest

from worker import havuz


@pytest.fixture(autouse=True)
def _oran_onbellegi_temiz() -> None:
    """Oran onbellegi testler arasinda tasmasin."""
    havuz.onbellek_temizle()


def test_hepsi_sifirsa_residential_yuz() -> None:
    """Hiç oran girilmemişse residential %100 kabul edilir."""
    assert havuz.oranlari_normalize({}) == {
        "oran_residential": 100, "oran_mobil": 0, "oran_datacenter": 0
    }


def test_toplam_yuze_tamamlanir() -> None:
    """Toplam 100 değilse en büyük kalana fark yazılarak 100'e tamamlanır."""
    sonuc = havuz.oranlari_normalize(
        {"oran_residential": 60, "oran_mobil": 60, "oran_datacenter": 0}
    )
    assert sum(sonuc.values()) == 100
    assert sonuc["oran_residential"] == sonuc["oran_mobil"] == 50


def test_negatif_deger_sifira_kirpilir() -> None:
    """Negatif oran sıfır sayılır."""
    sonuc = havuz.oranlari_normalize(
        {"oran_residential": 100, "oran_mobil": -20, "oran_datacenter": 0}
    )
    assert sonuc["oran_mobil"] == 0


def test_mobil_sifirsa_hic_sec_mez() -> None:
    """Mobil oranı sıfırken kura mobile düşmez."""
    oranlar = {"oran_residential": 50, "oran_mobil": 50, "oran_datacenter": 0}
    for yuzde in range(0, 100, 5):
        assert havuz.tur_sec(oranlar, mobil_acik=False, rastgele=yuzde) == "residential"


def test_mobil_pencere_acikken_secilebilir() -> None:
    """Mobil açıkken yüksek dilim mobile düşer."""
    oranlar = {"oran_residential": 20, "oran_mobil": 80, "oran_datacenter": 0}
    assert havuz.tur_sec(oranlar, mobil_acik=True, rastgele=90) == "mobile"


def test_hic_uygun_tur_yoksa_none() -> None:
    """Tüm oranlar sıfırsa tür seçilemez."""
    sifir = {"oran_residential": 0, "oran_mobil": 0, "oran_datacenter": 0}
    assert havuz.tur_sec(sifir, mobil_acik=True) is None
class _SahteImlec:
    """Yalnizca cerez_sec akisini taklit eden imlec."""

    def __init__(self) -> None:
        self.calismalar: list[tuple[str, tuple]] = []
        self.secim_sayisi = 0
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametre=None):
        self.calismalar.append((sql, tuple(parametre or ())))
        if sql.startswith("SELECT id, parmak_izzi"):
            self.secim_sayisi += 1

    def fetchone(self):
        if self.secim_sayisi == 1:
            return None
        return (7, "aile")

    def silinen_ciftler(self) -> list[tuple]:
        return [p for s, p in self.calismalar if s.startswith("DELETE FROM cookie_kullanim")]


class _SahteBaglanti:
    def __init__(self) -> None:
        self.imlec = _SahteImlec()

    def cursor(self):
        return self.imlec

    def close(self) -> None:
        pass


def _hazirla(monkeypatch, sahte) -> None:
    monkeypatch.setattr(havuz, "cerez_aktif", lambda: True)
    monkeypatch.setattr(havuz, "_cift_bul", lambda *_: (5, 9))
    monkeypatch.setattr(havuz, "_dugum_id", lambda: 1)
    monkeypatch.setattr(havuz, "_ayar_evet", lambda *_: True)
    monkeypatch.setattr(havuz, "_baglan", lambda: sahte)


def test_secim_sorgusu_ulkeyi_parametre_gecirir() -> None:
    sorgu, parametreler = havuz._secim_sorgusu(0, 1, "TR", None, None, False)
    assert "'TR'" not in sorgu
    assert "ulke = %s" in sorgu
    # Ulke artik suzgec degil siralama: TR cerezler yabancilarin onune gecer.
    assert "TR" in parametreler
    assert parametreler[-1] == "TR"


def test_il_kodu_varsa_suzgec_eklenir() -> None:
    sorgu, parametreler = havuz._secim_sorgusu(0, 1, "TR", 34, None, False)
    assert "(il_kodu = %s OR il_kodu IS NULL)" in sorgu
    assert 34 in parametreler


def test_il_kodu_yoksa_suzgec_eklenmez() -> None:
    sorgu, _ = havuz._secim_sorgusu(0, 1, "TR", None, None, False)
    assert "il_kodu = %s OR" not in sorgu


def test_cift_varsa_kullanim_suzgeci_eklenir() -> None:
    sorgu, parametreler = havuz._secim_sorgusu(0, 1, "TR", None, (5, 9), False)
    assert "NOT EXISTS" in sorgu
    assert 5 in parametreler and 9 in parametreler


def test_parametre_sayisi_yer_tutucuyla_uyusur() -> None:
    for gecmis, geo, cift, mobil in (
        (0, None, None, False),
        (1, 34, None, True),
        (0, None, (2, 3), False),
        (1, 6, (2, 3), True),
    ):
        sorgu, parametreler = havuz._secim_sorgusu(gecmis, 1, "TR", geo, cift, mobil)
        assert sorgu.count("%s") == len(parametreler)


def test_cift_tukenince_tur_basa_doner(monkeypatch) -> None:
    sahte = _SahteBaglanti()
    _hazirla(monkeypatch, sahte)

    assert havuz.cerez_sec(34, "a.com", "kelime", False) == (7, "aile")
    assert sahte.imlec.silinen_ciftler() == [(5, 9)]


def test_havuz_bossa_sarma_donguye_girmez(monkeypatch) -> None:
    sahte = _SahteBaglanti()
    _hazirla(monkeypatch, sahte)
    sahte.imlec.fetchone = lambda: None

    assert havuz.cerez_sec(34, "a.com", "kelime", False) is None
    # Her tarih grubunda cift bir kez sifirlanir (3 kademe x 2 grup).
    assert len(sahte.imlec.silinen_ciftler()) == 6


def test_cerezsiz_kapaliyken_none(monkeypatch) -> None:
    monkeypatch.setattr(havuz, "cerez_aktif", lambda: False)
    assert havuz.cerez_sec(34, "a.com", "kelime", False) is None

def _gecmis_aramalari(sahte) -> list[int]:
    return [
        p[0] for s, p in sahte.imlec.calismalar if s.startswith("SELECT id, parmak_izzi")
    ]


def test_suresiz_kullanim_kapaliyken_gecmis_aranmaz(monkeypatch) -> None:
    """Ayar kapaliyken suresi gecmis profiller hic denenmez."""
    sahte = _SahteBaglanti()
    _hazirla(monkeypatch, sahte)
    monkeypatch.setattr(havuz, "_ayar_evet", lambda *_: False)
    sahte.imlec.fetchone = lambda: None

    havuz.cerez_sec(34, "a.com", "kelime", False)

    assert _gecmis_aramalari(sahte) == [0] * 6


def test_suresiz_kullanim_acikken_once_tazeler_sonra_gecmisler(monkeypatch) -> None:
    """Ayar acikken sira once taze, sonra suresi gecmis gruptadir."""
    sahte = _SahteBaglanti()
    _hazirla(monkeypatch, sahte)
    sahte.imlec.fetchone = lambda: None

    havuz.cerez_sec(34, "a.com", "kelime", False)

    # Her canli kademesinde once taze, sonra gecmis grup denenir.
    assert _gecmis_aramalari(sahte) == [0, 0, 1, 1] * 3

class _OranImlec:
    def __init__(self, satirlar: list[tuple]) -> None:
        self.satirlar = satirlar

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, *_):
        pass

    def fetchall(self):
        return self.satirlar


class _OranBaglanti:
    def __init__(self, satirlar: list[tuple]) -> None:
        self.imlec = _OranImlec(satirlar)

    def cursor(self):
        return self.imlec

    def close(self) -> None:
        pass



def test_oranlar_tablo_okunamazsa_varsayilan(monkeypatch) -> None:
    """Tablo okunamazsa varsayilan oran gecerli olur; env devrede degil."""
    def patlat():
        raise RuntimeError("db yok")

    monkeypatch.setattr(havuz, "_baglan", patlat)

    assert havuz.oranlari_oku() == havuz.VARSAYILAN_ORAN


def test_oranlar_tablodan_okunur(monkeypatch) -> None:
    monkeypatch.setattr(havuz, "_baglan", lambda: _OranBaglanti([("oran_residential", "40"), ("oran_mobil", "60")]))

    sonuc = havuz.oranlari_oku()
    assert sonuc["oran_residential"] == 40
    assert sonuc["oran_mobil"] == 60


def test_oranlar_hicbir_kaynak_yoksa_varsayilan(monkeypatch) -> None:
    def patlat():
        raise RuntimeError("db yok")

    monkeypatch.setattr(havuz, "_baglan", patlat)

    assert havuz.oranlari_oku() == havuz.VARSAYILAN_ORAN


def test_mobil_orani_sifirsa_mobil_sec_mez(monkeypatch) -> None:
    monkeypatch.setattr(havuz, "_baglan", lambda: _OranBaglanti([("oran_residential", "100"), ("oran_mobil", "0")]))

    oranlar = havuz.oranlari_oku()
    for yuzde in range(0, 100, 10):
        assert havuz.tur_sec(oranlar, mobil_acik=True, rastgele=yuzde) == "residential"


def test_oran_onbellegi_ikinci_cagrida_db_okumaz(monkeypatch) -> None:
    """Onbellek doluyken veritabani tekrar okunmaz."""
    sayac = {"n": 0}

    def bag():
        sayac["n"] += 1
        return _OranBaglanti([("oran_residential", "40"), ("oran_mobil", "60")])

    monkeypatch.setattr(havuz, "_baglan", bag)
    havuz.oranlari_oku()
    havuz.oranlari_oku()
    assert sayac["n"] == 1

class _SiraliImlec:
    """Il kodu sorgusunda 34 doner, saglayici sorgusunda bos doner."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametre=None):
        self.sql = sql

    def fetchone(self):
        if "FROM geo WHERE slug" in self.sql:
            return (34,)
        return None


class _SiraliBaglanti:
    def cursor(self):
        return _SiraliImlec()

    def close(self) -> None:
        pass


def _sira_izle(monkeypatch) -> list:
    """Secim sirasini kaydeder; saglayici bulunamaz, dongu sonuna kadar doner."""
    sira: list = []

    def aday(kod):
        sira.append(kod)
        return "SELECT 1"

    monkeypatch.setattr(havuz, "oranlari_oku", lambda: {"oran_residential": 100, "oran_mobil": 0, "oran_datacenter": 0})
    monkeypatch.setattr(havuz, "_aday_sorgusu", aday)
    monkeypatch.setattr(havuz, "_baglan", lambda: _SiraliBaglanti())
    return sira


def test_il_seciliyken_once_il_sonra_tr(monkeypatch) -> None:
    """Il seciliyken butun türlerde il denenir, sonra TR geneli (C61)."""
    sira = _sira_izle(monkeypatch)
    havuz.sec_mod("istanbul", True)
    assert sira[0] == 34
    # Il kodlari TR geneline inmeden once gelir; ilk None'un ardindan il yok.
    ilk_none = sira.index(None)
    assert all(k == 34 for k in sira[:ilk_none])
    assert all(k is None for k in sira[ilk_none:])


def test_il_secilmemisse_dogrudan_tr(monkeypatch) -> None:
    """Il secili degilse yalnizca TR geneli denenir."""
    sira = _sira_izle(monkeypatch)
    havuz.sec_mod(None, True)
    assert sira and all(k is None for k in sira)

def test_canli_kademesi_tarihin_onunde(monkeypatch) -> None:
    """Calisan cerez her zaman once; sira canli, olculmemis, engelli (C45)."""
    kademeler: list = []

    def secim_sorgusu(gecmis, canli, *_):
        kademeler.append(canli)
        return "SELECT 1", (gecmis,)

    sahte = _SahteBaglanti()
    _hazirla(monkeypatch, sahte)
    sahte.imlec.fetchone = lambda: None
    monkeypatch.setattr(havuz, "_secim_sorgusu", secim_sorgusu)

    havuz.cerez_sec(34, "a.com", "kelime", False)

    # Ilk dort arama canli, sonraki dort olculmemis, en son dort engelli.
    assert kademeler[:4] == [1, 1, 1, 1]
    assert kademeler[4:8] == [None, None, None, None]
    assert kademeler[8:] == [0, 0, 0, 0]
