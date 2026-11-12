"""Veritabanı, kullanıcı ve yetkileri .env'den okuyarak kurar.

Amaç: şifreyi iki yerde tutmamak. .env ne yazıyorsa o uygulanır.
Idempotenttir; tekrar çalıştırıldığında şifreyi .env'e göre sabitler.
Root bağlantısı gerektirir.

Kullanım:
    python tools/bootstrap.py
"""

from __future__ import annotations

import os
import sys

import pymysql
from dotenv import load_dotenv

from db import KOK

# .env zorunlu; yoksa hiçbir şey yapılmaz.
load_dotenv(KOK / ".env")

SEMA = os.getenv("MYSQL_DATABASE", "unique_request_bot")
KULLANICI = os.getenv("MYSQL_USER", "request")
SIFRE = os.getenv("MYSQL_PASSWORD", "")
ROOT_SIFRE = os.getenv("MYSQL_ROOT_PASSWORD", "")

# Uygulamanın ihtiyaç duyduğu yetkiler. REFERENCES foreign key için gerekli.
YETKILER = "SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES"

# Kullanıcı iki host için tanımlanır: uzak bağlantı ve yerel soket.
HOSTLAR = ("%", "localhost")


def root_baglan() -> pymysql.connections.Connection:
    """Root ile, şema seçmeden bağlanır."""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user="root",
        password=ROOT_SIFRE,
        charset="utf8mb4",
        autocommit=True,
    )


def main() -> int:
    """Kurulumu uygular. Eksik değer veya hata varsa 1 döner."""
    if not SIFRE:
        print("HATA: .env içinde MYSQL_PASSWORD boş.")
        return 1
    if not ROOT_SIFRE:
        print("HATA: .env içinde MYSQL_ROOT_PASSWORD boş.")
        return 1

    baglanti = root_baglan()
    try:
        with baglanti.cursor() as imlec:
            # 1. Şema: utf8mb4 + Türkçe collation, yoksa oluşturulur.
            imlec.execute(
                f"CREATE DATABASE IF NOT EXISTS `{SEMA}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci"
            )

            # 2. Kullanıcı: yoksa oluşturulur, varsa şifresi .env'e çekilir.
            for host in HOSTLAR:
                imlec.execute(
                    f"CREATE USER IF NOT EXISTS '{KULLANICI}'@'{host}' "
                    "IDENTIFIED BY %s",
                    (SIFRE,),
                )
                imlec.execute(
                    f"ALTER USER '{KULLANICI}'@'{host}' IDENTIFIED BY %s",
                    (SIFRE,),
                )

            # 3. Yetki: yalnızca bu şemada, global yetki verilmez.
            for host in HOSTLAR:
                imlec.execute(
                    f"GRANT {YETKILER} ON `{SEMA}`.* TO '{KULLANICI}'@'{host}'"
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
        if karakter != "utf8mb4" or collation != "utf8mb4_turkish_ci":
            print("HATA: karakter seti veya collation beklendiği gibi değil.")
            return 1

        print(f"kullanıcı: {KULLANICI} · yetki verildi: {', '.join(HOSTLAR)}")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    sys.exit(main())