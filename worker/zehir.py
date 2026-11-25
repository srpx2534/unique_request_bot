"""Zehirlenmis SERP denetimi: donen sayfa gercekten bu kelimenin mi?

Google bazen engellemeden, duvar cikarmadan, normal gorunen ama baska bir
kelimenin listesini dondurur. Boyle bir sayfa kaydedilirse yanlis sira yazilir
ve tiklama, var olmayan bir siralamaya gonderilir.

Olcut: kelimenin anlamli parcalari sonuclarin basliginda ya da adresinde
gecmeli. Ilk N sonucta tek parca bile gecmiyorsa sayfa zehirli sayilir.

Bu denetim ayni kelimenin iki ayri liste varyantini (kume 1 / kume 2)
yakalamaz; orada kelime parcalari zaten geciyor. Aranan, tamamen alakasiz
sayfa.

Kullanim: worker/tarayici.py.
"""

from __future__ import annotations

import re

# Tek basina anlam tasimayan, her kelimede gecebilecek parcalar.
DURAKLAR = frozenset({"ve", "ile", "için", "icin", "bir", "bu", "the", "and", "for"})
ASGARI_PARCA = 3  # bu uzunlugun altindaki parcalar sayilmaz
AZAMI_BAKILAN = 10  # yalniz ilk N sonuc denetlenir
AYIRAC = re.compile(r"[^0-9a-zçğıöşü]+")

# Turkce kucultme: I -> i, İ -> i; Python'un lower()'i noktali/noktasiz
# ayrimini bozuyor ve "İSTANBUL" -> "i̇stanbul" gibi birlesik nokta uretiyor.
KUCULTME = str.maketrans({"I": "i", "İ": "i", "ı": "i"})


def _kucult(metin: str) -> str:
    """Metni Turkce uyumlu kucultur."""
    return (metin or "").translate(KUCULTME).lower()


def parcalar(sorgu: str) -> list[str]:
    """Sorguyu anlamli parcalara ayirir.

    Args:
        sorgu: Aranan kelime.

    Returns:
        Durak kelimeler ve kisa parcalar elenmis liste.
    """
    ham = AYIRAC.split(_kucult(sorgu))
    return [p for p in ham if len(p) >= ASGARI_PARCA and p not in DURAKLAR]


def zehirli_mi(sorgu: str, kayitlar: list[dict]) -> bool:
    """Donen listenin baska bir kelimeye ait olup olmadigini soyler.

    Args:
        sorgu: Aranan kelime.
        kayitlar: `{"baslik", "link"}` sozlukleri.

    Returns:
        Tek parca bile gecmiyorsa True; parca yoksa (karar verilemez) False.
    """
    istenen = parcalar(sorgu)
    if not istenen or not kayitlar:
        return False
    for kayit in kayitlar[:AZAMI_BAKILAN]:
        metin = f"{kayit.get('baslik') or ''} {kayit.get('link') or ''}"
        kucuk = _kucult(metin)
        if any(p in kucuk for p in istenen):
            return False
    return True