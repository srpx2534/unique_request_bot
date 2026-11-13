"""hit tablosunu gunluk bolumlere ayirir ve suresi dolan bolumleri duser.

Saklama 30 gun oldugu icin bolum granulerligi de gun: bolum siniri saklama
siniriyla ayni olcek. Boylece saklama, milyonlarca satirlik DELETE yerine
metadata islemine (DROP PARTITION) donusur.

Partition kolonu her benzersiz anahtarda bulunmak zorunda oldugu icin birincil
anahtar (id, created_at) bicimindedir. hit uzerinde baska benzersiz anahtar ve
yabanci anahtar yoktur; ikisi de bu tasarimi kolaylastirir.

Aylik bolum varsa gunluge cevrilir: 30 gunluk saklamada aylik bolum cok kaba.

Kullanim:
    python tools/hit_partition.py            # kur, ileri gunleri ac, eskileri dus
    python tools/hit_partition.py --durum    # sadece rapor
    python tools/hit_partition.py --ileri 14 # kac gun ileri acilacak
"""

from __future__ import annotations

import re
import sys
from datetime import date, timedelta

sys.path.insert(0, "tools")

from db import baglan  # noqa: E402

ILERI_GUN = 7  # gun; pmax yuvasi bu kadar ileriye bolunur
SAKLAMA_GUN = 30  # gun; §6.3
AZAMI_BOLUM = 400  # emniyet; sinirsiz buyumesin
PMAX = "pmax"
GUN_DESENI = re.compile(r"^p(\d{8})$")


def _bolumler(imlec) -> list[tuple[str, int]]:
    """Bolum adi ve ust sinirini (TO_DAYS) verir."""
    imlec.execute(
        "SELECT PARTITION_NAME, PARTITION_DESCRIPTION FROM information_schema.PARTITIONS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit'"
        " AND PARTITION_NAME IS NOT NULL AND PARTITION_NAME <> %s"
        " ORDER BY PARTITION_ORDINAL_POSITION",
        (PMAX,),
    )
    return [(ad, int(aciklama)) for ad, aciklama in imlec.fetchall()]


def _aylik_mi(bolumler: list[tuple[str, int]]) -> bool:
    """Bolum adlari gunluk degil de aylik kalipta mi."""
    return bool(bolumler) and not any(GUN_DESENI.match(ad) for ad, _ in bolumler)


def _tanim(gun: date) -> str:
    """Tek gunun bolum tanimi; gun kendi ust sinirina dahil edilir."""
    return (
        f"PARTITION p{gun:%Y%m%d} VALUES LESS THAN (TO_DAYS('{gun:%Y-%m-%d}') + 1)"
    )


def _kur(imlec, bugun: date) -> None:
    """Gunluk bolumleri kurar; eski aylik kalip once kaldirilir."""
    if _aylik_mi(_bolumler(imlec)):
        imlec.execute("ALTER TABLE hit REMOVE PARTITIONING")
        print("aylik kalip kaldirildi")

    imlec.execute("ALTER TABLE hit DROP PRIMARY KEY, ADD PRIMARY KEY (id, created_at)")
    gunler = [bugun - timedelta(days=g) for g in range(SAKLAMA_GUN, -1, -1)]
    gunler += [bugun + timedelta(days=g) for g in range(1, ILERI_GUN + 1)]
    tanimlar = [_tanim(g) for g in gunler]
    tanimlar.append(f"PARTITION {PMAX} VALUES LESS THAN MAXVALUE")
    imlec.execute(
        "ALTER TABLE hit PARTITION BY RANGE (TO_DAYS(created_at)) ("
        + ", ".join(tanimlar) + ")"
    )
    print(f"gunluk bolumlendi: {len(gunler)} gun + {PMAX}")


def _ileri_ac(imlec, bugun: date, ileri: int) -> int:
    """Eksik gelecek gunleri pmax'i bolerek acar."""
    var = {ad for ad, _ in _bolumler(imlec)}
    eksik = [
        bugun + timedelta(days=g)
        for g in range(1, ileri + 1)
        if f"p{bugun + timedelta(days=g):%Y%m%d}" not in var
    ]
    if not eksik:
        return 0
    if len(var) + len(eksik) > AZAMI_BOLUM:
        print(f"UYARI: bolum sayisi {AZAMI_BOLUM} uzerine cikiyor")
    tanimlar = [_tanim(g) for g in eksik]
    tanimlar.append(f"PARTITION {PMAX} VALUES LESS THAN MAXVALUE")
    imlec.execute(
        f"ALTER TABLE hit REORGANIZE PARTITION {PMAX} INTO (" + ", ".join(tanimlar) + ")"
    )
    return len(eksik)


def _eskileri_dus(imlec, bugun: date, saklama: int) -> int:
    """Saklama suresi dolmus bolumleri duser."""
    # Sinir TO_DAYS cinsinden okunur; Python ordinal'i ile karistirilmaz.
    imlec.execute("SELECT TO_DAYS(%s)", (bugun - timedelta(days=saklama),))
    sinir = int(imlec.fetchone()[0])
    eski = [
        ad for ad, ust in _bolumler(imlec)
        if GUN_DESENI.match(ad) and ust <= sinir
    ]
    if not eski:
        return 0
    imlec.execute("ALTER TABLE hit DROP PARTITION " + ", ".join(eski))
    return len(eski)


def main() -> int:
    """Kurulum, ileri acma ve saklama islemlerini yurutur."""
    ileri = ILERI_GUN
    if "--ileri" in sys.argv:
        ileri = int(sys.argv[sys.argv.index("--ileri") + 1])

    bugun = date.today()
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            bolumler = _bolumler(imlec)
            imlec.execute("SELECT COUNT(*) FROM hit")
            adet = imlec.fetchone()[0]
            print(f"hit: {adet} satir · bolum: {len(bolumler)} · bugun: {bugun}")
            if "--durum" in sys.argv:
                for ad, ust in bolumler:
                    print(f"  {ad} · ust {ust}")
                return 0

            if not bolumler:
                _kur(imlec, bugun)
            elif _aylik_mi(bolumler):
                _kur(imlec, bugun)

            print(f"ileri acilan gun: {_ileri_ac(imlec, bugun, ileri)}")
            print(f"dusen bolum: {_eskileri_dus(imlec, bugun, SAKLAMA_GUN)}")

            imlec.execute(
                "SELECT PARTITION_NAME FROM information_schema.PARTITIONS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit'"
                " AND PARTITION_NAME IS NOT NULL"
            )
            print(f"toplam bolum: {len(imlec.fetchall())}")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())