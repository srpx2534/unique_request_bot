"""Olcum-A kanali: SERP API'sinden ulusal, ulke uule'si sabitli olcum.

Olcum control plane'te degil burada kosar. Gerekce: uule sabiti, saglayici
secimi ve supheli sayfa tekrar karari ayni yerde durur; iki ayri kod yolu
(`olcum.ts` ve `serp.py`) birbirinden sapmaz (72).

Ulusal kelimede il ile alakali hicbir sey yoktur; il uule'si gonderilmez,
ulke uule'si gonderilir (66). Saglayici secimi de il istemez.

Yanit `search_parameters.gl` ile dogrulanir: taninmayan geo sessizce US'e
duser ve 200 doner, bu yuzden gl bos ya da TR degilse olcum suphelidir (70).

Supheli sayfa (zehirlenmis SERP) kaydedilmez; bir kez yeniden sorulur (71).
Suphe olcutu: geo dogrulanamadi, liste ince (10'un altinda) ya da son temiz
olcumun ilk 10 kumesiyle ortusme 3'un altinda.

Kullanim: worker/app.py (/worker/olcum_a), src/server/olcum.ts.
"""

from __future__ import annotations

import json
import random
import time

import pymysql

from worker import ayar_db, havuz, saglik_db, serp, tarayici
from worker.serp_ortak import ULKE_UULE, kok

KUME_UZUNLUK = 10  # sonuc kumesi; ilk 10 sira karsilastirilir
ASGARI_SONUC = 5  # altinda liste ince sayilir
ASGARI_ORTUSME = 3  # son temiz kumeyle en az bu kadar ortusme
DENEME = 2  # supheli sayfada toplam kac kez sorulur
BEKLEME_MIN = 1.0  # saniye; tekrar arasi
BEKLEME_MAX = 2.2  # saniye; ust sinir


def _baglan() -> pymysql.connections.Connection:
    """Salt okuma/yazma baglantisi; kimlik ayar_db'den gelir."""
    return ayar_db._baglan()


def _onceki_kume(kelime_id: int | None) -> set[str]:
    """Son temiz olcumun kumesini verir; yoksa bos kume."""
    if not kelime_id:
        return set()
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return set()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT kume FROM position WHERE keyword_id = %s"
                " AND channel = 'clean' AND kume IS NOT NULL"
                " ORDER BY checked_at DESC LIMIT 1",
                (kelime_id,),
            )
            satir = imlec.fetchone()
    except Exception:  # noqa: BLE001
        return set()
    finally:
        baglanti.close()
    if not satir or not satir[0]:
        return set()
    try:
        veri = json.loads(satir[0])
    except Exception:  # noqa: BLE001
        return set()
    return {str(k) for k in veri} if isinstance(veri, list) else set()


def _pozisyon_yaz(
    kelime_id: int, rank: int | None, kume: list[str], saglayici: str | None
) -> None:
    """Olcumu `position` tablosuna yazar; kume suphe denetimi icin saklanir."""
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "INSERT INTO position (keyword_id, channel, rank, kume, saglayici)"
                " VALUES (%s, 'clean', %s, %s, %s)",
                (kelime_id, rank, json.dumps(kume[:KUME_UZUNLUK]), saglayici),
            )
        baglanti.commit()
    except Exception:  # noqa: BLE001
        pass
    finally:
        baglanti.close()


def _uyari(kelime: str, domain: str, sebep: str) -> None:
    """Supheli sayfayi uyari olarak dusurur; 30 dakika sessizlik saglik_db'de."""
    saglik_db.uyari("serp_hatasi", None, f"supheli SERP: {sebep}",
                    kelime=kelime, domain=domain)


def supheli_mi(cevap: dict, onceki: set[str]) -> str:
    """Supheli sayfa sebebini dondurur; sayfa temizse bos metin.

    Args:
        cevap: `serp.serp_getir` sonucu.
        onceki: Son temiz olcumun kume kumesi.

    Returns:
        Sebep metni ya da bos metin.
    """
    # `search_parameters` yalniz Decodo yanitinda var. Diger saglayicilarda geo
    # dogrulanamaz; orada yalniz liste ve kume denetimi kalir, yoksa her olcum
    # supheli sayilip iki kez sorulurdu.
    if cevap.get("kaynak") == "decodo":
        gl = (cevap.get("gl") or "").upper()
        if not gl:
            return "geo dogrulanamadi: search_parameters.gl bos"
        if gl != "TR":
            return f"geo uyusmadi: gl={gl}"
        gonderilen = (cevap.get("geo_location") or "").strip().lower()
        if gonderilen and gonderilen not in ("turkey", "tr"):
            return f"geo taninmadi: {gonderilen}"
    organik = cevap.get("organik") or []
    if len(organik) < ASGARI_SONUC:
        return f"liste ince: {len(organik)} sonuc"
    if onceki:
        kume = {kok(str(k.get("link") or "")) for k in organik[:KUME_UZUNLUK]}
        if len(kume & onceki) < ASGARI_ORTUSME:
            return "onceki temiz kumeyle ortusme yok"
    return ""


