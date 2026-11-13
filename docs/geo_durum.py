import sys
sys.path.insert(0, "tools")
from db import baglan

c = baglan()
i = c.cursor()
i.execute("SELECT state, COUNT(*) FROM keyword_geo GROUP BY state")
for satir in i.fetchall():
    print("keyword_geo:", satir)
c.close()