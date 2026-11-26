from playwright.sync_api import sync_playwright

from worker import havuz, tarayici

secim = havuz.sec_mod(None, False)
sozluk = tarayici._proxy_sozlugu(secim[1] if secim else None)
print("proxy:", sozluk["server"] if sozluk else "yok")

with sync_playwright() as p:
    baglam = tarayici._baglam_ac(p, True, sozluk, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    sayfa = baglam.new_page()
    for sira in range(3):
        adres = f"{tarayici.ARAMA_URL}?q=erzurum%20escort&start={sira * 10}&hl=tr&gl=tr"
        try:
            y = sayfa.goto(adres, wait_until="domcontentloaded", timeout=40_000)
            durum = y.status if y else None
        except Exception as h:
            print(f"sayfa {sira + 1}: GOTO HATA {str(h)[:80]}")
            continue
        try:
            sayfa.wait_for_selector("#rso", timeout=12_000)
        except Exception:
            pass
        sayfa.wait_for_timeout(4_000)
        adet = sayfa.eval_on_selector_all("a[href]", "els => els.filter(a => a.querySelector('h3')).length")
        rso = sayfa.eval_on_selector_all("#rso", "els => els.length")
        print(f"sayfa {sira + 1}: http {durum} · rso {rso} · h3'lu bag {adet} · url {sayfa.url[:60]}")
        if adet:
            for h in sayfa.eval_on_selector_all("a[href]", "els => els.filter(a => a.querySelector('h3')).slice(0, 5).map(a => a.href)")[:5]:
                print("   ", h[:80])
    baglam.close()