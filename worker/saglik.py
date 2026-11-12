"""Sağlayıcı sağlığı: oran takibi, il tüketimi ve karantina.

Her hit sonrası sağlayıcı/il çiftinin sayaçları güncellenir. Oran eşiği
aşılırsa il çifti 60 dakika tükenmiş sayılır (C18), sağlayıcı geneli
eşiği aşarsa sağlayıcı 2 saat karantinaya alınır ve ağırlığı sıfırlanır
(§8). Karantina bitince ağırlık geri verilir.

Worker normalde veritabanına yazmaz (§3); `provider_geo` ve `alert`
toplu tablolar olduğu için burada tek istisna uygulanır.

Kullanım: worker/burst.py, worker/test_saglik.py.
"""

from __future__ import annotations

import pymysql

from worker import ayar

GEO_ESIK = 35  # yüzde; aşılırsa il çifti tükenir (C18)
GEO_SURE_DK = 60  # dakika; il çifti bekleme süresi (C18)
GENEL_ESIK = 20  # yüzde; aşılırsa sağlayıcı karantinaya girer (§8)
KARANTINA_SAAT = 2  # saat; karantina süresi (§8)
ASGARI_ORNEK = 10  # oran için gereken en az hit; tek hatada tüketmemek için
KARANTINA_AGIRLIK = 0  # karantinadaki sağlayıcının ağırlığı
VARSAYILAN_AGIRLIK = 10  # yedek yoksa dönülecek ağırlık


def oran_hesapla(captcha: int, toplam: int) -> float:
    """CAPTCHA yüzdesini hesaplar.

    Args:
        captcha: CAPTCHA sayısı.
        toplam: Toplam hit sayısı.

    Returns:
        Yüzde; toplam sıfırsa 0.
    """
    if toplam <= 0:
        return 0.0
    return round(captcha * 100.0 / toplam, 2)


def esik_asildi_mi(oran: float, toplam: int, esik: float) -> bool:
    """Eşik aşıldı mı diye bakar.

    Args:
        oran: Yüzde değeri.
        toplam: Örnek sayısı.
        esik: Yüzde eşiği.

    Returns:
        Örnek yeterliyse ve oran eşiği geçtiyse True.
    """
    return toplam >= ASGARI_ORNEK and oran > esik


def karantina_karari(oran: float, durum: str, suresi_doldu: bool) -> str:
    """Karantina için ne yapılacağını söyler.

    Args:
        oran: Sağlayıcı genel CAPTCHA yüzdesi.
        durum: Sağlayıcının mevcut durumu.
        suresi_doldu: Karantina süresi geçti mi.

    Returns:
        'karantina', 'ac' ya da 'yok'.
    """
    if durum == "active" and oran > GENEL_ESIK:
        return "karantina"
    if durum == "quarantine" and suresi_doldu:
        return "ac"
    return "yok"


def _baglan() -> pymysql.connections.Connection:
    """Yazma amaçlı bağlantı açar."""
    return pymysql.connect(
        host=ayar.oku("MYSQL_HOST", "127.0.0.1"),
        port=int(ayar.oku("MYSQL_PORT", "3306")),
        user=ayar.oku("MYSQL_USER", "request"),
        password=ayar.oku("MYSQL_PASSWORD"),
        database=ayar.oku("MYSQL_DATABASE", "unique_request_bot"),
        charset="utf8mb4",
        autocommit=True,
    )


def _kapat(baglanti) -> None:
    """Bağlantıyı kapatır; zaten kapalıysa hata vermez."""
    try:
        _kapat(baglanti)
    except Exception:  # noqa: BLE001
        pass


def uyari(kind: str, ref_id: int | None, mesaj: str) -> None:
    """`alert` tablosuna kayıt düşer."""
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "INSERT INTO alert (kind, ref_id, message) VALUES (%s, %s, %s)",
                (kind, ref_id, mesaj[:500]),
            )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)


