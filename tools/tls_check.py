"""Parmak izi doğrulaması (JA4 tabanlı, küme üyeliği).

Her profille tls.peet.ws adresine istek atar. Chromium 110+ uzantı sırasını
karıştırdığı için JA3 bağlantı başına değişir; JA4 de ALPN/SNI varyansı
yüzünden birden fazla değer alabilir. Bu yüzden kimlik doğrulaması küme
üyeliğiyle yapılır: ölçülen ja4, profilin bilinen kümesinde olmalıdır (C5).
Windows ve Linux aynı kümeye düşmelidir (§18.7).

Kullanım:
    python tools/tls_check.py --all --yaz      # referansı büyüt
    python tools/tls_check.py --all            # referansa karşı denetle
    python tools/tls_check.py --temizle        # referansı sıfırla
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Proje kökü sys.path'e eklenir; betik tools içinden çağrılır.
KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from curl_cffi import requests  # noqa: E402

from worker import fingerprint  # noqa: E402

HEDEF = "https://tls.peet.ws/api/all"
REFERANS = KOK / "docs" / "tls_reference.json"
ZAMAN_ASIMI = 25  # saniye; peet.ws ara sıra yavaş yanıt veriyor
DENEME = 2  # ağ hatasında tekrar sayısı


def olc(profil: str) -> dict:
    """Tek profil için hash'leri toplar.

    Args:
        profil: impersonate adı.

    Returns:
        ja4, ja3_hash, http_version ve ua alanlarını taşıyan sözlük.

    Raises:
        RuntimeError: İstek, tekrar denemelere rağmen başarısız olursa.
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
    """Referansı okur ve eski liste biçimini sözlüğe çevirir.

    Returns:
        profil -> {"ja4": [...], "ja3": [...]} sözlüğü. Dosya yoksa boş.
    """
    if not REFERANS.exists():
        return {}
    ham = json.loads(REFERANS.read_text(encoding="utf-8"))
    if isinstance(ham, dict):
        return ham
    # Eski biçim: [{"profil":..., "ja4":..., "ja3_hash":...}] listesi.
    cevrilmis: dict = {}
    for kayit in ham:
        girdi = cevrilmis.setdefault(kayit["profil"], {"ja4": [], "ja3": []})
        if kayit.get("ja4"):
            girdi["ja4"].append(kayit["ja4"])
        if kayit.get("ja3_hash"):
            girdi["ja3"].append(kayit["ja3_hash"])
    return cevrilmis


def yaz_referans(kayitlar: list[dict]) -> None:
    """Ölçülen değerleri referansa birleştirir.

    Kümeler birleşimle büyür: yeni bir sıra veya varyant görülmesi
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
    print(f"referans güncellendi: {REFERANS.name}")


def karsilastir(kayitlar: list[dict]) -> int:
    """Ölçümleri referansa karşı denetler. Sapma sayısını döndürür.

    Sapma ölçütü ja4 kümesidir. ja3 kümede yoksa yalnızca bilgi verilir.
    """
    referans = referans_oku()
    if not referans:
        print("referans yok, karşılaştırma atlandı.")
        return 0

    sapan = 0
    for kayit in kayitlar:
        girdi = referans.get(kayit["profil"])
        if not girdi:
            print(f"YENİ  {kayit['profil']}: referansta yok")
            continue
        if kayit["ja4"] not in girdi["ja4"]:
            print(f"SAPMA {kayit['profil']}: ja4 {kayit['ja4']} kümede yok")
            sapan += 1
        elif kayit["ja3_hash"] not in girdi["ja3"]:
            print(f"YENİ JA3 {kayit['profil']}: {kayit['ja3_hash']} (sıra değişimi, kabul)")
        else:
            print(f"UYAR  {kayit['profil']}: eşleşti")
    return sapan


def main() -> int:
    """Profilleri ölçer. Hata veya sapma varsa 1 döner."""
    ayar = argparse.ArgumentParser(description="Parmak izi doğrulaması")
    ayar.add_argument("--profil", help="tek profil ölç")
    ayar.add_argument("--all", action="store_true", help="tüm profilleri ölç")
    ayar.add_argument("--yaz", action="store_true", help="referansı güncelle")
    ayar.add_argument("--temizle", action="store_true", help="referansı sil")
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
    print(f"ölçülen: {len(kayitlar)} · hata: {hata} · sapma: {sapan}")
    return 1 if hata or sapan else 0


if __name__ == "__main__":
    raise SystemExit(main())