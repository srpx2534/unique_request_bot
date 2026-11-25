"""Gercek tarayici ile SERP okuma — olcum hattinin birinci yolu.

Yerel kullanicinin gordugu sayfayi uretmenin tek guvenilir yolu budur:
TR residential proxy uzerinden gercek Chromium, `tr-TR` yerel ayari,
Istanbul saat dilimi, masaustu olcude pencere. IP sinifi ve JS ile kurulan
sonuc listesi gercek kullaniciya yaklasir.

Neden gerekli: SERP API'leri otomatik trafige tam gorunen ama farkli sonuc
listesi dondurebiliyor (zehirlenmis SERP). Ayrica Google sonuc baglantilarini
`google.com/goto` ile sarmaladigi icin ham HTML'de hedef adres yoktur;
render edilmis `href` gercek adresi verir.

Playwright kurulu degilse `kullanilabilir()` False doner ve cagiran taraf
API yedegine duser; modul importu bu yuzden kosulludur.

Kullanim: worker/olcum_a.py, tools/serp_karsilastir.py.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from worker import guven, havuz, isinma, zehir
from worker.serp_ortak import ULKE_UULE, kok

try:  # pragma: no cover - kurulum ortamina bagli
    from playwright.sync_api import sync_playwright
except Exception:  # noqa: BLE001
    sync_playwright = None  # type: ignore[assignment]

KOK = Path(__file__).resolve().parents[1]
# Kalici profil: cerezler ve guven biriksin, her kosuda sifirdan baslamasin.
PROFIL = KOK / "veri" / "tarayici_profil"
# `AutomationControlled` kapatilir; yoksa yeni headless de yakalaniyor.
ARGUMANLAR = (
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-first-run", "--no-zygote", "--disable-gpu", "--hide-scrollbars",
    "--mute-audio", "--force-color-profile=srgb",
)
GIZLE_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => false});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr']});
window.chrome = { runtime: {}, loadTimes() {}, csi() {}, app: {} };
Object.defineProperty(window.screen, 'width', {get: () => 1920});
Object.defineProperty(window.screen, 'height', {get: () => 1080});
Object.defineProperty(window.screen, 'colorDepth', {get: () => 24});
"""
MOBIL_UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36")
MASUSTU_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/159.0.0.0 Safari/537.36")

ARAMA_URL = "https://www.google.com/search"
SAYFA_BASI = 10  # Google tek sayfada 10 organik sonuc verir
AZAMI_SAYFA = 10  # ilk 100 sira
ZAMAN_ASIMI_MS = 45_000
BEKLEME_MS = 4_000
DUVAR_BEKLEME_MS = 10_000  # duvar sonrasi ilk bekleme; her denemede katlanir
DUVAR_DENEME = 3
IP_DENEME = 2  # zehirli sayfa ya da duvarda kac IP denenir  # duvarda en fazla kac kez beklenip yeniden denenir  # sonuc listesi JS ile kurulur, kisa bekleme yetmez
# Onay duvarini atlar; cerezler oturum boyunca korunur.
ONAY_CEREZLERI = [
    {"name": "SOCS", "value": "CAISNQgQEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMzE5LjA4X3AxGgJlbiACGgYIgLC_rwY",
     "domain": ".google.com", "path": "/"},
    {"name": "CONSENT", "value": "YES+cb.20240101-00-p0.tr+FX+111",
     "domain": ".google.com", "path": "/"},
]
MASUSTU = {"width": 1366, "height": 768}
MOBIL = {"width": 412, "height": 915}
# Organik sonuc baglantilari: baslik (h3) tasiyan ve arama kutusunun icinde
# kalan baglantilar. Reklam ve "ilgili aramalar" h3 tasimadigi icin elenir.
# Baslik (h3) tasiyan baglantilar organik sonuctur; reklam ve gezinme
# baglantilari h3 tasimadigi icin elenir. `#rso` yoksa govdeye dusulur.
# Baslik (h3) tasiyan baglanti organik sonuctur. Organik baglanti cogu zaman
# `/url?q=` sarmalindadir, bu yuzden href oneki `http` ile suzulmez.
AYIKLA_JS = """
() => {
  const kapsam = document.querySelector('#rso') || document.body;
  return Array.from(kapsam.querySelectorAll('a[href]'))
    .filter(a => a.querySelector('h3'))
    .map(a => {
      const kutu = a.closest('div.g') || a.closest('div.MjjYud') ||
                   a.closest('div[data-hveid]') || a.parentElement;
      const cite = kutu ? kutu.querySelector('cite') : null;
      return { cite: cite ? cite.innerText : '', baslik: (a.querySelector('h3') || {}).innerText || '', href: a.href };
    });
}
"""


