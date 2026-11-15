"""Dosya boyutu esikleri (§23.2).

Proje calisir hale gelene kadar bolme yapilmaz. Bu yuzden iki esik var:
450 satir bolme hedefi, yalnizca raporlanir; 800 satir sert tavan, asilirsa
test kirilir. Boylece calisan hatti bolmeye zorlamadan gercek sismeyi yakalariz.
"""

from __future__ import annotations

from pathlib import Path

SINIR = 450  # bolme hedefi; proje bitene kadar zorunlu degil
SERT_SINIR = 800  # gercek tavan; asilirsa bolme kacinilmaz
KOK = Path(__file__).resolve().parents[1]
# Arayuz bilesenleri dogal olarak uzun; sinir oraya da uygulanir ama yuksek.
# Liste bir borc listesidir: dosya bolundukce buradan duser.
IZINLI = {
    "worker/havuz.py",
    "src/web/sayfa/cerezler.tsx",
}


def _dosyalar():
    for kok in (KOK / "worker", KOK / "src"):
        for yol in kok.rglob("*"):
            if yol.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if yol.name.startswith("test_") or yol.name.endswith(".test.ts"):
                continue
            yield yol


def test_sert_sinir_asilmaz() -> None:
    """Sert tavan asilirsa bolme kacinilmaz olur."""
    asanlar = {}
    for yol in _dosyalar():
        satir = len(yol.read_text(encoding="utf-8").splitlines())
        if satir > SERT_SINIR:
            asanlar[yol.relative_to(KOK).as_posix()] = satir
    beklenmeyen = {k: v for k, v in asanlar.items() if k not in IZINLI}
    assert not beklenmeyen, f"sert siniri asan yeni dosyalar: {beklenmeyen}"


def test_bolme_adaylari() -> None:
    """Hedef sinirin ustundekiler bilgi olarak yazilir; bolme zorunlu degil."""
    adaylar = {}
    for yol in _dosyalar():
        satir = len(yol.read_text(encoding="utf-8").splitlines())
        if satir > SINIR:
            adaylar[yol.relative_to(KOK).as_posix()] = satir
    print(f"bolme adaylari: {adaylar}")