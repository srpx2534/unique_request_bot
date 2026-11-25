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

from worker import ayar, saglik_db
from worker.serp_html import (
    captcha_mi as _captcha_mi,
    serp_getir_html,
    sonuclari_ayikla as _sonuclari_ayikla,
)
from worker.serp_ortak import bos_sonuc as _bos_sonuc, kok as _kok

# Saglayici uclari (§8): Decodo birincil, Serper ve SearchApi yedek.
API_URL = "https://data.decodo.com/v1/search"
UCLAR = {
    "decodo": API_URL,
    "serper": "https://google.serper.dev/search",
    "searchapi": "https://www.searchapi.io/api/v1/search",
}
ZAMAN_ASIMI = 25  # saniye; üstü burst'ü geciktirir
# Decodo `geo` alaninda ulke adi ister, kod degil; locale kucuk harfli
# dil-ulke bicimidir. Eslemede olmayan ulke kodu oldugu gibi yazilir.
ULKE_ADLARI = {"tr": "Turkey"}
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
# Accept bilerek yazilmaz: curl_cffi profilin kendi Accept basligini ve
# sirasini uygular, ezmek parmak izini bozar (C11). Accept-Language ise
# bilincli: TR sonuc listesi icin dil sinyali gerekiyor.
BASLIKLAR = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

ELENEN = ("google.", "gstatic.", "googleusercontent.", "policies.google")
DESEN_YONLENDIRME = re.compile(r"/url\?q=([^&\"']+)")
DESEN_DUZ = re.compile(r"<a[^>]+href=\"(https?://[^\"]+)\"")


def _govde_kur(saglayici: str, sorgu: str, sayfa: int, dil: str, ulke: str,
               uule: str | None, mobil: bool = False) -> dict:
    """Sağlayıcının beklediği istek gövdesini kurar.

    Üç sağlayıcının alan adları farklıdır; ortak gövde tek yerde tutulmaz.
    """
    if saglayici == "serper":
        govde = {"q": sorgu, "page": sayfa, "gl": ulke, "hl": dil}
        if uule:
            govde["uule"] = uule
        return govde
    if saglayici == "searchapi":
        govde = {"q": sorgu, "page": sayfa, "gl": ulke, "hl": dil}
        if uule:
            govde["uule"] = uule
        return govde
    # Geo ve locale her istekte sabittir: TR sonucu ulke adi ve kucuk harfli
    # locale ile istenir. proxy_pool premium hedef sablonun varsayilanidir,
    # acikca yazilir ki plan degisince sessizce dusmesin.
    # `device` Decodo'ya ozeldir; Serper/SearchApi govdesine yazilmaz.
    govde = {"query": sorgu, "page": sayfa, "locale": f"{dil}-{ulke}".lower(),
             "geo": ULKE_ADLARI.get(ulke, ulke), "proxy_pool": "premium",
             "device": "mobile" if mobil else "desktop"}
    if uule:
        govde["uule"] = uule
    return govde


def _basliklar(saglayici: str, anahtar: str) -> dict:
    """Sağlayıcının kimlik başlığını kurar."""
    if saglayici == "serper":
        return {"X-API-KEY": anahtar, "Content-Type": "application/json"}
    if saglayici == "searchapi":
        return {"Authorization": f"Bearer {anahtar}"}
    return {"authorization": f"Bearer {anahtar}"}


def _sayfa_cek(sorgu: str, sayfa: int, anahtar: str, dil: str, ulke: str,
               uule: str | None, saglayici: str = "decodo", mobil: bool = False
               ) -> tuple[list[dict], dict]:
    """Tek sayfayı API'den çeker.

    Returns:
        (organik liste, ham yanıt bilgisi) demeti.
    """
    govde = _govde_kur(saglayici, sorgu, sayfa, dil, ulke, uule, mobil)

    basladi = time.perf_counter()
    try:
        yanit = requests.post(
            UCLAR.get(saglayici, API_URL), json=govde,
            headers=_basliklar(saglayici, anahtar),
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
        # Kota sessizce tükenmesin: panel uyarıyı görsün.
        saglik_db.uyari("quota", None, "SERP kotası veya hız sınırı: 429")
        return [], bilgi
    if yanit.status_code != 200:
        bilgi["durum"], bilgi["mesaj"] = "error", yanit.text[:200]
        return [], bilgi

    try:
        veri = yanit.json()
    except Exception:  # noqa: BLE001
        bilgi["durum"], bilgi["mesaj"] = "error", "gövde JSON değil"
        return [], bilgi

    # Google hangi ulkeden arandigini kendi soyler: `gl` gercek ulke,
    # `geo_location` gonderilen deger. Ikisi karsilastirilip geo'nun taninip
    # taninmadigi anlasilir; taninmayan geo sessizce US'e dusuyor (70).
    parametreler = veri.get("search_parameters") or {}
    bilgi["gl"] = str(parametreler.get("gl") or "")
    bilgi["geo_location"] = str(parametreler.get("geo_location") or "")

    organik = (veri.get("organic")
               or veri.get("organic_results")
               or veri.get("results", {}).get("organic") or [])
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
    mobil: bool = False,
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

    # Saglayici ve anahtar birlikte secilir: birincil bos ise yedek devreye girer.
    saglayici, anahtar = ayar.serp_secim()
    if not anahtar:
        sonuc["result"] = "anahtar_yok"
        sonuc["mesaj"] = "ayar tablosunda SERP anahtari bos"
        return sonuc
    sonuc["kaynak"] = saglayici

    aranan = _kok(hedef_domain) if hedef_domain else ""
    toplam_ms = 0

    for sayfa in range(1, azami_sayfa + 1):
        organik, bilgi = _sayfa_cek(sorgu, sayfa, anahtar, dil, ulke, uule, saglayici, mobil)
        # Sonraki sayfa 503/429 ile düşerse bir kez, kısa beklemeden sonra
        # tekrar denenir. 503 burada hız sınırıdır, kalıcı engel değildir.
        if bilgi["durum"] in ("captcha", "error") and sayfa > 1:
            time.sleep(SAYFA_ARASI_MAX)
            organik, bilgi = _sayfa_cek(sorgu, sayfa, anahtar, dil, ulke, uule, saglayici, mobil)
        toplam_ms += bilgi["ms"]
        sonuc["elapsed_ms"] = toplam_ms
        sonuc["http_status"] = bilgi["http"]
        sonuc["bytes"] += bilgi["boy"]
        if bilgi.get("url"):
            sonuc["url"] = bilgi["url"]
        if bilgi.get("gl") is not None:
            sonuc["gl"] = bilgi["gl"]
            sonuc["geo_location"] = bilgi["geo_location"]

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