def kullanilabilir() -> bool:
    """Playwright ve Chromium kullanilabilir mi.

    Returns:
        Tarayici yolu denenebilirse True.
    """
    return sync_playwright is not None


def _proxy_sozlugu(proxy_adres: str | None) -> dict | None:
    """Proxy dizesini Playwright bicimine cevirir.

    Args:
        proxy_adres: http://kullanici:sifre@host:port

    Returns:
        Playwright proxy sozlugu ya da None.
    """
    if not proxy_adres:
        return None
    parca = proxy_adres.split("://", 1)[-1]
    kimlik, _, host = parca.rpartition("@")
    if not kimlik:
        return {"server": f"http://{host}"}
    kullanici, _, sifre = kimlik.partition(":")
    return {"server": f"http://{host}", "username": kullanici, "password": sifre}


def _gercek_adres(adres: str) -> str:
    """Google'in `/url?q=` sarmalini cozer; sarmal yoksa adresi oldugu gibi verir.

    Args:
        adres: Sayfadan toplanan ham adres.

    Returns:
        Hedef adres; cozulemezse ham adres.
    """
    try:
        parca = urlparse(adres)
    except ValueError:
        return adres
    if "google." in parca.netloc and parca.path == "/url":
        hedef = parse_qs(parca.query).get("q")
        if hedef:
            return unquote(hedef[0])
    return adres


def _temizle(adresler: list[str]) -> list[dict]:
    """Adres listesini benzersiz kok ve 1 tabanli siraya cevirir.

    Args:
        adresler: Sayfadan toplanan ham adresler.

    Returns:
        {"position", "link"} sozlukleri.
    """
    gorulen: set[str] = set()
    kayitlar: list[dict] = []
    for kayit in adresler:
        if isinstance(kayit, dict):
            cite = str(kayit.get("cite") or "").strip()
            ham = str(kayit.get("href") or "")
            baslik = str(kayit.get("baslik") or "").strip()
        else:
            cite, ham, baslik = "", str(kayit), ""
        # `/goto?url=CAES...` yerel cozulemiyor; sonuc satirinda gorunen adres
        # (`cite`) zaten hedef koku veriyor, ek istek gerekmiyor.
        adres = cite if cite else _gercek_adres(ham)
        if not adres or "google." in adres or "gstatic." in adres:
            continue
        k = kok(adres)
        if not k or k in gorulen:
            continue
        gorulen.add(k)
        kayitlar.append({
            "position": len(kayitlar) + 1,
            "baslik": baslik,
            "link": adres if "://" in adres else f"https://{adres}",
        })
    return kayitlar


def _bekle(sayfa, ms: int) -> bool:
    """Sayfayi bekler; sayfa kapanmissa False doner.

    Args:
        sayfa: Acik sayfa.
        ms: Bekleme, milisaniye.

    Returns:
        Sayfa hala aciksa True.
    """
    try:
        sayfa.wait_for_timeout(ms)
        return True
    except Exception:  # noqa: BLE001
        return False


