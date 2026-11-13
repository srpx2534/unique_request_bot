import sys
sys.path.insert(0, "tools")
from db import baglan

c = baglan()
i = c.cursor()
i.execute("SELECT TO_DAYS(UTC_DATE() - INTERVAL 30 DAY)")
sinir = i.fetchone()[0]
i.execute(
    "SELECT COUNT(*) FROM information_schema.PARTITIONS"
    " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s"
    " AND PARTITION_NAME REGEXP %s AND PARTITION_DESCRIPTION <= %s",
    ("hit", "^p[0-9]{8}$", sinir),
)
print("sinir", sinir, "dusecek bolum", i.fetchone()[0])
c.close()