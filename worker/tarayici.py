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

import os
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from worker import guven, havuz, isinma, zehir
from worker.serp_ortak import kok

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
BEKLEME_MS = 2_500
DUVAR_BEKLEME_MS = 10_000  # duvar sonrasi ilk bekleme; her denemede katlanir
DUVAR_DENEME = 3
IP_DENEME = 2  # zehirli sayfa ya da duvarda kac IP denenir
COZUM_SINIRI = 0  # sayfa basina en fazla kac /goto adresi cozulur  # duvarda en fazla kac kez beklenip yeniden denenir  # sonuc listesi JS ile kurulur, kisa bekleme yetmez
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
AYIKLA_JS = r"""
() => {
  // `#rso` tek basina yetmiyor: reklam, maps ve sitelink satirlari disarida
  // kaliyordu. Govde taranir, ayni adres bir kez sayilir.
  const gorulen = new Set();
  return Array.from(document.body.querySelectorAll('a[href]'))
    .filter(a => a.querySelector('h3'))
    .filter(a => (gorulen.has(a.href) ? false : (gorulen.add(a.href), true)))
    .map(a => {
      const kutu = a.closest('div.g') || a.closest('div.MjjYud') ||
                   a.closest('div[data-hveid]') || a.parentElement;
      const cite = kutu ? kutu.querySelector('cite') : null;
      let gorunen = cite ? cite.innerText : '';
      if (!gorunen && kutu) {
        // Modern isaretlemede `cite` yok; adres satir metninde gorunuyor.
        gorunen = (kutu.innerText || '').split('\\n').map(t => t.trim())
          .find(t => /^https?:\/\/\S+/.test(t) || /^[\w-]+(\.[\w-]+)+(\s|$)/.test(t)) || '';
      }
      return { cite: gorunen, baslik: (a.querySelector('h3') || {}).innerText || '', href: a.href };
    });
}
"""


def _iz(ad: str) -> None:
    """`TARAYICI_IZ=1` iken adim zaman damgasi basar."""
    if os.environ.get("TARAYICI_IZ") == "1":
        print(f"[iz {time.strftime('%H:%M:%S')}] {ad}", flush=True)


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


