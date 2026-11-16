"""saglik.py eşik testleri.

Ağa ve veritabanına çıkmaz; oran hesabı ile eşik kararının doğruluğu
doğrulanır. Eşik yanlış çalışırsa sağlayıcı erken tükenir ya da hiç
karantinaya girmez.
"""

from __future__ import annotations

from worker import havuz, saglik_db, saglik


def test_oran_hesabi() -> None:
    """Oran yüzde olarak hesaplanır."""
    assert saglik.oran_hesapla(3, 10) == 30.0


def test_sifir_toplamda_oran_sifir() -> None:
    """Toplam yoksa oran sıfırdır."""
    assert saglik.oran_hesapla(0, 0) == 0.0


def test_az_ornekte_esik_asilmaz() -> None:
    """Örnek sayısı yetersizken yüksek oran bile tüketmez."""
    assert saglik.esik_asildi_mi(80.0, 4, saglik.GEO_ESIK) is False


def test_ornek_yeterli_ve_oran_yuksekse_asilir() -> None:
    """Örnek yeterliyse ve oran eşiği geçtiyse tüketim uygulanır."""
    assert saglik.esik_asildi_mi(40.0, 20, saglik.GEO_ESIK) is True


def test_esitlikte_asilmaz() -> None:
    """Oran eşiğe eşitse tüketim uygulanmaz."""
    assert saglik.esik_asildi_mi(35.0, 20, saglik.GEO_ESIK) is False

def test_esikte_karantina_karari() -> None:
    """Eşik aşıldığında karantina kararı verilir."""
    assert saglik.karantina_karari(25.0, "active", False) == "karantina"


def test_esik_altinda_karar_yok() -> None:
    """Eşik altında karar çıkmaz."""
    assert saglik.karantina_karari(10.0, "active", False) == "yok"


def test_sure_dolunca_acilir() -> None:
    """Karantinadaki sağlayıcı süre dolunca açılır."""
    assert saglik.karantina_karari(30.0, "quarantine", True) == "ac"


def test_sure_dolmadan_acilmaz() -> None:
    """Süre dolmadan karantina kalkmaz."""
    assert saglik.karantina_karari(30.0, "quarantine", False) == "yok"

class _Imlec:
    """bayt_ekle akisini taklit eden imlec; fetchone kuyudan beslenir."""

    def __init__(self, kuyruk: list) -> None:
        self.kuyruk = list(kuyruk)
        self.calismalar: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametre=None):
        self.calismalar.append((" ".join(sql.split()), tuple(parametre or ())))

    def fetchone(self):
        return self.kuyruk.pop(0) if self.kuyruk else None

    def sorgular(self) -> list[str]:
        return [s for s, _ in self.calismalar]


class _Baglanti:
    def __init__(self, kuyruk: list) -> None:
        self.imlec = _Imlec(kuyruk)

    def cursor(self):
        return self.imlec

    def close(self) -> None:
        pass


def _kur(monkeypatch, kuyruk: list) -> tuple[_Baglanti, list]:
    baglanti = _Baglanti(kuyruk)
    uyarilar: list[tuple] = []
    monkeypatch.setattr(saglik_db, "_baglan", lambda: baglanti)
    monkeypatch.setattr(saglik_db, "uyari", lambda *a: uyarilar.append(a))
    return baglanti, uyarilar


def test_sifir_bayt_yazilmaz(monkeypatch) -> None:
    baglanti, _ = _kur(monkeypatch, [])
    saglik_db.bayt_ekle(3, 0)
    saglik_db.bayt_ekle(3, None)
    assert baglanti.imlec.calismalar == []


def test_ay_devri_kolonu_kullanilir(monkeypatch) -> None:
    baglanti, _ = _kur(monkeypatch, [(500, None)])
    saglik_db.bayt_ekle(3, 500)
    guncelleme = baglanti.imlec.sorgular()[0]
    assert "bytes_ay" in guncelleme
    assert "DATE_FORMAT" in guncelleme


def test_kota_yoksa_uyari_yok(monkeypatch) -> None:
    _, uyarilar = _kur(monkeypatch, [(10**9, None)])
    saglik_db.bayt_ekle(3, 1000)
    assert uyarilar == []


def test_esik_altinda_uyari_yok(monkeypatch) -> None:
    _, uyarilar = _kur(monkeypatch, [(500, 10_000)])
    saglik_db.bayt_ekle(3, 1000)
    assert uyarilar == []


def test_esik_asilinca_bir_kez_uyarir(monkeypatch) -> None:
    _, uyarilar = _kur(monkeypatch, [(9_500, 10_000), (0,)])
    saglik_db.bayt_ekle(3, 1000)
    assert len(uyarilar) == 1
    tur, kimlik, mesaj = uyarilar[0]
    assert tur == "quota"
    assert kimlik == 3
    assert "95" in mesaj


def test_acik_uyari_varsa_sessiz_kalir(monkeypatch) -> None:
    _, uyarilar = _kur(monkeypatch, [(9_500, 10_000), (1,)])
    saglik_db.bayt_ekle(3, 1000)
    assert uyarilar == []


