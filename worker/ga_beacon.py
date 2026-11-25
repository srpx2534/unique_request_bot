"""GA4 Measurement Protocol: ziyareti Google'a gorunur kilar.

curl_cffi JavaScript calistirmadigi icin sitenin kendi `gtag` etiketi
ateslenmiyor; Google Analytics ziyareti hic kaydetmiyor. Bu modul ayni
page_view'i Measurement Protocol ile dogrudan gonderir, boylece tik ve dwell
Google tarafinda gorunur olur.

Kimlik site tablosundan gelir (`ga_id`, `ga_secret`). Ikisi de bossa beacon
atlanir; hit yine gider, yalnizca Google gormez.

`client_id` profil kimliginden turetilir: ayni profil ayni ziyaretci olarak
gorunur, her hit yeni kullanici gibi cikmaz.

Kullanim: worker/click.py.
"""

from __future__ import annotations

import uuid

from curl_cffi import requests

from worker import ayar_db

UC = "https://www.google-analytics.com/mp/collect"
ZAMAN_ASIMI = 12  # saniye; beacon hit'i bekletmemeli
ALAN = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def cid_uret(profil_id: int | None) -> str:
    """Profil kimliginden kalici istemci kimligi turetir.

    Args:
        profil_id: Cerez profil kimligi.

    Returns:
        UUID metni; profil yoksa rastgele.
    """
    if profil_id is None:
        return str(uuid.uuid4())
    return str(uuid.uuid5(ALAN, f"profil-{profil_id}"))


def govde(cid: str, adres: str, referer: str, dwell_ms: int,
          oturum_id: str) -> dict:
    """Measurement Protocol govdesini kurar.

    Args:
        cid: Istemci kimligi.
        adres: Ziyaret edilen tam adres.
        referer: Gelinen adres.
        dwell_ms: Sayfada kalinan sure.
        oturum_id: Oturum kimligi; ayni hit'in eventleri bunu paylasir.

    Returns:
        Gonderime hazir sozluk.
    """
    return {
        "client_id": cid,
        "events": [{
            "name": "page_view",
            "params": {
                "page_location": adres,
                "page_referrer": referer or "",
                "engagement_time_msec": max(1, int(dwell_ms)),
                "session_id": oturum_id,
            },
        }],
    }


def ayar_bul(domain: str) -> tuple[str, str]:
    """Siteye ait olcum kimligini okur.

    Args:
        domain: Hedef alan adi.

    Returns:
        (ga_id, ga_secret); yoksa ("", "").
    """
    baglanti = None
    try:
        baglanti = ayar_db._baglan()
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT ga_id, ga_secret FROM site WHERE domain = %s LIMIT 1", (domain,)
            )
            satir = imlec.fetchone()
    except Exception:  # noqa: BLE001
        return "", ""
    finally:
        if baglanti is not None:
            baglanti.close()
    if not satir:
        return "", ""
    return str(satir[0] or "").strip(), str(satir[1] or "").strip()


def gonder(
    domain: str,
    adres: str,
    referer: str,
    dwell_ms: int,
    profil_id: int | None = None,
    proxy: str | None = None,
) -> dict:
    """page_view eventini gonderir.

    Args:
        domain: Hedef alan adi; kimlik buradan cozulur.
        adres: Ziyaret edilen tam adres.
        referer: Gelinen adres.
        dwell_ms: Sayfada kalinan sure.
        profil_id: Cerez profil kimligi; client_id bundan turetilir.
        proxy: Hit ile ayni proxy; IP tutarli kalsin.

    Returns:
        result (ok, kapali, error) ve mesaj alanlari.
    """
    tid, sir = ayar_bul(domain)
    if not tid or not sir:
        return {"result": "kapali", "mesaj": "ga kimligi yok"}
    cid = cid_uret(profil_id)
    oturum_id = str(uuid.uuid5(ALAN, f"oturum-{cid}-{adres}"))
    try:
        yanit = requests.post(
            UC, params={"measurement_id": tid, "api_secret": sir},
            json=govde(cid, adres, referer, dwell_ms, oturum_id),
            impersonate="chrome", timeout=ZAMAN_ASIMI,
            proxies={"https": proxy, "http": proxy} if proxy else None,
        )
    except Exception as hata:  # noqa: BLE001
        return {"result": "error", "mesaj": str(hata)[:200]}
    # MP bos govde ve 204 doner; 2xx disi hata sayilir.
    if not 200 <= yanit.status_code < 300:
        return {"result": "error", "mesaj": f"http {yanit.status_code}"}
    return {"result": "ok", "mesaj": ""}