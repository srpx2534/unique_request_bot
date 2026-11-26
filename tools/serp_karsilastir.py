"""Tarayici SERP'ini referans listeyle karsilastirir (80).

Referans, kullanicinin kendi tarayicisinda gordugu listedir. Olcumun basarisi
"hedef site bulunabiliyor mu" sorusudur; siralama degil bulunabilirlik esastir.

Kullanim: python tools/serp_karsilastir.py "erzurum escort" [--referans dosya]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker import tarayici  # noqa: E402
from worker.serp_ortak import kok  # noqa: E402

REFERANS = Path(__file__).resolve().parent / "veri" / "serp_referans.txt"


def liste_oku(yol: Path) -> list[str]:
    """Referans dosyasini kok alan adlari listesine cevirir."""
    adlar: list[str] = []
    for satir in yol.read_text(encoding="utf-8").splitlines():
        ham = satir.strip().lower()
        if not ham or ham.startswith("#"):
            continue
        k = kok(ham)
        if k and k not in adlar:
            adlar.append(k)
    return adlar


def main() -> int:
    """Tarayici listesini referansla karsilastirir."""
    ayar = argparse.ArgumentParser(description="Referans listeye gore bulunabilirlik")
    ayar.add_argument("kelime")
    ayar.add_argument("--referans", type=Path, default=REFERANS)
    secim = ayar.parse_args()

    if not secim.referans.exists():
        print(f"referans yok: {secim.referans}")
        return 1
    referans = liste_oku(secim.referans)
    if not referans:
        print("referans bos")
        return 1
    if not tarayici.kullanilabilir():
        print("tarayici yok: playwright kurulu degil")
        return 1

    cevap = tarayici.serp_oku(secim.kelime)
    print(f"kelime: {secim.kelime} · sonuc: {cevap['result']} · bulunan: {len(cevap['organik'])}")
    if cevap["result"] not in ("ok", "not_found"):
        print(f"mesaj: {cevap['mesaj'][:200]}")
        return 1

    yerler: dict[str, int] = {}
    for kayit in cevap["organik"]:
        k = kok(str(kayit.get("link") or ""))
        if k and k not in yerler:
            yerler[k] = kayit["position"]

    print("--- tarayicida gorunenler ---")
    for kayit in cevap["organik"][:20]:
        print(f"  {kayit['position']:02d} {kayit['link']}")

    print("--- referans ---")
    bulunan = 0
    for ad in referans:
        yer = yerler.get(ad)
        if yer:
            bulunan += 1
        print(f"  {'VAR' if yer else 'YOK'}  {ad}" + (f" · sira {yer}" if yer else ""))

    oran = bulunan / len(referans)
    print(f"bulunabilirlik: {bulunan}/{len(referans)} = %{round(oran * 100, 1)}")
    return 0 if bulunan == len(referans) else 2


if __name__ == "__main__":
    raise SystemExit(main())