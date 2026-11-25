import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curl_cffi import requests

ARAMA = "https://www.google.com/search"
CEREZLER = {
    "SOCS": "CAISNQgQEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMzE5LjA4X3AxGgJlbiACGgYIgLC_rwY",
    "CONSENT": "YES+cb.20240101-00-p0.tr+FX+111",
}

with requests.Session(impersonate="chrome131") as oturum:
    y = oturum.get(ARAMA, params={"q": "erzurum escort", "hl": "tr", "gl": "tr"},
                   headers={"Accept-Language": "tr-TR,tr;q=0.9"}, cookies=CEREZLER, timeout=30)

html = y.content.decode("utf-8", "replace")
print("durum:", y.status_code, "| uzunluk:", len(html))
for isaret in ("/url?q=", "/goto?", "data-ved", "rso", "cite", "h3", "MjjYud", "yuRUbf", "id=\"search\"", "erzurumescortr", "javascript"):
    print(isaret, "->", html.count(isaret))
print("--- ilk 600 ---")
print(html[:600].replace(chr(10), " ")[:600])