import sys
sys.path.insert(0, "tools")
from db import baglan

c = baglan()
i = c.cursor()
i.execute("SELECT anahtar, CHAR_LENGTH(deger) FROM ayar WHERE anahtar LIKE 'serp_%'")
for ad, uzunluk in i.fetchall():
    print(f"{ad}: {uzunluk} karakter")
i.execute("SELECT COUNT(*) FROM provider WHERE gateway IS NOT NULL")
print("kimlikli saglayici:", i.fetchone()[0])
c.close()