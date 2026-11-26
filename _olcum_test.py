from worker import tarayici

HEDEF = "erzurumescortr.com"
c = tarayici.serp_oku("erzurum escort")
print("result:", c["result"], "· sonuc:", len(c["organik"]), "· mesaj:", c["mesaj"])
for k in c["organik"][:15]:
    print(f"  {k['position']:02d} {k['link']}")
yer = [k["position"] for k in c["organik"] if HEDEF in k["link"]]
print("hedef sira:", yer or "yok")