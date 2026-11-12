"""Parmak izi doÄŸrulamasÄ± (JA4 tabanlÄ±, kÃ¼me Ã¼yeliÄŸi).

Her profille tls.peet.ws adresine istek atar. Chromium 110+ uzantÄ± sÄ±rasÄ±nÄ±
karÄ±ÅŸtÄ±rdÄ±ÄŸÄ± iÃ§in JA3 baÄŸlantÄ± baÅŸÄ±na deÄŸiÅŸir; JA4 de ALPN/SNI varyansÄ±
yÃ¼zÃ¼nden birden fazla deÄŸer alabilir. Bu yÃ¼zden kimlik doÄŸrulamasÄ± kÃ¼me
Ã¼yeliÄŸiyle yapÄ±lÄ±r: Ã¶lÃ§Ã¼len ja4, profilin bilinen kÃ¼mesinde olmalÄ±dÄ±r (C5).
Windows ve Linux aynÄ± kÃ¼meye dÃ¼ÅŸmelidir (Â§18.7).

KullanÄ±m:
    python tools/tls_check.py --all --yaz      # referansÄ± bÃ¼yÃ¼t
    python tools/tls_check.py --all            # referansa karÅŸÄ± denetle
    python tools/tls_check.py --temizle        # referansÄ± sÄ±fÄ±rla
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Proje kÃ¶kÃ¼ sys.path'e eklenir; betik tools iÃ§inden Ã§aÄŸrÄ±lÄ±r.
KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from curl_cffi import requests  # noqa: E402

from worker import fingerprint  # noqa: E402

HEDEF = "https://tls.peet.ws/api/all"
REFERANS = KOK / "docs" / "tls_reference.json"
ZAMAN_ASIMI = 25  # saniye; peet.ws ara sÄ±ra yavaÅŸ yanÄ±t veriyor
DENEME = 2  # aÄŸ hatasÄ±nda tekrar sayÄ±sÄ±


def olc(profil: str) -> dict:
    """Tek profil iÃ§in hash'leri toplar.

    Args:
        profil: impersonate adÄ±.

    Returns:
        ja4, ja3_hash, http_version ve ua alanlarÄ±nÄ± taÅŸÄ±yan sÃ¶zlÃ¼k.

    Raises:
        RuntimeError: Ä°stek, tekrar denemelere raÄŸmen baÅŸarÄ±sÄ±z olursa.
    """
    fingerprint.dogrula(profil)
    son_hata = ""
    for _ in range(DENEME):
        try:
            yanit = requests.get(HEDEF, impersonate=profil, timeout=ZAMAN_ASIMI)
            if yanit.status_code == 200:
                veri = yanit.json()
                tls = veri.get("tls", {})
                return {
                    "profil": profil,
                    "ja4": tls.get("ja4"),
                    "ja3_hash": tls.get("ja3_hash"),
                    "http_version": veri.get("http_version"),
                    "ua": veri.get("user_agent"),
                }
            son_hata = f"HTTP {yanit.status_code}"
        except Exception as hata:  # noqa: BLE001
            son_hata = str(hata)
    raise RuntimeError(f"{profil}: {son_hata}")


def referans_oku() -> dict:
    """ReferansÄ± okur ve eski liste biÃ§imini sÃ¶zlÃ¼ÄŸe Ã§evirir.

    Returns:
        profil -> {"ja4": [...], "ja3": [...]} sÃ¶zlÃ¼ÄŸÃ¼. Dosya yoksa boÅŸ.
    """
    if not REFERANS.exists():
        return {}
    ham = json.loads(REFERANS.read_text(encoding="utf-8"))
    if isinstance(ham, dict):
        return ham
    # Eski biÃ§im: [{"profil":..., "ja4":..., "ja3_hash":...}] listesi.
    cevrilmis: dict = {}
    for kayit in ham:
        girdi = cevrilmis.setdefault(kayit["profil"], {"ja4": [], "ja3": []})
        if kayit.get("ja4"):
            girdi["ja4"].append(kayit["ja4"])
        if kayit.get("ja3_hash"):
            girdi["ja3"].append(kayit["ja3_hash"])
    return cevrilmis


def yaz_referans(kayitlar: list[dict]) -> None:
    """Ã–lÃ§Ã¼len deÄŸerleri referansa birleÅŸtirir.

    KÃ¼meler birleÅŸimle bÃ¼yÃ¼r: yeni bir sÄ±ra veya varyant gÃ¶rÃ¼lmesi
    normaldir, eskiler silinmez.
    """
    referans = referans_oku()
    for kayit in kayitlar:
        girdi = referans.setdefault(kayit["profil"], {"ja4": [], "ja3": []})
        if kayit["ja4"] and kayit["ja4"] not in girdi["ja4"]:
            girdi["ja4"].append(kayit["ja4"])
        if kayit["ja3_hash"] and kayit["ja3_hash"] not in girdi["ja3"]:
            girdi["ja3"].append(kayit["ja3_hash"])
    REFERANS.parent.mkdir(parents=True, exist_ok=True)
    REFERANS.write_text(
        json.dumps(referans, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"referans gÃ¼ncellendi: {REFERANS.name}")


def karsilastir(kayitlar: list[dict]) -> int:
    """Ã–lÃ§Ã¼mleri referansa karÅŸÄ± denetler. Sapma sayÄ±sÄ±nÄ± dÃ¶ndÃ¼rÃ¼r.

    Sapma Ã¶lÃ§Ã¼tÃ¼ ja4 kÃ¼mesidir. ja3 kÃ¼mede yoksa yalnÄ±zca bilgi verilir.
    """
    referans = referans_oku()
    if not referans:
        print("referans yok, karÅŸÄ±laÅŸtÄ±rma atlandÄ±.")
        return 0

    sapan = 0
    for kayit in kayitlar:
        girdi = referans.get(kayit["profil"])
        if not girdi:
            print(f"YENÄ°  {kayit['profil']}: referansta yok")
            continue
        if kayit["ja4"] not in girdi["ja4"]:
            print(f"SAPMA {kayit['profil']}: ja4 {kayit['ja4']} kÃ¼mede yok")
            sapan += 1
        elif kayit["ja3_hash"] not in girdi["ja3"]:
            print(f"YENÄ° JA3 {kayit['profil']}: {kayit['ja3_hash']} (sÄ±ra deÄŸiÅŸimi, kabul)")
        else:
            print(f"UYAR  {kayit['profil']}: eÅŸleÅŸti")
    return sapan


def main() -> int:
    """Profilleri Ã¶lÃ§er. Hata veya sapma varsa 1 dÃ¶ner."""
    ayar = argparse.ArgumentParser(description="Parmak izi doÄŸrulamasÄ±")
    ayar.add_argument("--profil", help="tek profil Ã¶lÃ§")
    ayar.add_argument("--all", action="store_true", help="tÃ¼m profilleri Ã¶lÃ§")
    ayar.add_argument("--yaz", action="store_true", help="referansÄ± gÃ¼ncelle")
    ayar.add_argument("--temizle", action="store_true", help="referansÄ± sil")
    secim = ayar.parse_args()

    if secim.temizle:
        REFERANS.unlink(missing_ok=True)
        print("referans silindi.")
        return 0
    if not secim.profil and not secim.all:
        ayar.error("--profil veya --all gerekli")

    hedefler = list(fingerprint.PROFILLER) if secim.all else [secim.profil]
    kayitlar: list[dict] = []
    hata = 0

    for profil in hedefler:
        try:
            kayit = olc(profil)
        except RuntimeError as istisna:
            print(f"HATA  {istisna}")
            hata += 1
            continue
        kayitlar.append(kayit)
        print(
            f"{profil:12} ja4={kayit['ja4']} ja3={kayit['ja3_hash']} "
            f"http={kayit['http_version']}"
        )

    if kayitlar and secim.yaz:
        yaz_referans(kayitlar)

    sapan = 0 if secim.yaz else karsilastir(kayitlar)
    print(f"Ã¶lÃ§Ã¼len: {len(kayitlar)} Â· hata: {hata} Â· sapma: {sapan}")
    return 1 if hata or sapan else 0


if __name__ == "__main__":
    raise SystemExit(main())