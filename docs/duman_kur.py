"""Duman testi verisi kurar: gerçek alan adı, tek kelime, 81 il satırı.

Sahte alan adları ilk 100'de bulunmadığı için hit üretmiyor. Bu betik
sıralanan bir alan adıyla kelime açar ve dağıtımı 10/30/41 kurar.

Kullanım: python docs/duman_kur.py
"""

import sys

sys.path.insert(0, "tools")
from db import baglan

ALAN = "armut.com"
KELIME = "veteriner"

c = baglan()
i = c.cursor()

i.execute(
    "INSERT INTO site (domain, label) VALUES (%s, %s)"
    " ON DUPLICATE KEY UPDATE active = 1",
    (ALAN, "Duman testi"),
)
i.execute("SELECT id FROM site WHERE domain = %s", (ALAN,))
site = i.fetchone()[0]

i.execute(
    "INSERT INTO keyword (site_id, text, geo_scope, volume, state) VALUES (%s, %s, 'national', 100, 'active')"
    " ON DUPLICATE KEY UPDATE state = 'active', volume = 100",
    (site, KELIME),
)
i.execute("SELECT id FROM keyword WHERE site_id = %s AND text = %s", (site, KELIME))
kid = i.fetchone()[0]

i.execute("SELECT COUNT(*) FROM campaign WHERE keyword_id = %s AND stopped_at IS NULL", (kid,))
if i.fetchone()[0] == 0:
    i.execute("INSERT INTO campaign (keyword_id, step_size, config) VALUES (%s, 10, '{}')", (kid,))

i.execute("SELECT code FROM geo ORDER BY weight DESC, code ASC")
kodlar = [k for k, in i.fetchall()]
for sira, kod in enumerate(kodlar):
    tier = "core" if sira < 10 else ("normal" if sira < 40 else "passive")
    i.execute(
        "INSERT INTO keyword_geo (keyword_id, geo_code, tier) VALUES (%s, %s, %s)"
        " ON DUPLICATE KEY UPDATE tier = VALUES(tier)",
        (kid, kod, tier),
    )

i.execute("UPDATE keyword_geo SET state = 'pending', cooldown_until = NULL WHERE keyword_id = %s", (kid,))
print(f"hazir: site={site} kelime={kid} il={len(kodlar)}")
c.close()