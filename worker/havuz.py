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
import time

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


# Oran degisikligi bir dakika icinde etkili olur; her hit'te veritabani
# okumak baglanti acip kapatiyordu.
ORAN_ONBELLEK_SN = 60
_oran_onbellek: dict[str, int] | None = None
_oran_onbellek_ts = 0.0


def onbellek_temizle() -> None:
    """Oran onbellegini bosaltir; testler ve panel degisikligi icin."""
    global _oran_onbellek, _oran_onbellek_ts
    _oran_onbellek = None
    _oran_onbellek_ts = 0.0


def oranlari_oku() -> dict[str, int]:
    """Oranlari okur: once tablo, sonra varsayilan.

    Tablo okunamazsa varsayilan gecerli olur; oranlar yalniz tablodan gelir (23).
    Sonuc bir dakika onbellekte tutulur.

    Returns:
        normalize edilmis oran sozlugu.
    """
    global _oran_onbellek, _oran_onbellek_ts
    if _oran_onbellek is not None and time.monotonic() - _oran_onbellek_ts < ORAN_ONBELLEK_SN:
        return dict(_oran_onbellek)

    ham: dict[str, int] = {}
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        baglanti = None
    if baglanti is not None:
        try:
            with baglanti.cursor() as imlec:
                imlec.execute(
                    "SELECT anahtar, deger FROM ayar WHERE anahtar IN (%s, %s, %s)",
                    ORAN_ANAHTARLARI,
                )
                ham = {k: int(v) for k, v in imlec.fetchall() if str(v).isdigit()}
        except Exception:  # noqa: BLE001
            ham = {}
        finally:
            baglanti.close()
    sonuc = oranlari_normalize(ham) if ham else dict(VARSAYILAN_ORAN)
    _oran_onbellek = sonuc
    _oran_onbellek_ts = time.monotonic()
    return dict(sonuc)

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
        # Kotasi dolmus saglayici yeni hit almaz; kota yoksa hep uygundur.
        "(quota_bytes IS NULL OR bytes_month < quota_bytes)",
    ]
    if geo_kodu is not None:
        kosullar.append("city_capable = 1")
        kosullar.append(
            "NOT EXISTS (SELECT 1 FROM provider_geo pg WHERE pg.provider_id = provider.id"
            " AND pg.geo_code = %s AND pg.exhausted_until > NOW(3))"
        )
    return (
        "SELECT id, name, gateway, kullanici, sifre, ulke FROM provider WHERE "
        + " AND ".join(kosullar)
        + " ORDER BY (ulke = 'TR') DESC, -LOG(RAND()) / weight LIMIT 1"
    )


def sec_mod(
    geo_slug: str | None = None, mobil_acik: bool = True, zorunlu_tur: str | None = None
) -> tuple[int, str, str, str] | None:
    """Bir sağlayıcı seçer ve proxy dizesi üretir.

    Args:
        geo_slug: İl slug'ı; verilirse önce o ile ait IP'ler denenir, il tükenirse
            TR geneline düşülür. İl yoksa doğrudan TR geneli kullanılır.
        mobil_acik: Mobil havuzu katılsın mı.
        zorunlu_tur: Mobil kelimede "mobile" gecilir; o tur once denenir, yoksa normal siraya dusulur.

    Returns:
        (sağlayıcı kimliği, proxy dizesi) ya da hiçbiri yoksa None.
    """
    oranlar = oranlari_oku()
    istenen = tur_sec(oranlar, mobil_acik)

    # Sıra: istenen tür, sonra residential, sonra datacenter. Boş tür atlanır.
    sira = [t for t in (zorunlu_tur, istenen, "residential", "datacenter") if t]
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

            # Sıra: önce il, sonra TR geneli. İl seçiliyken o ile ait IP'ler
            # bütün türlerde tükenmeden ulusal havuza inilmez (C61). İl seçili
            # değilse `kodlar` yalnızca (None,) olur ve doğrudan TR geneli gelir.
            kodlar = (geo_kodu, None) if geo_kodu else (None,)
            for kod in kodlar:
                # İl hedefli denemede kimse yoksa ulusal sorguya düşülür (C17).
                for tur in sira:
                    sorgu = _aday_sorgusu(kod)
                    parametreler = (tur, kod) if kod is not None else (tur,)
                    imlec.execute(sorgu, parametreler)
                    kayit = imlec.fetchone()
                    if kayit:
                        saglayici_id, ad, gateway, kullanici, sifre, ulke = kayit
                        mod = "city" if kod else ("tr_fallback" if ulke == "TR" else "yabanci")
                        # Yabanci cikista ulke parametresi saglayicinin kendi ulkesi
                        # olur; TR yollarinda sabit TR yazilir (C40). Ulke yoksa
                        # parametre hic yazilmaz, karari saglayici verir.
                        cikis_ulke = "TR" if mod in ("city", "tr_fallback") else ulke
                        return saglayici_id, proxy.dize(
                            gateway, kullanici, sifre, cikis_ulke,
                            geo_slug, bicim=proxy.bicim_bul(ad)
                        ), mod, tur
    except Exception:  # noqa: BLE001
        return None
    finally:
        baglanti.close()
    return None

