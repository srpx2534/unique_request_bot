"""Worker HTTP ucu testleri.

Soket acilmaz; isleyici nesnesi taklit edilir. Token, imza, durdurma ve
bilinmeyen yol davranisi dogrulanir.
"""

from __future__ import annotations

import hashlib
import hmac
import json

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

    def _json(self, kod: int, govde: dict) -> None:
        self.yanitlar.append((kod, govde))

    # Gercek sinifin dogrulama metotlari sahteye baglanir; boylece testte
    # kopya mantik tutulmaz, uretimdeki kod kosar.
    _yetkili = app.Isleyici._yetkili
    _imza_dogrula = app.Isleyici._imza_dogrula
    _ham_oku = app.Isleyici._ham_oku


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
    assert app.Isleyici._ham_oku(sahte) is None  # type: ignore[arg-type]