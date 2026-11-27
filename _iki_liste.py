from worker import tarayici

yerel = tarayici.serp_oku("erzurum escort", proxy_yok=True)
print("YEREL:", yerel["result"], len(yerel["organik"]), yerel["mesaj"][:80])
for k in yerel["organik"][:12]:
    print("  Y", k["position"], k["link"][:70])

uzak = tarayici.serp_oku("erzurum escort", sehir="erzurum")
print("PROXY:", uzak["result"], len(uzak["organik"]), uzak["mesaj"][:80])
for k in uzak["organik"][:12]:
    print("  P", k["position"], k["link"][:70])