"""Saglayici sagliginin veritabani tarafi.

Her hit sonrasi saglayici sayaci artirilir; il hedefli hit'te ayrica
provider_geo satiri islenir. Esik asilirsa il cifti tuketilir (C18), saglayici
geneli asirsa saglayici karantinaya alinir ve agirligi yedege alinir (§8).

Worker normalde veritabanina yazmaz (§3); provider, provider_geo ve alert
toplu tablolar oldugu icin burada istisna uygulanir.

Uyari baglami metinle degil kimlikle cozulur: cagiran taraf kelime ve domain
verir, burada kelime_id/site_id bulunur. Bulunamazsa bos kalir.

Kullanim: worker/burst.py, tools/saglik_dene.py.
"""

from __future__ import annotations

import pymysql

from worker import ayar, ayar_db, saglik

ESIK_ORANI = 0.9
UYARI_SESSIZ_DK = 30


def _baglan() -> pymysql.connections.Connection:
    """Yazma amacli baglanti acar."""
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


def _kapat(baglanti) -> None:
    """Baglantiyi kapatir; zaten kapaliysa hata vermez."""
    if baglanti is None:
        return
    try:
        baglanti.close()
    except Exception:  # noqa: BLE001
        pass


def uyari(
    kind: str,
    ref_id: int | None,
    mesaj: str,
    kelime: str | None = None,
    domain: str | None = None,
) -> None:
    """`alert` tablosuna baglamli kayit dusurur.

    Args:
        kind: Uyari turu.
        ref_id: Ilgili kayit kimligi (saglayici, burst).
        mesaj: Okunur aciklama.
        kelime: Sorunun ciktigi kelime.
        domain: Kelimenin sitesi.
    """
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            kelime_id = site_id = None
            if kelime:
                imlec.execute(
                    "SELECT k.id, k.site_id FROM keyword k"
                    " JOIN site s ON s.id = k.site_id"
                    " WHERE k.text = %s AND s.domain = %s LIMIT 1",
                    (kelime, domain),
                )
                satir = imlec.fetchone()
                if satir:
                    kelime_id, site_id = satir
            imlec.execute(
                "INSERT INTO alert (kind, ref_id, keyword_id, site_id, message)"
                " VALUES (%s, %s, %s, %s, %s)",
                (kind, ref_id, kelime_id, site_id, mesaj[:500]),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)


def bayt_ekle(saglayici_id: int, bayt: int | None) -> None:
    """Aylik bayt sayacini artirir, kotaya yaklasinca bir kez uyarir.

    Sayac ay degince sifirlanir; `bytes_ay` hangi aya ait oldugunu tutar.
    Kota tanimli degilse yalnizca sayac islenir.

    Args:
        saglayici_id: Saglayici kimligi.
        bayt: Bu hit'te tasinan bayt; bilinmiyorsa 0 ya da None.
    """
    if not bayt or bayt <= 0:
        return
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    mesaj: str | None = None
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE provider SET"
                " bytes_month = IF(bytes_ay IS NULL"
                "   OR bytes_ay <> DATE_FORMAT(UTC_TIMESTAMP(), '%%Y-%%m'), 0, bytes_month) + %s,"
                " bytes_ay = DATE_FORMAT(UTC_TIMESTAMP(), '%%Y-%%m')"
                " WHERE id = %s",
                (bayt, saglayici_id),
            )
            imlec.execute(
                "SELECT bytes_month, quota_bytes FROM provider WHERE id = %s",
                (saglayici_id,),
            )
            satir = imlec.fetchone()
            if satir and satir[1] is not None:
                kullanilan = int(satir[0])
                kota = int(satir[1])
                if kota > 0 and kullanilan >= kota * ESIK_ORANI:
                    imlec.execute(
                        "SELECT COUNT(*) FROM alert WHERE kind = 'quota' AND ref_id = %s"
                        " AND acknowledged = 0"
                        " AND created_at > UTC_TIMESTAMP(3) - INTERVAL %s MINUTE",
                        (saglayici_id, UYARI_SESSIZ_DK),
                    )
                    if not int(imlec.fetchone()[0]):
                        yuzde = round(kullanilan * 100 / kota)
                        mesaj = f"saglayici {saglayici_id} bayt kotasinin %{yuzde}inde"
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)
    if mesaj:
        uyari("quota", saglayici_id, mesaj)

