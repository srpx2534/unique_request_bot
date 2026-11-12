"""VeritabanÃ„Â±, kullanÃ„Â±cÃ„Â± ve yetkileri .env'den okuyarak kurar.

AmaÃƒÂ§: Ã…Å¸ifreyi iki yerde tutmamak. .env ne yazÃ„Â±yorsa o uygulanÃ„Â±r.
BaÃ„Å¸lantÃ„Â± sÃ„Â±rasÃ„Â±: root/.env -> root/boÃ…Å¸ -> uygulama kullanÃ„Â±cÃ„Â±sÃ„Â±/.env
BÃƒÂ¶ylece root Ã…Å¸ifresi bilinmese de kurulum yÃƒÂ¼rÃƒÂ¼r.
KullanÃ„Â±cÃ„Â± ve host deÃ„Å¸erleri %s ile geÃƒÂ§irilir; host '%' olduÃ„Å¸u iÃƒÂ§in
sorguya gÃƒÂ¶mÃƒÂ¼lÃƒÂ¼rse PyMySQL biÃƒÂ§imlendirmesi kÃ„Â±rÃ„Â±lÃ„Â±r.
FLUSH PRIVILEGES ÃƒÂ§aÃ„Å¸rÃ„Â±lmaz (Aria bozukluÃ„Å¸unda hata veriyor).

KullanÃ„Â±m:
    python tools/bootstrap.py
"""

from __future__ import annotations

import sys

import pymysql

from db import COLLATION, ayar

SEMA = ayar("MYSQL_DATABASE", "unique_request_bot")
KULLANICI = ayar("MYSQL_USER", "request")
SIFRE = ayar("MYSQL_PASSWORD")
ROOT_SIFRE = ayar("MYSQL_ROOT_PASSWORD")

# UygulamanÃ„Â±n ihtiyaÃƒÂ§ duyduÃ„Å¸u yetkiler. REFERENCES foreign key iÃƒÂ§in gerekli.
YETKILER = "ALL PRIVILEGES"

# KullanÃ„Â±cÃ„Â± iki host iÃƒÂ§in tanÃ„Â±mlanÃ„Â±r: uzak baÃ„Å¸lantÃ„Â± ve yerel soket.
HOSTLAR = ("%", "localhost")


def _dene(kullanici: str, sifre: str) -> pymysql.connections.Connection:
    """Tek hesap ile Ã…Å¸ema seÃƒÂ§meden baÃ„Å¸lanmayÃ„Â± dener."""
    return pymysql.connect(
        host=ayar("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar("MYSQL_PORT", "3306")),
        user=kullanici,
        password=sifre,
        charset="utf8mb4",
        autocommit=True,
    )


def deneme_baglan() -> pymysql.connections.Connection:
    """HesaplarÃ„Â± sÃ„Â±rayla dener, ilk baÃ…Å¸arÃ„Â±lÃ„Â± baÃ„Å¸lantÃ„Â±yÃ„Â± dÃƒÂ¶ndÃƒÂ¼rÃƒÂ¼r."""
    adaylar = [("root", ROOT_SIFRE), ("root", "")]
    if SIFRE:
        adaylar.append((KULLANICI, SIFRE))

    hatalar: list[str] = []
    for kullanici, sifre in adaylar:
        try:
            baglanti = _dene(kullanici, sifre)
            print(f"[OK] baÃ„Å¸lantÃ„Â±: {kullanici} (Ã…Å¸ifre {'var' if sifre else 'boÃ…Å¸'})")
            return baglanti
        except Exception as hata:  # noqa: BLE001
            hatalar.append(f"{kullanici}: {hata}")

    print("HATA: hiÃƒÂ§bir hesap ile baÃ„Å¸lanÃ„Â±lamadÃ„Â±.")
    print("      .env iÃƒÂ§indeki MYSQL_ROOT_PASSWORD veya MYSQL_PASSWORD alanÃ„Â±nÃ„Â± doldur.")
    for satir in hatalar:
        print(f"      - {satir}")
    sys.exit(1)


def main() -> int:
    """Kurulumu uygular. DoÃ„Å¸rulama tutmazsa 1 dÃƒÂ¶ner."""
    if not SIFRE:
        print("HATA: .env iÃƒÂ§inde MYSQL_PASSWORD boÃ…Å¸.")
        return 1

    baglanti = deneme_baglan()
    try:
        with baglanti.cursor() as imlec:
            # 1. Ã…Âema: utf8mb4 + TÃƒÂ¼rkÃƒÂ§e collation, yoksa oluÃ…Å¸turulur.
            imlec.execute(
                f"CREATE DATABASE IF NOT EXISTS `{SEMA}` "
                f"CHARACTER SET utf8mb4 COLLATE {COLLATION}"
            )
            # 1b. Ãƒâ€“nceden yanlÃ„Â±Ã…Å¸ collation ile aÃƒÂ§Ã„Â±lmÃ„Â±Ã…Å¸sa dÃƒÂ¼zeltilir.
            imlec.execute(
                f"ALTER DATABASE `{SEMA}` CHARACTER SET utf8mb4 COLLATE {COLLATION}"
            )

            # 2. KullanÃ„Â±cÃ„Â±: yoksa oluÃ…Å¸turulur, varsa Ã…Å¸ifresi .env'e ÃƒÂ§ekilir.
            for host in HOSTLAR:
                imlec.execute(
                    "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                    (KULLANICI, host, SIFRE),
                )
                imlec.execute(
                    "ALTER USER %s@%s IDENTIFIED BY %s",
                    (KULLANICI, host, SIFRE),
                )

            # 3. Yetki: yalnÃ„Â±zca bu Ã…Å¸emada, global yetki verilmez.
            for host in HOSTLAR:
                imlec.execute(
                    f"GRANT {YETKILER} ON `{SEMA}`.* TO %s@%s",
                    (KULLANICI, host),
                )

        # 4. DoÃ„Å¸rulama: Ã…Å¸ema ve collation gerÃƒÂ§ekten yerinde mi.
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (SEMA,),
            )
            satir = imlec.fetchone()

        if not satir:
            print("HATA: Ã…Å¸ema oluÃ…Å¸madÃ„Â±.")
            return 1

        karakter, collation = satir
        print(f"Ã…Å¸ema: {SEMA} Ã‚Â· {karakter} Ã‚Â· {collation}")
        if karakter != "utf8mb4" or collation != COLLATION:
            print("HATA: karakter seti veya collation beklendiÃ„Å¸i gibi deÃ„Å¸il.")
            return 1

        print(f"kullanÃ„Â±cÃ„Â±: {KULLANICI} Ã‚Â· yetki verildi: {', '.join(HOSTLAR)}")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    sys.exit(main())