def kelime_mobil(kelime: str) -> bool:
    """Kelimenin mobil isaretini okur; okunamazsa False."""
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return False
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT mobil FROM keyword WHERE text = %s LIMIT 1", (kelime,))
            satir = imlec.fetchone()
            return bool(satir and satir[0])
    except Exception:  # noqa: BLE001
        return False
    finally:
        baglanti.close()


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
) -> tuple[int, str, str, str] | None:
    """`sec_mod` sonucundan yalnızca sağlayıcı ve proxy dizesini verir."""
    sonuc = sec_mod(geo_slug, mobil_acik)
    return None if sonuc is None else (sonuc[0], sonuc[1])
# Son seçimin hangi yoldan geldiğini tutar: city, tr_fallback, yabanci.
# Geriye uyumluluk için duruyor; eşzamanlı burst'te yarışa açıktır, bu yüzden
# `varsayilan_secici` modu kapanışın kendi içinde taşır.
son_mod = "yabanci"


def varsayilan_secici(geo_slug: str | None = None, mobil_acik: bool = True):
    """Havuzdan seçim yapan kapanış döndürür.

    Seçilen her proxy için mod kapanışın kendi içinde tutulur; global
    `son_mod` eşzamanlı burst'te başka burst'ün moduyla eziliyordu.

    Args:
        geo_slug: İl slug'ı; verilirse önce o il denenir.
        mobil_acik: Mobil havuz katılsın mı.

    Returns:
        Parametresiz çağrılabilir; proxy dizesi ya da None.
        `secici.mod` son seçimin yolunu taşır (city, tr_fallback, yabanci).
    """

    def secici() -> str | None:
        global son_mod
        sonuc = sec_mod(geo_slug, mobil_acik)
        if sonuc is None:
            return None
        secici.mod = sonuc[2]
        son_mod = sonuc[2]
        return sonuc[1]

    secici.mod = "yabanci"
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


def cerez_olcum_orani() -> int:
    """Olculmemis cerez secme yuzdesi.

    Canli cerez daima onde oldugu icin tek canli cerez sonsuza kadar donuyor
    ve olculmemisler hic kullanilmiyordu. Bu oran kadar hit olculmemis
    cerezden gider; boylece hem canli sayaci artar hem parmak izi yayilir.

    Returns:
        0-100 arasi yuzde; ayar okunamazsa 20.
    """
    try:
        from worker import ayar_db

        ham = int(ayar_db.oku("cerez_olcum_orani", "20") or 20)
    except Exception:  # noqa: BLE001
        ham = 20
    return max(0, min(100, ham))


def _canli_sirasi(olcum: bool) -> tuple[int | None, ...]:
    """Canli kademesi sirasi.

    Args:
        olcum: True ise olculmemis cerezler once gelir.

    Returns:
        Kademe demeti.
    """
    return (None, 1, 0) if olcum else (1, None, 0)


def _dugum_id() -> int | None:
    """Bu dugumun kayit kimligi; ad varsa ad, yoksa IP ile cozulur."""
    if _dugum_onbellek:
        return _dugum_onbellek[0]
    kimlik: int | None = None
    try:
        from worker import kalp

        baglanti = _baglan()
        try:
            with baglanti.cursor() as imlec:
                ad = (ayar.oku("DUGUM_ADI") or "").strip()
                if ad:
                    imlec.execute("SELECT id FROM dugum WHERE ad = %s LIMIT 1", (ad,))
                else:
                    imlec.execute("SELECT id FROM dugum WHERE ip = %s LIMIT 1", (kalp._ip(),))
                satir = imlec.fetchone()
                kimlik = int(satir[0]) if satir else None
        finally:
            baglanti.close()
    except Exception:  # noqa: BLE001
        kimlik = None
    # None önbelleklenmez: düğüm henüz kayıtlı değilse sonraki çağrı yeniden
    # dener; aksi hâlde kimlik sonsuza kadar None kalırdı.
    if kimlik is not None:
        _dugum_onbellek.append(kimlik)
    return kimlik