def kaydet(saglayici_id: int, geo_kodu: int | None, sonuc: str) -> None:
    """Hit sonucunu saglayiciya, il varsa il ciftine isler.

    Args:
        saglayici_id: Saglayici kimligi.
        geo_kodu: Il kodu; ulusal hit'te None.
        sonuc: hit sonucu (ok, captcha, ...).
    """
    captcha = 1 if sonuc == "captcha" else 0
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            # Sayac her hit'te artar; ulusal trafik de devre kesiciye girer.
            # Tek ifade: pencere dolduysa sayaclar sifirlanip bu hit sayilir,
            # dolmadiysa uzerine eklenir. MySQL atamalari soldan saga isler,
            # bu yuzden captcha_pct guncellenmis sayaclardan hesaplanir.
            imlec.execute(
                "UPDATE provider SET"
                " hits_1h = IF(sayac_baslangic IS NULL"
                "   OR sayac_baslangic < UTC_TIMESTAMP(3) - INTERVAL 1 HOUR, 1, hits_1h + 1),"
                " captcha_1h = IF(sayac_baslangic IS NULL"
                "   OR sayac_baslangic < UTC_TIMESTAMP(3) - INTERVAL 1 HOUR, %s, captcha_1h + %s),"
                " sayac_baslangic = IF(sayac_baslangic IS NULL"
                "   OR sayac_baslangic < UTC_TIMESTAMP(3) - INTERVAL 1 HOUR,"
                "   UTC_TIMESTAMP(3), sayac_baslangic),"
                " captcha_pct = ROUND(captcha_1h * 100 / hits_1h, 2)"
                " WHERE id = %s",
                (captcha, captcha, saglayici_id),
            )

            # Il cifti yalnizca il hedefli hit'te tutulur; anahtar il kodudur.
            if geo_kodu is None:
                return
            # Ciftte de saatlik pencere: esik %35 asilana kadar sayac seyrelmemeli.
            imlec.execute(
                "INSERT INTO provider_geo"
                " (provider_id, geo_code, hits_1h, captcha_1h, sayac_baslangic)"
                " VALUES (%s, %s, 1, %s, UTC_TIMESTAMP(3)) ON DUPLICATE KEY UPDATE"
                " hits_1h = IF(sayac_baslangic IS NULL"
                "   OR sayac_baslangic < UTC_TIMESTAMP(3) - INTERVAL 1 HOUR, 1, hits_1h + 1),"
                " captcha_1h = IF(sayac_baslangic IS NULL"
                "   OR sayac_baslangic < UTC_TIMESTAMP(3) - INTERVAL 1 HOUR, VALUES(captcha_1h),"
                "   captcha_1h + VALUES(captcha_1h)),"
                " sayac_baslangic = IF(sayac_baslangic IS NULL"
                "   OR sayac_baslangic < UTC_TIMESTAMP(3) - INTERVAL 1 HOUR,"
                "   UTC_TIMESTAMP(3), sayac_baslangic)",
                (saglayici_id, geo_kodu, captcha),
            )
            imlec.execute(
                "UPDATE provider_geo SET captcha_pct = ROUND(captcha_1h * 100 / hits_1h, 2)"
                " WHERE provider_id = %s AND geo_code = %s AND hits_1h > 0",
                (saglayici_id, geo_kodu),
            )
            imlec.execute(
                "SELECT captcha_1h, hits_1h, captcha_pct FROM provider_geo"
                " WHERE provider_id = %s AND geo_code = %s",
                (saglayici_id, geo_kodu),
            )
            satir = imlec.fetchone()
            # Esikler panelden gelir; okunamazsa sozlesme degerleri gecerli.
            esik_geo = int(ayar_db.oku("esik_geo", str(saglik.GEO_ESIK)) or saglik.GEO_ESIK)
            asgari = int(ayar_db.oku("asgari_ornek", str(saglik.ASGARI_ORNEK)) or saglik.ASGARI_ORNEK)
            if satir and saglik.esik_asildi_mi(float(satir[2]), int(satir[1]), esik_geo, asgari):
                imlec.execute(
                    "UPDATE provider_geo SET exhausted_until = NOW(3) + INTERVAL %s MINUTE"
                    " WHERE provider_id = %s AND geo_code = %s"
                    " AND (exhausted_until IS NULL OR exhausted_until < NOW(3))",
                    (saglik.GEO_SURE_DK, saglayici_id, geo_kodu),
                )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)


