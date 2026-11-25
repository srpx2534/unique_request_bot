"""API sirasi ile gercek tarayici sirasini karsilastirir.

EKSIKLER O bolumunun kapanis olcusu budur: ayni kelime icin API'den gelen
ilk 20 sonuc kumesi ile tarayicidan gelen kume ortusmeli. Ortusme %90'in
altindaysa olcum gercegi temsil etmiyor demektir.

Ayrica hedef sitenin iki taraftaki sirasi yazilir; asil soru "bizim site
kacta" oldugu icin siralar arasindaki fark dogrudan gorunur.

SERP anahtari yoksa araç API'yi atlar ve tarayicinin kendi kararliligini
olcer (iki ardisik okuma). Boylece anahtar gelmeden de sayfa kararliligi
hakkinda fikir verir.

Kullanim:
    python tools/serp_karsilastir.py --db --tarayici
    python tools/serp_karsilastir.py kelimeler.txt --tarayici
    python tools/serp_karsilastir.py kelimeler.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker import ayar, serp, tarayici  # noqa: E402
from worker.serp_ortak import ULKE_UULE, kok  # noqa: E402

LIMIT = 20  # karsilastirilan sira sayisi
ESIK = 90.0  # yuzde; altinda kelime basarisiz sayilir


def _kume(sonuc: dict) -> list[str]:
    """Sonucun ilk LIMIT kok alan adini sirayla verir."""
    return [kok(str(k.get("link") or "")) for k in (sonuc.get("organik") or [])[:LIMIT]]


def _sira(kume: list[str], hedef: str) -> str:
    """Hedefin sirada karsiligi; yoksa 'yok'."""
    kok_hedef = kok(hedef)
    for sira, adres in enumerate(kume, start=1):
        if adres == kok_hedef:
            return str(sira)
    return "yok"


def _ortusme(a: list[str], b: list[str]) -> float:
    """Iki kume icin yuzde ortusme; ikisi de bossa 0."""
    kume_a, kume_b = set(a), set(b)
    if not kume_a or not kume_b:
        return 0.0
    return len(kume_a & kume_b) * 100 / max(len(kume_a), len(kume_b))


def _db_kelimeler(adet: int) -> list[tuple[str, str]]:
    """Aktif kelimeleri site alan adiyla verir."""
    from tools import db  # noqa: PLC0415

    baglanti = db.baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT k.text, s.domain FROM keyword k JOIN site s ON s.id = k.site_id"
                " WHERE k.state = 'active' AND s.active = 1 ORDER BY k.id LIMIT %s",
                (adet,),
            )
            return [(str(a), str(b)) for a, b in imlec.fetchall()]
    finally:
        baglanti.close()


def main() -> int:
    """Kelimeleri karsilastirir; ortalama esigin altindaysa 1 doner."""
    ayristirici = argparse.ArgumentParser(description="API ile tarayici sirasini karsilastir")
    ayristirici.add_argument("dosya", nargs="?", help="her satirda 'kelime<TAB>domain'")
    ayristirici.add_argument("--db", action="store_true", help="kelimeleri veritabanindan al")
    ayristirici.add_argument("--adet", type=int, default=10, help="db'den alinacak kelime")
    ayristirici.add_argument("--tarayici", action="store_true", help="tarayici yolunu kullan")
    arguman = ayristirici.parse_args()

    if arguman.db:
        ciftler = _db_kelimeler(arguman.adet)
    elif arguman.dosya:
        ciftler = []
        for satir in Path(arguman.dosya).read_text(encoding="utf-8").splitlines():
            if not satir.strip():
                continue
            parca = satir.split("\t")
            ciftler.append((parca[0].strip(), parca[1].strip() if len(parca) > 1 else ""))
    else:
        print("kelime kaynagi yok: dosya ya da --db ver")
        return 1

    if not ciftler:
        print("kelime bulunamadi")
        return 1
    if not arguman.tarayici:
        print("UYARI: --tarayici verilmedi, API'nin kendi tekrari olculur")

    _, anahtar = ayar.serp_secim()
    if not anahtar:
        print("UYARI: SERP anahtari yok, API tarafi bos kalir; kararlilik olculur")

    toplam = 0.0
    for kelime, domain in ciftler:
        # Hedef verilmemisse 1. okumadaki 10. sonuc baz alinir. Boylece
        # uydurma domain gerekmez; kiyas gercek bir rakip uzerinden yapilir
        # ve o rakibin iki okumadaki sirasi karsilastirilir.
        if arguman.tarayici:
            birinci = _kume(tarayici.serp_oku(kelime, domain=domain or None))
        else:
            birinci = _kume(serp.serp_getir(kelime, hedef_domain=domain or None, uule=ULKE_UULE))
        if not domain:
            domain = birinci[9] if len(birinci) >= 10 else (birinci[-1] if birinci else "")
            print(f"       hedef otomatik: {domain or '-'} (1. okuma)")
        if arguman.tarayici:
            ikinci = _kume(tarayici.serp_oku(kelime, domain=domain or None))
            etiket = "tarayici"
        else:
            ikinci = _kume(serp.serp_getir(kelime, hedef_domain=domain or None, uule=ULKE_UULE))
            etiket = "api"
        oran = _ortusme(birinci, ikinci)
        toplam += oran
        print(
            f"{oran:5.1f}%  {etiket:9s} s1={_sira(birinci, domain):>4s}"
            f" s2={_sira(ikinci, domain):>4s}  {kelime}  [{domain}]"
        )

    ortalama = toplam / len(ciftler)
    print(f"\nORTALAMA: {ortalama:.1f}%  esik: {ESIK:.0f}%  kelime: {len(ciftler)}")
    return 0 if ortalama >= ESIK else 1


if __name__ == "__main__":
    raise SystemExit(main())