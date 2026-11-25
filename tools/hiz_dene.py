import json
import re
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

KOK = Path(r"C:\Users\developer\Desktop\App\unique_request_bot")
CIKTI = KOK / "veri" / "hiz_dene.json"
KELIME = "erzurum escort"
EKLE = "&gl=tr&hl=tr"
KUME1 = "erzurumescortr.com"

GIZLE = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    "Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']});"
    "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});"
    "window.chrome = {runtime: {}};"
)

ARGUMANLAR = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,OptimizationHints",
    "--lang=tr-TR",
    "--disable-dev-shm-usage",
]

AYIKLA = """
() => {
  const kapsam = document.querySelector('#rso') || document.body;
  return Array.from(kapsam.querySelectorAll('a[href]'))
    .filter(a => a.querySelector('h3'))
    .map(a => {
      const c = a.querySelector('cite');
      return {h: a.href, c: c ? c.textContent : ''};
    });
}
"""

SEMA = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")
ALAN = re.compile(r"^[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-]+)+$")


def host(ham):
    for metin in (ham.get("h") or "", ham.get("c") or ""):
        m = (metin or "").strip()
        if not m:
            continue
        for isaret in ("/url?q=", "/url?url=", "/goto?url="):
            if isaret in m:
                m = unquote(m.split(isaret, 1)[1].split("&")[0])
                break
        m = SEMA.sub("", m).strip().split(" ")[0]
        m = m.split("/")[0].split("?")[0].split("#")[0].strip().lower()
        if m.startswith("www."):
            m = m[4:]
        if ALAN.match(m):
            return m
    return ""


def google_mu(k):
    return (
        k in ("google.com", "google.com.tr", "gstatic.com")
        or k.startswith("www.google.")
        or k.startswith("accounts.google.")
        or k.startswith("policies.google.")
    )


def liste(sayfa):
    try:
        ham = sayfa.evaluate(AYIKLA) or []
    except Exception:
        return []
    gorulen = []
    for kayit in ham:
        k = host(kayit)
        if not k or google_mu(k) or "gstatic" in k:
            continue
        if k not in gorulen:
            gorulen.append(k)
    return gorulen


def kutu(sayfa):
    for sec in ("textarea[name=q]", "input[name=q]", "#APjFqb"):
        try:
            e = sayfa.locator(sec).first
            if e.count():
                return e
        except Exception:
            pass
    return None


def kos(no):
    bas = time.time()
    yol = tempfile.mkdtemp(prefix="hiz_")
    kayit = {"no": no, "sonuc": "?", "liste": [], "sure": 0.0}
    baglam = None
    try:
        with sync_playwright() as pw:
            baglam = pw.chromium.launch_persistent_context(
                yol,
                headless=False,
                channel="chromium",
                viewport={"width": 1536, "height": 730},
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                args=ARGUMANLAR,
                ignore_default_args=["--enable-automation"],
            )
            baglam.add_init_script(GIZLE)
            sayfa = baglam.pages[0] if baglam.pages else baglam.new_page()
            sayfa.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=60000)
            sayfa.wait_for_timeout(1800)
            for sec in ("#L2AGLb", "button:has-text('Tumunu kabul et')", "button:has-text('Kabul et')", "button:has-text('Accept all')"):
                try:
                    d = sayfa.locator(sec).first
                    if d.count():
                        d.click(timeout=2500)
                        sayfa.wait_for_timeout(900)
                        break
                except Exception:
                    pass
            e = kutu(sayfa)
            if e is None:
                kayit["sonuc"] = "kutu_yok"
            else:
                e.click()
                e.fill("")
                for parca in KELIME.split(" "):
                    e.type(parca + " ", delay=60)
                e.press("Enter")
                for i in range(3):
                    sayfa.wait_for_timeout(2200 + i * 2000)
                    try:
                        if "/sorry/" not in sayfa.url:
                            break
                    except Exception:
                        break
                try:
                    url = sayfa.url
                except Exception:
                    url = ""
                if "/sorry/" in url:
                    kayit["sonuc"] = "duvar"
                else:
                    sayfa.goto(url + EKLE, wait_until="domcontentloaded", timeout=60000)
                    sayfa.wait_for_timeout(2600)
                    for _ in range(6):
                        try:
                            sayfa.mouse.wheel(0, 2400)
                            sayfa.wait_for_timeout(650)
                        except Exception:
                            break
                    kayit["liste"] = liste(sayfa)
                    kayit["sonuc"] = "ok" if kayit["liste"] else "bos"
    except Exception as hata:
        kayit["sonuc"] = "hata"
        kayit["not"] = str(hata)[:120]
    finally:
        try:
            baglam.close()
        except Exception:
            pass
        shutil.rmtree(yol, ignore_errors=True)
        kayit["sure"] = round(time.time() - bas, 1)
    return kayit


def grup(n, etiket):
    bas = time.time()
    with ThreadPoolExecutor(max_workers=n) as havuz:
        kayitlar = list(havuz.map(kos, range(1, n + 1)))
    duvar = round(time.time() - bas, 1)
    kume1 = sum(1 for k in kayitlar if KUME1 in k["liste"])
    duvarlar = sum(1 for k in kayitlar if k["sonuc"] == "duvar")
    hatalar = sum(1 for k in kayitlar if k["sonuc"] == "hata")
    ort = round(sum(k["sure"] for k in kayitlar) / max(len(kayitlar), 1), 1)
    print("###", etiket, "| eszamanli:", n, "| duvar saat:", duvar, "sn | kelime/sn:", ort,
          "| kume1:", kume1, "/", n, "| duvar:", duvarlar, "| hata:", hatalar,
          "| hit/dk:", round(n * 60 / max(duvar, 1), 2))
    for k in kayitlar:
        print("   ", k["no"], k["sonuc"], k["sure"], "sn", "kume1" if KUME1 in k["liste"] else "kume2")
    return {"etiket": etiket, "n": n, "duvar": duvar, "kume1": kume1, "duvar_sayisi": duvarlar,
            "hata": hatalar, "hit_dk": round(n * 60 / max(duvar, 1), 2)}


def main():
    hepsi = []
    for n, etiket in ((1, "tek"), (4, "paralel4"), (8, "paralel8")):
        hepsi.append(grup(n, etiket))
        time.sleep(4)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(hepsi, ensure_ascii=False, indent=1), encoding="utf-8")
    print("dosya:", CIKTI)


if __name__ == "__main__":
    main()