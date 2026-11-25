"""Guvenilen Google cerez seti: yeni IP'lere tasinir.

Google'in kabulu adresten cok cereze bakiyor. Bir kez kabul gormus `NID`
seti yeni proxy IP'sine tasindiginda arama isitilmis kimlikten cikar; her IP
icin tarayici isitma bedeli ortadan kalkar. 20 makine planinin sarti budur.

Yalnizca Google alan adlarina ait cerezler saklanir; hedef site cerezleri
havuzda (`cookie_profil`) durur, burada degil.

Set bayatlar: sure asilinca ya da ust uste red yedikce gecersiz sayilir ve
tarayici isitmasina geri donulur. Red sayaci basarili aramada sifirlanir.

Dosya bicimi: Playwright cerez kayitlarinin JSON listesi. Dosya yoksa
`uygula`/`kavanoza` 0 doner, cagiran taraf duragan onay cerezlerine duser.

Kullanim: worker/tarayici.py, worker/serp_html.py.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
DOSYA = KOK / "veri" / "google_cerez.json"
RED_DOSYA = KOK / "veri" / "google_cerez.red"
# Google alan adlari: google.com, www.google.com.tr, .google.com ...
GOOGLE_ALAN = re.compile(r"(^|\.)google\.[a-z]{2,}(\.[a-z]{2,})?$")
VARSAYILAN_OMUR_DK = 180
AZAMI_RED = 2  # ust uste bu kadar red sonrasi set bayat sayilir


def omur_dk() -> int:
    """Setin gecerlilik suresini ayardan okur.

    Returns:
        Dakika; ayar okunamazsa varsayilan.
    """
    try:
        from worker import ayar_db

        return max(5, int(ayar_db.oku("guven_cerez_dk", str(VARSAYILAN_OMUR_DK))))
    except Exception:  # noqa: BLE001
        return VARSAYILAN_OMUR_DK


def _yaz(yol: Path, metin: str) -> None:
    """Dosyayi atomik yazar; yarim kalan yazim okumayi bozmasin."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    tani, gecici = tempfile.mkstemp(dir=str(yol.parent), prefix=yol.name)
    with os.fdopen(tani, "w", encoding="utf-8") as tutamac:
        tutamac.write(metin)
    os.replace(gecici, yol)


def kaydet(cerezler: list[dict]) -> int:
    """Google cerezlerini suzer ve dosyaya yazar.

    Args:
        cerezler: Playwright `context.cookies()` ciktisi.

    Returns:
        Yazilan cerez sayisi.
    """
    secilen = [
        {
            "name": str(c.get("name") or ""),
            "value": str(c.get("value") or ""),
            "domain": str(c.get("domain") or ""),
            "path": str(c.get("path") or "/"),
            "secure": bool(c.get("secure")),
            "httpOnly": bool(c.get("httpOnly")),
            "sameSite": c.get("sameSite") or "Lax",
            "expires": c.get("expires"),
        }
        for c in cerezler or []
        if GOOGLE_ALAN.search(str(c.get("domain") or "").lower()) and c.get("name")
    ]
    if not secilen:
        return 0
    _yaz(DOSYA, json.dumps(secilen, ensure_ascii=False))
    sifirla()
    return len(secilen)


def oku() -> list[dict]:
    """Saklanan cerezleri okur.

    Returns:
        Cerez listesi; dosya yoksa ya da bozuksa bos liste.
    """
    try:
        veri = json.loads(DOSYA.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return [k for k in veri if isinstance(k, dict) and k.get("name")] if isinstance(veri, list) else []


def red_sayisi() -> int:
    """Ust uste kac kez reddedildigini verir."""
    try:
        return int(RED_DOSYA.read_text(encoding="utf-8").strip())
    except Exception:  # noqa: BLE001
        return 0


def reddet() -> int:
    """Bir red kaydeder.

    Returns:
        Yeni red sayisi.
    """
    yeni = red_sayisi() + 1
    _yaz(RED_DOSYA, str(yeni))
    return yeni


def sifirla() -> None:
    """Red sayacini temizler; basarili aramada cagrilir."""
    try:
        RED_DOSYA.unlink()
    except Exception:  # noqa: BLE001
        pass


def taze_mi() -> bool:
    """Set kullanilabilir mi.

    Returns:
        Dosya varsa, suresi gecmemisse ve ust uste red esigi asilmamissa True.
    """
    try:
        yas_dk = (os.path.getmtime(DOSYA) and (os.path.getmtime(DOSYA)))
    except Exception:  # noqa: BLE001
        return False
    import time

    if (time.time() - yas_dk) / 60 > omur_dk():
        return False
    if red_sayisi() >= AZAMI_RED:
        return False
    return bool(oku())


def uygula(baglam) -> int:
    """Cerezleri bir Playwright baglamina ekler.

    Args:
        baglam: Acik tarayici baglami.

    Returns:
        Eklenen cerez sayisi; set kullanilamazsa 0.
    """
    if not taze_mi():
        return 0
    cerezler = oku()
    try:
        baglam.add_cookies(cerezler)
    except Exception:  # noqa: BLE001
        return 0
    return len(cerezler)


def kavanoza(oturum) -> int:
    """Cerezleri bir curl_cffi oturumuna yukler.

    Args:
        oturum: curl_cffi oturumu.

    Returns:
        Yuklenen cerez sayisi; set kullanilamazsa 0.
    """
    if not taze_mi():
        return 0
    eklenen = 0
    for cerez in oku():
        try:
            oturum.cookies.set(
                cerez["name"], cerez["value"],
                domain=cerez.get("domain") or ".google.com",
                path=cerez.get("path") or "/",
            )
            eklenen += 1
        except Exception:  # noqa: BLE001
            continue
    return eklenen