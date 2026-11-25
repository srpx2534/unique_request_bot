"""Yedek yol: Google'a dogrudan HTML istegi.

Google 2025'ten beri sonuc listesini JS ile basiyor; govde ~90 KB'lik bos
kabuk olarak donuyor. Istek yine Google'a gercek IP'den gider, bu yuzden
izlenim sayilir ve tiklama ayni oturumdan yapilir. Oturum verilirse cerezler
cagiran tarafta korunur ve tiklamaya tasinir.
"""

from __future__ import annotations

import re
import time
from urllib.parse import unquote

from curl_cffi import requests

from worker import fingerprint, guven, isinma
from worker.serp_ortak import bos_sonuc, kok

ZAMAN_ASIMI = 25  # saniye
# Kabuk govde esigi: 2025'ten beri Google sonuclari JS ile basiyor, govde
# ~90 KB'lik bos kabuk oluyor. Bundan kisa govde tek basina guvenilmez.
KABUK_ESIGI = 20_000
DENEME = 2  # 429/503'te kac kez denenir
TEKRAR_BEKLEME = 1.8  # saniye; 429 cogu zaman kisa sureli
ARAMA_URL = "https://www.google.com/search"
CEREZLER = {
    "SOCS": "CAISNQgQEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMzE5LjA4X3AxGgJlbiACGgYIgLC_rwY",
    "CONSENT": "YES+cb.20240101-00-p0.tr+FX+111",
}
# Accept bilerek yazilmaz: curl_cffi profilin kendi Accept basligini ve
# sirasini uygular, ezmek parmak izini bozar (C11).
BASLIKLAR = {"Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}

ELENEN = ("google.", "gstatic.", "googleusercontent.", "policies.google")
DESEN_YONLENDIRME = re.compile(r"/url\?q=([^&\"']+)")
DESEN_DUZ = re.compile(r"<a[^>]+href=\"(https?://[^\"]+)\"")
# Google govdesi izleri. Kisa govde bunlardan birini tasiyorsa sayfa gercekten
# Google'dir (kabuk ya da bos sonuc); tasimiyorsa gateway bes baytlik sahte
# bir govde dondurmus olabilir ve basari sayilmamalidir.
GOOGLE_IZ = ("af_initdatacallback", "gstatic", "google search")


def sonuclari_ayikla(html: str) -> list[str]:
    """HTML'den benzersiz kok alan adlarini sirayla cikarir."""
    adresler = [unquote(m) for m in DESEN_YONLENDIRME.findall(html)]
    adresler += DESEN_DUZ.findall(html)
    gorulen: set[str] = set()
    sira: list[str] = []
    for adres in adresler:
        if any(e in adres for e in ELENEN):
            continue
        k = kok(adres)
        if k and k not in gorulen:
            gorulen.add(k)
            sira.append(k)
    return sira


def sonuc_kayitlari(html: str) -> list[dict]:
    """HTML'den sira ve baglanti tasiyan kayitlari cikarir.

    `sonuclari_ayikla` yalniz kok dondurur ve baglanti kaybolur; B kanali
    tiklamak icin tam adrese ihtiyac duyar. Ayni kok ikinci kez yazilmaz.

    Args:
        html: SERP govdesi.

    Returns:
        {"position": 1 tabanli sira, "link": tam adres} sozlukleri.
    """
    adresler = [unquote(m) for m in DESEN_YONLENDIRME.findall(html)]
    adresler += DESEN_DUZ.findall(html)
    gorulen: set[str] = set()
    kayitlar: list[dict] = []
    for adres in adresler:
        if any(e in adres for e in ELENEN):
            continue
        k = kok(adres)
        if k and k not in gorulen:
            gorulen.add(k)
            kayitlar.append({"position": len(kayitlar) + 1, "link": adres})
    return kayitlar


def captcha_mi(son_url: str, html: str) -> bool:
    """Yanitin CAPTCHA duvari olup olmadigini soyler."""
    if "/sorry/" in son_url:
        return True
    kucuk = html[:4000].lower()
    return "recaptcha" in kucuk or "unusual traffic" in kucuk


def _google_govdesi(html: str) -> bool:
    """Govdenin Google'a ait oldugunu soyler."""
    kucuk = html[:80_000].lower()
    return any(iz in kucuk for iz in GOOGLE_IZ)

def serp_getir_html(
    sorgu: str,
    hedef_domain: str | None = None,
    uule: str | None = None,
    proxy: str | None = None,
    onceki_profil: str | None = None,
    oturum: requests.Session | None = None,
) -> dict:
    """Google'a dogrudan HTML istegi yapar.

    Args:
        sorgu: Aranacak kelime.
        hedef_domain: Sirasi aranacak alan adi.
        uule: Konum parametresi.
        proxy: http://kullanici:sifre@host:port biciminde proxy.
        onceki_profil: Kullanilacak profil.
        oturum: Acik oturum. None ise yenisi acilir ve kapatilir.

    Returns:
        Sonuc sozlugu. result: ok, captcha, error, timeout.
    """
    sonuc = bos_sonuc()
    sonuc["kaynak"] = "html"
    profil = onceki_profil or fingerprint.profil_sec()
    sonuc["profil"] = profil

    # `pws=0` kisiselleştirmeyi, `nfpr=1` otomatik duzeltmeyi kapatir: siralama
    # temiz okunur. Ikisi de kullanici adresine yazilmaz, Referer origin'dir.
    parametreler = {"q": sorgu, "hl": "tr", "gl": "tr", "pws": "0", "nfpr": "1"}
    if uule:
        parametreler["uule"] = uule

    kendi = oturum is None
    oturum = oturum or requests.Session(impersonate=profil)
    # Taze IP dogrudan Google'a girmesin: kisa isinma yapilir. Kabul gormus
    # cerez seti varsa onay cerezleri yerine o yuklenir.
    isinma.http(oturum, aralik=(2_000, 4_000), adet=1)
    cerezler = None if guven.kavanoza(oturum) else CEREZLER

    basladi = time.perf_counter()
    yanit = None
    try:
        # 429/503 hiz siniridir, kalici engel degildir: bir kez bekleyip
        # yeniden denenir. Ikinci deneme de duserse hata olarak doner.
        for deneme in range(1, DENEME + 1):
            try:
                yanit = oturum.get(
                    ARAMA_URL, params=parametreler, headers=BASLIKLAR,
                    cookies=cerezler, timeout=ZAMAN_ASIMI,
                    proxies={"https": proxy, "http": proxy} if proxy else None,
                )
            except Exception as hata:  # noqa: BLE001
                sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
                sonuc["result"] = "timeout" if "timed out" in str(hata).lower() else "error"
                sonuc["mesaj"] = str(hata)[:200]
                return sonuc
            if yanit.status_code in (429, 503) and deneme < DENEME:
                time.sleep(TEKRAR_BEKLEME)
                continue
            break
    finally:
        if kendi:
            oturum.close()

    html = yanit.content.decode("utf-8", "replace")
    sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
    sonuc["http_status"] = yanit.status_code
    sonuc["bytes"] = len(yanit.content)
    sonuc["url"] = str(yanit.url)

    if yanit.status_code != 200:
        sonuc["result"] = "error"
        sonuc["mesaj"] = f"http {yanit.status_code}"
        return sonuc
    if captcha_mi(sonuc["url"], html):
        sonuc["result"] = "captcha"
        return sonuc

    hostlar = sonuclari_ayikla(html)
    # Govdede host yoksa sirasi burst hattinda SERP API'sinden geliyor; burada
    # onemli olan arama ve tiklamanin ayni IP'den cikmasi. Ama taninmayan kisa
    # govde (gateway'in bes baytlik sahte yaniti) gercek SERP degildir.
    if not hostlar:
        if _google_govdesi(html) or sonuc["bytes"] >= KABUK_ESIGI:
            sonuc["result"] = "ok"
            sonuc["mesaj"] = "kabuk govde: sonuc listesi JS ile geliyor"
            return sonuc
        sonuc["result"] = "error"
        sonuc["mesaj"] = f"govde taninmadi ({sonuc['bytes']} bayt)"
        return sonuc
    sonuc["result"] = "ok"
    if hedef_domain and kok(hedef_domain) in hostlar:
        sonuc["position"] = hostlar.index(kok(hedef_domain)) + 1
    return sonuc
