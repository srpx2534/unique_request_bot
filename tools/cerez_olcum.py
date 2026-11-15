"""Cerez canliligi olcumu.

Her profili tek hafif istekle sinar: cerezler oturuma yuklenir ve Google'a
arama atilir. Olcut oturum acilmasi degil, engellenmemesidir: CAPTCHA ya da
engel yiyen profil olu sayilir, normal cevap donen canli. Ag hatasinda deger
NULL birakilir ki gecici kesinti cerezi oldurmesin.

Proxy denenir; proxy duserse istek bir kez dogrudan tekrarlanir ve
`olcum_proxy=0` yazilir. Boylece olu proxy olcumu kilitlemez.

Kullanim: python tools/cerez_olcum.py --adet 200
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

import pymysql  # noqa: E402
from curl_cffi import requests  # noqa: E402

from worker import ayar, cookie, fingerprint, havuz  # noqa: E402

ARAMA = "https://www.google.com/search"
BASLIKLAR = {"Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}
SORGU = "veteriner"
ZAMAN_ASIMI = 20  # saniye; olcum burst degil, kisa tutulur
TEKRAR_DK = 24 * 60  # dakika; ayni profil bir gunde ikinci kez olculmez


def baglan() -> pymysql.connections.Connection:
    """Olcum yazimi icin baglanti acar."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user=ayar.oku("MYSQL_USER", "request"),
        password=ayar.oku("MYSQL_PASSWORD"),
        database=ayar.oku("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
        autocommit=True,
    )


def adaylar(baglanti, adet: int) -> list[tuple]:
    """Olculecek profilleri secer: hic olculmemisler once, eski olcumler sonra."""
    with baglanti.cursor() as imlec:
        imlec.execute(
            "SELECT id, parmak_izzi FROM cookie_profil WHERE durum = 'hazir'"
            " AND (son_kontrol_at IS NULL"
            "   OR son_kontrol_at < UTC_TIMESTAMP(3) - INTERVAL %s MINUTE)"
            " ORDER BY (canli IS NULL) DESC, (son_kontrol_at IS NULL) DESC, id ASC"
            " LIMIT %s",
            (TEKRAR_DK, adet),
        )
        return list(imlec.fetchall())


def _istek(profil: str, cerezler: list[dict], proxy: str | None):
    """Tek istegi atar; hata olursa istisnayi cagirana birakir."""
    with requests.Session(impersonate=profil) as oturum:
        if cerezler:
            cookie.oturuma_yukle(oturum, cerezler)
        return oturum.get(
            ARAMA,
            params={"q": SORGU, "hl": "tr", "gl": "tr", "num": "1"},
            headers=BASLIKLAR,
            timeout=ZAMAN_ASIMI,
            proxies={"https": proxy, "http": proxy} if proxy else None,
        )


def olc(profil_id: int, parmak: str | None, proxy: str | None) -> tuple[bool | None, bool]:
    """Tek profili sinar.

    Returns:
        (sonuc, proxy_kullanildi). sonuc: True engellenmiyor, False engellendi,
        None belirsiz (ag hatasi).
    """
    cerezler = cookie.suz(havuz.cerez_al(profil_id), "google.com")
    # `parmak_izzi` aile tutar (chrome, firefox, bilinmiyor); impersonate
    # degeri degildir. Bilinmeyen ailede Chrome secilir: Safari ve Edge
    # profilleri Windows'ta dusuyor ve olcum belirsiz kaliyor.
    aile = parmak if parmak in ("chrome", "firefox", "safari") else "chrome"
    profil = fingerprint.profil_sec(aile=aile)

    kullanilan = bool(proxy)
    try:
        yanit = _istek(profil, cerezler, proxy)
    except Exception:  # noqa: BLE001
        if not proxy:
            return None, False
        # Proxy olu olabilir; olcum kilitlenmesin diye bir kez dogrudan denenir.
        try:
            yanit = _istek(profil, cerezler, None)
            kullanilan = False
        except Exception:  # noqa: BLE001
            return None, False

    kucuk = yanit.text[:4000].lower()
    if "/sorry/" in str(yanit.url) or "unusual traffic" in kucuk or "recaptcha" in kucuk:
        return False, kullanilan
    if yanit.status_code in (401, 403):
        return False, kullanilan
    return (True if yanit.status_code == 200 else None), kullanilan


def main() -> int:
    """Olcumu calistirir ve sonuclari yazar."""
    ayar_p = argparse.ArgumentParser(description="Cerez canliligi olcumu")
    ayar_p.add_argument("--adet", type=int, default=200)
    ayar_p.add_argument("--bekleme", type=float, default=1.0)
    ayar_p.add_argument("--proxy-yok", action="store_true", help="proxy hic denenmez")
    secim = ayar_p.parse_args()

    baglanti = baglan()
    satirlar = adaylar(baglanti, max(1, secim.adet))
    print(f"olculecek profil: {len(satirlar)}")
    canli = olu = belirsiz = 0
    for sira, (profil_id, parmak) in enumerate(satirlar, 1):
        proxy = None
        if not secim.proxy_yok:
            secilen = havuz.sec_mod(None, False)
            proxy = secilen[1] if secilen else None
        sonuc, kullanilan = olc(profil_id, parmak, proxy)
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE cookie_profil SET canli = %s,"
                " son_kontrol_at = UTC_TIMESTAMP(3), olcum_proxy = %s WHERE id = %s",
                (None if sonuc is None else int(sonuc), 1 if kullanilan else 0, profil_id),
            )
        if sonuc is True:
            canli += 1
        elif sonuc is False:
            olu += 1
        else:
            belirsiz += 1
        if sira % 25 == 0:
            print(f"  {sira}/{len(satirlar)} · canli={canli} olu={olu} belirsiz={belirsiz}")
        time.sleep(secim.bekleme)
    baglanti.close()
    print(f"bitti · canli={canli} olu={olu} belirsiz={belirsiz}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())