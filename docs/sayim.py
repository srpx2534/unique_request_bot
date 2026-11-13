import sys
sys.path.insert(0, "tools")
from db import baglan

c = baglan()
i = c.cursor()
for tablo in ("burst", "hit", "traffic_daily", "position"):
    i.execute(f"SELECT COUNT(*) FROM {tablo}")
    print(f"{tablo}: {i.fetchone()[0]}")
i.execute("SELECT result, geo_mode, http_status, latency_ms FROM hit ORDER BY id DESC LIMIT 5")
for satir in i.fetchall():
    print("  hit:", satir)
c.close()