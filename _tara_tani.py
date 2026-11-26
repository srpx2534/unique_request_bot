from playwright.sync_api import sync_playwright

from worker import havuz, tarayici, zehir

secim = havuz.sec_mod(None, False)
sozluk = tarayici._proxy_sozlugu(secim[1] if secim else None)
sonuc = {"result": "error", "organik": [], "url": "", "mesaj": ""}

with sync_playwright() as p:
    baglam = tarayici._baglam_ac(p, True, sozluk, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    tarayici._tara(baglam, "erzurum escort", None, 3, sonuc)
    baglam.close()

print("result:", sonuc["result"], "· adet:", len(sonuc["organik"]), "· mesaj:", sonuc["mesaj"][:80])
for k in sonuc["organik"]:
    print(f"  {k['position']:02d} {k['link']}")
print("zehirli:", zehir.zehirli_mi("erzurum escort", sonuc["organik"]))