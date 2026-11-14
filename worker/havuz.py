"""Sağlayıcı havuzu ve tür oranı.

Oranlar `ayar` tablosundan okunur ve panelden düzenlenir. Önce tür kurası
çekilir (residential / mobile / datacenter), sonra o türde uygun sağlayıcı
arasından A-Res ile ağırlıklı seçim yapılır (§5). Seçilen tür boş kalırsa
sırayla residential ve datacenter denenir, hiçbiri yoksa doğrudan bağlantıya
düşülür; iş durmaz (C17).

Mobil yalnızca burst'ün ilk saniyelerinde devreye girer, çağıran taraf
`mobil_acik` ile bunu bildirir.

Okuma amaçlı bağlantı açılır; worker veritabanına yazmaz (§3).

Kullanım: worker/burst.py, tools/proxy_dene.py.
"""

from __future__ import annotations

import random

import pymysql

from worker import ayar, proxy

ORAN_ANAHTARLARI = ("oran_residential", "oran_mobil", "oran_datacenter")
VARSAYILAN_ORAN = {"oran_residential": 100, "oran_mobil": 0, "oran_datacenter": 0}


def oranlari_normalize(ham: dict[str, int]) -> dict[str, int]:
    """Oranları 100'e tamamlar.

    Panel yüzde girer ama toplam 100 tutmayabilir; eksik ya da fazla
    değerler burada dengelenir ki seçim dağılımı bozulmasın.

    Args:
        ham: Anahtar -> ham değer.

    Returns:
        Toplamı 100 olan sözlük. Hepsi sıfırsa residential 100 olur.
    """
    temiz = {k: max(0, int(ham.get(k, 0))) for k in ORAN_ANAHTARLARI}
    toplam = sum(temiz.values())
    if toplam == 0:
        return dict(VARSAYILAN_ORAN)
    if toplam == 100:
        return temiz
    # En büyük kalana yuvarlama hatası yazılır, böylece toplam tam 100 olur.
    olcekli = {k: v * 100 // toplam for k, v in temiz.items()}
    kalan = 100 - sum(olcekli.values())
    if kalan:
        en_buyuk = max(temiz, key=lambda k: temiz[k])
        olcekli[en_buyuk] += kalan
    return olcekli


def tur_sec(
    oranlar: dict[str, int],
    mobil_acik: bool,
    rastgele: float | None = None,
) -> str | None:
    """Oranlara göre tür kurası çeker.

    Args:
        oranlar: normalize edilmiş oranlar.
        mobil_acik: False ise mobil havuzu hiç katılmaz.
        rastgele: 0-100 arası değer; test için verilebilir.

    Returns:
        Tür adı ya da hiçbiri uygunsa None.
    """
    agirliklar = {
        "residential": oranlar.get("oran_residential", 0),
        "mobile": oranlar.get("oran_mobil", 0) if mobil_acik else 0,
        "datacenter": oranlar.get("oran_datacenter", 0),
    }
    toplam = sum(agirliklar.values())
    if toplam <= 0:
        return None

    esik = random.uniform(0, toplam) if rastgele is None else rastgele * toplam / 100
    birikim = 0.0
    for tur, agirlik in agirliklar.items():
        birikim += agirlik
        if esik <= birikim:
            return tur
    return "residential"


def _baglan() -> pymysql.connections.Connection:
    """Salt okuma amaçlı bağlantı açar."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user=ayar.oku("MYSQL_USER", "request"),
        password=ayar.oku("MYSQL_PASSWORD"),
        database=ayar.oku("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        init_command="SET time_zone = '+00:00'",
        autocommit=True,
    )


def oranlari_oku() -> dict[str, int]:
    """Oranları veritabanından okur.

    Returns:
        normalize edilmiş oran sözlüğü. Tablo okunamazsa varsayılan döner.
    """
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return dict(VARSAYILAN_ORAN)
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT anahtar, deger FROM ayar WHERE anahtar IN (%s, %s, %s)",
                ORAN_ANAHTARLARI,
            )
            ham = {k: int(v) for k, v in imlec.fetchall() if str(v).isdigit()}
    except Exception:  # noqa: BLE001
        return dict(VARSAYILAN_ORAN)
    finally:
        baglanti.close()
    return oranlari_normalize(ham)


def _aday_sorgusu(geo_kodu: int | None) -> str:
    """Uygun sağlayıcıyı seçen sorguyu kurar.

    A-Res: -LOG(RAND()) / weight sıralaması ağırlıklı tek seçim verir (§5).
    Karantinadaki ve kimlik bilgisi eksik sağlayıcılar dışarıda kalır.
    """
    kosullar = [
        "kind = %s",
        "state = 'active'",
        # Ya tam kimlik ya hiç kimlik: yarım kimlikli satır işe yaramaz.
        "((kullanici IS NOT NULL AND sifre IS NOT NULL)"
        " OR (kullanici IS NULL AND sifre IS NULL))",
        "gateway IS NOT NULL",
        "(quarantine_until IS NULL OR quarantine_until < NOW(3))",
    ]
    if geo_kodu is not None:
        kosullar.append("city_capable = 1")
        kosullar.append(
            "NOT EXISTS (SELECT 1 FROM provider_geo pg WHERE pg.provider_id = provider.id"
            " AND pg.geo_code = %s AND pg.exhausted_until > NOW(3))"
        )
    return (
        "SELECT id, gateway, kullanici, sifre, ulke FROM provider WHERE "
        + " AND ".join(kosullar)
        + " ORDER BY (ulke = 'TR') DESC, -LOG(RAND()) / weight LIMIT 1"
    )


def sec_mod(
    geo_slug: str | None = None, mobil_acik: bool = True
) -> tuple[int, str] | None:
    """Bir sağlayıcı seçer ve proxy dizesi üretir.

    Args:
        geo_slug: İl slug'ı; verilirse yalnızca il hedefleyebilenler arasından
            seçilir. Uygun yoksa ulusal seçime düşülür.
        mobil_acik: Mobil havuzu katılsın mı.

    Returns:
        (sağlayıcı kimliği, proxy dizesi) ya da hiçbiri yoksa None.
    """
    oranlar = oranlari_oku()
    istenen = tur_sec(oranlar, mobil_acik)

    # Sıra: istenen tür, sonra residential, sonra datacenter. Boş tür atlanır.
    sira = [t for t in (istenen, "residential", "datacenter") if t]
    sira = list(dict.fromkeys(sira))

    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return None

    try:
        with baglanti.cursor() as imlec:
            geo_kodu = None
            if geo_slug:
                imlec.execute("SELECT code FROM geo WHERE slug = %s", (geo_slug,))
                satir = imlec.fetchone()
                geo_kodu = satir[0] if satir else None

            for tur in sira:
                # İl hedefli denemede kimse yoksa ulusal sorguya düşülür (C17).
                for kod in (geo_kodu, None):
                    sorgu = _aday_sorgusu(kod)
                    parametreler = (tur, kod) if kod is not None else (tur,)
                    imlec.execute(sorgu, parametreler)
                    kayit = imlec.fetchone()
                    if kayit:
                        saglayici_id, gateway, kullanici, sifre, ulke = kayit
                        mod = "city" if kod else ("tr_fallback" if ulke == "TR" else "yabanci")
                        return saglayici_id, proxy.dize(
                            gateway, kullanici, sifre, geo_slug if kod else None
                        ), mod
    except Exception:  # noqa: BLE001
        return None
    finally:
        baglanti.close()
    return None

def slug_bul(geo_kodu: int) -> str | None:
    """İl kodundan slug üretir.

    Args:
        geo_kodu: Plaka kodu.

    Returns:
        Slug ya da bulunamazsa None.
    """
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return None
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT slug FROM geo WHERE code = %s", (geo_kodu,))
            satir = imlec.fetchone()
            return satir[0] if satir else None
    except Exception:  # noqa: BLE001
        return None
    finally:
        baglanti.close()

def kod_bul(geo_slug: str) -> int | None:
    """Slug'dan il kodu üretir.

    Args:
        geo_slug: İl slug'ı.

    Returns:
        Plaka kodu ya da bulunamazsa None.
    """
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return None
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT code FROM geo WHERE slug = %s", (geo_slug,))
            satir = imlec.fetchone()
            return int(satir[0]) if satir else None
    except Exception:  # noqa: BLE001
        return None
    finally:
        baglanti.close()

def durum_sayaci() -> dict[str, int]:
    """Sağlayıcıları duruma göre sayar.

    Returns:
        active, quarantine, disabled sayıları. Okunamazsa boş sözlük.
    """
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return {}
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT state, COUNT(*) FROM provider GROUP BY state")
            return {satir[0]: int(satir[1]) for satir in imlec.fetchall()}
    except Exception:  # noqa: BLE001
        return {}
    finally:
        baglanti.close()
def sec(
    geo_slug: str | None = None, mobil_acik: bool = True
) -> tuple[int, str] | None:
    """`sec_mod` sonucundan yalnızca sağlayıcı ve proxy dizesini verir."""
    sonuc = sec_mod(geo_slug, mobil_acik)
    return None if sonuc is None else (sonuc[0], sonuc[1])
# Son seçimin hangi yoldan geldiğini tutar: city, tr_fallback, yabanci.
son_mod = "yabanci"


def varsayilan_secici(geo_slug: str | None = None, mobil_acik: bool = True):
    """Havuzdan seçim yapan kapanış döndürür.

    Seçilen her proxy için `son_mod` güncellenir; böylece çağıran taraf
    hit kaydına hangi yoldan gidildiğini yazabilir.

    Args:
        geo_slug: İl slug'ı; verilirse önce o il denenir.
        mobil_acik: Mobil havuz katılsın mı.

    Returns:
        Parametresiz çağrılabilir; proxy dizesi ya da None.
    """

    def secici() -> str | None:
        global son_mod
        sonuc = sec_mod(geo_slug, mobil_acik)
        if sonuc is None:
            return None
        son_mod = sonuc[2]
        return sonuc[1]

    return secici


# --- Cerez havuzu ---------------------------------------------------------
# Havuz kuralinin istisnasi: sahiplenme icin cookie_profil'e yazilir (§3).
# Birden fazla dugum ayni havuzdan beslenir; sahiplenme atomiktir.

CEREZ_BIRAKMA_DK = 10  # dakika; dugum olurse kilit bu sure sonunda duser
_dugum_onbellek: list = []


def _ayar_evet(anahtar: str, varsayilan: str = "1") -> bool:
    """Ayari evet/hayir olarak okur; okunamazsa varsayilana doner."""
    try:
        from worker import ayar_db

        ham = (ayar_db.oku(anahtar, varsayilan) or varsayilan).strip().lower()
        return ham not in ("0", "", "hayir", "hayır", "false")
    except Exception:  # noqa: BLE001
        return varsayilan != "0"


def cerez_aktif() -> bool:
    """Panelden cerez kullanimi acik mi."""
    return _ayar_evet("cerez_kullan", "1")


def _dugum_id() -> int | None:
    """Bu dugumun kayit kimligi; bir kez cozulur."""
    if _dugum_onbellek:
        return _dugum_onbellek[0]
    kimlik: int | None = None
    try:
        from worker import kalp

        baglanti = _baglan()
        try:
            with baglanti.cursor() as imlec:
                imlec.execute("SELECT id FROM dugum WHERE ip = %s LIMIT 1", (kalp._ip(),))
                satir = imlec.fetchone()
                kimlik = int(satir[0]) if satir else None
        finally:
            baglanti.close()
    except Exception:  # noqa: BLE001
        kimlik = None
    _dugum_onbellek.append(kimlik)
    return kimlik


def cerez_sec(geo_kodu: int | None = None) -> int | None:
    """Havuzdan bir cerez profili sahiplenir.

    Once suresi dolmamis profiller, ayar aciksa sonra suresi gecmisler
    denenir; her ikisinde de en az kullanilan once gelir. Sahiplenme
    kosullu UPDATE ile yapilir, iki dugum ayni profili alamaz.

    Args:
        geo_kodu: Il kodu; verilirse il etiketli profiller one alinir.

    Returns:
        Profil kimligi; havuz bossa ya da cerez kapaliysa None.
    """
    if not cerez_aktif():
        return None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return None
    try:
        with baglanti.cursor() as imlec:
            # Olu dugumlerin biraktigi kilitler duser.
            imlec.execute(
                "UPDATE cookie_profil SET durum = 'hazir', dugum_id = NULL"
                " WHERE durum = 'kullaniliyor'"
                " AND (alindi_at IS NULL OR alindi_at < UTC_TIMESTAMP(3) - INTERVAL %s MINUTE)",
                (CEREZ_BIRAKMA_DK,),
            )
            # Suresi yeni dolmus profiller isaretlenir.
            imlec.execute(
                "UPDATE cookie_profil SET suresi_gecmis = 1 WHERE durum = 'hazir'"
                " AND suresi_gecmis = 0 AND sona_erme IS NOT NULL"
                " AND sona_erme < UTC_TIMESTAMP(3)"
            )
            gecmisler = (0, 1) if _ayar_evet("cerez_suresiz_kullan", "1") else (0,)
            for gecmis in gecmisler:
                for _ in range(3):
                    imlec.execute(
                        "SELECT id FROM cookie_profil WHERE durum = 'hazir'"
                        " AND suresi_gecmis = %s AND (il_kodu IS NULL OR il_kodu = %s)"
                        " ORDER BY kullanim ASC, id ASC LIMIT 1",
                        (gecmis, geo_kodu or 0),
                    )
                    satir = imlec.fetchone()
                    if not satir:
                        break
                    profil_id = int(satir[0])
                    imlec.execute(
                        "UPDATE cookie_profil SET durum = 'kullaniliyor', dugum_id = %s,"
                        " alindi_at = UTC_TIMESTAMP(3) WHERE id = %s AND durum = 'hazir'",
                        (_dugum_id(), profil_id),
                    )
                    if imlec.rowcount:
                        return profil_id
            return None
    except Exception:  # noqa: BLE001
        return None
    finally:
        baglanti.close()


def cerez_al(profil_id: int) -> list[dict]:
    """Profilin cerezlerini okur; okunamazsa bos liste."""
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return []
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT domain, ad, deger, yol FROM cookie WHERE profil_id = %s", (profil_id,)
            )
            return [
                {"domain": d, "ad": a, "deger": dg, "yol": y or "/"}
                for d, a, dg, y in imlec.fetchall()
            ]
    except Exception:  # noqa: BLE001
        return []
    finally:
        baglanti.close()


def cerez_birak(profil_id: int) -> None:
    """Profili tukendi olarak kapatir ve kullanimi artirir."""
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE cookie_profil SET durum = 'tukendi', kullanim = kullanim + 1,"
                " dugum_id = NULL WHERE id = %s",
                (profil_id,),
            )
    except Exception:  # noqa: BLE001
        pass
    finally:
        baglanti.close()