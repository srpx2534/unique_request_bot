"""Şema migration çalıştırıcı.

db/migrations altındaki .sql dosyalarını dosya adı sırasıyla uygular.
Uygulananlar schema_migration tablosunda tutulur, tekrar çalıştırma güvenlidir.

Kullanım:
    python tools/migrate.py            # bekleyenleri uygula
    python tools/migrate.py --status   # sadece durum göster
"""

from __future__ import annotations

import sys

from db import (MIGRATION_DIZINI, baglan_yonetici, sema_olustur, sql_dosyasini_ayristir)


def durum_tablosu_hazirla(baglanti) -> None:
    """Migration defterini yoksa oluşturur."""
    with baglanti.cursor() as imlec:
        imlec.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migration (
              ad          VARCHAR(191) PRIMARY KEY,
              uygulandi_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
            ) ENGINE=InnoDB
            """
        )


def uygulananlar(baglanti) -> set[str]:
    """Daha önce uygulanmış migration adlarını döndürür."""
    with baglanti.cursor() as imlec:
        imlec.execute("SELECT ad FROM schema_migration")
        return {satir[0] for satir in imlec.fetchall()}


def main() -> int:
    """Bekleyen migration'ları uygular. Hata varsa 1 döner."""
    if not MIGRATION_DIZINI.exists():
        print(f"HATA: migration dizini yok: {MIGRATION_DIZINI}")
        return 1

    dosyalar = sorted(MIGRATION_DIZINI.glob("*.sql"))
    if not dosyalar:
        print("HATA: uygulanacak migration bulunamadı.")
        return 1

    sema_olustur()
    baglanti = baglan_yonetici()
    # Teşhis: hangi kimlikle çalıştığımızı ve yetkileri yaz.
    with baglanti.cursor() as imlec:
        imlec.execute("SELECT CURRENT_USER()")
        print(f"kimlik: {imlec.fetchone()[0]}")
        imlec.execute("SHOW GRANTS")
        for (satir,) in imlec.fetchall():
            print(f"  yetki: {satir}")
    try:
        durum_tablosu_hazirla(baglanti)
        atlanan = uygulananlar(baglanti)

        sadece_durum = "--status" in sys.argv
        bekleyen = [d for d in dosyalar if d.name not in atlanan]

        if sadece_durum:
            # Durum modunda hiçbir şey uygulanmaz.
            for d in dosyalar:
                im = "UYGULANDI" if d.name in atlanan else "BEKLIYOR"
                print(f"{im:10} {d.name}")
            return 0

        if not bekleyen:
            print("Bekleyen migration yok.")
            return 0

        for dosya in bekleyen:
            print(f"Uygulanıyor: {dosya.name}")
            for ifade in sql_dosyasini_ayristir(dosya):
                with baglanti.cursor() as imlec:
                    imlec.execute(ifade)
            # Başarılıysa deftere yazılır, tekrar denenmez.
            with baglanti.cursor() as imlec:
                imlec.execute(
                    "INSERT INTO schema_migration (ad) VALUES (%s)", (dosya.name,)
                )
            print(f"  tamam: {dosya.name}")

        print(f"Bitti: {len(bekleyen)} migration uygulandı.")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    sys.exit(main())