import pathlib
import pymysql
d = {}
for satir in pathlib.Path(".env").read_text(encoding="utf-8").splitlines():
    if "=" in satir and not satir.strip().startswith("#"):
        k, v = satir.split("=", 1)
        d[k.strip()] = v.strip()
try:
    pymysql.connect(host=d.get("MYSQL_HOST", "127.0.0.1"), port=int(d.get("MYSQL_PORT", "3306")),
                    user=d.get("MYSQL_USER", "root"), password=d.get("MYSQL_PASSWORD", ""),
                    database=d.get("MYSQL_DATABASE", "unique_request_bot")).close()
    print("BAGLANTI OK", d.get("MYSQL_USER"), d.get("MYSQL_DATABASE"))
except Exception as h:
    print("BAGLANTI YOK:", h)