def _cift_bul(site_domain: str | None, kelime: str | None) -> tuple[int, int] | None:
    """Site alan adi ve kelime metninden (site_id, keyword_id) ciftini bulur."""
    if not site_domain or not kelime:
        return None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return None
    try:
        with baglanti.cursor() as imlec:
            # Sira sabitlenir: ayni metinli iki kayit varsa LIMIT 1 rastgele
            # satir donduruyor ve yanlis cifte kullanim yaziliyordu.
            imlec.execute(
                "SELECT k.site_id, k.id FROM keyword k JOIN site s ON s.id = k.site_id"
                " WHERE s.domain = %s AND k.text = %s ORDER BY k.id LIMIT 1",
                (site_domain, kelime),
            )
            satir = imlec.fetchone()
            return (int(satir[0]), int(satir[1])) if satir else None
    except Exception:  # noqa: BLE001
        return None
    finally:
        baglanti.close()


def _secim_sorgusu(
    gecmis: int,
    canli: int | None,
    ulke: str,
    geo_kodu: int | None,
    cift: tuple[int, int] | None,
    mobil: bool,
) -> tuple[str, tuple]:
    """Secim sorgusunu ve parametrelerini kurar.

    Sorgu ayri tutulur; boylece veritabanina cikmadan sinanabilir. Kosullar
    sirasiyla parametre listesine yazilir, ORDER BY parametreleri sonda kalir.

    Args:
        gecmis: 0 taze, 1 suresi gecmis.
        ulke: Cerez ulkesi; ulkesi bos kayitlar toleransli sayilir.
        geo_kodu: Il kodu; verilirse il suzgeci eklenir.
        cift: Site-kelime kimlikleri; verilirse kullanim suzgeci eklenir.
        mobil: Mobil tercih; siralama parametresi.

    Returns:
        Sorgu metni ve yer tutuculara karsilik gelen parametre demeti.
    """
    # Ulke burada suzgec degil: TR cerezler yabancilarin onune gecer, yabanci
    # cerez ancak TR cerez kalmadiginda secilir.
    kosullar = [
        "durum = 'hazir'",
        "suresi_gecmis = %s",
    ]
    parametreler: list = [gecmis]
    if canli is None:
        kosullar.append("canli IS NULL")
    else:
        kosullar.append("canli = %s")
        parametreler.append(canli)
    if geo_kodu:
        kosullar.append("(il_kodu = %s OR il_kodu IS NULL)")
        parametreler.append(geo_kodu)
    if cift:
        kosullar.append(
            "NOT EXISTS (SELECT 1 FROM cookie_kullanim ck"
            " WHERE ck.profil_id = cookie_profil.id"
            " AND ck.site_id = %s AND ck.keyword_id = %s)"
        )
        parametreler.extend([cift[0], cift[1]])
    sorgu = (
        "SELECT id, parmak_izzi FROM cookie_profil WHERE "
        + " AND ".join(kosullar)
        + " ORDER BY (il_kodu = %s) DESC, (COALESCE(mobil, 0) = %s) DESC,"
        + " (ulke IS NULL OR ulke = %s) DESC, kullanim ASC, id ASC LIMIT 1"
    )
    parametreler.extend([geo_kodu or 0, 1 if mobil else 0, ulke])
    return sorgu, tuple(parametreler)