def _google_mu(adres: str) -> bool:
    """Adres arama sayfasi ya da statik Google mi.

    `sites.google.com` bir sonuc olarak sayilir; yalniz arama sayfasi ve
    gstatic elenir.

    Args:
        adres: Denetlenecek adres.

    Returns:
        Elenmesi gerekiyorsa True.
    """
    try:
        host = (urlparse(adres).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    if host in ("gstatic.com",) or host.endswith(".gstatic.com"):
        return True
    return host in ("google.com", "www.google.com") or host.startswith("google.") \
        or host.startswith("www.google.")


def _cite_kok(cite: str) -> str:
    """Sonuc satirindaki gorunen adresten kok alan adini cikarir.

    Google `cite` alanini yol izi olarak veriyor (`www.site.com › alt`); ham
    metin `kok()`'a verilirse `com` gibi anlamsiz kokler uretiyordu.

    Args:
        cite: Sonuc satirindan okunan gorunen adres.

    Returns:
        Kok alan adi; metin adres gibi degilse bos metin.
    """
    ham = (cite or "").strip()
    if not ham:
        return ""
    # Adres izi bosluk ve " › " ile devam ediyor; yalniz ilk parca alinir.
    # `urlparse` bu satirlarda netloc'u tum metin sandigi icin siralama onemli.
    for ayrac in ("›", ">", " "):
        ham = ham.split(ayrac)[0].strip()
    if "://" in ham:
        ham = ham.split("://", 1)[1]
    for ayrac in ("/", "?", "#", ":"):
        ham = ham.split(ayrac)[0].strip()
    ham = ham.removeprefix("www.")
    if not ham or "." not in ham:
        return ""
    return ham


def _goto_coz(baglam, adres: str) -> str:
    """`/goto?url=` sarmalini gercek adrese cozer.

    Google sonuc baglantilarini sifreli bir yonlendirmeye sarar; sarmalin
    icinde hedef yoktur. Ayni baglamin istek tasiyicisi cerezleri paylastigi
    icin yonlendirme kovalanip gercek adres alinir. Cozulemezse bos doner ve
    cagiran taraf `cite` ile yetinir.

    Args:
        baglam: Acik tarayici baglami.
        adres: `/goto` adresi.

    Returns:
        Gercek adres; cozulemezse bos metin.
    """
    try:
        yanit = baglam.request.get(adres, timeout=ZAMAN_ASIMI_MS, max_redirects=5)
    except Exception:  # noqa: BLE001
        return ""
    son = str(getattr(yanit, "url", "") or "")
    if not son.startswith("http") or "google." in son:
        return ""
    return son


def _temizle(adresler: list[str], cozucu=None) -> list[dict]:
    """Adres listesini benzersiz kok ve 1 tabanli siraya cevirir.

    Args:
        adresler: Sayfadan toplanan ham adresler.

    Returns:
        {"position", "link"} sozlukleri.
    """
    gorulen: set[str] = set()
    kayitlar: list[dict] = []
    cozulen = 0
    for kayit in adresler:
        if isinstance(kayit, dict):
            cite = str(kayit.get("cite") or "").strip()
            ham = str(kayit.get("href") or "")
            baslik = str(kayit.get("baslik") or "").strip()
        else:
            cite, ham, baslik = "", str(kayit), ""
        # `/goto?url=CAES...` yerel cozulemiyor; sonuc satirinda gorunen adres
        # (`cite`) zaten hedef koku veriyor, ek istek gerekmiyor.
        adres = ""
        if cozucu and "/goto?" in ham and cozulen < COZUM_SINIRI:
            cozulen += 1
            adres = cozucu(ham)
        if not adres:
            # Sirasiyla: cozulmus sarmal, duz adres, gorunen adres. Duz adres
            # google'e cikiyorsa atlanir, cite'in host kismina dusulur.
            duz = _gercek_adres(ham)
            if duz and not _google_mu(duz):
                adres = duz
        if not adres:
            adres = _cite_kok(cite)
        if not adres or _google_mu(adres):
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


def _git(sayfa, adres: str, deneme: int = 2):
    """Sayfayi acar; gezinme baska bir gezinmeyle kesilirse tekrar dener.

    Args:
        sayfa: Acik sayfa.
        adres: Gidilecek adres.
        deneme: Toplam deneme sayisi.

    Returns:
        Goto yaniti; son denemede de duserse hata yukari birakilir.
    """
    for i in range(deneme):
        try:
            return sayfa.goto(adres, wait_until="domcontentloaded",
                              timeout=ZAMAN_ASIMI_MS)
        except Exception:  # noqa: BLE001
            if i == deneme - 1:
                raise
    return None


def _ara(sayfa, sorgu: str):
    """Aramayi kutuya yazarak yapar.

    Adrese `hl/gl/start` yazmak baska bir SERP varyanti getiriyordu; kutuya
    yazinca Google kendi `sca_esv` cipasini uretiyor ve liste yerel aramayla
    ortusuyor.

    Args:
        sayfa: Acik sayfa.
        sorgu: Aranacak kelime.

    Returns:
        Arama gezinmesinin yaniti; yakalanamazsa None.
    """
    # `commit` ile acilir, arama kutusu beklenir: proxy'de domcontentloaded
    # 45 saniyeyi doldurup olcumu dusuruyordu. Bir kez de tekrar denenir.
    ana = f"{ARAMA_URL.rsplit('/', 1)[0]}/?hl=tr"
    secici_kutu = "textarea[name=q], input[name=q]"
    _iz("ara basladi")
    for deneme in range(2):
        try:
            sayfa.goto(ana, wait_until="commit", timeout=20_000)
            _iz("ana sayfa acildi")
            sayfa.wait_for_selector(secici_kutu, timeout=12_000)
            break
        except Exception:  # noqa: BLE001
            if deneme == 1:
                pass
    for secici in ("button:has-text('Tümünü kabul et')", "button:has-text('Accept all')"):
        try:
            sayfa.click(secici, timeout=2_500)
            break
        except Exception:  # noqa: BLE001
            pass
    try:
        _iz("kutu dolduruluyor")
        sayfa.fill("textarea[name=q], input[name=q]", sorgu)
        sayfa.keyboard.press("Enter")
        sayfa.wait_for_url("**/search**", timeout=15_000)
        _iz("arama sayfasi")
    except Exception:  # noqa: BLE001
        pass
    # Durum kodu performans kaydindan okunur: `expect_navigation` her sayfada
    # 45 saniye zaman asimina ugrayip olcumu dakikalara cikariyordu.
    durum = 0
    try:
        durum = int(sayfa.evaluate(
            "() => (performance.getEntriesByType('navigation')[0] || {}).responseStatus || 0"))
    except Exception:  # noqa: BLE001
        pass
    return type("Yanit", (), {"status": durum})() if durum else None


def _sonraki(sayfa) -> bool:
    """Sonraki sonuc sayfasina gecer.

    Args:
        sayfa: Acik sayfa.

    Returns:
        Gecildiyse True.
    """
    eski = sayfa.url
    try:
        sayfa.click("a#pnnext", timeout=8_000)
        sayfa.wait_for_url(lambda adres: adres != eski, timeout=15_000)
        return True
    except Exception:  # noqa: BLE001
        return False


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
    cozucu = (lambda h: _goto_coz(baglam, h)) if hasattr(baglam, "request") else None
    # Isinma ayri sayfada kosar: ayni sayfada kalirsa arama gezinmesi
    # "interrupted by another navigation" ile dusuyordu. Cerezler baglamda
    # ortak oldugu icin isitma etkisi korunur.
    _iz("isinma basliyor")
    isinma_sayfasi = baglam.new_page()
    sonuc["isinma"] = isinma.tarayicida(isinma_sayfasi)["result"]
    _iz(f"isinma bitti: {sonuc['isinma']}")
    try:
        isinma_sayfasi.close()
    except Exception:  # noqa: BLE001
        pass
    sayfa = baglam.new_page()
    http_hatasi = False
    for sira in range(azami):
        basla = sira * SAYFA_BASI
        # Ulusal olcumde uule gonderilmez (66): IP cografyasi yeterli sinyal,
        # uule listeyi baska kumeye dusuruyordu. gl/hl dil ve ulke sinyalidir.
        adres = f"{ARAMA_URL}?q={quote(sorgu)}&start={basla}&hl=tr&gl=tr"
        _iz(f"sayfa {sira + 1}: git")
        yanit = _git(sayfa, adres)
        sonuc["url"] = sayfa.url
        _iz(f"sayfa {sira + 1}: yanit {getattr(yanit, 'status', '?')} {sayfa.url[:70]}")
        # Duvar kontrolu durum kodundan once gelir; duvar 429/503 ile geliyor.
        deneme = 0
        while "/sorry/" in sayfa.url and deneme < DUVAR_DENEME:
            deneme += 1
            _iz(f"sayfa {sira + 1}: duvar, bekleme {deneme}")
            if not _bekle(sayfa, DUVAR_BEKLEME_MS * deneme):
                break
            yanit = _git(sayfa, adres)
            sonuc["url"] = sayfa.url
        if "/sorry/" in sayfa.url and elle:
            # Gorunur pencerede kullanici kutuyu isaretler; cozulunce Google
            # kendisi arama sayfasina dondurur, en cok 90 saniye beklenir.
            _iz("sayfa: elle cozme bekleniyor")
            for _ in range(18):
                if not _bekle(sayfa, 5_000):
                    break
                if "/sorry/" not in sayfa.url:
                    break
            sonuc["url"] = sayfa.url
        if "/sorry/" in sayfa.url:
            sonuc["result"] = "captcha"
            sonuc["mesaj"] = "duvar: /sorry/"
            _iz("sayfa: captcha")
            return sonuc
        # Sonraki sayfa 429 verse de elimizdeki liste gecerlidir; ama hic sonuc
        # yokken gelen 5xx basarili olcum degildir (77).
        if yanit is not None and yanit.status >= 400 and not sonuc["organik"]:
            sonuc["mesaj"] = f"http {yanit.status}"
            http_hatasi = True
            _iz(f"sayfa {sira + 1}: http {yanit.status}, duruluyor")
            break
        try:
            _iz(f"sayfa {sira + 1}: rso bekleniyor")
            sayfa.wait_for_selector("#rso", timeout=15_000)
            sayfa.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:  # noqa: BLE001
            pass
        _iz(f"sayfa {sira + 1}: rso hazir")
        if not _bekle(sayfa, BEKLEME_MS):
            _iz(f"sayfa {sira + 1}: sayfa kapandi")
            break
        _iz(f"sayfa {sira + 1}: ayiklaniyor")
        adresler = sayfa.eval_on_selector_all("a[href]", AYIKLA_JS)
        _iz(f"sayfa {sira + 1}: ham {len(adresler)}")
        if not adresler:
            # Bos sayfa taramayi erken kesiyordu (429 ya da gec yukleme): bir
            # kez daha denenir, yine bossa durulur.
            if not _bekle(sayfa, 2_500):
                _iz(f"sayfa {sira + 1}: sayfa kapandi (bos)")
                break
            _iz(f"sayfa {sira + 1}: bos, yeniden git")
            yanit = _git(sayfa, adres)
            try:
                _iz(f"sayfa {sira + 1}: rso tekrar bekleniyor")
                sayfa.wait_for_selector("#rso", timeout=10_000)
            except Exception:  # noqa: BLE001
                pass
            if not _bekle(sayfa, BEKLEME_MS):
                break
            adresler = sayfa.eval_on_selector_all("a[href]", AYIKLA_JS)
            _iz(f"sayfa {sira + 1}: ham (tekrar) {len(adresler)}")
            if not adresler:
                _iz(f"sayfa {sira + 1}: bos, duruluyor")
                break
        onceki = len(sonuc["organik"])
        _iz(f"sayfa {sira + 1}: temizle")
        for kayit in _temizle(adresler, cozucu):
            sonuc["organik"].append(
                {"position": onceki + kayit["position"], "link": kayit["link"]}
            )
        _iz(f"sayfa {sira + 1}: toplam {len(sonuc['organik'])}")
        if domain and any(
            kok(str(k["link"])) == kok(domain) for k in sonuc["organik"]
        ):
            _iz("hedef bulundu")
            return sonuc
        if len(sonuc["organik"]) >= 100:
            break
    if sonuc["organik"]:
        sonuc["result"] = "ok"
    elif http_hatasi:
        # 500/502 "ilk 100'de yok" gibi yazilip siralamayi bozmasin (77).
        sonuc["result"] = "error"
    else:
        sonuc["result"] = "not_found"
    _iz(f"tarama bitti: {sonuc['result']} {len(sonuc['organik'])}")
    return sonuc

def serp_oku(
    sorgu: str, domain: str | None = None, mobil: bool = False, azami: int = AZAMI_SAYFA,
    sehir: str | None = None,
    proxy_yok: bool = False,
    isinma_aralik: tuple[int, int] | None = None,
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
                secim = None if proxy_yok else havuz.sec_mod(sehir, mobil_acik=False)
                proxy_ayar = _proxy_sozlugu(secim[1] if secim else None)
                sonuc = {"result": "error", "organik": [], "url": "", "mesaj": ""}

                # 1) gizli dene; sonuc geldiyse zehir denetimine gec.
                try:
                    baglam = _baglam_ac(p, True, proxy_ayar, olcek, ua)
                except Exception as hata:  # noqa: BLE001
                    sonuc["mesaj"] = f"baglam acilmadi: {hata}"[:200]
                    continue
                try:
                    sonuc = _tara(baglam, sorgu, domain, azami, sonuc, isinma_aralik=isinma_aralik)
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
                            sonuc = _tara(baglam, sorgu, domain, azami, sonuc, elle=True, isinma_aralik=isinma_aralik)
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