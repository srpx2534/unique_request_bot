"""Olcum-B kanali: kalici cookie jar'li kucuk profil havuzu (35, C20).

A kanali SERP API'sinden ulusal gider; B kanali gercek tarayici gibi davranir:
profil basina kalici cookie jar, HTML izlenim ve hedefe tikla. Profil
KULLANIM_SINIRI kadar kullanildiktan sonra yakilir ki havuz kucuk kalsin.
"""

from __future__ import annotations

import json

from curl_cffi import requests

from worker import click, cookie, fingerprint, serp
from worker import ayar_db

KULLANIM_SINIRI = 3
JAR_SINIRI = 400


def _baglan():
    return ayar_db._baglan()


def _jar_coz(ham) -> list[dict]:
    """JSON jar'i cerez listesine cevirir; bozuksa bos liste."""
    try:
        veri = json.loads(ham) if isinstance(ham, str) else ham
    except Exception:  # noqa: BLE001
        return []
    if isinstance(veri, dict):
        veri = veri.get("cookies")
    if not isinstance(veri, list):
        return []
    return [c for c in veri if isinstance(c, dict) and c.get("ad")]


def _jar_yaz(oturum) -> str:
    """Oturumun cerezlerini JSON'a cevirir; jar sinirla kirpilir."""
    kayitlar = []
    for cerez in list(oturum.cookies.jar)[:JAR_SINIRI]:
        try:
            kayitlar.append({
                "ad": cerez.name,
                "deger": cerez.value,
                "domain": cerez.domain or "",
                "yol": cerez.path or "/",
                "host_only": 0 if (cerez.domain or "").startswith(".") else 1,
            })
        except Exception:  # noqa: BLE001
            continue
    return json.dumps(kayitlar)

def profil_al(geo_kodu: int | None = None) -> dict | None:
    """Canli profil verir; yoksa yeni uretir. Profil uretilemezse None."""
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return None
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT id, ua, ja3_profile, cookie_jar FROM profile"
                " WHERE burned_at IS NULL ORDER BY kullanim ASC, id ASC LIMIT 1"
            )
            satir = imlec.fetchone()
            if satir:
                return {"id": satir[0], "ja3_profile": satir[2], "jar": satir[3]}
            imlec.execute(
                "SELECT id FROM provider WHERE state = 'active'"
                " ORDER BY weight DESC, id ASC LIMIT 1"
            )
            saglayici = imlec.fetchone()
            if not saglayici:
                return None
            profil = fingerprint.profil_sec(mobil=False)
            imlec.execute(
                "INSERT INTO profile (ua, ja3_profile, cookie_jar, provider_id, geo_code)"
                " VALUES (%s, %s, '[]', %s, %s)",
                (fingerprint.ua(profil), profil, saglayici[0], geo_kodu),
            )
            yeni = imlec.lastrowid
        baglanti.commit()
        return {"id": yeni, "ja3_profile": profil, "jar": "[]"}
    except Exception:  # noqa: BLE001
        return None
    finally:
        baglanti.close()


def profil_guncelle(profil_id: int, oturum) -> None:
    """Jar'i kaydeder, kullanimi artirir, sinirda profili yakar."""
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE profile SET cookie_jar = %s, kullanim = kullanim + 1 WHERE id = %s",
                (_jar_yaz(oturum), profil_id),
            )
            imlec.execute(
                "UPDATE profile SET burned_at = UTC_TIMESTAMP(3)"
                " WHERE id = %s AND kullanim >= %s AND burned_at IS NULL",
                (profil_id, KULLANIM_SINIRI),
            )
        baglanti.commit()
    except Exception:  # noqa: BLE001
        pass
    finally:
        baglanti.close()

def _pozisyon_yaz(kelime_id: int, rank: int | None) -> None:
    """B kanali olcumunu position tablosuna yazar."""
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "INSERT INTO position (keyword_id, channel, rank)"
                " VALUES (%s, 'post_click', %s)",
                (kelime_id, rank),
            )
        baglanti.commit()
    except Exception:  # noqa: BLE001
        pass
    finally:
        baglanti.close()

def olcum_b_yap(kelime: str, domain: str, geo_kodu: int | None = None, kelime_id: int | None = None) -> dict:
    """B kanalinda tek olcum yapar; sonucu sozluk olarak doner."""
    sonuc = {"result": "error", "channel": "post_click", "rank": None, "mesaj": ""}
    profil = profil_al(geo_kodu)
    if not profil:
        sonuc["mesaj"] = "profil yok"
        return sonuc

    oturum = requests.Session(impersonate=profil["ja3_profile"])
    cerezler = _jar_coz(profil["jar"])
    if cerezler:
        cookie.oturuma_yukle(oturum, cerezler, sadece_hedef=True)
    try:
        izlenim = serp.serp_getir_html(
            kelime, domain, None, None, profil["ja3_profile"], oturum
        )
        sonuc["result"] = izlenim.get("result", "error")
        sonuc["mesaj"] = izlenim.get("mesaj", "")
        for kayit in izlenim.get("organik") or []:
            if kayit.get("link") and domain in str(kayit["link"]):
                sonuc["rank"] = kayit.get("position")
                tik = click.tikla(
                    str(kayit["link"]), izlenim.get("url"), None,
                    profil["ja3_profile"], True, oturum,
                )
                if tik.get("result") != "ok":
                    sonuc["result"] = "error"
                    sonuc["mesaj"] = tik.get("mesaj", "")
                break
    except Exception as hata:  # noqa: BLE001
        sonuc["mesaj"] = str(hata)[:200]
    finally:
        profil_guncelle(profil["id"], oturum)
    if kelime_id and sonuc["result"] == "ok":
        _pozisyon_yaz(kelime_id, sonuc["rank"])
    return sonuc