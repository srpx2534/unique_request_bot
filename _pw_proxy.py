from worker import havuz, tarayici

secim = havuz.sec_mod(None, False)
print("secim:", secim[0], secim[1][:55])
sozluk = tarayici._proxy_sozlugu(secim[1])
print("proxy sozlugu:", sozluk["server"], "· kullanici:", (sozluk.get("username") or "")[:20],
      "· sifre var:", bool(sozluk.get("password")))

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    baglam = p.chromium.launch_persistent_context(
        str(tarayici.PROFIL), headless=True, channel="chromium", proxy=sozluk,
        locale="tr-TR", timezone_id="Europe/Istanbul", viewport=tarayici.MASUSTU,
        user_agent=tarayici.MASUSTU_UA, args=list(tarayici.ARGUMANLAR),
        ignore_default_args=["--enable-automation"],
    )
    sayfa = baglam.new_page()
    for adres in ("https://ipinfo.io/json", "https://www.google.com/search?q=erzurum+escort&hl=tr&gl=tr"):
        try:
            y = sayfa.goto(adres, wait_until="domcontentloaded", timeout=40_000)
            print(adres[:45], "→", y.status if y else None, "·", sayfa.url[:60])
            print("  govde:", sayfa.inner_text("body")[:120].replace("\n", " "))
        except Exception as h:
            print(adres[:45], "→ HATA:", str(h)[:120])
    baglam.close()