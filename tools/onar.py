"""mysql sistem tablolarını onarır ve request yetkilerini sıfırlar.

REVOKE, bozuk mysql.db yüzünden 1141 veriyor ve GRANT satırları birleşmiyor.
Bu yüzden satırlar doğrudan silinir, sonra tek GRANT atılır.
Her adım ayrı ayrı raporlanır; bir adım düşse de devam edilir.
"""

import pymysql

from db import ayar

SEMA = "unique_request_bot"
HOSTLAR = ("%", "localhost")
ONARILACAK = ("mysql", "db"), ("mysql", "user")


def dene(imlec, etiket: str, sorgu: str, parametre=None) -> None:
    """Tek ifadeyi çalıştırır; hatayı yutar ve raporlar."""
    try:
        imlec.execute(sorgu, parametre)
        for satir in imlec.fetchall() or ():
            print(f"   {satir}")
        print(f"OK    {etiket}")
    except Exception as hata:  # noqa: BLE001
        print(f"HATA  {etiket}: {hata}")


def main() -> int:
    """Onarım ve yetki sıfırlama."""
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
            for sema, tablo in ONARILACAK:
                dene(imlec, f"onarım {sema}.{tablo}",
                     f"REPAIR TABLE `{sema}`.`{tablo}`")

            # Yetki satırları doğrudan silinir; kullanıcı hesabı korunur.
            for host in HOSTLAR:
                dene(imlec, f"sil {host}",
                     "DELETE FROM mysql.db WHERE Db=%s AND User=%s",
                     (SEMA, "request"))
                dene(imlec, f"grant {host}",
                     f"GRANT ALL PRIVILEGES ON `{SEMA}`.* TO %s@%s",
                     ("request", host))

            dene(imlec, "flush", "FLUSH PRIVILEGES")

            for host in HOSTLAR:
                imlec.execute("SHOW GRANTS FOR %s@%s", ("request", host))
                satirlar = [s[0] for s in imlec.fetchall()]
                sema_li = [s for s in satirlar if SEMA in s]
                print(f"request@{host}: {len(sema_li)} şema yetki satırı")
                for satir in satirlar:
                    print(f"   {satir}")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())