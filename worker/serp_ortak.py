"""SERP yollarinda ortak kucuk yardimcilar (§23.2)."""

from __future__ import annotations

from urllib.parse import urlparse

# Iki etiketli uzantilar: yalniz son iki etiket alinirsa "com.tr" gibi bir
# parca kalir ve o uzanti altindaki butun siteler birbiriyle eslesir.
IKI_ETIKET = frozenset({
    "com.tr", "net.tr", "org.tr", "gov.tr", "edu.tr", "av.tr", "bel.tr",
    "biz.tr", "info.tr", "tv.tr", "gen.tr", "web.tr", "name.tr", "k12.tr",
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "co.nz", "com.br",
})


# Cok parcali uzantilar: son iki etiket tek basina kok vermez, ucuncu etiket
# de kokun parcasi olur. Aksi halde "site.com.tr" ile her ".com.tr" rakip
# eslesiyor ve yanlis sira yaziliyordu.
COK_PARCALI_UZANTI = frozenset((
    "com.tr", "net.tr", "org.tr", "gov.tr", "edu.tr", "av.tr", "bel.tr",
    "k12.tr", "gen.tr", "web.tr", "co.uk", "org.uk", "ac.uk", "com.br",
    "com.au", "co.jp", "com.de", "com.ru",
))


# Ulke uule'si: "Turkey" adinin uzunluk harfli kodlamasi (6 bayt -> G).
# Ulusal kelimede il secimi yoktur ama ulke sabiti sarttir; yoksa Google
# ulke-notr kompozit sayfa dondurur ve yerel arama ile tutmaz.
ULKE_UULE = "w+CAIQICIGVHVya2V5"


def kok(adres: str) -> str:
    """Adresten kok alan adini cikarir.

    Args:
        adres: Tam URL veya alan adi.

    Returns:
        www. oneki atilmis kok; cozulemezse bos metin.
    """
    ham = adres.strip().lower()
    if "://" in ham:
        ham = urlparse(ham).netloc
    ham = ham.split("/")[0].split(":")[0]
    if ham.startswith("www."):
        ham = ham[4:]
    etiketler = [e for e in ham.split(".") if e]
    if len(etiketler) < 2:
        return ham
    son_iki = ".".join(etiketler[-2:])
    if son_iki in IKI_ETIKET and len(etiketler) >= 3:
        return ".".join(etiketler[-3:])
    return son_iki


def bos_sonuc() -> dict:
    """Ortak sonuc iskeletini uretir."""
    return {
        "result": "error",
        "position": None,
        "url": None,
        "http_status": None,
        "elapsed_ms": 0,
        "bytes": 0,
        "profil": None,
        "kaynak": None,
        "organik": [],
        "mesaj": "",
    }
