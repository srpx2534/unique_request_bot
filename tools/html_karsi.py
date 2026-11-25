import json
import re
import time
from pathlib import Path

from curl_cffi import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker.serp_html import captcha_mi, sonuclari_ayikla
from worker.serp_ortak import kok

KOK = Path(r"C:\Users\developer\Desktop\App\unique_request_bot")
CIKTI = KOK / "veri" / "html_karsi.json"
KELIME = "erzurum escort"
ARAMA = "https://www.google.com/search"
PROFIL = "chrome131"
CEREZLER = {
    "SOCS": "CAISNQgQEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMzE5LjA4X3AxGgJlbiACGgYIgLC_rwY",
    "CONSENT": "YES+cb.20240101-00-p0.tr+FX+111",
}
BASLIKLAR = {"Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}

REF = [
    "erzurumescortr.com", "isataka.site", "smartlogogenerator.site", "aisin-job.site",
    "webtensor.site", "squanch.live", "elitescorthatun.com", "erzurumescortvip.com",
    "sites.google.com", "escortturizmerzurumsb.rehberalem.com",
]


def tek(no, num):
    kayit = {"no": no, "num": num, "result": "?", "sayi": 0, "bytes": 0, "liste": [], "kume1": False}
    parametreler = {"q": KELIME, "hl": "tr", "gl": "tr"}
    if num:
        parametreler["num"] = "100"
    try:
        with requests.Session(impersonate=PROFIL) as oturum:
            yanit = oturum.get(ARAMA, params=parametreler, headers=BASLIKLAR,
                               cookies=CEREZLER, timeout=30)
        html = yanit.content.decode("utf-8", "replace")
        kayit["bytes"] = len(yanit.content)
        if yanit.status_code != 200:
            kayit["result"] = "http" + str(yanit.status_code)
        elif captcha_mi(str(yanit.url), html):
            kayit["result"] = "duvar"
        else:
            liste = sonuclari_ayikla(html)
            kayit["liste"] = liste
            kayit["sayi"] = len(liste)
            kayit["kume1"] = "erzurumescortr.com" in liste
            kayit["result"] = "ok" if liste else "bos"
    except Exception as hata:
        kayit["result"] = "hata"
        kayit["not"] = str(hata)[:120]
    return kayit


def oran(liste_):
    return round(100 * len(set(liste_[:20]) & set(REF)) / len(REF), 1)


def main():
    hepsi = []
    for num in (True, False):
        for no in range(1, 4):
            k = tek(no, num)
            hepsi.append(k)
            print("===", "num100" if num else "num_yok", no, "|", k["result"],
                  "| sayi:", k["sayi"], "| bytes:", k["bytes"], "| REF:", oran(k["liste"]), "%")
            for i, h in enumerate(k["liste"][:12], 1):
                print("   ", i, h, "" if h in REF else "  <-- REF disi")
            time.sleep(3)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(hepsi, ensure_ascii=False, indent=1), encoding="utf-8")
    print("dosya:", CIKTI)


if __name__ == "__main__":
    main()