def test_aday_sorgusu_kotayi_suzer() -> None:
    sorgu = havuz._aday_sorgusu("residential")
    assert "(quota_bytes IS NULL OR bytes_month < quota_bytes)" in sorgu

def test_asgari_ornek_altinda_esik_asilmaz() -> None:
    assert saglik.esik_asildi_mi(50.0, 5, 35.0, 10) is False


def test_asgari_ornek_dolunca_esik_asilir() -> None:
    assert saglik.esik_asildi_mi(50.0, 10, 35.0, 10) is True


class _EsikImlec:
    def __init__(self, kuyruk: list) -> None:
        self.kuyruk = list(kuyruk)
        self.calismalar: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametre=None):
        self.calismalar.append((" ".join(sql.split()), tuple(parametre or ())))

    def fetchone(self):
        return self.kuyruk.pop(0) if self.kuyruk else None


class _EsikBaglanti:
    def __init__(self, kuyruk: list) -> None:
        self.imlec = _EsikImlec(kuyruk)

    def cursor(self):
        return self.imlec

    def close(self) -> None:
        pass


def test_kaydet_esikleri_ayardan_okur(monkeypatch) -> None:
    baglanti = _EsikBaglanti([(12, 20, 60.0)])
    monkeypatch.setattr(saglik_db, "_baglan", lambda: baglanti)
    monkeypatch.setattr(saglik_db.ayar_db, "oku", lambda anahtar, varsayilan="": {
        "esik_geo": "50", "asgari_ornek": "20",
    }.get(anahtar, varsayilan))

    saglik_db.kaydet(4, 34, "captcha")

    tuketim = [p for s, p in baglanti.imlec.calismalar if "exhausted_until" in s]
    assert tuketim, "il cifti tuketilmedi"
    assert 60 in tuketim[0]


def test_kaydet_esik_altinda_tuketmez(monkeypatch) -> None:
    baglanti = _EsikBaglanti([(3, 20, 15.0)])
    monkeypatch.setattr(saglik_db, "_baglan", lambda: baglanti)
    monkeypatch.setattr(saglik_db.ayar_db, "oku", lambda anahtar, varsayilan="": varsayilan)

    saglik_db.kaydet(4, 34, "captcha")

    assert not [s for s, _ in baglanti.imlec.calismalar if "exhausted_until" in s]


class _KotaImlec:
    """kota_isle akisini taklit eden imlec; rowcount guncellemeye bagli."""

    def __init__(self, kuyruk: list) -> None:
        self.kuyruk = list(kuyruk)
        self.calismalar: list[tuple[str, tuple]] = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametre=None):
        tek = " ".join(sql.split())
        self.calismalar.append((tek, tuple(parametre or ())))
        self.rowcount = 1 if tek.startswith("UPDATE provider SET quota_bytes") else 0

    def fetchone(self):
        return self.kuyruk.pop(0) if self.kuyruk else None


class _KotaBaglanti:
    def __init__(self, kuyruk: list) -> None:
        self.imlec = _KotaImlec(kuyruk)

    def cursor(self):
        return self.imlec

    def close(self) -> None:
        pass


def _kota_kur(monkeypatch, kuyruk: list) -> tuple[_KotaBaglanti, list]:
    baglanti = _KotaBaglanti(kuyruk)
    uyarilar: list[tuple] = []
    monkeypatch.setattr(saglik_db, "_baglan", lambda: baglanti)
    monkeypatch.setattr(saglik_db, "uyari", lambda *a: uyarilar.append(a))
    return baglanti, uyarilar


def test_kota_mi_kodu_tanir() -> None:
    """466 reddi kota sayilir."""
    mesaj = "CONNECT tunnel failed, response 466. See https://curl.se/libcurl/c/libcurl-errors.html"
    assert saglik.kota_mi(mesaj) is True


def test_kota_mi_baska_kodu_ayirir() -> None:
    """407 ve bos metin kota degildir."""
    assert saglik.kota_mi("CONNECT tunnel failed, response 407") is False
    assert saglik.kota_mi("") is False
    assert saglik.kota_mi(None) is False


def test_kota_isle_kotayi_yazar_ve_uyarir(monkeypatch) -> None:
    """Kota siniri bayt sayacina esitlenir, tek uyari dusulur."""
    baglanti, uyarilar = _kota_kur(monkeypatch, [(0,)])
    saglik_db.kota_isle(7)
    guncelleme = baglanti.imlec.calismalar[0][0]
    assert "quota_bytes = bytes_month" in guncelleme
    assert "hata_sayac = 0" in guncelleme
    assert len(uyarilar) == 1
    tur, kimlik, _ = uyarilar[0]
    assert tur == "quota"
    assert kimlik == 7


def test_kota_isle_acik_uyarida_sessiz(monkeypatch) -> None:
    """Acik kota uyarisi varsa yenisi yazilmaz."""
    _, uyarilar = _kota_kur(monkeypatch, [(1,)])
    saglik_db.kota_isle(7)
    assert uyarilar == []
