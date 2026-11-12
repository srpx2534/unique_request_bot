"""SERP sonuç listesi: birincil yol API, yedek yol doğrudan HTML.

Google 2025'ten beri /search için JavaScript zorunlu kıldı; düz HTTP istek
sonuç yerine uygulama kabuğu döndürüyor (HTTP 200, ~94 KB, sıfır sonuç).
Sözleşme headless tarayıcıyı kapsam dışı bıraktığı için burst hattında
sonuç listesi SERP API'sinden alınır. Tıklama yine proxy üzerinden doğrudan
yapılır (worker/click.py), böylece IP sinyali gerçek kalır.

API tek sayfada 10 sonuç veriyor; ilk 100 sırayı görmek için `page`
parametresiyle sayfalar çekilir ve hedef bulununca erken durulur. Böylece
hem kota korunur hem gereksiz istek atılmaz.

Kullanım: worker/burst.py, tools/serp_dene.py.
"""

from __future__ import annotations

import random
import re
import time
from urllib.parse import unquote, urlparse

from curl_cffi import requests

from worker import ayar, fingerprint

API_URL = "https://data.decodo.com/v1/search"
ZAMAN_ASIMI = 25  # saniye; üstü burst'ü geciktirir
SAYFA_BASI = 10  # API'nin tek yanıtta döndürdüğü sonuç sayısı
AZAMI_SAYFA = 10  # 10 x 10 = ilk 100 sıra
SAYFA_ARASI_MIN = 0.6  # saniye; API saniyede çok isteği 503 ile kesiyor
SAYFA_ARASI_MAX = 1.3  # saniye; üst sınır, jitter için

# Doğrudan HTML yedeği için. Bugün sonuç vermiyor, duvar kalkarsa kullanılır.
ARAMA_URL = "https://www.google.com/search"
CEREZLER = {
    "SOCS": "CAISNQgQEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMzE5LjA4X3AxGgJlbiACGgYIgLC_rwY",
    "CONSENT": "YES+cb.20240101-00-p0.tr+FX+111",
}
BASLIKLAR = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ELENEN = ("google.", "gstatic.", "googleusercontent.", "policies.google")
DESEN_YONLENDIRME = re.compile(r"/url\?q=([^&\"']+)")
DESEN_DUZ = re.compile(r"<a[^>]+href=\"(https?://[^\"]+)\"")


def _kok(adres: str) -> str:
    """Adresten kök alan adını çıkarır.

    Args:
        adres: Tam URL veya alan adı.

    Returns:
        www. öneki atılmış kök; çözülemezse boş metin.
    """
    ham = adres.strip().lower()
    if "://" in ham:
        ham = urlparse(ham).netloc
    ham = ham.split("/")[0]
    if ham.startswith("www."):
        ham = ham[4:]
    etiketler = [e for e in ham.split(".") if e]
    return ".".join(etiketler[-2:]) if len(etiketler) >= 2 else ham


def _sonuclari_ayikla(html: str) -> list[str]:
    """HTML'den benzersiz kök alan adlarını sırayla çıkarır."""
    adresler = [unquote(m) for m in DESEN_YONLENDIRME.findall(html)]
    adresler += DESEN_DUZ.findall(html)
    gorulen: set[str] = set()
    sira: list[str] = []
    for adres in adresler:
        if any(e in adres for e in ELENEN):
            continue
        kok = _kok(adres)
        if kok and kok not in gorulen:
            gorulen.add(kok)
            sira.append(kok)
    return sira


def _captcha_mi(son_url: str, html: str) -> bool:
    """Yanıtın CAPTCHA duvarı olup olmadığını söyler."""
    if "/sorry/" in son_url:
        return True
    kucuk = html[:4000].lower()
    return "recaptcha" in kucuk or "unusual traffic" in kucuk


def _bos_sonuc() -> dict:
    """Ortak sonuç iskeletini üretir."""
    return {
        "result": "error",
        "position": None,
        "url": None,
        "http_status": None,
        "elapsed_ms": 0,
        "bytes": 0,
        "profil": None,
        "kaynak": None,
        "organik": [],
        "mesaj": "",
    }


