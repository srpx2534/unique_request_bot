import pathlib
import pymysql

d = {}
for satir in pathlib.Path(".env").read_text(encoding="utf-8").splitlines():
    if "=" in satir and not satir.strip().startswith("#"):
        k, v = satir.split("=", 1)
        d[k.strip()] = v.strip()

c = pymysql.connect(host=d.get("MYSQL_HOST", "127.0.0.1"), port=int(d.get("MYSQL_PORT", "3306")),
                    user=d.get("MYSQL_USER", "root"), password=d.get("MYSQL_PASSWORD", ""),
                    database=d.get("MYSQL_DATABASE", "unique_request_bot"), autocommit=True)
cur = c.cursor()
hedef = "SELECT id FROM provider WHERE name LIKE 'sil-%' AND (gateway LIKE 'sil.test%' OR gateway IS NULL)"
for tablo in ("profile", "provider_geo"):
    cur.execute(f"DELETE FROM {tablo} WHERE provider_id IN ({hedef})")
    print(tablo, "silinen:", cur.rowcount)
cur.execute("UPDATE hit SET provider_id = NULL WHERE provider_id IN (" + hedef + ")")
print("hit bosaltilan:", cur.rowcount)
cur.execute(f"DELETE FROM provider WHERE id IN ({hedef})")
print("provider silinen:", cur.rowcount)
cur.execute("SELECT id, name, kind, state, ulke, gateway FROM provider ORDER BY id")
for r in cur.fetchall():
    print(r)
c.close()