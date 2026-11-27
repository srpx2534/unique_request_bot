from curl_cffi import requests

from worker import havuz

for sehir in ("erzurum", None):
    secim = havuz.sec_mod(sehir, False)
    if secim is None:
        print(f"sehir={sehir}: secim yok")
        continue
    adres = secim[1]
    print(f"sehir={sehir}: mod={secim[2]} tur={secim[3]}")
    print("   adres:", adres)
    try:
        r = requests.get("https://ipinfo.io/json", proxies={"http": adres, "https": adres},
                         impersonate="chrome124", timeout=40)
        veri = r.json()
        print("   →", r.status_code, veri.get("city"), veri.get("region"), veri.get("country"))
    except Exception as h:
        print("   → HATA:", str(h)[:120])