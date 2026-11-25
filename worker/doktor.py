"""Tarayici saglik kontrolu: siteye ne gorunuyor.

Google bazi makinelere cok daha az sayfa veriyor; headless izi, kapali WebGL
ya da kucuk ekran bunun sebepleridir. Bu modul hicbir sey gondermeden
tarayicinin ne gosterdigini okur ve sorunlari listeler.

`kontrol()` aga cikar (tarayici acar), `karar()` saf fonksiyondur; karar
mantigi boylece agsiz sinanir.

Kullanim: tools/doktor.py, worker/tarayici.py (acilista uyari).
"""

from __future__ import annotations

OKU_JS = """
() => {
  const tuval = document.createElement('canvas');
  let webgl = '';
  try {
    const g = tuval.getContext('webgl') || tuval.getContext('experimental-webgl');
    const uzanti = g && g.getExtension('WEBGL_debug_renderer_info');
    webgl = uzanti ? g.getParameter(uzanti.UNMASKED_RENDERER_WEBGL) : (g ? 'var' : '');
  } catch (e) { webgl = ''; }
  return {
    webdriver: navigator.webdriver,
    chrome: typeof window.chrome !== 'undefined' && !!window.chrome.runtime,
    diller: navigator.languages || [],
    genislik: window.screen.width,
    yukseklik: window.screen.height,
    webgl: webgl || '',
  };
}
"""


def karar(veri: dict) -> list[str]:
    """Okunan degerlerden sorun listesi cikarir.

    Args:
        veri: `OKU_JS` ciktisi.

    Returns:
        Sorun metinleri; bos liste saglikli demektir.
    """
    sorunlar: list[str] = []
    if veri.get("webdriver"):
        sorunlar.append("navigator.webdriver acik")
    if not veri.get("chrome"):
        sorunlar.append("window.chrome yok")
    if not veri.get("webgl"):
        sorunlar.append("webgl yok")
    if int(veri.get("genislik") or 0) < 1000:
        sorunlar.append(f"ekran dar: {veri.get('genislik')}x{veri.get('yukseklik')}")
    diller = [str(d) for d in (veri.get("diller") or [])]
    if not any(d.lower().startswith("tr") for d in diller):
        sorunlar.append("diller arasinda tr yok")
    return sorunlar


def kontrol(headless: bool = False) -> dict:
    """Tarayiciyi acar, ne gorundugunu okur ve karari verir.

    Args:
        headless: Gizli pencereyle kontrol; sitenin gordugu deger budur.

    Returns:
        veri, sorunlar ve temiz alanlarini tasiyan sozluk. Playwright yoksa
        ya da tarayici acilmazsa `mesaj` dolu doner.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as hata:  # noqa: BLE001
        return {"veri": {}, "sorunlar": [], "temiz": False, "mesaj": str(hata)[:200]}

    try:
        with sync_playwright() as p:
            tarayici = p.chromium.launch(
                headless=headless, channel="chromium",
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )
            try:
                sayfa = tarayici.new_page(viewport={"width": 1366, "height": 768},
                                          locale="tr-TR")
                sayfa.goto("about:blank")
                veri = sayfa.evaluate(OKU_JS)
            finally:
                tarayici.close()
    except Exception as hata:  # noqa: BLE001
        return {"veri": {}, "sorunlar": [], "temiz": False, "mesaj": str(hata)[:200]}

    sorunlar = karar(veri)
    return {"veri": veri, "sorunlar": sorunlar, "temiz": not sorunlar, "mesaj": ""}