def karantina_kontrol(saglayici_id: int) -> None:
    """Saglayici genel oranini denetler, esikte karantinaya alir.

    Args:
        saglayici_id: Denetlenecek saglayici.
    """
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT captcha_pct, hits_1h, state,"
                " (quarantine_until IS NOT NULL AND NOW(3) > quarantine_until)"
                " FROM provider WHERE id = %s",
                (saglayici_id,),
            )
            satir = imlec.fetchone()
            if not satir:
                return
            oran = float(satir[0])
            ornek = int(satir[1])
            durum = satir[2]
            suresi_doldu = bool(satir[3])

            # Esik panelden gelir; okunamazsa sozlesme degeri (20) gecerli.
            esik = int(ayar_db.oku("esik_captcha", str(saglik.GENEL_ESIK)) or saglik.GENEL_ESIK)
            karar = saglik.karantina_karari(oran, durum, suresi_doldu, esik)
            # Ornek esigin altindaysa yalnizca karantinaya alma ertelenir;
            # suresi dolmus karantina her halukarda acilir.
            asgari = int(ayar_db.oku("asgari_ornek", str(saglik.ASGARI_ORNEK)) or saglik.ASGARI_ORNEK)
            if durum == "active" and not saglik.esik_asildi_mi(oran, ornek, esik, asgari):
                karar = "yok"

            if karar == "karantina":
                imlec.execute(
                    "UPDATE provider SET weight_yedek = weight, state = 'quarantine',"
                    " weight = %s, quarantine_until = NOW(3) + INTERVAL %s HOUR"
                    " WHERE id = %s",
                    (saglik.KARANTINA_AGIRLIK, saglik.KARANTINA_SAAT, saglayici_id),
                )
                uyari("provider_down", saglayici_id,
                      f"saglayici {saglayici_id} karantinada · captcha %{oran}")
            elif karar == "ac":
                # Karantina doldu: agirlik yedekten doner, sayaclar sifirlanir.
                imlec.execute(
                    "UPDATE provider SET state = 'active',"
                    " weight = COALESCE(weight_yedek, %s), weight_yedek = NULL,"
                    " quarantine_until = NULL, captcha_pct = 0, hits_1h = 0,"
                    " captcha_1h = 0, hata_sayac = 0 WHERE id = %s",
                    (saglik.VARSAYILAN_AGIRLIK, saglayici_id),
                )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)

HEDEF_YOK_VARSAYILAN = 3


