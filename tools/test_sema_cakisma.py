"""001 sema dosyasi ile migration'lar ayni kolonu eklemesin.

001 sonradan eklenen kolonlarla elle yamalaniyor. Bir kolon hem 001'de hem
ADD COLUMN migration'inda durursa temiz kurulum 1060 "Duplicate column" ile
duser: 045 (hit.tur) ve 046 (provider.hata_sayac) tam olarak boyle patladi.
"""

from __future__ import annotations

import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
DIZIN = KOK / "db" / "migrations"
SEMA = DIZIN / "001_schema.sql"

TABLO = re.compile(r"CREATE TABLE (\w+) \((.*?)\n\) ENGINE", re.S)
KOLON = re.compile(r"^\s{2}(\w+)\s", re.M)
EKLE = re.compile(r"ALTER TABLE (\w+)\s+ADD\s+(?:COLUMN\s+)?(\w+)", re.I)
# ADD KEY / ADD INDEX gibi kolon olmayan eklemeler.
ANAHTAR_KELIMELER = {"KEY", "INDEX", "PRIMARY", "UNIQUE", "CONSTRAINT", "FOREIGN", "FULLTEXT", "SPATIAL"}


def _sema_kolonlari() -> set[tuple[str, str]]:
    """001'deki (tablo, kolon) ciftleri."""
    kume: set[tuple[str, str]] = set()
    for eslesme in TABLO.finditer(SEMA.read_text(encoding="utf-8")):
        tablo, govde = eslesme.group(1), eslesme.group(2)
        for kolon in KOLON.finditer(govde):
            kume.add((tablo, kolon.group(1)))
    return kume


def test_eklenen_kolon_001_de_zaten_yok() -> None:
    """ADD COLUMN ile gelen kolon 001'de bulunmamali."""
    var = _sema_kolonlari()
    assert var, "001 sema dosyasi okunamadi"

    cakisan: list[str] = []
    for dosya in sorted(DIZIN.glob("*.sql")):
        if dosya.name.startswith("001"):
            continue
        for no, satir in enumerate(dosya.read_text(encoding="utf-8").splitlines(), 1):
            for eslesme in EKLE.finditer(satir):
                anahtar = (eslesme.group(1), eslesme.group(2))
                if anahtar[1].upper() in ANAHTAR_KELIMELER:
                    continue
                if anahtar in var:
                    cakisan.append(f"{dosya.name}:{no} -> {anahtar[0]}.{anahtar[1]}")

    assert not cakisan, "001'de olan kolon tekrar ekleniyor: " + "; ".join(cakisan)
