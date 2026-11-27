import pathlib
import tempfile

from playwright.sync_api import sync_playwright

from worker import guven, tarayici

tarayici.PROFIL = pathlib.Path(tempfile.mkdtemp(prefix="gizli_"))
guven.uygula = lambda *a, **k: False

sonuc = {"result": "error", "organik": [], "url": "", "mesaj": ""}
with sync_playwright() as p:
    baglam = tarayici._baglam_ac(p, True, None, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    tarayici._tara(baglam, "erzurum escort", None, 2, sonuc)
    baglam.close()

print("TEMIZ PROFIL:", sonuc["result"], len(sonuc["organik"]), sonuc["mesaj"][:80])
for k in sonuc["organik"][:15]:
    print("  ", k["position"], k["link"][:70])