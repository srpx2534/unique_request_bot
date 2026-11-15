"""Uyari turlerinin gercekten uretildigini dogrular (55).

Sema turleri sabittir; biri uretilmezse panelde o tur hic gorunmez. Test
kaynagi tarar, veritabanina cikmaz.
"""

from __future__ import annotations

import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
TURLER = (
    "captcha",
    "provider_down",
    "queue_lag",
    "quota",
    "fallback_high",
    "hedef_yok",
    "failover",
    "burst_hata",
    "partition",
    "kilit_cakismasi",
)
CAGRI = re.compile(r'uyari\(\s*"(\w+)"')
DEGER = re.compile(r"VALUES\s*\(\s*'(\w+)'")


def _uretilenler() -> set[str]:
    bulunan: set[str] = set()
    for yol in list((KOK / "worker").rglob("*.py")) + list((KOK / "src").rglob("*.ts")):
        if yol.name.startswith("test_") or yol.name.endswith(".test.ts"):
            continue
        metin = yol.read_text(encoding="utf-8")
        bulunan.update(CAGRI.findall(metin))
        bulunan.update(DEGER.findall(metin))
    return bulunan


def test_her_tur_uretilir() -> None:
    eksik = [tur for tur in TURLER if tur not in _uretilenler()]
    assert not eksik, f"uretilmeyen uyarilar: {eksik}"