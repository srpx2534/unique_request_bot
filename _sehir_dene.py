import pathlib
import secrets

import pymysql
from playwright.sync_api import sync_playwright

from worker import proxy, tarayici
from worker.serp_ortak import kok

d = {}
for satir in pathlib.Path(".env").read_text(encoding="utf-8").splitlines():
    if "=" in satir and not satir.strip().startswith("#"):
        k, v = satir.split("=", 1)
        d[k.strip()] = v.strip()
c = pymysql.connect(host=d.get("MYSQL_HOST", "127.0.0.1"), port=int(d.get("MYSQL_PORT", "3306")),
                    user=d.get("MYSQL_USER", "root"), password=d.get("MYSQL_PASSWORD", ""),
                    database=d.get("MYSQL_DATABASE", "unique_request_bot"))
cur = c.cursor()
cur.execute("SELECT gateway, kullanici, sifre FROM provider WHERE id = 72")
gw, kul, sif = cur.fetchone()
c.close()

ref = [kok(s) for s in pathlib.Path("tools/veri/serp_referans.txt").read_text(encoding="utf-8").splitlines()
       if s and not s.startswith("#")]

for sehir in ("erzurum", None):
    adres = proxy._dataimpulse(gw, kul, sif, "tr", sehir, secrets.token_hex(4))
    sozluk = tarayici._proxy_sozlugu(adres)
    sonuc = {"result": "error", "organik": [], "url": "", "mesaj": ""}
    with sync_playwright() as p:
        try:
            baglam = tarayici._baglam_ac(p, True, sozluk, tarayici.MASUSTU, tarayici.MASUSTU_UA)
        except Exception as h:
            print(f"sehir={sehir}: baglam yok {str(h)[:60]}")
            continue
        tarayici._tara(baglam, "erzurum escort", None, 2, sonuc)
        baglam.close()
    kumeler = [kok(k["link"]) for k in sonuc["organik"]]
    var = [r for r in ref if r in kumeler]
    print(f"sehir={sehir}: result {sonuc['result']} · adet {len(kumeler)} · referans {len(var)}/{len(ref)}")
    for k in sonuc["organik"][:10]:
        print("   ", k["position"], k["link"][:70])