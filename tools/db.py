"""Veritabanı bağlantısı ve SQL dosyası yardımcıları.

İki tür bağlantı vardır:
  - baglan()          : uygulama kullanıcısı, normal işler
  - baglan_yonetici() : DDL ve yetki işleri, root öncelikli

Bağlantı ayarları .env üzerinden okunur, kodda sabit değer yoktur.
Collation taşınabilir: utf8mb4_turkish_ci hem MySQL hem MariaDB'de var.
"""

from __future__ import annotations

import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

# Proje kökü: bu dosyanın bir üst dizini.
KOK = Path(__file__).resolve().parents[1]
MIGRATION_DIZINI = KOK / "db" / "migrations"
COLLATION = "utf8mb4_turkish_ci"

# .env varsa yüklenir; yoksa ortam değişkenleri olduğu gibi kullanılır.
load_dotenv(KOK / ".env")


def ayar(anahtar: str, varsayilan: str = "") -> str:
    """Ortam değişkenini okur, yoksa varsayılanı döndürür."""
    return os.getenv(anahtar, varsayilan)


def _ham_baglan(sifre: str, kullanici: str) -> pymysql.connections.Connection:
    """Şema seçmeden bağlanır; şema henüz yokken de çalışır."""
    return pymysql.connect(
        host=ayar("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar("MYSQL_PORT", "3306")),
        user=kullanici,
        password=sifre,
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
        autocommit=True,
    )


def _yonetici_adaylari() -> list[tuple[str, str]]:
    """Denenecek hesap listesi: root/.env, root/boş, uygulama kullanıcısı."""
    adaylar = [("root", ayar("MYSQL_ROOT_PASSWORD")), ("root", "")]
    if ayar("MYSQL_PASSWORD"):
        adaylar.append((ayar("MYSQL_USER", "request"), ayar("MYSQL_PASSWORD")))
    return adaylar


def baglan(veritabani: str | None = None) -> pymysql.connections.Connection:
    """Uygulama kullanıcısı ile bağlantı açar.

    Args:
        veritabani: Hedef şema adı. None ise .env'deki ad kullanılır.

    Returns:
        Açık bağlantı. Çağıran taraf kapatmakla yükümlüdür.
    """
    return pymysql.connect(
        host=ayar("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar("MYSQL_PORT", "3306")),
        user=ayar("MYSQL_USER", "request"),
        password=ayar("MYSQL_PASSWORD"),
        database=veritabani or ayar("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
        autocommit=True,
        cursorclass=pymysql.cursors.Cursor,
    )


def baglan_yonetici() -> pymysql.connections.Connection:
    """DDL ve yetki işleri için bağlantı açar; root önceliklidir.

    Returns:
        Açık bağlantı. Hiçbir hesap tutmazsa RuntimeError yükselir.
    """
    hatalar: list[str] = []
    for kullanici, sifre in _yonetici_adaylari():
        try:
            baglanti = pymysql.connect(
                host=ayar("MYSQL_HOST", "127.0.0.1"),
                port=int(ayar("MYSQL_PORT", "3306")),
                user=kullanici,
                password=sifre,
                database=ayar("MYSQL_DATABASE", "unique_request_bot"),
                charset="utf8mb4",
                init_command="SET time_zone = '+00:00'",
                autocommit=True,
            )
            print(f"[OK] yönetici bağlantısı: {kullanici}")
            return baglanti
        except Exception as hata:  # noqa: BLE001
            hatalar.append(f"{kullanici}: {hata}")
    raise RuntimeError("yönetici bağlantısı kurulamadı: " + "; ".join(hatalar))


def sema_olustur() -> None:
    """Hedef şemayı yoksa oluşturur. Var olan şemaya dokunmaz."""
    ad = ayar("MYSQL_DATABASE", "unique_request_bot")
    son_hata: Exception | None = None
    for kullanici, sifre in _yonetici_adaylari():
        try:
            baglanti = _ham_baglan(sifre, kullanici)
        except Exception as hata:  # noqa: BLE001
            son_hata = hata
            continue
        try:
            with baglanti.cursor() as imlec:
                imlec.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{ad}` "
                    f"CHARACTER SET utf8mb4 COLLATE {COLLATION}"
                )
            return
        finally:
            baglanti.close()
    raise RuntimeError(f"şema oluşturulamadı: {son_hata}")


def sql_dosyasini_ayristir(yol: Path) -> list[str]:
    """SQL dosyasını tek tek çalıştırılabilir ifadelere böler.

    Yorum satırları (`--`) atılır, noktalı virgülden bölünür, boşlar süzülür.

    Args:
        yol: Okunacak .sql dosyası.

    Returns:
        Çalıştırılabilir ifade listesi.
    """
    ham = yol.read_text(encoding="utf-8")
    satirlar = [s for s in ham.splitlines() if not s.lstrip().startswith("--")]
    ifadeler = []
    for parca in "\n".join(satirlar).split(";"):
        temiz = parca.strip()
        if temiz:
            ifadeler.append(temiz)
    return ifadeler