def hedef_yok_islet(sorgu: str, domain: str | None) -> tuple[int, bool]:
    """Hedefi bulunamayan kelimenin sayacini artirir, esikte durdurur.

    Sayac yalnizca gercek "hedef ilk 100'de yok" durumunda artar; gecici API
    hatasini cagiran taraf ayirir, yoksa tek bir 429 kelimeyi durdurur.

    Args:
        sorgu: Kelime metni.
        domain: Kelimenin sitesi.

    Returns:
        (sayac, durduruldu) demeti. Kelime bulunamazsa (0, False).
    """
    if not domain:
        return 0, False
    esik = int(ayar_db.oku("hedef_yok_durma", str(HEDEF_YOK_VARSAYILAN))
               or HEDEF_YOK_VARSAYILAN)
    if esik <= 0:
        return 0, False
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return 0, False
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT k.id FROM keyword k JOIN site s ON s.id = k.site_id"
                " WHERE k.text = %s AND s.domain = %s ORDER BY k.id LIMIT 1",
                (sorgu, domain),
            )
            satir = imlec.fetchone()
            if not satir:
                return 0, False
            kelime_id = int(satir[0])
            imlec.execute(
                "UPDATE keyword SET hedef_yok_sayac = hedef_yok_sayac + 1 WHERE id = %s",
                (kelime_id,),
            )
            imlec.execute("SELECT hedef_yok_sayac FROM keyword WHERE id = %s", (kelime_id,))
            satir = imlec.fetchone()
            sayac = int(satir[0]) if satir else 0
            if sayac < esik:
                return sayac, False
            # Esik asildi: kelime durur, acik kampanya da kapatilir.
            imlec.execute(
                "UPDATE keyword SET state = 'paused' WHERE id = %s AND state = 'active'",
                (kelime_id,),
            )
            imlec.execute(
                "UPDATE campaign SET stopped_at = UTC_TIMESTAMP(3)"
                " WHERE keyword_id = %s AND stopped_at IS NULL",
                (kelime_id,),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
        return 0, False
    finally:
        _kapat(baglanti)
    uyari("hedef_yok_durdu", kelime_id,
          f"'{sorgu}' {sayac} kez ilk 100'de yok, kelime durduruldu",
          kelime=sorgu, domain=domain)
    return sayac, True


def hedef_yok_sifirla(sorgu: str, domain: str | None) -> None:
    """Basarili burst sayaci sifirlar; tek sorgu, bosuna yazmaz."""
    if not domain:
        return
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE keyword k JOIN site s ON s.id = k.site_id"
                " SET k.hedef_yok_sayac = 0"
                " WHERE k.text = %s AND s.domain = %s AND k.hedef_yok_sayac > 0",
                (sorgu, domain),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)

HATA_ESIGI = 3


def hata_isle(saglayici_id: int) -> None:
    """Ardisik basarisiz hit sayar; esikte saglayiciyi kapatir.

    Args:
        saglayici_id: Hata alan saglayici.
    """
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    sayac = 0
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE provider SET hata_sayac = hata_sayac + 1 WHERE id = %s",
                (saglayici_id,),
            )
            imlec.execute("SELECT hata_sayac, state FROM provider WHERE id = %s", (saglayici_id,))
            satir = imlec.fetchone()
            if not satir:
                return
            sayac = int(satir[0])
            if sayac < HATA_ESIGI or satir[1] == "disabled":
                return
            imlec.execute(
                "UPDATE provider SET state = 'disabled', hata_sayac = 0 WHERE id = %s",
                (saglayici_id,),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
        return
    finally:
        _kapat(baglanti)
    uyari("provider_down", saglayici_id,
          f"saglayici {saglayici_id} calismiyor · {HATA_ESIGI} ardisik hata")


def hata_sifirla(saglayici_id: int) -> None:
    """Basarili hit ardisik hata sayacini sifirlar.

    Args:
        saglayici_id: Basarili hit alan saglayici.
    """
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE provider SET hata_sayac = 0 WHERE id = %s AND hata_sayac > 0",
                (saglayici_id,),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)


def saglayici_yok_dur(sorgu: str, domain: str | None) -> None:
    """Saglayici calismadigi icin kelimeyi durdurur.

    Args:
        sorgu: Kelime metni.
        domain: Kelimenin sitesi.
    """
    baglanti = None
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    kelime_id = None
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT k.id FROM keyword k JOIN site s ON s.id = k.site_id"
                " WHERE k.text = %s AND s.domain = %s ORDER BY k.id LIMIT 1",
                (sorgu, domain),
            )
            satir = imlec.fetchone()
            if not satir:
                return
            kelime_id = int(satir[0])
            imlec.execute(
                "UPDATE keyword SET state = 'paused' WHERE id = %s AND state = 'active'",
                (kelime_id,),
            )
            imlec.execute(
                "UPDATE campaign SET stopped_at = UTC_TIMESTAMP(3)"
                " WHERE keyword_id = %s AND stopped_at IS NULL",
                (kelime_id,),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
        return
    finally:
        _kapat(baglanti)
    uyari("provider_down", None,
          f"'{sorgu}' durdu · saglayici calismiyor (ok=0)",
          kelime=sorgu, domain=domain)
