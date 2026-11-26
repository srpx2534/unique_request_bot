import time
from pathlib import Path

from worker import guven, isinma, tarayici

for ad in (guven.DOSYA, guven.RED_DOSYA):
    p = Path(ad)
    print(p.name, "var:", p.exists(), "· yas dk:", round((time.time() - p.stat().st_mtime) / 60, 1) if p.exists() else "-")
print("isinma acik:", isinma.acik())

for i in (1, 2):
    c = tarayici.serp_oku("erzurum escort")
    print(f"deneme {i}:", c["result"], len(c["organik"]), "·", c["mesaj"][:110].replace("\n", " "))
    if c["organik"]:
        print("  ilk:", c["organik"][0]["link"])