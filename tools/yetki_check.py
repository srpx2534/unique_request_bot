"""request kullanıcısının yetkilerini ve gerçek erişimini denetler.

İki aşama: root ile yetki dökümü, sonra request ile gerçek yazma/okuma.
Amacı tahmin bırakmamak; her adım OK veya HATA yazar.
"""

import pymysql

from db import ayar, baglan


def yetki_dokumu() -> None:
    """root ile her iki host için SHOW GRANTS çalıştırır."""
    baglanti = pymysql.connect(
        host=ayar("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar("MYSQL_PORT", "3306")),
        user="root",
        password=ayar("MYSQL_ROOT_PASSWORD"),
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with baglanti.cursor() as imlec:
            for host in ("%", "localhost"):
                imlec.execute("SHOW GRANTS FOR %s@%s", ("request", host))
                print(f"--- request@{host} ---")
                for (satir,) in imlec.fetchall():
                    print(f"   {satir}")
    finally:
        baglanti.close()


def erisim_denemesi() -> int:
    """request ile gerçek sorgular dener. Hata sayısını döndürür."""
    adimlar = [
        ("okuma geo", "SELECT COUNT(*) FROM geo"),
        ("okuma view", "SELECT COUNT(*) FROM v_live"),
        ("yazma site", "INSERT INTO site (domain) VALUES ('deneme.test') "
                       "ON DUPLICATE KEY UPDATE domain=VALUES(domain)"),
        ("yazma keyword", "INSERT INTO keyword (site_id, text, geo_scope) "
                          "SELECT id, 'deneme kelime', 'national' FROM site "
                          "WHERE domain='deneme.test' "
                          "ON DUPLICATE KEY UPDATE text=VALUES(text)"),
        ("silme keyword", "DELETE FROM keyword WHERE text='deneme kelime'"),
        ("silme site", "DELETE FROM site WHERE domain='deneme.test'"),
    ]
    hata = 0
    baglanti = baglan()
    try:
        for ad, sorgu in adimlar:
            try:
                with baglanti.cursor() as imlec:
                    imlec.execute(sorgu)
                    imlec.fetchall()
                print(f"OK    {ad}")
            except Exception as istisna:  # noqa: BLE001
                print(f"HATA  {ad}: {istisna}")
                hata += 1
    finally:
        baglanti.close()
    return hata


def main() -> int:
    """Denetimi yürütür."""
    yetki_dokumu()
    hata = erisim_denemesi()
    print(f"hata sayısı: {hata}")
    return 1 if hata else 0


if __name__ == "__main__":
    raise SystemExit(main())