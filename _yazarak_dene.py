import pathlib
import tempfile

from playwright.sync_api import sync_playwright

from worker import guven, tarayici

tarayici.PROFIL = pathlib.Path(tempfile.mkdtemp(prefix="yaz_"))
guven.uygula = lambda *a, **k: False

with sync_playwright() as p:
    baglam = tarayici._baglam_ac(p, True, None, tarayici.MASUSTU, tarayici.MASUSTU_UA)
    sayfa = baglam.new_page()
    sayfa.goto("https://www.google.com/?hl=tr", wait_until="domcontentloaded", timeout=40_000)
    for secici in ("button:has-text('Tümünü kabul et')", "button:has-text('Accept all')"):
        try:
            sayfa.click(secici, timeout=2_500)
            break
        except Exception:
            pass
    sayfa.fill("textarea[name=q], input[name=q]", "erzurum escort")
    sayfa.keyboard.press("Enter")
    try:
        sayfa.wait_for_selector("#rso", timeout=20_000)
    except Exception:
        pass
    sayfa.wait_for_timeout(4_000)
    print("URL:", sayfa.url[:110])
    ham = sayfa.eval_on_selector_all("a[href]", tarayici.AYIKLA_JS)
    temiz = tarayici._temizle(ham, None)
    print("YAZARAK:", len(ham), "ham ·", len(temiz), "temiz")
    for r in temiz[:15]:
        print("  ", r["position"], r["link"][:70])
    baglam.close()