"""burst.py akış testleri.

Ağa çıkmaz; SERP, tıklama ve pogo taklit edilir. Durdurma davranışı (C21)
ve sayaçların doğru işlediği doğrulanır.
"""

from __future__ import annotations

import pytest

from worker import burst, click, serp


@pytest.fixture
def taklit(monkeypatch):
    """Ağ adımlarını taklit eder, çağrı sayısını tutar."""
    sayac = {"izlenim": 0, "tik": 0, "pogo": 0}

    def sahte_serp(*_a, **_k):
        sayac["izlenim"] += 1
        return {"result": "not_found", "position": None, "url": None,
                "http_status": 200, "elapsed_ms": 1, "bytes": 1,
                "profil": "chrome124", "kaynak": "html", "organik": [], "mesaj": ""}

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
    monkeypatch.setattr(burst.time, "sleep", lambda _s: None)
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
    """Hedef ilk 100'de yoksa tüm adet not_found yazılır."""
    monkeypatch.setattr(serp, "serp_getir", lambda *_a, **_k: {
        "result": "not_found", "position": None, "organik": [], "url": None,
        "profil": None, "kaynak": "api", "mesaj": "", "http_status": 200,
        "elapsed_ms": 1, "bytes": 1})
    sonuc = burst.burst_yap("a", "yok.com", 5)
    assert sonuc["result"] == "hedef_yok"
    assert sonuc["not_found"] == 5
    assert taklit["tik"] == 0


def test_adet_ust_sinira_kirpilir(taklit) -> None:
    """Adet AZAMI_HIT'i geçemez."""
    sonuc = burst.burst_yap("a", "a.com", 500)
    assert sonuc["ok"] == burst.AZAMI_HIT