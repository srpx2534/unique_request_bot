"""Tek hit: izlenim, tikla, dwell, pogo.

Burst dongusunden ayrildi (§23.2); cagiran taraf saglayici ve profili secer,
burada yalnizca hit yurutulur.

Hata metni kayda tasinir: proxy reddi kodu (407 kimlik, 466 kota, 403 bicim)
yalnizca metinde gorunur ve cagiran taraf karari buna gore verir (C81).
"""

from __future__ import annotations

from curl_cffi import requests

from worker import click, cookie, serp


def sayaclar() -> dict:
    """Sonuc sayaci iskeletini uretir.

    hedef_yok bir hit sonucu degil, burst seviyesinde kalir: hedef hic
    bulunamadi ve hit atilmadi.
    """
    return {"ok": 0, "captcha": 0, "not_found": 0, "hedef_yok": 0,
            "timeout": 0, "error": 0}


def tek_hit(
    sorgu: str,
    hedef_url: str,
    serp_url: str,
    proxy_adres: str | None,
    profil: str,
    uule: str | None,
    cerezler: list[dict] | None = None,
) -> dict:
    """Bir hit'i uctan uca dener.

    Kayit, sonucu belirleyen adimin HTTP kodu ve bayt sayisiyla doner.
    Ayrica dwell dusulmus ag suresi tasinir: dwell bir uyku oldugu icin
    latency'ye katilmaz, kolon saglayici ve ag kalitesini gostermeli.

    Returns:
        sira, saglayici_id ve geo_mode disindaki alanlari tasiyan sozluk.
    """
    kayit = {"profil": profil, "izlenim": None, "tik": None, "pogo": None,
             "result": "error", "http_status": None, "bytes": None,
             "latency_ms": 0, "mesaj": ""}

    with requests.Session(impersonate=profil) as oturum:
        # Cerez varsa oturuma yuklenir; yoksa hit cerezsiz gider.
        if cerezler:
            cookie.oturuma_yukle(oturum, cerezler)
        izlenim = serp.serp_getir_html(sorgu, uule=uule, proxy=proxy_adres,
                                       onceki_profil=profil, oturum=oturum)
        kayit["izlenim"] = izlenim["result"]
        # Yalnizca CAPTCHA duvari tiklamayi engeller: hedef adres burst
        # basinda zaten cozuldu, izlenimin bos donmesi hedefi yok saymaz (C9).
        if izlenim["result"] == "captcha":
            kayit["result"] = izlenim["result"]
            kayit["http_status"] = izlenim["http_status"]
            kayit["bytes"] = izlenim["bytes"]
            kayit["latency_ms"] = izlenim["elapsed_ms"]
            kayit["mesaj"] = izlenim.get("mesaj", "")
            return kayit

        tik = click.tikla(hedef_url, referer=serp_url, proxy=proxy_adres,
                          onceki_profil=profil, oturum=oturum)
        kayit["tik"] = tik["result"]
        # Tiklama suresi dwell'i de olcer; dwell dusulerek ag suresi bulunur.
        ag_ms = izlenim["elapsed_ms"] + tik["elapsed_ms"] - tik["dwell_ms"]
        if tik["result"] != "ok":
            kayit["result"] = tik["result"]
            kayit["http_status"] = tik["http_status"]
            kayit["bytes"] = tik["bytes"]
            kayit["latency_ms"] = max(0, ag_ms)
            kayit["mesaj"] = tik.get("mesaj", "")
            return kayit

        pog = click.pogo(serp_url, sorgu, proxy=proxy_adres,
                         onceki_profil=profil, oturum=oturum)
        kayit["pogo"] = pog["result"]
        kayit["http_status"] = tik["http_status"]
        kayit["bytes"] = tik["bytes"]
        kayit["latency_ms"] = max(0, ag_ms + pog["elapsed_ms"])
        if pog["result"] != "ok":
            kayit["mesaj"] = pog.get("mesaj", "")

    # Pogo basarisizsa hit "ok" sayilmaz.
    kayit["result"] = "ok" if pog is not None and pog["result"] == "ok" else "error"
    return kayit
