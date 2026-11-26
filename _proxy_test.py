from curl_cffi import requests

from worker import havuz

secim = havuz.sec_mod(None, False)
if secim is None:
    print("SECIM YOK")
    raise SystemExit(1)
print("saglayici:", secim[0], "mod:", secim[2], "tur:", secim[3])
print("adres:", secim[1][:60])
try:
    r = requests.get("https://ipinfo.io/json", proxies={"http": secim[1], "https": secim[1]},
                     impersonate="chrome124", timeout=40)
    print("durum:", r.status_code)
    print(r.text[:400])
except Exception as h:
    print("HATA:", h)