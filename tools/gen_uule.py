"""geo koordinatlarından uule değeri üretir ve SQL dosyası yazar.

uule, Google'a "şu noktadan aranmış" demenin yoludur. Şehir hedefleyen proxy
bulunamadığında SERP'in doğru ili göstermesi için kullanılır; tıklama IP'sini
değiştirmez. Format Google tarafından belgelenmemiştir, bu yüzden değerler
ampirik olarak doğrulanır.

Girdi : db/init/003_geo.sql (lat/lon)
Çıktı : db/init/004_uule.sql (UPDATE ifadeleri)
Bağımlılık yoktur; Windows ve Linux'ta aynı çalışır.
"""

from __future__ import annotations

import base64
import re
import sys
import time
from pathlib import Path

# Proje kökü: bu dosyanın iki üst dizini. Windows'ta da doğru çözülür.
KOK = Path(__file__).resolve().parents[1]
GEO_SQL = KOK / "db" / "init" / "003_geo.sql"
CIKTI_SQL = KOK / "db" / "init" / "004_uule.sql"

# Şehir yarıçapı metre cinsinden. 65 km, il merkezini ve çevresini kapsar.
YARICAP_M = 65_000

# geo satırlarını yakalayan desen: (kod, lat, lon)
SATIR_DESENI = re.compile(r"\((\d+),'[^']*','[^']*',\d+,([\d.]+),([\d.]+)\)")


def uule_uret(lat: str, lon: str) -> str:
    """Verilen koordinat için uule dizesi döndürür.

    Args:
        lat: Enlem, ondalık metin.
        lon: Boylam, ondalık metin.

    Returns:
        Google'ın beklediği w+CAIQICI önekli kodlanmış dize.
    """
    # Zaman damgası milisaniye; Google tazelik kontrolünde kullanır.
    zaman = int(time.time() * 1000)
    govde = (
        f"role:1 producer:12 provenance:6 timestamp:{zaman} "
        f"latlng:{lat},{lon} radius:{YARICAP_M}"
    )
    # Base64 URL-güvenli, dolgu karakterleri atılır.
    kodlu = base64.urlsafe_b64encode(govde.encode("utf-8")).decode().rstrip("=")
    return "w+CAIQICI" + kodlu


def main() -> int:
    """Seed dosyasını okur, uule SQL'i üretir. Hata varsa 1 döner."""
    if not GEO_SQL.exists():
        print(f"HATA: seed dosyası bulunamadı: {GEO_SQL}")
        return 1

    icerik = GEO_SQL.read_text(encoding="utf-8")
    satirlar = SATIR_DESENI.findall(icerik)

    if len(satirlar) != 81:
        print(f"HATA: 81 il bekleniyordu, {len(satirlar)} bulundu.")
        return 1

    parcalar = [
        "-- Üretilmiş dosya. Elle düzenlenmez.",
        "-- Kaynak: tools/gen_uule.py, girdi: 003_geo.sql",
        "SET NAMES utf8mb4;",
    ]
    # Her il için tek UPDATE; kod plaka kodudur.
    for kod, lat, lon in satirlar:
        parcalar.append(f"UPDATE geo SET uule='{uule_uret(lat, lon)}' WHERE code={kod};")

    CIKTI_SQL.write_text("\n".join(parcalar) + "\n", encoding="utf-8", newline="\n")
    print(f"OK: {len(satirlar)} il için uule yazıldı -> {CIKTI_SQL.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())