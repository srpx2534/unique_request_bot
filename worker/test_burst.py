"""burst.py akış testleri.

Ağa çıkmaz; SERP, tıklama ve pogo taklit edilir. Durdurma davranışı (C21)
ve sayaçların doğru işlediği doğrulanır.
"""

from __future__ import annotations

import pytest

from worker import burst, burst_hit, click, serp


@pytest.fixture
def taklit(monkeypatch):
    """Ağ adımlarını taklit eder, çağrı sayısını tutar."""
    sayac = {"izlenim": 0, "tik": 0, "pogo": 0}

    def sahte_serp(*_a, **_k):
        sayac["izlenim"] += 1
        return {"result": "ok", "position": 1, "url": "https://www.google.com/search?q=a",
                "http_status": 200, "elapsed_ms": 1, "bytes": 1,
                "profil": "chrome124", "kaynak": "html",
                "organik": [{"position": 1, "link": "https://a.com/"}], "mesaj": ""}

    def sahte_cozum(*_a, **_k):
        return {"result": "ok", "position": 1, "url": "https://www.google.com/search?q=a",
                "http_status": 200, "elapsed_ms": 1, "bytes": 1, "profil": None,
                "kaynak": "api", "organik": [{"position": 1, "link": "https://a.com/"}],
                "mesaj": ""}

    def sahte_tik(*_a, **_k):
        sayac["tik"] += 1
        return {"result": "ok", "http_status": 200, "elapsed_ms": 1, "bytes": 1,
                "dwell_ms": 0, "profil": "chrome124", "url": None, "mesaj": ""}

    def sahte_pogo(*_a, **_k):
        sayac["pogo"] += 1
        return {"result": "ok", "http_status": 200, "elapsed_ms": 1,
                "bekleme_ms": 0, "mesaj": ""}

    monkeypatch.setattr(serp, "serp_getir", sahte_cozum)
    monkeypatch.setattr(serp, "serp_getir_html", sahte_serp)
    monkeypatch.setattr(click, "tikla", sahte_tik)
    monkeypatch.setattr(click, "pogo", sahte_pogo)
    monkeypatch.setattr(click, "POGO_ORANI", 100)
    monkeypatch.setattr(burst.time, "sleep", lambda _s: None)
    # Sağlık yazımı veritabanına gider; birim testi kirletmesin diye susturulur.
    monkeypatch.setattr(burst.saglik_db, "uyari", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "kaydet", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "karantina_kontrol", lambda *_a, **_k: None)
    # Proxy secimi ve kalan saglik yazimlari da veritabanina gider; birim
    # testi DB olmadan (CI) kosabilsin diye hepsi sabitlenir.
    monkeypatch.setattr(burst.havuz, "sec_mod",
                        lambda *_a, **_k: (1, "http://proxy:1", "tr_fallback", "residential"))
    monkeypatch.setattr(burst.havuz, "cerez_sec", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.havuz, "cerez_al", lambda *_a, **_k: [])
    monkeypatch.setattr(burst.havuz, "cerez_canli", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.havuz, "cerez_birak", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.havuz, "kelime_mobil", lambda *_a, **_k: False)
    monkeypatch.setattr(burst.havuz, "kod_bul", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "hedef_yok_islet", lambda *_a, **_k: (0, False))
    monkeypatch.setattr(burst.saglik_db, "hedef_yok_sifirla", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "hata_sifirla", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "hata_isle", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "kota_isle", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "bayt_ekle", lambda *_a, **_k: None)
    monkeypatch.setattr(burst.saglik_db, "saglayici_yok_dur", lambda *_a, **_k: None)
    return sayac


def test_durdurulunca_kalan_hit_atilmaz(taklit) -> None:
    """devam False dönünce döngü kırılır, fazladan hit atılmaz."""
    kalan = {"n": 2}

    def devam() -> bool:
        if kalan["n"] <= 0:
            return False
        kalan["n"] -= 1
        return True

    sonuc = burst.burst_yap("a", "a.com", 10, devam=devam)
    assert sonuc["durduruldu"] is True
    assert sonuc["ok"] == 2
    assert taklit["tik"] == 2


