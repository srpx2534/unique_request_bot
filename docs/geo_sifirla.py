import sys
sys.path.insert(0, "tools")
from db import baglan

c = baglan()
i = c.cursor()
i.execute("UPDATE keyword_geo SET state = 'pending' WHERE state = 'running'")
print("pending'e cekilen:", i.rowcount)
c.close()