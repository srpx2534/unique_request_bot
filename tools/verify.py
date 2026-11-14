"""Kurulum dogrulamasi: zorunlu tablo, view, seed ve migration defteri.

Tablo sayisi sabit tutulmaz; migration eklendikce liste buyur ve sayi
degisir. Zorunlu tablolar tek tek aranir, eksik olan adiyla yazilir.
"""

from db import baglan

SEMA = "unique_request_bot"

# Kurulumda bulunmasi zorunlu tablolar. Yeni tablo eklenince buraya yazilir.
ZORUNLU = (
    "geo", "site", "keyword", "keyword_geo", "provider", "provider_geo",
    "serp_provider", "profile", "campaign", "burst", "hit", "position",
    "traffic_daily", "alert", "audit_log", "kullanici", "dugum", "dugum_olay", "ayar",
)

# Asgari migration sayisi; defter bunun altindaysa kurulum yarim kalmistir.
# Depoda 32 dosya var (001-032); esik gercek sayiya esitlenir ki yarim
# kurulum sessizce gecmesin.
ASGARI_MIGRATION = 32


def main() -> int:
    """Eksikleri yazar. Eksik varsa 1 doner."""
    baglanti = baglan()
    try:
        imlec = baglanti.cursor()

        imlec.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = %s AND table_type = 'BASE TABLE'",
            (SEMA,),
        )
        var = {satir[0] for satir in imlec.fetchall()}
        eksik = [t for t in ZORUNLU if t not in var]

        imlec.execute(
            "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = %s",
            (SEMA,),
        )
        view = imlec.fetchone()[0]

        imlec.execute("SELECT COUNT(*), COUNT(uule) FROM geo")
        geo, uule = imlec.fetchone()

        imlec.execute("SELECT ad FROM schema_migration ORDER BY ad")
        defter = [satir[0] for satir in imlec.fetchall()]

        print(f"tablo: {len(var)} · eksik: {len(eksik)}")
        for ad in eksik:
            print(f"  EKSIK {ad}")
        print(f"view: {view}")
        print(f"geo: {geo} · uule: {uule}")
        print(f"migration: {len(defter)}")

        hata = bool(eksik) or view < 2 or geo != 81 or uule != 81
        if len(defter) < ASGARI_MIGRATION:
            print(f"HATA: en az {ASGARI_MIGRATION} migration bekleniyordu.")
            hata = True
        if hata:
            print("HATA: dogrulama tutmadi.")
            return 1
        print("DOGRULAMA TAMAM.")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())