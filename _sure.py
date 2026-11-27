import time

from playwright.sync_api import sync_playwright

from worker import havuz, isinma, tarayici

t0 = time.perf_counter()
secim = havuz.sec_mod("erzurum", False)
sozluk = tarayici._proxy_sozlugu(secim[1])
print("proxy hazir:", round(time.perf_counter() - t0, 1))

with sync_playwright() as p:
    t = time.perf_counter()
    baglam = tarayici._baglam_ac(p, True, sozluk, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    print("baglam:", round(time.perf_counter() - t, 1))
    sayfa = baglam.new_page()
    t = time.perf_counter()
    print("isinma:", isinma.tarayicida(sayfa)["result"], round(time.perf_counter() - t, 1))
    sayfa2 = baglam.new_page()
    t = time.perf_counter()
    yanit = tarayici._ara(sayfa2, "erzurum escort")
    print("ara:", yanit.status if yanit else None, round(time.perf_counter() - t, 1))
    t = time.perf_counter()
    try:
        sayfa2.wait_for_selector("#rso", timeout=12_000)
    except Exception:
        pass
    tarayici._bekle(sayfa2, 2_500)
    ham = sayfa2.eval_on_selector_all("a[href]", tarayici.AYIKLA_JS)
    print("ayikla:", len(ham), round(time.perf_counter() - t, 1))
    baglam.close()
print("toplam:", round(time.perf_counter() - t0, 1))