def _baglam_ac(p, headless: bool, proxy_ayar, olcek, ua):
    """Kalici profille baglam acar.

    Args:
        p: Playwright nesnesi.
        headless: Gizli mi calissin; duvarda gorunur pencereye gecmek icin False.
        proxy_ayar: Proxy sozlugu ya da None.
        olcek: Pencere olcusu.
        ua: User-Agent.

    Returns:
        Baglam.
    """
    baglam = p.chromium.launch_persistent_context(
        str(PROFIL), headless=headless, channel="chromium", proxy=proxy_ayar,
        locale="tr-TR", timezone_id="Europe/Istanbul", viewport=olcek,
        user_agent=ua, args=list(ARGUMANLAR),
        ignore_default_args=["--enable-automation"],
    )
    baglam.add_init_script(GIZLE_JS)
    # Kabul gormus Google cerez seti varsa onay cerezleri yerine o yuklenir:
    # arama isitilmis kimlikten cikar ve her IP icin tarayici isitmasi gerekmez.
    if not guven.uygula(baglam):
        baglam.add_cookies(ONAY_CEREZLERI)
    return baglam


def _tara(baglam, sorgu: str, domain: str | None, azami: int, sonuc: dict,
          elle: bool = False) -> dict:
    """Sayfalari gezer ve organik kayitlari toplar.

    Args:
        baglam: Tarayici baglami.
        sorgu: Aranacak kelime.
        domain: Hedef alan adi; bulununca tarama kesilir.
        azami: En fazla sayfa.
        sonuc: Doldurulacak sozluk.
        elle: Duvar cikarsa elle cozme beklenir (gorunur pencere).

    Returns:
        Guncellenmis sonuc sozlugu.
    """
    sayfa = baglam.new_page()
    # Arama isitilmis kimlikten cikmali: taze proxy IP'sinde Google dogrudan
    # acilirsa duvar ya da baska kelimenin listesi gelebiliyor.
    sonuc["isinma"] = isinma.tarayicida(sayfa)["result"]
    for sira in range(azami):
        basla = sira * SAYFA_BASI
        adres = (f"{ARAMA_URL}?q={quote(sorgu)}&start={basla}&hl=tr&gl=tr"
                 f"&uule={quote(ULKE_UULE, safe='')}")
        yanit = sayfa.goto(adres, wait_until="commit", timeout=ZAMAN_ASIMI_MS)
        sonuc["url"] = sayfa.url
        # Duvar kontrolu durum kodundan once gelir; duvar 429/503 ile geliyor.
        deneme = 0
        while "/sorry/" in sayfa.url and deneme < DUVAR_DENEME:
            deneme += 1
            if not _bekle(sayfa, DUVAR_BEKLEME_MS * deneme):
                break
            yanit = sayfa.goto(adres, wait_until="commit", timeout=ZAMAN_ASIMI_MS)
            sonuc["url"] = sayfa.url
        if "/sorry/" in sayfa.url and elle:
            # Gorunur pencerede kullanici kutuyu isaretler; cozulunce Google
            # kendisi arama sayfasina dondurur, en cok 90 saniye beklenir.
            for _ in range(18):
                if not _bekle(sayfa, 5_000):
                    break
                if "/sorry/" not in sayfa.url:
                    break
            sonuc["url"] = sayfa.url
        if "/sorry/" in sayfa.url:
            sonuc["result"] = "captcha"
            sonuc["mesaj"] = "duvar: /sorry/"
            return sonuc
        # Sonraki sayfa 429 verse de elimizdeki liste gecerlidir.
        if yanit is not None and yanit.status >= 400 and not sonuc["organik"]:
            sonuc["mesaj"] = f"http {yanit.status}"
            break
        try:
            sayfa.wait_for_selector("#rso", timeout=15_000)
            sayfa.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:  # noqa: BLE001
            pass
        if not _bekle(sayfa, BEKLEME_MS):
            break
        adresler = sayfa.eval_on_selector_all("a[href]", AYIKLA_JS)
        if not adresler:
            break
        onceki = len(sonuc["organik"])
        for kayit in _temizle(adresler):
            sonuc["organik"].append(
                {"position": onceki + kayit["position"], "link": kayit["link"]}
            )
        if domain and any(
            kok(str(k["link"])) == kok(domain) for k in sonuc["organik"]
        ):
            return sonuc
        if len(sonuc["organik"]) >= 100:
            break
    sonuc["result"] = "ok" if sonuc["organik"] else "not_found"
    return sonuc


