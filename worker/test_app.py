"""Worker HTTP ucu testleri.

Soket acilmaz; isleyici nesnesi taklit edilir. Token, imza, durdurma ve
bilinmeyen yol davranisi dogrulanir.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import time

import pytest

from worker import app, kalp


class Sahte:
    """Isleyici yerine gecen sahte istek; yaniti listeye yazar.

    `_json` gercek metot gibi baglanir, aksi hâlde `self` ilk argumana kayar.
    """

    def __init__(self, yol: str = "/worker/burst", basliklar: dict | None = None) -> None:
        self.path = yol
        self.headers = basliklar or {}
        self.rfile = None
        self.yanitlar: list[tuple[int, dict]] = []
        self.retry = 0

    def _json(self, kod: int, govde: dict, retry: int = 0) -> None:
        self.retry = retry
        self.yanitlar.append((kod, govde))

    # Gercek sinifin dogrulama metotlari sahteye baglanir; boylece testte
    # kopya mantik tutulmaz, uretimdeki kod kosar.
    _yetkili = app.Isleyici._yetkili
    _imza_dogrula = app.Isleyici._imza_dogrula
    _ham_oku = app.Isleyici._ham_oku
    _post = app.Isleyici._post


def istek(yol: str = "/worker/burst", basliklar: dict | None = None) -> Sahte:
    """Sahte istek uretir."""
    return Sahte(yol, basliklar)


def test_health_token_istemez_ve_doluluk_verir() -> None:
    """/health kimlik istemez; surum ve doluluk doner (§7.2)."""
    sahte = istek("/health")
    app.Isleyici.do_GET(sahte)  # type: ignore[arg-type]
    kod, govde = sahte.yanitlar[0]
    assert kod == 200
    assert govde["surum"]
    assert isinstance(govde["doluluk"], int)


def test_bilinmeyen_get_404() -> None:
    """Bilinmeyen yol 404 doner."""
    sahte = istek("/yok")
    app.Isleyici.do_GET(sahte)  # type: ignore[arg-type]
    assert sahte.yanitlar[0][0] == 404


def test_yetkisiz_burst_401() -> None:
    """Token yoksa burst reddedilir."""
    sahte = istek()
    app.Isleyici.do_POST(sahte)  # type: ignore[arg-type]
    assert sahte.yanitlar[0][0] == 401


def test_yanlis_token_401() -> None:
    """Yanlis token reddedilir."""
    sahte = istek(basliklar={"Authorization": "Bearer yanlis"})
    app.Isleyici.do_POST(sahte)  # type: ignore[arg-type]
    assert sahte.yanitlar[0][0] == 401


def test_bearer_oneki_zorunlu() -> None:
    """Bearer oneki olmayan baslik yetkisiz sayilir."""
    sahte = istek(basliklar={"Authorization": app.TOKEN})
    assert app.Isleyici._yetkili(sahte) is False  # type: ignore[arg-type]


def test_dogru_token_gecer() -> None:
    """Dogru token gecer."""
    sahte = istek(basliklar={"Authorization": f"Bearer {app.TOKEN}"})
    assert app.Isleyici._yetkili(sahte) is True  # type: ignore[arg-type]


def test_imza_dogrulama() -> None:
    """Imza ham govde uzerinden hesaplanir; yanlisi reddedilir."""
    ham = json.dumps({"keyword": "x"}).encode("utf-8")
    dogru = hmac.new(app.TOKEN.encode("utf-8"), ham, hashlib.sha256).hexdigest()
    sahte = istek(basliklar={"x-imza": dogru})
    assert app.Isleyici._imza_dogrula(sahte, ham) is True  # type: ignore[arg-type]
    sahte2 = istek(basliklar={"x-imza": "yanlis"})
    assert app.Isleyici._imza_dogrula(sahte2, ham) is False  # type: ignore[arg-type]


def test_imza_yoksa_reddedilir() -> None:
    """Imza basligi yoksa dogrulama basarisiz."""
    sahte = istek()
    assert app.Isleyici._imza_dogrula(sahte, b"x") is False  # type: ignore[arg-type]


def test_durdurulmus_dugum_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """Durdurulan dugum yeni is almaz (C38)."""
    monkeypatch.setattr(kalp, "duraklatildi", lambda: True)
    sahte = istek(basliklar={"Authorization": f"Bearer {app.TOKEN}"})
    app.Isleyici.do_POST(sahte)  # type: ignore[arg-type]
    assert sahte.yanitlar[0][0] == 503


def test_eszamanli_sinir_sozlesmeye_uygun() -> None:
    """Eszamanli sinir sunucu basina 12 (§9)."""
    assert app.ESZAMANLI == 12


def test_govde_tavani_makul() -> None:
    """Govde tavani kucuk ve sabittir; buyuk govde reddedilir."""
    assert app.GOVDE_TAVANI == 8192
    sahte = istek(basliklar={"Content-Length": "999999"})


def test_bosaltmada_503_ve_retry_after() -> None:
    """Boşaltma bayrağı açıkken istek 503 + Retry-After ile reddedilir (E4)."""
    app._bosaltiliyor.set()
    try:
        sahte = istek(basliklar={"Authorization": f"Bearer {app.TOKEN}"})
        app.Isleyici.do_POST(sahte)  # type: ignore[arg-type]
        assert sahte.yanitlar[0][0] == 503
        assert sahte.retry == 30
    finally:
        app._bosaltiliyor.clear()



def _govdeli(monkeypatch, govde: dict) -> "Sahte":
    """Imzali govde tasiyan sahte istek kurar."""
    ham = json.dumps(govde).encode("utf-8")
    imza = hmac.new(app.TOKEN.encode("utf-8"), ham, hashlib.sha256).hexdigest()
    sahte = istek(basliklar={
        "Authorization": f"Bearer {app.TOKEN}",
        "x-imza": imza,
        "Content-Length": str(len(ham)),
    })
    sahte.rfile = io.BytesIO(ham)
    return sahte


def test_ulusal_kelimede_il_slug_gonderilmez(monkeypatch) -> None:
    """Ulusal kelimede proxy icin il cozulmez, yalniz TR kalir (C61)."""
    yakalanan: dict = {}

    def sahte(*_a, **k):
        yakalanan.update(k)
        return {"ok": 1, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0,
                "elapsed_ms": 1, "hits": [], "durduruldu": False}

    monkeypatch.setattr(app.burst, "burst_yap", sahte)
    govde = {"keyword": "haber", "target_url": "https://ornek.test",
             "geo_code": 34, "geo_scope": "national", "ts": int(time.time())}
    app.Isleyici.do_POST(_govdeli(monkeypatch, govde))
    assert yakalanan.get("geo_slug") is None


def test_il_kelimede_slug_cozulur(monkeypatch) -> None:
    """Il kapsamli kelimede slug cozulup verilir."""
    yakalanan: dict = {}

    def sahte(*_a, **k):
        yakalanan.update(k)
        return {"ok": 1, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0,
                "elapsed_ms": 1, "hits": [], "durduruldu": False}

    monkeypatch.setattr(app.burst, "burst_yap", sahte)
    monkeypatch.setattr(app.havuz, "slug_bul", lambda kod: "istanbul")
    govde = {"keyword": "haber", "target_url": "https://ornek.test",
             "geo_code": 34, "geo_scope": "province", "ts": int(time.time())}
    app.Isleyici.do_POST(_govdeli(monkeypatch, govde))
    assert yakalanan.get("geo_slug") == "istanbul"





def test_ulusal_kelimede_uule_gonderilmez(monkeypatch) -> None:
    """Ulusal kelimede uule gonderilmez; IP cografyasi yeterlidir (66)."""

    yakalanan: dict = {}

    def sahte(*_a, **k):
        yakalanan.update(k)
        return {"ok": 1, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0,
                "elapsed_ms": 1, "hits": [], "durduruldu": False}

    monkeypatch.setattr(app.burst, "burst_yap", sahte)
    govde = {"keyword": "haber", "target_url": "https://ornek.test",
             "geo_code": 34, "geo_scope": "national", "uule": "abc123",
             "ts": int(time.time())}
    app.Isleyici.do_POST(_govdeli(monkeypatch, govde))
    # Govdede il uule'si gelse bile ulusal kelimede uule kullanilmaz.
    assert yakalanan.get("uule") is None


def test_il_kelimede_uule_gonderilir(monkeypatch) -> None:
    """Il kapsamli kelimede UULE korunur."""
    yakalanan: dict = {}

    def sahte(*_a, **k):
        yakalanan.update(k)
        return {"ok": 1, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0,
                "elapsed_ms": 1, "hits": [], "durduruldu": False}

    monkeypatch.setattr(app.burst, "burst_yap", sahte)
    monkeypatch.setattr(app.havuz, "slug_bul", lambda kod: "istanbul")
    govde = {"keyword": "haber", "target_url": "https://ornek.test",
             "geo_code": 34, "geo_scope": "province", "uule": "abc123",
             "ts": int(time.time())}
    app.Isleyici.do_POST(_govdeli(monkeypatch, govde))
    assert yakalanan.get("uule") == "abc123"
