"""request kullanıcısına şema yetkisini verir ve yazıldığını doğrular.

Onarım sonrası GRANT sessizce düşebiliyor; bu yüzden her host için
üç kez denenir ve sonuç SHOW GRANTS ile kontrol edilir.
"""

import pymysql

from db import ayar

SEMA = "unique_request_bot"
HOSTLAR = ("%", "localhost")
DENEME = 3


def yetki_satiri(imlec, host: str) -> int:
    """Verilen host için şema yetki satırı sayısını döndürür."""
    imlec.execute("SHOW GRANTS FOR %s@%s", ("request", host))
    return len([s for s in imlec.fetchall() if SEMA in s[0]])


def main() -> int:
    """Yetkiyi verir, doğrular. Eksik kalırsa 1 döner."""
    baglanti = pymysql.connect(
        host=ayar("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar("MYSQL_PORT", "3306")),
        user="root",
        password=ayar("MYSQL_ROOT_PASSWORD"),
        charset="utf8mb4",
        autocommit=True,
    )
    eksik = 0
    try:
        with baglanti.cursor() as imlec:
            for host in HOSTLAR:
                sayi = yetki_satiri(imlec, host)
                for deneme in range(1, DENEME + 1):
                    if sayi >= 1:
                        break
                    imlec.execute(
                        f"GRANT ALL PRIVILEGES ON `{SEMA}`.* TO %s@%s",
                        ("request", host),
                    )
                    try:
                        imlec.execute("FLUSH PRIVILEGES")
                    except Exception:  # noqa: BLE001
                        pass
                    sayi = yetki_satiri(imlec, host)
                    print(f"{host}: deneme {deneme} -> {sayi} satır")

                if sayi != 1:
                    print(f"HATA: {host} için {sayi} satır kaldı.")
                    eksik += 1
                else:
                    print(f"OK    {host}: 1 satır")
        return 1 if eksik else 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())