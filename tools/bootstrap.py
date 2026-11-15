"""Veritabanı, kullanıcı ve yetkileri .env'den okuyarak kurar.

Amaç: şifreyi iki yerde tutmamak. .env ne yazıyorsa o uygulanır.
Bağlantı sırası: root/.env -> root/boş -> uygulama kullanıcısı/.env
Böylece root şifresi bilinmese de kurulum yürür.
Kullanıcı ve host değerleri %s ile geçirilir; host '%' olduğu için
sorguya gömülürse PyMySQL biçimlendirmesi kırılır.
FLUSH PRIVILEGES çağrılmaz (Aria bozukluğunda hata veriyor).

Kullanım:
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

# Uygulamanın ihtiyaç duyduğu yetkiler. REFERENCES foreign key için gerekli.
YETKILER = "ALL PRIVILEGES"

# Kullanıcı iki host için tanımlanır: uzak bağlantı ve yerel soket.
HOSTLAR = ("%", "localhost")


def _dene(kullanici: str, sifre: str) -> pymysql.connections.Connection:
    """Tek hesap ile şema seçmeden bağlanmayı dener."""
    return pymysql.connect(
        host=ayar("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar("MYSQL_PORT", "3306")),
        user=kullanici,
        password=sifre,
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
        autocommit=True,
    )


def deneme_baglan() -> pymysql.connections.Connection:
    """Hesapları sırayla dener, ilk başarılı bağlantıyı döndürür."""
    adaylar = [("root", ROOT_SIFRE), ("root", "")]
    if SIFRE:
        adaylar.append((KULLANICI, SIFRE))

    hatalar: list[str] = []
    for kullanici, sifre in adaylar:
        try:
            baglanti = _dene(kullanici, sifre)
            print(f"[OK] bağlantı: {kullanici} (şifre {'var' if sifre else 'boş'})")
            return baglanti
        except Exception as hata:  # noqa: BLE001
            hatalar.append(f"{kullanici}: {hata}")

    print("HATA: hiçbir hesap ile bağlanılamadı.")
    print("      .env içindeki MYSQL_ROOT_PASSWORD veya MYSQL_PASSWORD alanını doldur.")
    for satir in hatalar:
        print(f"      - {satir}")
    sys.exit(1)


def main() -> int:
    """Kurulumu uygular. Doğrulama tutmazsa 1 döner."""
    if not SIFRE:
        print("HATA: .env içinde MYSQL_PASSWORD boş.")
        return 1

    baglanti = deneme_baglan()
    try:
        with baglanti.cursor() as imlec:
            # 1. Şema: utf8mb4 + Türkçe collation, yoksa oluşturulur.
            imlec.execute(
                f"CREATE DATABASE IF NOT EXISTS `{SEMA}` "
                f"CHARACTER SET utf8mb4 COLLATE {COLLATION}"
            )
            # 1b. Önceden yanlış collation ile açılmışsa düzeltilir.
            imlec.execute(
                f"ALTER DATABASE `{SEMA}` CHARACTER SET utf8mb4 COLLATE {COLLATION}"
            )

            # 2. Kullanıcı: yoksa oluşturulur, varsa şifresi .env'e çekilir.
            for host in HOSTLAR:
                imlec.execute(
                    "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                    (KULLANICI, host, SIFRE),
                )
                imlec.execute(
                    "ALTER USER %s@%s IDENTIFIED BY %s",
                    (KULLANICI, host, SIFRE),
                )

            # 3. Yetki: yalnızca bu şemada, global yetki verilmez.
            for host in HOSTLAR:
                imlec.execute(
                    f"GRANT {YETKILER} ON `{SEMA}`.* TO %s@%s",
                    (KULLANICI, host),
                )

        # 4. Doğrulama: şema ve collation gerçekten yerinde mi.
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (SEMA,),
            )
            satir = imlec.fetchone()

        if not satir:
            print("HATA: şema oluşmadı.")
            return 1

        karakter, collation = satir
        print(f"şema: {SEMA} · {karakter} · {collation}")
        if karakter != "utf8mb4" or collation != COLLATION:
            print("HATA: karakter seti veya collation beklendiği gibi değil.")
            return 1

        print(f"kullanıcı: {KULLANICI} · yetki verildi: {', '.join(HOSTLAR)}")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    sys.exit(main())