import sys
sys.path.insert(0, "tools")
from db import baglan

c = baglan()
i = c.cursor()
i.execute("SELECT id, target_count, ended_at, stats FROM burst ORDER BY id DESC LIMIT 5")
for satir in i.fetchall():
    print("burst:", satir)
i.execute("SELECT id, text, state, geo_scope FROM keyword ORDER BY id DESC LIMIT 5")
for satir in i.fetchall():
    print("kelime:", satir)
i.execute("SELECT id, ad, ip, durum, son_kalp_at FROM dugum")
for satir in i.fetchall():
    print("dugum:", satir)
i.execute("SELECT id, kind, LEFT(message, 90) FROM alert ORDER BY id DESC LIMIT 5")
for satir in i.fetchall():
    print("uyari:", satir)
c.close()