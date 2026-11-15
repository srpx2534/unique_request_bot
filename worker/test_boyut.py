"""250 satir siniri (§23.2).

Sinirin ustundeki dosyalar izin listesinde tutulur; bolundukce liste kuculur.
Listede olmayan bir dosya siniri asarsa test kirilir.
"""

from __future__ import annotations

from pathlib import Path

SINIR = 250
KOK = Path(__file__).resolve().parents[1]
IZINLI = {
    "worker/havuz.py",
    "worker/saglik_db.py",
}


def _dosyalar():
    for kok in (KOK / "worker", KOK / "src"):
        for yol in kok.rglob("*"):
            if yol.suffix not in {".py", ".ts"}:
                continue
            if yol.name.startswith("test_") or yol.name.endswith(".test.ts"):
                continue
            yield yol


def test_sinir_asilmaz() -> None:
    asanlar = {}
    for yol in _dosyalar():
        satir = len(yol.read_text(encoding="utf-8").splitlines())
        if satir > SINIR:
            asanlar[yol.relative_to(KOK).as_posix()] = satir
    beklenmeyen = {k: v for k, v in asanlar.items() if k not in IZINLI}
    assert not beklenmeyen, f"sinir asan yeni dosyalar: {beklenmeyen}"