def serp_oku(
    sorgu: str, domain: str | None = None, mobil: bool = False, azami: int = AZAMI_SAYFA
) -> dict:
    """SERP'i gercek tarayiciyla okur.

    Once gizli denenir; duvara carparsa ayni profille gorunur pencereye gecilir
    ve kullaniciya cozme suresi verilir. Duvari asmanin guvenilir yolu budur.

    Sayfa baska bir kelimenin listesini donduruyorsa (zehirlenmis SERP) sonuc
    kaydedilmez: yeni bir proxy IP'siyle bastan denenir. Zehirlenme IP'ye
    baglidir, bu yuzden ayni IP'de tekrar denemek ise yaramaz.

    Args:
        sorgu: Aranacak kelime.
        domain: Hedef alan adi; bulunursa tarama kesilir.
        mobil: True ise mobil pencere ve mobil UA kullanilir.
        azami: Taranacak en fazla sayfa sayisi.

    Returns:
        result, organik, url ve mesaj alanlarini tasiyan sozluk.
        result: ok, captcha, zehirli, not_found, error.
    """
    sonuc: dict = {"result": "error", "organik": [], "url": "", "mesaj": ""}
    if sync_playwright is None:
        sonuc["mesaj"] = "playwright yok"
        return sonuc

    olcek = MOBIL if mobil else MASUSTU
    ua = (MOBIL_UA if mobil else MASUSTU_UA)

    try:
        with sync_playwright() as p:
            for deneme in range(1, IP_DENEME + 1):
                # Her deneme yeni IP: ne zehirlenme ne duvar IP'ye yapisik kalir.
                secim = havuz.sec_mod(None, mobil_acik=False)
                proxy_ayar = _proxy_sozlugu(secim[1] if secim else None)
                sonuc = {"result": "error", "organik": [], "url": "", "mesaj": ""}

                # 1) gizli dene; sonuc geldiyse zehir denetimine gec.
                try:
                    baglam = _baglam_ac(p, True, proxy_ayar, olcek, ua)
                except Exception as hata:  # noqa: BLE001
                    sonuc["mesaj"] = f"baglam acilmadi: {hata}"[:200]
                    continue
                try:
                    sonuc = _tara(baglam, sorgu, domain, azami, sonuc)
                    if sonuc["organik"]:
                        # Kabul gormus seti tazele; sonraki IP'ler bundan baslar.
                        guven.kaydet(baglam.cookies())
                finally:
                    try:
                        baglam.close()
                    except Exception:  # noqa: BLE001
                        pass

                # 2) duvarda gorunur pencere: elle cozulunce duvar kalkar.
                if sonuc["result"] == "captcha":
                    try:
                        baglam = _baglam_ac(p, False, proxy_ayar, olcek, ua)
                    except Exception as hata:  # noqa: BLE001
                        # Sunucuda X yoksa gorunur pencere acilamaz; gizli sonuc kalir.
                        sonuc["mesaj"] = f"gorunur pencere acilmadi: {hata}"[:200]
                    else:
                        try:
                            sonuc = _tara(baglam, sorgu, domain, azami, sonuc, elle=True)
                            if sonuc["organik"]:
                                guven.kaydet(baglam.cookies())
                        finally:
                            try:
                                baglam.close()
                            except Exception:  # noqa: BLE001
                                pass

                if sonuc["result"] == "captcha":
                    # Set reddedildi: ust uste reddedilirse bayatlar, isitmaya donulur.
                    guven.reddet()
                if sonuc["result"] in ("captcha", "error"):
                    if deneme < IP_DENEME:
                        continue
                    return sonuc

                if sonuc["organik"] and zehir.zehirli_mi(sorgu, sonuc["organik"]):
                    sonuc["result"] = "zehirli"
                    sonuc["mesaj"] = "baska kelimenin listesi"
                    if deneme < IP_DENEME:
                        continue
                    return sonuc

                return sonuc
    except Exception as hata:  # noqa: BLE001
        sonuc["mesaj"] = str(hata)[:200]
        return sonuc
    return sonuc