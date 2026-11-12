"""Kurulum doğrulaması: tablo, view, seed ve migration defteri.

Tek satırlık -c komutlarında tırnak kaçışı sorun çıkardığı için dosya.
"""

from db import baglan

SEMA = "unique_request_bot"


def main() -> int:
    """Sayımları yazar. Eksik varsa 1 döner."""
    baglanti = baglan()
    try:
        imlec = baglanti.cursor()

        imlec.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema=%s AND table_type='BASE TABLE'",
            (SEMA,),
        )
        tablo = imlec.fetchone()[0]

        imlec.execute(
            "SELECT COUNT(*) FROM information_schema.views WHERE table_schema=%s",
            (SEMA,),
        )
        view = imlec.fetchone()[0]

        imlec.execute("SELECT COUNT(*), COUNT(uule) FROM geo")
        geo, uule = imlec.fetchone()

        imlec.execute("SELECT ad FROM schema_migration ORDER BY ad")
        defter = [satir[0] for satir in imlec.fetchall()]

        print(f"tablo: {tablo}")
        print(f"view: {view}")
        print(f"geo: {geo} · uule: {uule}")
        print(f"migration: {defter}")

        if tablo != 16 or view < 1 or geo != 81 or uule != 81 or len(defter) != 4:
            print("HATA: doğrulama tutmadı.")
            return 1
        print("DOĞRULAMA TAMAM.")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())