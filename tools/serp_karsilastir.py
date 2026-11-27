"""Proxy'li olcum ile ayni dakikadaki yerel aramayi karsilastirir (80).

Referans sabit liste degil, bu makinenin kendi IP'sinden yapilan aramadir;
liste her seferinde degistigi icin ancak boyle dogru olur. Iki arama ayni
profille, ayni dakikada kosar; tek fark proxy.

Kullanim: python tools/serp_karsilastir.py "erzurum escort" [--sehir slug]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker import tarayici  # noqa: E402
from worker.serp_ortak import kok  # noqa: E402


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


def kume(organik: list[dict]) -> list[str]:
    """Organik kayitlardan benzersiz kok listesi cikarir."""
    adlar: list[str] = []
    for kayit in organik:
        k = kok(str(kayit.get("link") or ""))
        if k and k not in adlar:
            adlar.append(k)
    return adlar


def main() -> int:
    """Yerel ve proxy'li aramayi karsilastirir."""
    ayar = argparse.ArgumentParser(description="Yerel arama ile proxy olcumu")
    ayar.add_argument("kelime")
    ayar.add_argument("--sehir", default=None, help="il slug ile sehir hedefli IP")
    ayar.add_argument("--sayfa", type=int, default=2, help="taranacak sayfa sayisi")
    ayar.add_argument("--referans", type=Path, default=None, help="sabit referans dosyasi")
    ayar.add_argument("--temiz", action="store_true", help="gizli pencere gibi temiz profil")
    secim = ayar.parse_args()

    if secim.temiz:
        import tempfile

        from worker import guven

        tarayici.PROFIL = Path(tempfile.mkdtemp(prefix="temiz_"))
        guven.uygula = lambda *fazla, **adli: False

    if not tarayici.kullanilabilir():
        print("tarayici yok: playwright kurulu degil")
        return 1

    if secim.referans:
        yerel_kume = liste_oku(secim.referans)[:20]
        print(f"referans dosyasi: {len(yerel_kume)} site")
    else:
        # Kisa isinma: arac hizli kossun, gercek olcum 20-45 sn ile calisir.
        yerel = tarayici.serp_oku(secim.kelime, azami=secim.sayfa, proxy_yok=True,
                                  isinma_aralik=(3_000, 5_000))
        print(f"yerel: {yerel['result']} · {len(yerel['organik'])} sonuc")
        if yerel["result"] not in ("ok", "not_found"):
            print(f"yerel dustu: {yerel['mesaj'][:160]}")
            return 1
        # Sozlesme olcusu ilk 20: derinlik farki orani bozuyordu.
        yerel_kume = kume(yerel["organik"])[:20]

    uzak = tarayici.serp_oku(secim.kelime, azami=secim.sayfa, sehir=secim.sehir,
                             isinma_aralik=(3_000, 5_000))
    print(f"proxy: {uzak['result']} · {len(uzak['organik'])} sonuc")
    if uzak["result"] not in ("ok", "not_found"):
        print(f"proxy dustu: {uzak['mesaj'][:160]}")
        return 1

    yerler: dict[str, int] = {}
    for kayit in uzak["organik"]:
        k = kok(str(kayit.get("link") or ""))
        if k and k not in yerler:
            yerler[k] = kayit["position"]

    print("--- yerel liste (referans) ---")
    bulunan = 0
    for ad in yerel_kume:
        yer = yerler.get(ad)
        if yer:
            bulunan += 1
        print(f"  {'VAR' if yer else 'YOK'}  {ad}" + (f" · sira {yer}" if yer else ""))

    oran = bulunan / len(yerel_kume) if yerel_kume else 0.0
    print(f"bulunabilirlik: {bulunan}/{len(yerel_kume)} = %{round(oran * 100, 1)}")
    return 0 if bulunan == len(yerel_kume) else 2


if __name__ == "__main__":
    raise SystemExit(main())