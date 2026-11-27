import pathlib
import tempfile

from playwright.sync_api import sync_playwright

from worker import tarayici

tarayici.PROFIL = pathlib.Path(tempfile.mkdtemp(prefix="dok_"))
with sync_playwright() as p:
    baglam = p.chromium.launch_persistent_context(
        str(tarayici.PROFIL), headless=True, channel="chromium",
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
    ham = sayfa.eval_on_selector_all("a[href]", tarayici.AYIKLA_JS)
    print("ham:", len(ham))
    for i, r in enumerate(ham, 1):
        print(f"  {i:02d} cite={r['cite'][:45]!r} href={r['href'][:55]}")
    temiz = tarayici._temizle(ham, None)
    print("temiz:", len(temiz))
    for r in temiz:
        print("   →", r["link"][:60])
    baglam.close()