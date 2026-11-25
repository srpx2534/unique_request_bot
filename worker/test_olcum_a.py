"""olcum_a suphe denetimi ve tekrar davranisi.

Olcumun kendisi aga cikmadan sinanir: `serp.serp_getir` yerine sahte cevap
verilir, `position` yazimi ve uyari yakalanir. Amac iki kurali sabitlemek:
zehirlenmis sayfa kaydedilmez (71), geo uyusmazligi suphe sebebidir (70).
"""

from __future__ import annotations

from worker import olcum_a


def _cevap(**fazla) -> dict:
    """Temiz varsayilan cevap; istenen alan ezilir."""
    cevap = {
        "result": "ok",
        "position": 3,
        "kaynak": "decodo",
        "gl": "TR",
        "geo_location": "Turkey",
        "organik": [{"position": i, "link": f"https://site{i}.com.tr"} for i in range(1, 11)],
        "mesaj": "",
    }
    cevap.update(fazla)
    return cevap


def test_temiz_sayfa_supheli_degil() -> None:
    assert olcum_a.supheli_mi(_cevap(), set()) == ""


def test_gl_bossa_supheli() -> None:
    assert "gl bos" in olcum_a.supheli_mi(_cevap(gl=""), set())


def test_gl_tr_degilse_supheli() -> None:
    assert "geo uyusmadi" in olcum_a.supheli_mi(_cevap(gl="US"), set())


def test_geo_taninmadiysa_supheli() -> None:
    assert "geo taninmadi" in olcum_a.supheli_mi(_cevap(geo_location="Germany"), set())


def test_ince_liste_supheli() -> None:
    cevap = _cevap(organik=[{"position": 1, "link": "https://a.com.tr"}])
    assert "liste ince" in olcum_a.supheli_mi(cevap, set())


def test_onceki_kumeyle_ortusme_yoksa_supheli() -> None:
    onceki = {f"baska{i}.com" for i in range(10)}
    assert "ortusme yok" in olcum_a.supheli_mi(_cevap(), onceki)


def test_serper_geo_denetimi_yapmaz() -> None:
    """search_parameters dondurmeyen saglayicida geo denetimi atlanir."""
    cevap = _cevap(kaynak="serper", gl="", geo_location="")
    assert olcum_a.supheli_mi(cevap, set()) == ""


def test_temiz_olcum_yazilir(monkeypatch) -> None:
    yazilan: list = []
    monkeypatch.setattr(olcum_a.tarayici, "kullanilabilir", lambda: False)
    monkeypatch.setattr(olcum_a.serp, "serp_getir", lambda *a, **k: _cevap())
    monkeypatch.setattr(olcum_a, "_pozisyon_yaz", lambda *a: yazilan.append(a))
    monkeypatch.setattr(olcum_a, "_onceki_kume", lambda *_: set())

    sonuc = olcum_a.olcum_a_yap("kelime", "site0.com.tr", 7)

    assert sonuc["result"] == "ok"
    assert sonuc["rank"] == 3
    assert len(yazilan) == 1 and yazilan[0][1] == 3


def test_supheli_sayfa_tekrar_edilir_ve_null_yazilir(monkeypatch) -> None:
    cagri = {"n": 0}
    yazilan: list = []
    uyarilar: list = []

    def sahte(*_a, **_k):
        cagri["n"] += 1
        return _cevap(gl="US")

    monkeypatch.setattr(olcum_a.tarayici, "kullanilabilir", lambda: False)
    monkeypatch.setattr(olcum_a.serp, "serp_getir", sahte)
    monkeypatch.setattr(olcum_a.time, "sleep", lambda *_: None)
    monkeypatch.setattr(olcum_a, "_pozisyon_yaz", lambda *a: yazilan.append(a))
    monkeypatch.setattr(olcum_a, "_uyari", lambda *a: uyarilar.append(a))
    monkeypatch.setattr(olcum_a, "_onceki_kume", lambda *_: set())

    sonuc = olcum_a.olcum_a_yap("kelime", "site0.com.tr", 7)

    assert cagri["n"] == olcum_a.DENEME
    assert sonuc["result"] == "supheli"
    assert sonuc["rank"] is None
    assert yazilan and yazilan[0][1] is None
    assert uyarilar


def test_kota_hatasi_tekrar_edilmez(monkeypatch) -> None:
    cagri = {"n": 0}

    def sahte(*_a, **_k):
        cagri["n"] += 1
        return {"result": "captcha", "position": None, "organik": [], "kaynak": "decodo",
                "gl": "", "geo_location": "", "mesaj": "kota"}

    monkeypatch.setattr(olcum_a.tarayici, "kullanilabilir", lambda: False)
    monkeypatch.setattr(olcum_a.serp, "serp_getir", sahte)
    monkeypatch.setattr(olcum_a, "_pozisyon_yaz", lambda *a: None)
    monkeypatch.setattr(olcum_a, "_onceki_kume", lambda *_: set())

    sonuc = olcum_a.olcum_a_yap("kelime", "site0.com.tr", 7)

    assert cagri["n"] == 1
    assert sonuc["result"] == "captcha"

def test_tarayici_yolu_once_denenir(monkeypatch) -> None:
    """Tarayici kullanilabiliyorsa API'ye hic gidilmez; yerel arama sarti."""
    yazilan: list = []
    cagri = {"api": 0}

    def api(*_a, **_k):
        cagri["api"] += 1
        return _cevap()

    monkeypatch.setattr(olcum_a.tarayici, "kullanilabilir", lambda: True)
    # Ince liste supheli sayilir; cevap gercekci uzunlukta verilir.
    monkeypatch.setattr(olcum_a.tarayici, "serp_oku", lambda *a, **k: {
        "result": "ok",
        "organik": [
            {"position": 1, "link": "https://baska1.com"},
            {"position": 2, "link": "https://site0.com.tr/x"},
            {"position": 3, "link": "https://baska2.com"},
            {"position": 4, "link": "https://baska3.com"},
            {"position": 5, "link": "https://baska4.com"},
        ],
        "url": "", "mesaj": "",
    })
    monkeypatch.setattr(olcum_a.serp, "serp_getir", api)
    monkeypatch.setattr(olcum_a, "_pozisyon_yaz", lambda *a: yazilan.append(a))
    monkeypatch.setattr(olcum_a, "_onceki_kume", lambda *_: set())

    sonuc = olcum_a.olcum_a_yap("kelime", "site0.com.tr", 7)

    assert cagri["api"] == 0
    assert sonuc["saglayici"] == "tarayici"
    assert sonuc["rank"] == 2
    assert yazilan and yazilan[0][3] == "tarayici"


def test_tarayici_duvarinda_api_yedegi_devreye_girer(monkeypatch) -> None:
    """Tarayici duvara carparsa API denenir, olcum durmaz."""
    monkeypatch.setattr(olcum_a.tarayici, "kullanilabilir", lambda: True)
    monkeypatch.setattr(olcum_a.tarayici, "serp_oku", lambda *a, **k: {
        "result": "captcha", "organik": [], "url": "", "mesaj": "duvar",
    })
    monkeypatch.setattr(olcum_a.serp, "serp_getir", lambda *a, **k: _cevap())
    monkeypatch.setattr(olcum_a, "_pozisyon_yaz", lambda *a: None)
    monkeypatch.setattr(olcum_a, "_onceki_kume", lambda *_: set())

    sonuc = olcum_a.olcum_a_yap("kelime", "site0.com.tr", 7)

    assert sonuc["result"] == "ok"
    assert sonuc["saglayici"] == "decodo"