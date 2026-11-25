import json
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

KOK = Path(r"C:\Users\developer\Desktop\App\unique_request_bot")
CIKTI = KOK / "veri" / "oylama_dene.json"
KELIME = "erzurum escort"
ULKE = "w+CAIQICIGVHVya2V5"
EKLE = "&gl=tr&hl=tr"

REF = [
    "erzurumescortr.com", "isataka.site", "smartlogogenerator.site", "aisin-job.site",
    "webtensor.site", "squanch.live", "elitescorthatun.com", "erzurumescortvip.com",
    "sites.google.com", "escortturizmerzurumsb.rehberalem.com",
]

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


def kos(pw, ad, ekle):
    yol = tempfile.mkdtemp(prefix="oyl_")
    kayit = {"ad": ad, "ekle": ekle or "", "sonuc": "?", "liste": []}
    baglam = None
    try:
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
        sayfa.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=45000)
        sayfa.wait_for_timeout(2200)
        for sec in ("#L2AGLb", "button:has-text('Tumunu kabul et')", "button:has-text('Kabul et')", "button:has-text('Accept all')"):
            try:
                d = sayfa.locator(sec).first
                if d.count():
                    d.click(timeout=3000)
                    sayfa.wait_for_timeout(1200)
                    break
            except Exception:
                pass
        e = kutu(sayfa)
        if e is None:
            kayit["sonuc"] = "kutu_yok"
            return kayit
        e.click()
        e.fill("")
        for parca in KELIME.split(" "):
            e.type(parca + " ", delay=90)
        e.press("Enter")
        for i in range(3):
            sayfa.wait_for_timeout(2600 + i * 2200)
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
            if ekle:
                try:
                    sayfa.goto(url + ekle, wait_until="domcontentloaded", timeout=45000)
                    sayfa.wait_for_timeout(3000)
                except Exception as hata:
                    kayit["not"] = str(hata)[:120]
            for _ in range(8):
                try:
                    sayfa.mouse.wheel(0, 2400)
                    sayfa.wait_for_timeout(800)
                except Exception:
                    break
            kayit["liste"] = liste(sayfa)
            kayit["sonuc"] = "ok" if kayit["liste"] else "bos"
    except Exception as hata:
        kayit["sonuc"] = "hata"
        kayit["not"] = str(hata)[:200]
    finally:
        try:
            baglam.close()
        except Exception:
            pass
        shutil.rmtree(yol, ignore_errors=True)
    return kayit


def oran(liste_, ref):
    a = set(liste_[:20])
    b = set(ref)
    if not b:
        return 0.0
    return round(100 * len(a & b) / len(b), 1)


def oyla(kosular):
    sayac = Counter()
    sira = defaultdict(list)
    for k in kosular:
        for i, h in enumerate(k["liste"][:20]):
            sayac[h] += 1
            sira[h].append(i)
    siralama = sorted(sayac, key=lambda h: (-sayac[h], sum(sira[h]) / len(sira[h])))
    return siralama


def main():
    sonuc = []
    with sync_playwright() as pw:
        for n in range(1, 7):
            ekle = (EKLE + "&uule=" + ULKE) if n % 2 == 1 else EKLE
            sonuc.append(kos(pw, "R" + str(n) + ("_uule" if n % 2 == 1 else "_uulesiz"), ekle))
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in sonuc:
        print("===", k["ad"], "|", k["sonuc"], "| sayi:", len(k["liste"]), "| REF:", oran(k["liste"], REF), "%")
    uuleli = [k for k in sonuc if "uule" in k["ad"] and "uulesiz" not in k["ad"]]
    uulesiz = [k for k in sonuc if "uulesiz" in k["ad"]]
    for ad, grup in (("UULELI_OY", uuleli), ("UULESIZ_OY", uulesiz), ("TUM_OY", sonuc)):
        oy = oyla(grup)
        print("---", ad, "| REF:", oran(oy, REF), "%")
        for i, h in enumerate(oy[:15], 1):
            print("  ", i, h, "" if h in REF else "  <-- REF'te yok")
    print("dosya:", CIKTI)


if __name__ == "__main__":
    main()