def kaydet(saglayici_id: int, geo_kodu: int | None, sonuc: str) -> None:
    """Hit sonucunu sağlayıcı ve il çiftine işler.

    Args:
        saglayici_id: Sağlayıcı kimliği.
        geo_kodu: İl kodu; ulusal hit'te None.
        sonuc: hit sonucu (ok, captcha, ...).
    """
    if geo_kodu is None:
        return
    captcha = 1 if sonuc == "captcha" else 0
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "INSERT INTO provider_geo (provider_id, geo_code, hits_1h, captcha_1h)"
                " VALUES (%s, %s, 1, %s) ON DUPLICATE KEY UPDATE"
                " hits_1h = hits_1h + 1, captcha_1h = captcha_1h + VALUES(captcha_1h)",
                (saglayici_id, geo_kodu, captcha),
            )
            imlec.execute(
                "UPDATE provider_geo SET captcha_pct = ROUND(captcha_1h * 100 / hits_1h, 2)"
                " WHERE provider_id = %s AND geo_code = %s AND hits_1h > 0",
                (saglayici_id, geo_kodu),
            )
            # Sağlayıcı genel oranı il sayaçlarından yeniden hesaplanır;
            # devre kesici bu değere bakar.
            imlec.execute(
                "UPDATE provider p SET captcha_pct = COALESCE(("
                " SELECT ROUND(SUM(pg.captcha_1h) * 100 / SUM(pg.hits_1h), 2)"
                " FROM provider_geo pg WHERE pg.provider_id = p.id AND pg.hits_1h > 0"
                "), 0) WHERE p.id = %s",
                (saglayici_id,),
            )
            imlec.execute(
                "SELECT captcha_1h, hits_1h, captcha_pct FROM provider_geo"
                " WHERE provider_id = %s AND geo_code = %s",
                (saglayici_id, geo_kodu),
            )
            satir = imlec.fetchone()
            if satir and esik_asildi_mi(float(satir[2]), int(satir[1]), GEO_ESIK):
                # Çift tüketilir: havuz bu ili bu sağlayıcıda artık denemez.
                imlec.execute(
                    "UPDATE provider_geo SET exhausted_until ="
                    " NOW(3) + INTERVAL %s MINUTE"
                    " WHERE provider_id = %s AND geo_code = %s"
                    " AND (exhausted_until IS NULL OR exhausted_until < NOW(3))",
                    (GEO_SURE_DK, saglayici_id, geo_kodu),
                )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)


def karantina_kontrol(saglayici_id: int) -> None:
    """Sağlayıcı genel CAPTCHA oranını denetler, eşikte karantinaya alır."""
    try:
        baglanti = _baglan()
    except Exception:  # noqa: BLE001
        return
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT captcha_pct, state FROM provider WHERE id = %s", (saglayici_id,)
            )
            satir = imlec.fetchone()
            if not satir:
                return
            oran, durum = float(satir[0]), satir[1]

            suresi_doldu = False
            if durum == "quarantine":
                imlec.execute(
                    "SELECT quarantine_until IS NOT NULL AND NOW(3) > quarantine_until"
                    " FROM provider WHERE id = %s",
                    (saglayici_id,),
                )
                suresi_doldu = bool(imlec.fetchone()[0])

            karar = karantina_karari(oran, durum, suresi_doldu)
            if karar == "karantina":
                # Ağırlık sıfırlanırken eski değer yedeğe alınır.
                imlec.execute(
                    "UPDATE provider SET weight_yedek = weight, state = 'quarantine',"
                    " weight = %s, quarantine_until = NOW(3) + INTERVAL %s HOUR"
                    " WHERE id = %s",
                    (KARANTINA_AGIRLIK, KARANTINA_SAAT, saglayici_id),
                )
                uyari("provider_down", saglayici_id,
                      f"sağlayıcı {saglayici_id} karantinada · captcha %{oran}")
            elif karar == "ac":
                # Karantina doldu: ağırlık yedekten geri verilir, oran sıfırlanır
                # ki sağlayıcı hemen yeniden karantinaya düşmesin.
                imlec.execute(
                    "UPDATE provider SET state = 'active',"
                    " weight = COALESCE(weight_yedek, %s), weight_yedek = NULL,"
                    " quarantine_until = NULL, captcha_pct = 0 WHERE id = %s",
                    (VARSAYILAN_AGIRLIK, saglayici_id),
                )
    except Exception as hata:  # noqa: BLE001
        print(f"[saglik] {hata}")
    finally:
        _kapat(baglanti)
        _kapat(baglanti)