def _serp_oku(kelime: str, domain: str, mobil: bool) -> dict:
    """SERP'i once gercek tarayiciyla, olmazsa API ile okur.

    Tarayici yolu yerel kullanicinin sartlarini uretir; API yedegi yalniz
    tarayici kurulu degilken ya da duvara carptiginda devreye girer.

    Args:
        kelime: Aranacak kelime.
        domain: Sirasi aranan alan adi.
        mobil: Mobil SERP istensin mi.

    Returns:
        `serp.serp_getir` ile ayni alanlari tasiyan sozluk.
    """
    if tarayici.kullanilabilir():
        cevap = tarayici.serp_oku(kelime, mobil=mobil)
        if cevap["result"] in ("ok", "not_found"):
            cevap["kaynak"] = "tarayici"
            cevap.setdefault("position", None)
            if cevap["result"] == "ok":
                aranan = kok(domain)
                for kayit in cevap["organik"]:
                    if kok(str(kayit.get("link") or "")) == aranan:
                        cevap["position"] = kayit["position"]
                        break
                else:
                    cevap["result"] = "not_found"
            return cevap
    return serp.serp_getir(kelime, hedef_domain=domain, uule=ULKE_UULE, mobil=mobil)


def olcum_a_yap(kelime: str, domain: str, kelime_id: int | None = None) -> dict:
    """Tek kelimeyi ulusal olarak olcer ve sonucu `position`'a yazar.

    Args:
        kelime: Aranacak kelime.
        domain: Sirasi aranan alan adi.
        kelime_id: Kayit kimligi; verilirse olcum yazilir.

    Returns:
        result, rank, kume, saglayici, suphe ve mesaj alanlarini tasiyan
        sozluk. result: ok, not_found, supheli, captcha, error, anahtar_yok.
    """
    sonuc: dict = {"result": "error", "rank": None, "kume": [], "saglayici": None,
                   "suphe": "", "mesaj": ""}
    onceki = _onceki_kume(kelime_id)
    # Mobil isaretli kelime mobil SERP ile olculur (C48); mobil kelimede
    # masaustu sayfasindan olcum siralamayi kaydiriyordu.
    mobil = havuz.kelime_mobil(kelime)

    for deneme in range(1, DENEME + 1):
        cevap = _serp_oku(kelime, domain, mobil)
        sonuc["saglayici"] = cevap.get("kaynak")
        sonuc["result"] = cevap.get("result", "error")
        sonuc["rank"] = cevap.get("position")
        sonuc["mesaj"] = cevap.get("mesaj", "")
        sonuc["kume"] = [
            kok(str(k.get("link") or "")) for k in (cevap.get("organik") or [])[:KUME_UZUNLUK]
        ]

        # Anahtar yok, kota ya da ag hatasi: suphe denetimi anlamsiz, cikilir.
        if sonuc["result"] not in ("ok", "not_found"):
            return sonuc

        suphe = supheli_mi(cevap, onceki)
        sonuc["suphe"] = suphe
        if not suphe:
            if kelime_id:
                _pozisyon_yaz(kelime_id, sonuc["rank"], sonuc["kume"], sonuc["saglayici"])
            return sonuc
        if deneme < DENEME:
            time.sleep(random.uniform(BEKLEME_MIN, BEKLEME_MAX))

    # Ikinci deneme de supheli: satir yine yazilir ama rank NULL birakilir,
    # boylece "ilk 100'de yok" ile karismaz; uyari takibe duser.
    sonuc["result"] = "supheli"
    # Supheli satirda rank tutulmaz: sayfa gercek siralama sayilmaz, "ilk
    # 100'de yok" ile karismasin diye NULL yazilir.
    sonuc["rank"] = None
    _uyari(kelime, domain, sonuc["suphe"])
    if kelime_id:
        _pozisyon_yaz(kelime_id, None, sonuc["kume"], sonuc["saglayici"])
    return sonuc