"""SERP yollarinda ortak kucuk yardimcilar (§23.2)."""

from __future__ import annotations

from urllib.parse import urlparse


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
    ham = ham.split("/")[0]
    if ham.startswith("www."):
        ham = ham[4:]
    etiketler = [e for e in ham.split(".") if e]
    return ".".join(etiketler[-2:]) if len(etiketler) >= 2 else ham


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