def test_devam_yoksa_tum_hitler_atilir(taklit) -> None:
    """devam verilmezse adet kadar hit atılır."""
    sonuc = burst.burst_yap("a", "a.com", 3)
    assert sonuc["durduruldu"] is False
    assert sonuc["ok"] == 3


def test_hedef_yoksa_not_found_sayilir(taklit, monkeypatch) -> None:
    """Hedef ilk 100'de yoksa tüm adet hedef_yok yazılır, not_found sıfır kalır."""
    monkeypatch.setattr(serp, "serp_getir", lambda *_a, **_k: {
        "result": "not_found", "position": None, "organik": [], "url": None,
        "profil": None, "kaynak": "api", "mesaj": "", "http_status": 200,
        "elapsed_ms": 1, "bytes": 1})
    sonuc = burst.burst_yap("a", "yok.com", 5)
    assert sonuc["result"] == "hedef_yok"
    # Hit atılmadığı için kayıp not_found değil, hedef_yok olarak sayılır.
    assert sonuc["hedef_yok"] == 5
    assert sonuc["not_found"] == 0
    assert taklit["tik"] == 0


def test_adet_ust_sinira_kirpilir(taklit) -> None:
    """Adet AZAMI_HIT'i geçemez."""
    sonuc = burst.burst_yap("a", "a.com", 500)
    assert sonuc["ok"] == burst.AZAMI_HIT

def test_failover_yeni_saglayiciyla_tekrarlar(taklit, monkeypatch) -> None:
    """İlk deneme düşerse hit yeni sağlayıcıyla bir kez daha denenir (C6)."""
    sayac = {"n": 0}

    def sahte_tik(*_a, **_k):
        sayac["n"] += 1
        if sayac["n"] == 1:
            return {"result": "timeout", "http_status": None, "elapsed_ms": 1,
                    "bytes": 0, "dwell_ms": 0, "profil": "chrome124", "url": None,
                    "mesaj": "deneme"}
        return {"result": "ok", "http_status": 200, "elapsed_ms": 1, "bytes": 1,
                "dwell_ms": 0, "profil": "chrome124", "url": None, "mesaj": ""}

    monkeypatch.setattr(click, "tikla", sahte_tik)
    adresler = iter(["http://birinci:1", "http://ikinci:1"])

    sonuc = burst.burst_yap("a", "a.com", 1, proxy_secici=lambda: next(adresler, None))

    assert sonuc["ok"] == 1
    assert sonuc["hits"][0].get("failover") is True
    assert sayac["n"] == 2


def test_ikinci_deneme_de_duserse_hata_sayilir(taklit, monkeypatch) -> None:
    """İki deneme de düşerse hit hata olarak sayılır, üçüncü denenmez."""
    sayac = {"n": 0}

    def sahte_tik(*_a, **_k):
        sayac["n"] += 1
        return {"result": "error", "http_status": None, "elapsed_ms": 1,
                "bytes": 0, "dwell_ms": 0, "profil": "chrome124", "url": None,
                "mesaj": "düştü"}

    monkeypatch.setattr(click, "tikla", sahte_tik)
    sonuc = burst.burst_yap("a", "a.com", 1, proxy_secici=lambda: "http://p:1")

    assert sonuc["error"] == 1
    assert sayac["n"] == 2

def test_mobil_kelime_mobil_saglayici_ve_android_profil_secer(taklit, monkeypatch) -> None:
    """Mobil isaretli kelime mobile saglayiciyi zorlar ve android profil kullanir."""
    zorlanan: list = []

    def sahte_sec_mod(_geo, _mobil_acik, zorunlu_tur=None):
        zorlanan.append(zorunlu_tur)
        return 1, "http://proxy", "city", "mobile"

    monkeypatch.setattr(burst.havuz, "kelime_mobil", lambda _k: True)
    monkeypatch.setattr(burst.havuz, "sec_mod", sahte_sec_mod)
    monkeypatch.setattr(burst.havuz, "cerez_sec", lambda *_a, **_k: None)

    sonuc = burst.burst_yap("a", "a.com", 3)
    assert zorlanan == ["mobile"] * 3
    assert {k["profil"] for k in sonuc["hits"]} == {"chrome131_android"}


