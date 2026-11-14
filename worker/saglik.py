"""Saglayici sagligi kararlari: oran, esik ve karantina.

Veritabani erisimi `worker/saglik_db.py` icindedir; bu modul saf hesap
yapar ve test edilebilir kalir. Esikler sozlesmeden gelir: il cifti %35'te
60 dakika tukenir (C18), saglayici geneli %20'de 2 saat karantinaya girer
(§8). Oranlar en az 10 ornek toplanmadan degerlendirilmez.

Kullanim: worker/saglik_db.py, worker/test_saglik.py.
"""

from __future__ import annotations

GEO_ESIK = 35  # yuzde; asilirsa il cifti tukenir (C18)
GEO_SURE_DK = 60  # dakika; il cifti bekleme suresi (C18)
GENEL_ESIK = 20  # yuzde; asilirsa saglayici karantinaya girer (§8)
KARANTINA_SAAT = 2  # saat; karantina suresi (§8)
ASGARI_ORNEK = 10  # ornek; tek hatada tuketmemek icin alt sinir
KARANTINA_AGIRLIK = 0  # karantinadaki saglayicinin agirligi
VARSAYILAN_AGIRLIK = 10  # yedek agirlik yoksa donulecek deger


def oran_hesapla(captcha: int, toplam: int) -> float:
    """CAPTCHA yuzdesini hesaplar.

    Args:
        captcha: CAPTCHA sayisi.
        toplam: Toplam hit sayisi.

    Returns:
        Yuzde; toplam sifirsa 0.
    """
    if toplam <= 0:
        return 0.0
    return round(captcha * 100.0 / toplam, 2)


def esik_asildi_mi(oran: float, toplam: int, esik: float) -> bool:
    """Esik asildi mi diye bakar.

    Args:
        oran: Yuzde degeri.
        toplam: Ornek sayisi.
        esik: Yuzde esigi.

    Returns:
        Ornek yeterliyse ve oran esigi gectiyse True.
    """
    return toplam >= ASGARI_ORNEK and oran > esik


def karantina_karari(
    oran: float, durum: str, suresi_doldu: bool, esik: float = GENEL_ESIK
) -> str:
    """Karantina icin ne yapilacagini soyler.

    Args:
        oran: Saglayici genel CAPTCHA yuzdesi.
        durum: Saglayicinin mevcut durumu.
        suresi_doldu: Karantina suresi gecti mi.
        esik: Yuzde esigi. Panelden gelen deger gecirilir; verilmezse
            sozlesme degeri kullanilir. Esik iki yerde tutulmaz.

    Returns:
        'karantina', 'ac' ya da 'yok'.
    """
    if durum == "active" and oran > esik:
        return "karantina"
    if durum == "quarantine" and suresi_doldu:
        return "ac"
    return "yok"