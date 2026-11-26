import pathlib
import pymysql

d = {}
for satir in pathlib.Path(".env").read_text(encoding="utf-8").splitlines():
    if "=" in satir and not satir.strip().startswith("#"):
        k, v = satir.split("=", 1)
        d[k.strip()] = v.strip()

c = pymysql.connect(host=d.get("MYSQL_HOST", "127.0.0.1"), port=int(d.get("MYSQL_PORT", "3306")),
                    user=d.get("MYSQL_USER", "root"), password=d.get("MYSQL_PASSWORD", ""),
                    database=d.get("MYSQL_DATABASE", "unique_request_bot"))
cur = c.cursor()

print("--- provider ---")
cur.execute("SELECT id, name, kind, state, ulke, gateway, kullanici IS NOT NULL, weight FROM provider ORDER BY id")
for r in cur.fetchall():
    print(r)

print("--- ayar ---")
cur.execute("SELECT anahtar, deger FROM ayar WHERE anahtar LIKE 'oran%' OR anahtar IN "
            "('olcum_araligi_dk','step_size','hedef_yok_durma','serp_decodo','serp_serper','serp_searchapi')")
for r in cur.fetchall():
    print(r)

print("--- sayim ---")
for tablo in ("site", "keyword", "campaign", "cookie_profil", "dugum", "position"):
    cur.execute(f"SELECT COUNT(*) FROM {tablo}")
    print(tablo, cur.fetchone()[0])
c.close()