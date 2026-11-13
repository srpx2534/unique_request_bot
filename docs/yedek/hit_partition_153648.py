"""hit tablosunu aylik bolumlere ayirir.

Sozlesme §6.3: partition, hit 10 milyon satiri gecince eklenir. Bu yuzden
migration degil arac; esik dolmadan calistirmak zararsizdir, islem yapmaz.

Partition kolonu her benzersiz anahtarda bulunmak zorunda oldugu icin once
birincil anahtar (id, created_at) olarak yeniden kurulur. AUTO_INCREMENT
kolonu indekste kalmaya devam eder.

Gecerli aylar ve pmax yuvasi acilir; her calistirmada pmax, gelecek aylara
bolunur. Boylece yeni ay icin elle islem gerekmez.

Kullanim:
    python tools/hit_partition.py            # esik dolduysa uygula
    python tools/hit_partition.py --zorla    # esigi yok say
    python tools/hit_partition.py --durum    # sadece rapor
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "tools")

from db import baglan  # noqa: E402

ESIK = 10_000_000  # satir; §6.3
GERI_AY = 2  # gecmis ay; gec yazan istekler icin
ILERI_AY = 3  # gelecek ay; pmax yuvasi bunlara bolunur
PMAX = "pmax"


def _ay(yil: int, ay: int) -> str:
    """YYYYMM biciminde bolum adi uretir."""
    return f"p{yil}{ay:02d}"


def _kaydir(taban: datetime, ay_farki: int) -> datetime:
    """Ay ekleyip cikarir; gun 1'e sabitlenir."""
    toplam = (taban.year * 12 + taban.month - 1) + ay_farki
    return datetime(toplam // 12, toplam % 12 + 1, 1, tzinfo=timezone.utc)


def _bolumlu_mu(imlec) -> bool:
    """Tablo zaten bolumlenmis mi."""
    imlec.execute(
        "SELECT COUNT(*) FROM information_schema.PARTITIONS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit'"
        " AND PARTITION_NAME IS NOT NULL"
    )
    return imlec.fetchone()[0] > 0


def _aylari_bol(imlec, aylar: list[datetime]) -> None:
    """pmax yuvasini verilen aylara boler, pmax'i yeniden ekler."""
    parcalar = [
        f"PARTITION {_ay(a.year, a.month)} VALUES LESS THAN (TO_DAYS('{a:%Y-%m-01}'))"
        for a in aylar
    ]
    parcalar.append(f"PARTITION {PMAX} VALUES LESS THAN MAXVALUE")
    imlec.execute(
        f"ALTER TABLE hit REORGANIZE PARTITION {PMAX} INTO (" + ", ".join(parcalar) + ")"
    )


def main() -> int:
    """Esik ve duruma gore islem yapar."""
    zorla = "--zorla" in sys.argv
    durum = "--durum" in sys.argv

    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT COUNT(*) FROM hit")
            adet = imlec.fetchone()[0]
            bolumlu = _bolumlu_mu(imlec)
            print(f"hit: {adet} satir · bolumlu: {bolumlu} · esik: {ESIK}")
            if durum:
                return 0
            if adet < ESIK and not zorla and not bolumlu:
                print("esik dolmadi, islem yok (zorlamak icin --zorla).")
                return 0

            if not bolumlu:
                # Once anahtar tasinir; partition kolonu anahtarda olmak zorunda.
                imlec.execute(
                    "ALTER TABLE hit DROP PRIMARY KEY, ADD PRIMARY KEY (id, created_at)"
                )
                simdi = datetime.now(timezone.utc).replace(day=1)
                aylar = [_kaydir(simdi, f) for f in range(-GERI_AY, 1)]
                parcalar = [
                    f"PARTITION {_ay(a.year, a.month)}"
                    f" VALUES LESS THAN (TO_DAYS('{a:%Y-%m-01}'))"
                    for a in aylar
                ]
                parcalar.append(f"PARTITION {PMAX} VALUES LESS THAN MAXVALUE")
                imlec.execute(
                    "ALTER TABLE hit PARTITION BY RANGE (TO_DAYS(created_at)) ("
                    + ", ".join(parcalar) + ")"
                )
                print(f"bolumlendi: {len(aylar)} gecmis ay + {PMAX}")

            # Gelecek aylar her calistirmada acilir; pmax tek yuvada kalmaz.
            simdi = datetime.now(timezone.utc).replace(day=1)
            gelecek = [_kaydir(simdi, f) for f in range(1, ILERI_AY + 1)]
            _aylari_bol(imlec, gelecek)
            print(f"ileri aylar acildi: {len(gelecek)}")

            imlec.execute(
                "SELECT PARTITION_NAME, TABLE_ROWS FROM information_schema.PARTITIONS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit'"
                " ORDER BY PARTITION_ORDINAL_POSITION"
            )
            for ad, satir in imlec.fetchall():
                print(f"  {ad}: {satir or 0}")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())