def test_web_kelime_mobil_saglayici_zorlamaz(taklit, monkeypatch) -> None:
    """Mobil olmayan kelimede zorunlu tur gecilmez, web profili secilir."""
    zorlanan: list = []

    def sahte_sec_mod(_geo, _mobil_acik, zorunlu_tur=None):
        zorlanan.append(zorunlu_tur)
        return 1, "http://proxy", "city", "residential"

    monkeypatch.setattr(burst.havuz, "kelime_mobil", lambda _k: False)
    monkeypatch.setattr(burst.havuz, "sec_mod", sahte_sec_mod)
    monkeypatch.setattr(burst.havuz, "cerez_sec", lambda *_a, **_k: None)

    sonuc = burst.burst_yap("a", "a.com", 3)
    assert zorlanan == [None] * 3
    assert "chrome131_android" not in {k["profil"] for k in sonuc["hits"]}

def test_not_found_izleniminde_de_tiklanir(taklit, monkeypatch) -> None:
    """Izlenim bos donse de hedef adres bilindigi icin tiklama denenir (C9)."""
    def sahte_serp(*_a, **_k):
        return {"result": "not_found", "position": None, "url": None,
                "http_status": 200, "elapsed_ms": 1, "bytes": 5,
                "profil": "chrome124", "kaynak": "html", "organik": [], "mesaj": ""}

    monkeypatch.setattr(serp, "serp_getir_html", sahte_serp)
    sonuc = burst.burst_yap("a", "a.com", 2)
    assert sonuc["ok"] == 2
    assert sonuc["not_found"] == 0
    assert taklit["tik"] == 2


def test_pogo_duserse_hit_hata_sayilir(taklit, monkeypatch) -> None:
    """Pogo basarisizsa hit ok sayilmaz."""
    def sahte_pogo(*_a, **_k):
        return {"result": "error", "http_status": None, "elapsed_ms": 1,
                "bekleme_ms": 0, "mesaj": "düştü"}

    monkeypatch.setattr(click, "pogo", sahte_pogo)
    monkeypatch.setattr(click, "POGO_ORANI", 100)
    sonuc = burst.burst_yap("a", "a.com", 1)
    assert sonuc["error"] == 1
    assert sonuc["ok"] == 0

def test_pogo_atlanirsa_hit_ok_sayilir(taklit, monkeypatch) -> None:
    """Pogo olasiligi sifirsa SERP'e donulmez ama hit basarili kalir."""
    monkeypatch.setattr(click, "POGO_ORANI", 0)
    sonuc = burst.burst_yap("a", "a.com", 1)
    assert sonuc["ok"] == 1
    assert sonuc["hits"][0]["pogo"] == "atlandi"
    assert taklit["pogo"] == 0


def test_arada_ana_sayfadan_girilir(taklit, monkeypatch) -> None:
    """Hitlerin bir kismi siteye kokten girer, tam adresten degil."""
    gelen: list = []

    def sahte_tik(url, **_k):
        gelen.append(url)
        return {"result": "ok", "http_status": 200, "elapsed_ms": 1, "bytes": 1,
                "dwell_ms": 0, "profil": "chrome124", "url": None, "mesaj": ""}

    monkeypatch.setattr(click, "tikla", sahte_tik)
    monkeypatch.setattr(burst_hit, "ENTRY_ANA_ORANI", 100)

    burst.burst_yap("a", "a.com", 1, hedef_url="https://a.com/derin/sayfa")
    assert gelen == ["https://a.com/"]
