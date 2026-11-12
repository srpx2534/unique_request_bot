"""request kullanıcısının şema yetkilerini tek GRANT satırına indirir.

Her bootstrap çalışması yeni bir GRANT satırı ekliyor; bu betik birikmişi
temizler. Yalnızca şema kapsamlı yetki verilir, global yetki verilmez.
"""

import pymysql

from db import ayar

SEMA = "unique_request_bot"
HOSTLAR = ("%", "localhost")


def main() -> int:
    """Yetkileri sıfırlar ve tek satır olarak yeniden verir."""
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
            for host in HOSTLAR:
                imlec.execute(
                    f"REVOKE ALL PRIVILEGES ON `{SEMA}`.* FROM %s@%s",
                    ("request", host),
                )
                imlec.execute(
                    f"GRANT ALL PRIVILEGES ON `{SEMA}`.* TO %s@%s",
                    ("request", host),
                )
            # Sonuç doğrulanır: her host için tek satır kalmalı.
            for host in HOSTLAR:
                imlec.execute("SHOW GRANTS FOR %s@%s", ("request", host))
                satirlar = [s[0] for s in imlec.fetchall()]
                sema_li = [s for s in satirlar if SEMA in s]
                print(f"request@{host}: {len(sema_li)} şema yetki satırı")
                for satir in satirlar:
                    print(f"   {satir}")
    finally:
        baglanti.close()
    print("yetkiler tek satıra indirildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())