def cerez_sec(
    geo_kodu: int | None = None,
    site_domain: str | None = None,
    kelime: str | None = None,
    mobil: bool = False,
    ulke: str | None = None,
) -> tuple[int, str | None] | None:
    """Havuzdan bir cerez profili sahiplenir.

    Kural: ayni profil ayni site-kelime ciftinde ikinci kez kullanilmaz;
    farkli sitede ayni kelime icin kullanilabilir.

    Sira: aktif il eslesen, aktif TR, diger aktifler; ancak o grup bitince
    suresi gecmisler ayni ic sirayla. Grup icinde en az kullanilan secilir.
    Sahiplenme kosullu UPDATE ile atomiktir.

    Ulke daima TR'dir; parametre yalnizca sabiti kaldirmak icin var.
    Il kodu verilirse yalnizca o ilin cerezleri secilir (eski kayitlarda il
    kodu bos olanlar dahil). Cift tukenirse kullanim kayitlari yaslandirilip
    tur basa alinir; havuz bosuna kapanmaz.

    Args:
        geo_kodu: Il kodu; il bazli islemde o ilin cerezleri one alinir.
        site_domain: Hedef alan adi; cifti bulmak icin.
        kelime: Aranan kelime; cifti bulmak icin.
        ulke: Cerez ulkesi; verilmezse TR.

    Returns:
        Profil kimligi ve parmak izi ailesi; havuz bossa ya da cerez kapaliysa None.
    """
    if not cerez_aktif():
        return None
    cift = _cift_bul(site_domain, kelime)
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
            ulke_kodu = ulke or "TR"
            # Olcum karari cagri basina bir kez verilir: kademeler arasi
            # gecis ayni hit icinde degismesin.
            olcum = random.randrange(100) < cerez_olcum_orani()
            gecmisler = (0, 1) if _ayar_evet("cerez_suresiz_kullan", "1") else (0,)
            # Kademe: canli once, sonra olculmemis, en sonda engelli (C45).
            # Canli, suresi gecmemis VE engellenmiyor olandir; calisan cerez
            # her halukarda ondedir, tarihi sonra gelir.
            for canli in _canli_sirasi(olcum):
                for gecmis in gecmisler:
                    sifirlandi = False
                    for _ in range(3):
                        sorgu, secim_parametreleri = _secim_sorgusu(
                            gecmis, canli, ulke_kodu, geo_kodu, cift, mobil
                        )
                        imlec.execute(sorgu, secim_parametreleri)
                        satir = imlec.fetchone()
                        if not satir:
                            if cift and not sifirlandi:
                                # Cift tukendi: kullanim kayitlari yaslandirilir ve
                                # tur basa alinir; havuz bosuna kapanmaz.
                                imlec.execute(
                                    "DELETE FROM cookie_kullanim"
                                    " WHERE site_id = %s AND keyword_id = %s",
                                    (cift[0], cift[1]),
                                )
                                sifirlandi = True
                                continue
                            break
                        profil_id = int(satir[0])
                        parmak = satir[1]
                        imlec.execute(
                            "UPDATE cookie_profil SET durum = 'kullaniliyor', dugum_id = %s,"
                            " alindi_at = UTC_TIMESTAMP(3) WHERE id = %s AND durum = 'hazir'",
                            (_dugum_id(), profil_id),
                        )
                        if not imlec.rowcount:
                            continue
                        if cift:
                            imlec.execute(
                                "INSERT IGNORE INTO cookie_kullanim (profil_id, site_id, keyword_id)"
                                " VALUES (%s, %s, %s)",
                                (profil_id, cift[0], cift[1]),
                            )
                        return profil_id, parmak
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
                "SELECT domain, ad, deger, yol, host_only FROM cookie WHERE profil_id = %s",
                (profil_id,),
            )
            return [
                {"domain": d, "ad": a, "deger": dg, "yol": y or "/",
                 "host_only": int(h or 0)}
                for d, a, dg, y, h in imlec.fetchall()
            ]
    except Exception:  # noqa: BLE001
        return []
    finally:
        baglanti.close()


def cerez_canli(profil_id: int) -> None:
    """Basarili hit alan cerez profilini canli isaretler.

    Esas kanal olcum turudur (`tools/cerez_olcum.py`); bu yalnizca calisan
    cerez sayaci artirsin diye eklenen ikinci kanaldir. Yazim basarisiz
    olursa sessiz kalinir, hit durmaz.

    Args:
        profil_id: Basarili hit alan profil.
    """
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE cookie_profil SET canli = 1, son_kontrol_at = UTC_TIMESTAMP(3)"
                " WHERE id = %s AND (canli IS NULL OR canli = 0)",
                (profil_id,),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[havuz] {hata}")
    finally:
        baglanti.close()


def cerez_birak(profil_id: int) -> None:
    """Profili yeniden havuza birakir ve kullanimi artirir."""
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE cookie_profil SET durum = 'hazir', kullanim = kullanim + 1,"
                " dugum_id = NULL WHERE id = %s",
                (profil_id,),
            )
    except Exception:  # noqa: BLE001
        pass
    finally:
        baglanti.close()