def _sayfa_cek(sorgu: str, sayfa: int, anahtar: str, dil: str, ulke: str,
               uule: str | None) -> tuple[list[dict], dict]:
    """Tek sayfayı API'den çeker.

    Returns:
        (organik liste, ham yanıt bilgisi) demeti.
    """
    govde = {"query": sorgu, "page": sayfa, "locale": f"{dil}-{ulke.upper()}",
             "geo": ulke}
    if uule:
        govde["uule"] = uule

    basladi = time.perf_counter()
    try:
        yanit = requests.post(
            API_URL, json=govde,
            headers={"authorization": f"Bearer {anahtar}"},
            impersonate="chrome", timeout=ZAMAN_ASIMI,
        )
    except Exception as hata:  # noqa: BLE001
        return [], {"durum": "timeout" if "timed out" in str(hata).lower() else "error",
                    "mesaj": str(hata)[:200], "ms": int((time.perf_counter() - basladi) * 1000),
                    "http": None, "boy": 0}

    bilgi = {"durum": "ok", "mesaj": "", "http": yanit.status_code,
             "boy": len(yanit.content), "ms": int((time.perf_counter() - basladi) * 1000)}

    if yanit.status_code in (401, 403):
        bilgi["durum"], bilgi["mesaj"] = "error", "anahtar reddedildi"
        return [], bilgi
    if yanit.status_code == 429:
        bilgi["durum"], bilgi["mesaj"] = "captcha", "kota veya hız sınırı"
        return [], bilgi
    if yanit.status_code != 200:
        bilgi["durum"], bilgi["mesaj"] = "error", yanit.text[:200]
        return [], bilgi

    try:
        veri = yanit.json()
    except Exception:  # noqa: BLE001
        bilgi["durum"], bilgi["mesaj"] = "error", "gövde JSON değil"
        return [], bilgi

    organik = veri.get("organic") or veri.get("results", {}).get("organic") or []
    bilgi["url"] = veri.get("url")
    return organik, bilgi


def serp_getir(
    sorgu: str,
    hedef_domain: str | None = None,
    uule: str | None = None,
    proxy: str | None = None,
    onceki_profil: str | None = None,
    dil: str = "tr",
    ulke: str = "tr",
    azami_sayfa: int = AZAMI_SAYFA,
) -> dict:
    """SERP sonuçlarını sayfa sayfa API'den alır.

    Hedef verilmişse bulunduğu sayfada durur; verilmemişse tüm sayfalar
    taranır. Sıra numarası sayfa ofsetiyle birlikte 1 tabanlıdır.

    Args:
        sorgu: Aranacak kelime.
        hedef_domain: Sıralaması aranacak alan adı.
        uule: Konum parametresi; API desteklerse gönderilir.
        proxy: Yalnızca HTML yedeğinde kullanılır.
        onceki_profil: Yedek yolda profil tekrarını önlemek için.
        dil: Dil kodu (hl).
        ulke: Ülke kodu (gl).
        azami_sayfa: Taranacak en fazla sayfa sayısı.

    Returns:
        result, position, url, http_status, elapsed_ms, bytes, kaynak,
        organik ve mesaj alanlarını taşıyan sözlük. result değerleri: ok,
        captcha, not_found, timeout, error, anahtar_yok.
    """
    sonuc = _bos_sonuc()
    sonuc["kaynak"] = "api"

    anahtar = ayar.oku("DECODO_SERP_KEY")
    if not anahtar:
        sonuc["result"] = "anahtar_yok"
        sonuc["mesaj"] = ".env içinde DECODO_SERP_KEY boş"
        return sonuc

    aranan = _kok(hedef_domain) if hedef_domain else ""
    toplam_ms = 0

    for sayfa in range(1, azami_sayfa + 1):
        organik, bilgi = _sayfa_cek(sorgu, sayfa, anahtar, dil, ulke, uule)
        # Sonraki sayfa 503/429 ile düşerse bir kez, kısa beklemeden sonra
        # tekrar denenir. 503 burada hız sınırıdır, kalıcı engel değildir.
        if bilgi["durum"] in ("captcha", "error") and sayfa > 1:
            time.sleep(SAYFA_ARASI_MAX)
            organik, bilgi = _sayfa_cek(sorgu, sayfa, anahtar, dil, ulke, uule)
        toplam_ms += bilgi["ms"]
        sonuc["elapsed_ms"] = toplam_ms
        sonuc["http_status"] = bilgi["http"]
        sonuc["bytes"] += bilgi["boy"]
        if bilgi.get("url"):
            sonuc["url"] = bilgi["url"]

        if bilgi["durum"] != "ok":
            # İlk sayfa düştüyse hata; sonraki sayfa düştüyse elimizdekiyle döneriz.
            if sayfa == 1:
                sonuc["result"] = bilgi["durum"]
                sonuc["mesaj"] = bilgi["mesaj"]
                return sonuc
            sonuc["mesaj"] = bilgi["mesaj"]
            break

        if not organik:
            break  # sonuç bitti

        ofset = (sayfa - 1) * SAYFA_BASI
        for sira, kayit in enumerate(organik, start=1):
            sonuc["organik"].append(
                {"position": ofset + sira, "link": kayit.get("link") or kayit.get("url", "")}
            )

        if aranan and any(_kok(k["link"]) == aranan for k in sonuc["organik"]):
            break  # hedef bulundu, fazla sayfa harcanmaz

        # Sayfalar arası rastgele bekleme: sabit aralık da kalıp bırakıyor.
        time.sleep(random.uniform(SAYFA_ARASI_MIN, SAYFA_ARASI_MAX))

    if not sonuc["organik"]:
        sonuc["result"] = "not_found"
        return sonuc

    sonuc["result"] = "ok"
    if aranan:
        for kayit in sonuc["organik"]:
            if _kok(kayit["link"]) == aranan:
                sonuc["position"] = kayit["position"]
                break
        else:
            sonuc["result"] = "not_found"
    return sonuc


