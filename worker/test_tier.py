"""tier.py dağılım testleri.

Ağa ve veritabanına çıkmaz. C14'ün sayıları kilitlenir: national kelime
81 satır üretir, dağılım 10/30/41'dir; province kelime tek core satır
üretir. Core dilimi nüfus sırasının ilk 10 ilidir.
"""

from __future__ import annotations

import pytest

from worker import tier


def _kodlar() -> list[int]:
    """Nüfus sırasına dizilmiş 81 il kodu."""
    return list(range(1, 82))


def test_national_seksen_bir_satir_uretir() -> None:
    """National kelime 81 keyword_geo satırı üretir."""
    assert len(tier.dagitim(_kodlar(), "national")) == 81


def test_national_dagilim_on_otuz_kirk_bir() -> None:
    """Tier dağılımı 10 core, 30 normal, 41 passive olur."""
    ciftler = tier.dagitim(_kodlar(), "national")
    sayim = {"core": 0, "normal": 0, "passive": 0}
    for _kod, etiket in ciftler:
        sayim[etiket] += 1
    assert sayim == {"core": 10, "normal": 30, "passive": 41}


def test_core_dilimi_siranin_ilk_onu() -> None:
    """Core tier nüfus sırasının ilk 10 ilini alır."""
    ciftler = tier.dagitim(_kodlar(), "national")
    core = [kod for kod, etiket in ciftler if etiket == "core"]
    assert core == list(range(1, 11))


def test_province_tek_core_satir() -> None:
    """Province kelime tek satır üretir ve o satır core'dur."""
    assert tier.dagitim(_kodlar(), "province", home_geo=34) == [(34, "core")]


def test_province_il_yoksa_hata() -> None:
    """Province kapsamında il verilmezse hata yükselir."""
    with pytest.raises(ValueError):
        tier.dagitim(_kodlar(), "province")


def test_bilinmeyen_kapsam_hata() -> None:
    """Tanınmayan kapsam reddedilir."""
    with pytest.raises(ValueError):
        tier.dagitim(_kodlar(), "ilce")


def test_eksik_liste_hata() -> None:
    """81'den az il gelirse sessizce geçilmez."""
    with pytest.raises(ValueError):
        tier.dagitim(list(range(1, 80)), "national")