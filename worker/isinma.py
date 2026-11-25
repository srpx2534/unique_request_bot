"""Yeni proxy IP'sini aramadan once isitir.

Google taze proxy IP'ye ilk aramada duvar donduruyor ya da baska kelimenin
listesini veriyor (zehirlenmis SERP). Once birkac siradan sayfa acip uzerinde
20-45 saniye beklemek cerez kavanozunu ve gezinme gecmisini doldurur; arama
boylece isitilmis bir kimlikten cikar.

Sayfalar Google'a ait olmamali: Google'i isitmak ona erken istek atmak olur.
Notr TR siteleri secilir; hafif olanlar tercih edilir, agir ana sayfalar
tarayiciyi yavaslatir.

Isinma kapaliysa (`isinma_acik=0`) hicbir istek atilmaz ve `atlandi` doner;
cagiran taraf bunu hata saymaz.

Kullanim: worker/tarayici.py, worker/burst_hit.py.
"""

from __future__ import annotations

import random
import time

from worker import ayar_db

# Notr TR sayfalari. Hepsi Google disi; hafif ve hizli yanit verenler secildi.
SAYFALAR = (
    "https://www.mgm.gov.tr/",
    "https://www.ntv.com.tr/",
    "https://www.hurriyet.com.tr/",
    "https://www.haberturk.com/",
    "https://www.doviz.com/",
)
VARSAYILAN_SAYFA = 2
AZAMI_SAYFA = 4
VARSAYILAN_BEKLEME_MS = (20_000, 45_000)
ZAMAN_ASIMI_MS = 20_000


def acik() -> bool:
    """Isinma panelden acik mi.

    Returns:
        Ayar yoksa ya da `0`/`hayir` degilse True.
    """
    try:
        ham = (ayar_db.oku("isinma_acik", "1") or "1").strip().lower()
    except Exception:  # noqa: BLE001
        return True
    return ham not in ("0", "", "hayir", "hayır", "false")


def sayfa_sayisi() -> int:
    """Kac sayfa acilacagini verir.

    Returns:
        1 ile AZAMI_SAYFA arasinda sayi; ayar okunamazsa varsayilan.
    """
    try:
        ham = int(ayar_db.oku("isinma_sayfa", str(VARSAYILAN_SAYFA)) or VARSAYILAN_SAYFA)
    except Exception:  # noqa: BLE001
        ham = VARSAYILAN_SAYFA
    return max(1, min(AZAMI_SAYFA, ham))


def bekleme() -> tuple[int, int]:
    """Sayfa basina bekleme araligini verir.

    Returns:
        (en az, en cok) milisaniye.
    """
    try:
        alt = int(ayar_db.oku("isinma_bekleme_min", str(VARSAYILAN_BEKLEME_MS[0])))
        ust = int(ayar_db.oku("isinma_bekleme_max", str(VARSAYILAN_BEKLEME_MS[1])))
    except Exception:  # noqa: BLE001
        return VARSAYILAN_BEKLEME_MS
    if alt < 1_000:
        alt = VARSAYILAN_BEKLEME_MS[0]
    if ust < alt:
        ust = alt
    return alt, ust


def sayfa_sec(rastgele: random.Random | None = None) -> list[str]:
    """Isinma sayfalarini rastgele secer.

    Args:
        rastgele: Test icin tohumlanmis uretici.

    Returns:
        Benzersiz adres listesi.
    """
    r = rastgele or random
    adet = min(sayfa_sayisi(), len(SAYFALAR))
    return r.sample(list(SAYFALAR), adet)


def _sonuc(sonuc: str, acilan: int, bekleme_ms: int, mesaj: str = "") -> dict:
    """Ortak sonuc iskeletini uretir."""
    return {"result": sonuc, "sayfa": acilan, "bekleme_ms": bekleme_ms, "mesaj": mesaj}


def _sure(r: random.Random, aralik: tuple[int, int]) -> int:
    """Araliktan rastgele bekleme secer."""
    return r.randint(aralik[0], aralik[1])


def tarayicida(
    sayfa,
    rastgele: random.Random | None = None,
    aralik: tuple[int, int] | None = None,
) -> dict:
    """Acik tarayici sayfasinda isinma yapar.

    Args:
        sayfa: Acik Playwright sayfasi.
        rastgele: Test icin tohumlanmis uretici.
        aralik: Bekleme araligi; verilmezse ayardan okunur.

    Returns:
        result (ok, atlandi, error), sayfa, bekleme_ms ve mesaj alanlari.
    """
    if not acik():
        return _sonuc("atlandi", 0, 0, "isinma kapali")
    r = rastgele or random
    aralik = aralik or bekleme()
    acilan = 0
    toplam = 0
    for adres in sayfa_sec(r):
        try:
            sayfa.goto(adres, wait_until="domcontentloaded", timeout=ZAMAN_ASIMI_MS)
        except Exception:  # noqa: BLE001
            continue
        sure = _sure(r, aralik)
        try:
            sayfa.wait_for_timeout(sure)
        except Exception:  # noqa: BLE001
            pass
        acilan += 1
        toplam += sure
    if not acilan:
        return _sonuc("error", 0, 0, "isinma sayfasi acilmadi")
    return _sonuc("ok", acilan, toplam)


def http(
    oturum,
    rastgele: random.Random | None = None,
    aralik: tuple[int, int] | None = None,
) -> dict:
    """Tarayicisiz yolda curl_cffi oturumuyla isinma yapar.

    Args:
        oturum: Proxy'ye bagli curl_cffi oturumu.
        rastgele: Test icin tohumlanmis uretici.
        aralik: Bekleme araligi; verilmezse ayardan okunur.

    Returns:
        result, sayfa, bekleme_ms ve mesaj alanlari.
    """
    if not acik():
        return _sonuc("atlandi", 0, 0, "isinma kapali")
    r = rastgele or random
    aralik = aralik or bekleme()
    acilan = 0
    toplam = 0
    for adres in sayfa_sec(r):
        try:
            oturum.get(adres, timeout=ZAMAN_ASIMI_MS // 1000)
        except Exception:  # noqa: BLE001
            continue
        sure = _sure(r, aralik)
        time.sleep(sure / 1000)
        acilan += 1
        toplam += sure
    if not acilan:
        return _sonuc("error", 0, 0, "isinma sayfasi acilmadi")
    return _sonuc("ok", acilan, toplam)