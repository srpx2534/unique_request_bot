from playwright.sync_api import sync_playwright

from worker import havuz, tarayici

secim = havuz.sec_mod(None, False)
sozluk = tarayici._proxy_sozlugu(secim[1] if secim else None)

with sync_playwright() as p:
    baglam = tarayici._baglam_ac(p, True, sozluk, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    cozucu = lambda h: tarayici._goto_coz(baglam, h)
    sayfa = baglam.new_page()
    for sira in range(3):
        adres = f"{tarayici.ARAMA_URL}?q=erzurum%20escort&start={sira * 10}&hl=tr&gl=tr"
        yanit = tarayici._git(sayfa, adres)
        try:
            sayfa.wait_for_selector("#rso", timeout=15_000)
            sayfa.wait_for_load_state("networkidle", timeout=15_000)
        except Exception as h:
            print("  bekleme hatasi:", str(h)[:60])
        tarayici._bekle(sayfa, 4_000)
        ham = sayfa.eval_on_selector_all("a[href]", tarayici.AYIKLA_JS)
        temiz = tarayici._temizle(ham, cozucu)
        print(f"sayfa {sira + 1}: http {yanit.status if yanit else None} · ham {len(ham)} · temiz {len(temiz)}")
        for r in temiz:
            print("   ", r["position"], r["link"][:70])
    baglam.close()