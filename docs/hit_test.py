import sys
sys.path.insert(0, "tools")
from db import baglan

c = baglan()
i = c.cursor()
i.execute("INSERT INTO hit (burst_id, provider_id, result) VALUES (1, 1, 'ok')")
y = i.lastrowid
print("eklendi", y)
i.execute("SELECT COUNT(*) FROM hit")
print("sayi", i.fetchone()[0])
i.execute("DELETE FROM hit WHERE id = %s", (y,))
print("silindi")
c.close()