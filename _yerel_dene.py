import pathlib
import tempfile

from playwright.sync_api import sync_playwright

from worker import tarayici
from worker.serp_ortak import kok

REF = ["erzurumescortr.com", "happyescorts.com", "escortlar185.xyz", "erzurumescort.icu",
       "escortlar178.xyz", "elitescorthatun.com", "rehberalem.com", "yandex.com",
       "google.com", "erzurumescortvip.com"]


def dene(kanal: str, headless: bool) -> None:
    tarayici.PROFIL = pathlib.Path(tempfile.mkdtemp(prefix="dene_"))
    try:
        with sync_playwright() as p:
            baglam = p.chromium.launch_persistent_context(
                str(tarayici.PROFIL), headless=headless, channel=kanal,
                locale="tr-TR", timezone_id="Europe/Istanbul", viewport=tarayici.MASUSTU,
                user_agent=tarayici.MASUSTU_UA, args=list(tarayici.ARGUMANLAR),
                ignore_default_args=["--enable-automation"])
            baglam.add_init_script(tarayici.GIZLE_JS)
            baglam.add_cookies(tarayici.ONAY_CEREZLERI)
            sayfa = baglam.new_page()
            tarayici._ara(sayfa, "erzurum escort")
            try:
                sayfa.wait_for_selector("#rso", timeout=12_000)
            except Exception:
                pass
            tarayici._bekle(sayfa, 2_500)
            ua = sayfa.evaluate("() => navigator.userAgent")
            ham = sayfa.eval_on_selector_all("a[href]", tarayici.AYIKLA_JS)
            temiz = tarayici._temizle(ham, None)
            baglam.close()
    except Exception as h:
        print(f"[{kanal} headless={headless}] HATA: {str(h)[:90]}")
        return
    kumeler = [kok(k["link"]) for k in temiz]
    var = [r for r in REF if r in kumeler]
    print(f"[{kanal} headless={headless}] adet {len(kumeler)} · eslesme {len(var)}/{len(REF)}")
    print("   UA:", ua[:90])
    for k in temiz[:12]:
        print("   ", k["position"], k["link"][:66])


dene("chromium", True)
dene("chromium", False)
dene("chrome", False)