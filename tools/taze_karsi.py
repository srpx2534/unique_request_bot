import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

KOK = Path(r"C:\Users\developer\Desktop\App\unique_request_bot")
CIKTI = KOK / "veri" / "taze_karsi.json"

TAM = "https://www.google.com/search?q=erzurum+escort&sca_esv=d692c529a49cacda&sxsrf=AKL5yDiaRJGHh_pQFsptqIaqnw4ZOe-OdA%3A1794940662520&ei=9p78ap6kH-zlxc8P8LeqoQg&biw=1536&bih=730&uact=5&oq=erzurum+escort&gs_lp=Egxnd3Mtd2l6LXNlcnAiDmVyenVydW0gZXNjb3J0SO0DUABYAHABeACQAQCYAQCgAQCqAQC4AQPIAQCYAgCgAgCYAwCIBgGSBwCgBwCyBwC4BwDCBwDIBwCACAE&sclient=gws-wiz-serp"
SADE = "https://www.google.com/search?q=erzurum+escort&hl=tr&gl=tr"
ULKE = "w+CAIQICIGVHVya2V5"

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


def liste(sayfa):
    try:
        ham = sayfa.evaluate(AYIKLA) or []
    except Exception:
        return []
    gorulen = []
    for kayit in ham:
        k = host(kayit)
        if not k or "google." in k or "gstatic" in k:
            continue
        if k not in gorulen:
            gorulen.append(k)
    return gorulen


def kos(pw, ad, url, olcu, kaydir):
    yol = tempfile.mkdtemp(prefix="taze_")
    kayit = {"ad": ad, "sonuc": "?", "liste": [], "son_url": ""}
    baglam = None
    try:
        baglam = pw.chromium.launch_persistent_context(
            yol,
            headless=False,
            channel="chromium",
            viewport=olcu,
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            args=ARGUMANLAR,
            ignore_default_args=["--enable-automation"],
        )
        baglam.add_init_script(GIZLE)
        sayfa = baglam.pages[0] if baglam.pages else baglam.new_page()
        for i in range(3):
            try:
                sayfa.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception as hata:
                kayit["not"] = str(hata)[:140]
            try:
                sayfa.wait_for_timeout(2500 + i * 2500)
            except Exception:
                pass
            try:
                if "/sorry/" not in sayfa.url:
                    break
            except Exception:
                break
        try:
            kayit["son_url"] = sayfa.url
        except Exception:
            kayit["son_url"] = ""
        if "/sorry/" in kayit["son_url"]:
            kayit["sonuc"] = "duvar"
        else:
            if kaydir:
                for _ in range(10):
                    try:
                        sayfa.mouse.wheel(0, 2600)
                        sayfa.wait_for_timeout(900)
                    except Exception:
                        break
            kayit["liste"] = liste(sayfa)
            kayit["sonuc"] = "ok" if kayit["liste"] else "bos"
    except Exception as hata:
        kayit["sonuc"] = "hata"
        kayit["not"] = str(hata)[:220]
    finally:
        try:
            baglam.close()
        except Exception:
            pass
        shutil.rmtree(yol, ignore_errors=True)
    return kayit


def main():
    sonuc = []
    with sync_playwright() as pw:
        sonuc.append(kos(pw, "D_tam_uule_yok_kaydir", TAM, {"width": 1536, "height": 730}, True))
        sonuc.append(kos(pw, "E_eski_ayar_uule_1366", SADE + "&uule=" + ULKE, {"width": 1366, "height": 768}, True))
        sonuc.append(kos(pw, "F_tam_uule_1536", TAM + "&uule=" + ULKE, {"width": 1536, "height": 730}, True))
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in sonuc:
        print("===", k["ad"], "|", k["sonuc"], "| sayi:", len(k["liste"]))
        for i, h in enumerate(k["liste"], 1):
            print("  ", i, h)
        if k.get("not"):
            print("   not:", k["not"])
    for i in range(len(sonuc)):
        for j in range(i + 1, len(sonuc)):
            a = set(sonuc[i]["liste"][:20])
            b = set(sonuc[j]["liste"][:20])
            if a and b:
                print("ortak", sonuc[i]["ad"], "/", sonuc[j]["ad"], ":", round(100 * len(a & b) / max(len(a), len(b)), 1), "%")
    print("dosya:", CIKTI)


if __name__ == "__main__":
    main()