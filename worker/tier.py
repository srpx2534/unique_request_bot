"""keyword_geo tier dağılımı.

Sözleşme §7: `national` kelime 81 satır üretir ve dağılım 10 core,
30 normal, 41 passive olur. `province` kelime tek satır üretir ve o satır
core'dur. Sıra, nüfusa göre ağırlıklı listeden gelir; bu modül listeyi
dışarıdan alır, böylece veritabanı olmadan test edilebilir.

Core tier nüfusa göre ilk 10 ildir (§6.2): 34, 6, 35, 16, 7, 42, 1, 63,
27, 41. Ağırlık sütunu nüfusun karekökü olduğu için ağırlık sırası nüfus
sırasıyla aynıdır.

Kullanım: tools/keyword_ekle.py, worker/test_tier.py.
"""

from __future__ import annotations

CORE_ADET = 10  # nüfusa göre ilk 10 il; burst'ün core fazı bunları kullanır
NORMAL_ADET = 30  # ikinci halka; core tükendikten sonra devreye girer
BEKLENEN_IL = 81


def dagitim(
    sirali_kodlar: list[int], geo_scope: str, home_geo: int | None = None
) -> list[tuple[int, str]]:
    """Kelime kapsamına göre (il, tier) çiftleri üretir.

    Args:
        sirali_kodlar: Nüfus ağırlığına göre azalan sıradaki il kodları.
        geo_scope: 'national' veya 'province'.
        home_geo: `province` kapsamında zorunlu il kodu.

    Returns:
        (il kodu, tier) çiftlerinden oluşan liste.

    Raises:
        ValueError: Kapsam tanınmıyorsa, il eksikse veya liste kısaysa.
    """
    if geo_scope == "province":
        if home_geo is None:
            raise ValueError("province kapsamında home_geo zorunlu")
        # İl kelimesi tek satır üretir ve doğrudan core sayılır: hedef il
        # zaten seçilmiş, ayrıca tier dağıtmak anlamsız olur.
        return [(home_geo, "core")]

    if geo_scope != "national":
        raise ValueError(f"tanınmayan kapsam: {geo_scope}")

    if len(sirali_kodlar) != BEKLENEN_IL:
        raise ValueError(f"{BEKLENEN_IL} il bekleniyordu, {len(sirali_kodlar)} geldi")

    ciftler: list[tuple[int, str]] = []
    for sira, kod in enumerate(sirali_kodlar):
        if sira < CORE_ADET:
            ciftler.append((kod, "core"))
        elif sira < CORE_ADET + NORMAL_ADET:
            ciftler.append((kod, "normal"))
        else:
            ciftler.append((kod, "passive"))
    return ciftler