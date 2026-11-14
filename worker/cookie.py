"""Cerez dosyasi ayristirici ve oturum yukleyici.

Iki bicim desteklenir: EditThisCookie tarzi JSON ({"cookies": [...]}) ve
Netscape .txt (sekme ayracli, #HttpOnly_ oneki olabilir). Ayristirma saf
fonksiyonlardir; veritabanina yazmaz, boylece test edilebilir kalir.

Kullanim: worker/burst.py, tools/cerez_dene.py.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

# Kullanilacak alan adlari: Google yuzeyleri. Hedef site cagiran taraftan eklenir.
GOOGLE_ALANLARI = (
    "google.com", "google.com.tr", "google.co.uk", "google.de", "google.nl",
    "google.es", "google.fr", "google.ae", "google.com.au", "google.ca",
    "gstatic.com", "googleusercontent.com",
)

# Il kodu dosya adindan: basta ya da sonda iki hane (01-81).
IL_DESENI = re.compile(r"(?:^|[^0-9])(0?[1-9]|[1-7][0-9]|8[01])(?:[^0-9]|$)")

_SAYI = re.compile(r"^-?\d+(?:\.\d+)?$")


def _kok(alan: str) -> str:
    """Alan adini sadelestirir: bas nokta ve www. oneki atilir."""
    ham = alan.strip().lower().lstrip(".")
    return ham[4:] if ham.startswith("www.") else ham


def _zaman(deger) -> datetime | None:
    """Unix saniyesini UTC zamana cevirir; 0/negatif/bos ise None."""
    if deger is None:
        return None
    ham = str(deger).strip()
    if not ham or not _SAYI.match(ham):
        return None
    saniye = float(ham)
    if saniye <= 0:
        return None
    try:
        return datetime.fromtimestamp(saniye, tz=timezone.utc).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        return None


def _bayrak(deger) -> bool:
    """TRUE/true/1 degerlerini dogru sayar."""
    return str(deger).strip().lower() in ("true", "1", "yes", "evet")


def _kayit(**alanlar) -> dict:
    """Eksik alanlari varsayilanla doldurur."""
    kayit = {
        "domain": "",
        "ad": "",
        "deger": "",
        "yol": "/",
        "sona_erme": None,
        "guvenli": False,
        "http_only": False,
        "same_site": None,
        "oncelik": None,
        "oturumluk": False,
        "boyut": None,
        "kaynak_port": None,
        "kaynak_sema": None,
        "same_party": False,
        "partition_ust": None,
        "partition_ata": None,
        "host_only": False,
    }
    kayit.update(alanlar)
    return kayit


def json_coz(metin: str) -> list[dict]:
    """JSON bicimini cozer. Bozuksa ValueError atar."""
    veri = json.loads(metin)
    if isinstance(veri, dict):
        ham = veri.get("cookies") or veri.get("Cookies")
        if not isinstance(ham, list):
            raise ValueError("JSON icinde cookies dizisi yok")
    elif isinstance(veri, list):
        ham = veri
    else:
        raise ValueError("JSON kok nesnesi taninmadi")

    cerezler: list[dict] = []
    for kayit in ham:
        if not isinstance(kayit, dict):
            continue
        ad = str(kayit.get("name") or "").strip()
        domain = _kok(str(kayit.get("domain") or ""))
        if not ad or not domain:
            continue
        bolum = kayit.get("partitionKey") or {}
        cerezler.append(_kayit(
            domain=domain,
            ad=ad[:191],
            deger=str(kayit.get("value") or ""),
            yol=str(kayit.get("path") or "/")[:255],
            sona_erme=_zaman(kayit.get("expires")),
            guvenli=_bayrak(kayit.get("secure")),
            http_only=_bayrak(kayit.get("httpOnly")),
            same_site=(str(kayit.get("sameSite")).lower() if kayit.get("sameSite") else None),
            oncelik=(str(kayit.get("priority")).lower() if kayit.get("priority") else None),
            oturumluk=_bayrak(kayit.get("session")),
            boyut=(int(kayit["size"]) if str(kayit.get("size", "")).isdigit() else None),
            kaynak_port=(int(kayit["sourcePort"]) if str(kayit.get("sourcePort", "")).isdigit() else None),
            kaynak_sema=(str(kayit.get("sourceScheme")).lower() if kayit.get("sourceScheme") else None),
            same_party=_bayrak(kayit.get("sameParty")),
            partition_ust=(str(bolum.get("topLevelSite"))[:191] if isinstance(bolum, dict) and bolum.get("topLevelSite") else None),
            partition_ata=(int(bool(bolum.get("hasCrossSiteAncestor"))) if isinstance(bolum, dict) and "hasCrossSiteAncestor" in bolum else None),
            host_only=not str(kayit.get("domain") or "").startswith("."),
        ))
    return cerezler


def netscape_coz(metin: str) -> list[dict]:
    """Netscape bicimini cozer. Hic satir yoksa ValueError atar."""
    cerezler: list[dict] = []
    for satir in metin.splitlines():
        ham = satir.strip()
        if not ham:
            continue
        http_only = False
        if ham.startswith("#HttpOnly_"):
            http_only = True
            ham = ham[len("#HttpOnly_"):]
        elif ham.startswith("#"):
            continue
        parcalar = ham.split("\t")
        if len(parcalar) < 7:
            continue
        domain, alt_alan, yol, guvenli, bitis, ad, deger = parcalar[:7]
        domain = _kok(domain)
        ad = ad.strip()
        if not ad or not domain:
            continue
        cerezler.append(_kayit(
            domain=domain,
            ad=ad[:191],
            deger=deger,
            yol=(yol.strip() or "/")[:255],
            sona_erme=_zaman(bitis),
            guvenli=_bayrak(guvenli),
            http_only=http_only,
            oturumluk=not _bayrak(alt_alan),
            host_only=not domain.startswith("."),
        ))
    if not cerezler:
        raise ValueError("Netscape biciminde gecerli satir yok")
    return cerezler


def coz(metin: str, tur: str) -> list[dict]:
    """Bicime gore cozer."""
    if tur == "json":
        return json_coz(metin)
    if tur == "netscape":
        return netscape_coz(metin)
    raise ValueError(f"bilinmeyen bicim: {tur}")


def bicim_bul(metin: str) -> str | None:
    """Icerige bakarak bicimi tahmin eder; taninamazsa None."""
    kirpik = metin.lstrip()[:64]
    if kirpik.startswith("{"):
        return "json"
    for satir in metin.splitlines():
        ham = satir.strip()
        if not ham:
            continue
        if ham.startswith("#HttpOnly_"):
            return "netscape"
        if ham.startswith("#"):
            continue
        return "netscape" if ham.count("\t") >= 6 else None
    return None


def il_bul(dosya_adi: str) -> int | None:
    """Dosya adindan il kodu cikarir; bulunamazsa None."""
    bulunan = IL_DESENI.search(dosya_adi)
    if not bulunan:
        return None
    kod = int(bulunan.group(1))
    return kod if 1 <= kod <= 81 else None


def _kapsar(domain: str, kume: tuple[str, ...]) -> bool:
    """Alan adi kumeden birine esit ya da alt alan mi."""
    return any(domain == k or domain.endswith("." + k) for k in kume)


def suz(cerezler: list[dict], hedef_domain: str | None = None) -> list[dict]:
    """Yalnizca Google ve hedef site cerezlerini birakir."""
    kume = GOOGLE_ALANLARI
    if hedef_domain:
        kok = _kok(urlparse(hedef_domain).netloc or hedef_domain)
        if kok:
            kume = kume + (kok,)
    return [c for c in cerezler if _kapsar(c["domain"], kume)]


def oturuma_yukle(oturum, cerezler: list[dict], sadece_hedef: bool = False) -> int:
    """Cerezleri curl_cffi oturumuna yukler; yuklenen sayiyi dondurur."""
    yuklenen = 0
    for cerez in cerezler:
        if sadece_hedef and not _kapsar(cerez["domain"], GOOGLE_ALANLARI):
            continue
        try:
            oturum.cookies.set(
                cerez["ad"], cerez["deger"],
                domain=cerez["domain"], path=cerez["yol"] or "/",
            )
            yuklenen += 1
        except Exception:  # noqa: BLE001
            continue
    return yuklenen