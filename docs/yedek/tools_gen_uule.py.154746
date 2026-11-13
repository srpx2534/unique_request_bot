"""geo koordinatlarÃ„Â±ndan uule deÃ„Å¸eri ÃƒÂ¼retir ve SQL dosyasÃ„Â± yazar.

uule, Google'a "Ã…Å¸u noktadan aranmÃ„Â±Ã…Å¸" demenin yoludur. Ã…Âehir hedefleyen proxy
bulunamadÃ„Â±Ã„Å¸Ã„Â±nda SERP'in doÃ„Å¸ru ili gÃƒÂ¶stermesi iÃƒÂ§in kullanÃ„Â±lÃ„Â±r; tÃ„Â±klama IP'sini
deÃ„Å¸iÃ…Å¸tirmez. Format Google tarafÃ„Â±ndan belgelenmemiÃ…Å¸tir, bu yÃƒÂ¼zden deÃ„Å¸erler
ampirik olarak doÃ„Å¸rulanÃ„Â±r.

Girdi : db/init/003_geo.sql (lat/lon)
Ãƒâ€¡Ã„Â±ktÃ„Â± : db/init/004_uule.sql (UPDATE ifadeleri)
BaÃ„Å¸Ã„Â±mlÃ„Â±lÃ„Â±k yoktur; Windows ve Linux'ta aynÃ„Â± ÃƒÂ§alÃ„Â±Ã…Å¸Ã„Â±r.
"""

from __future__ import annotations

import base64
import re
import sys
import time
from pathlib import Path

# Proje kÃƒÂ¶kÃƒÂ¼: bu dosyanÃ„Â±n iki ÃƒÂ¼st dizini. Windows'ta da doÃ„Å¸ru ÃƒÂ§ÃƒÂ¶zÃƒÂ¼lÃƒÂ¼r.
KOK = Path(__file__).resolve().parents[1]
GEO_SQL = KOK / "db" / "migrations" / "003_geo.sql"
CIKTI_SQL = KOK / "db" / "migrations" / "004_uule.sql"

# Ã…Âehir yarÃ„Â±ÃƒÂ§apÃ„Â± metre cinsinden. 65 km, il merkezini ve ÃƒÂ§evresini kapsar.
YARICAP_M = 65_000

# geo satÃ„Â±rlarÃ„Â±nÃ„Â± yakalayan desen: (kod, lat, lon)
SATIR_DESENI = re.compile(r"\((\d+),'[^']*','[^']*',\d+,([\d.]+),([\d.]+)\)")


def uule_uret(lat: str, lon: str) -> str:
    """Verilen koordinat iÃƒÂ§in uule dizesi dÃƒÂ¶ndÃƒÂ¼rÃƒÂ¼r.

    Args:
        lat: Enlem, ondalÃ„Â±k metin.
        lon: Boylam, ondalÃ„Â±k metin.

    Returns:
        Google'Ã„Â±n beklediÃ„Å¸i w+CAIQICI ÃƒÂ¶nekli kodlanmÃ„Â±Ã…Å¸ dize.
    """
    # Zaman damgasÃ„Â± milisaniye; Google tazelik kontrolÃƒÂ¼nde kullanÃ„Â±r.
    zaman = int(time.time() * 1000)
    govde = (
        f"role:1 producer:12 provenance:6 timestamp:{zaman} "
        f"latlng:{lat},{lon} radius:{YARICAP_M}"
    )
    # Base64 URL-gÃƒÂ¼venli, dolgu karakterleri atÃ„Â±lÃ„Â±r.
    kodlu = base64.urlsafe_b64encode(govde.encode("utf-8")).decode().rstrip("=")
    return "w+CAIQICI" + kodlu


def main() -> int:
    """Seed dosyasÃ„Â±nÃ„Â± okur, uule SQL'i ÃƒÂ¼retir. Hata varsa 1 dÃƒÂ¶ner."""
    if not GEO_SQL.exists():
        print(f"HATA: seed dosyasÃ„Â± bulunamadÃ„Â±: {GEO_SQL}")
        return 1

    icerik = GEO_SQL.read_text(encoding="utf-8")
    satirlar = SATIR_DESENI.findall(icerik)

    if len(satirlar) != 81:
        print(f"HATA: 81 il bekleniyordu, {len(satirlar)} bulundu.")
        return 1

    parcalar = [
        "-- ÃƒÅ“retilmiÃ…Å¸ dosya. Elle dÃƒÂ¼zenlenmez.",
        "-- Kaynak: tools/gen_uule.py, girdi: 003_geo.sql",
        "SET NAMES utf8mb4;",
    ]
    # Her il iÃƒÂ§in tek UPDATE; kod plaka kodudur.
    for kod, lat, lon in satirlar:
        parcalar.append(f"UPDATE geo SET uule='{uule_uret(lat, lon)}' WHERE code={kod};")

    CIKTI_SQL.write_text("\n".join(parcalar) + "\n", encoding="utf-8", newline="\n")
    print(f"OK: {len(satirlar)} il iÃƒÂ§in uule yazÃ„Â±ldÃ„Â± -> {CIKTI_SQL.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())