def serp_getir_html(
    sorgu: str,
    hedef_domain: str | None = None,
    uule: str | None = None,
    proxy: str | None = None,
    onceki_profil: str | None = None,
    oturum: requests.Session | None = None,
) -> dict:
    """Yedek yol: Google'a doğrudan HTML isteği (izlenim).

    Bugün kabuk döndüğü için genelde not_found verir, ama istek Google'a
    gerçek IP'den gider ve izlenim sayılır. Oturum verilirse cookie'ler
    çağıran tarafta korunur ve tıklamaya taşınır.

    Args:
        sorgu: Aranacak kelime.
        hedef_domain: Sıralaması aranacak alan adı.
        uule: Konum parametresi.
        proxy: http://kullanici:sifre@host:port biçiminde proxy.
        onceki_profil: Kullanılacak profil.
        oturum: Açık oturum. None ise yenisi açılır ve kapatılır.

    Returns:
        Sonuç sözlüğü. result: ok, captcha, not_found, timeout, error.
    """
    sonuc = _bos_sonuc()
    sonuc["kaynak"] = "html"
    profil = onceki_profil or fingerprint.profil_sec()
    sonuc["profil"] = profil

    parametreler = {"q": sorgu, "num": "100", "hl": "tr", "gl": "tr"}
    if uule:
        parametreler["uule"] = uule

    kendi = oturum is None
    oturum = oturum or requests.Session(impersonate=profil)

    basladi = time.perf_counter()
    try:
        yanit = oturum.get(
            ARAMA_URL, params=parametreler, headers=BASLIKLAR,
            cookies=CEREZLER, timeout=ZAMAN_ASIMI,
            proxies={"https": proxy, "http": proxy} if proxy else None,
        )
    except Exception as hata:  # noqa: BLE001
        sonuc["elapsed_ms"] = int((time.perf_counter() - basladi) * 1000)
        sonuc["result"] = "timeout" if "timed out" in str(hata).lower() else "error"
        sonuc["mesaj"] = str(hata)[:200]
        return sonuc
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
        return sonuc
    if _captcha_mi(sonuc["url"], html):
        sonuc["result"] = "captcha"
        return sonuc

    hostlar = _sonuclari_ayikla(html)
    if not hostlar:
        sonuc["result"] = "not_found"
        return sonuc
    sonuc["result"] = "ok"
    if hedef_domain and _kok(hedef_domain) in hostlar:
        sonuc["position"] = hostlar.index(_kok(hedef_domain)) + 1
    return sonuc