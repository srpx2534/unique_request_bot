"""Devre kesiciyi uçtan uca dener.

Sahte bir sağlayıcı ekler, CAPTCHA eşiğini aştırır, karantinaya girip
süre dolunca ağırlığına dönerek açıldığını doğrular. Sonra temizler.

Kullanım:
    python tools/saglik_dene.py
"""

from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "tools"))

from db import baglan  # noqa: E402

from worker import saglik_db  # noqa: E402

SAGLAYICI = 99
GEO = 34
TEKRAR = 12  # ASGARI_ORNEK'in üstünde; oran eşiği aşsın


def _durum(imlec) -> tuple:
    """Sağlayıcının durum, ağırlık ve yedeğini okur."""
    imlec.execute(
        "SELECT state, weight, weight_yedek, captcha_pct FROM provider WHERE id = %s",
        (SAGLAYICI,),
    )
    return imlec.fetchone()


def main() -> int:
    """Sınamayı yürütür. Beklenen sonuç çıkmazsa 1 döner."""
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("DELETE FROM provider WHERE id = %s", (SAGLAYICI,))
            imlec.execute(
                "INSERT INTO provider (id, name, kind, city_capable, weight, state,"
                " gateway, kullanici, sifre) VALUES (%s, 'Deneme', 'residential', 1,"
                " 5, 'active', 'host:10001', 'k', 's')",
                (SAGLAYICI,),
            )
            imlec.execute("DELETE FROM provider_geo WHERE provider_id = %s", (SAGLAYICI,))
    finally:
        baglanti.close()

    # Eşiğin üstünde CAPTCHA üretilir; hem il çifti hem genel oran aşar.
    for _ in range(TEKRAR):
        saglik_db.kaydet(SAGLAYICI, GEO, "captcha")
    saglik_db.karantina_kontrol(SAGLAYICI)

    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            durum, agirlik, yedek, oran = _durum(imlec)
            imlec.execute(
                "SELECT exhausted_until IS NOT NULL FROM provider_geo"
                " WHERE provider_id = %s AND geo_code = %s",
                (SAGLAYICI, GEO),
            )
            tukendi = imlec.fetchone()[0]
    finally:
        baglanti.close()

    print(f"captcha oranı: %{oran} · il çifti tükendi: {tukendi}")
    print(f"karantina: state={durum} weight={agirlik} yedek={yedek}")

    # Süre dolmuş gibi gösterilir, sonra tekrar denenir.
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "UPDATE provider SET quarantine_until = NOW(3) - INTERVAL 1 MINUTE"
                " WHERE id = %s",
                (SAGLAYICI,),
            )
    finally:
        baglanti.close()
    saglik_db.karantina_kontrol(SAGLAYICI)

    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            durum2, agirlik2, yedek2, oran2 = _durum(imlec)
    finally:
        baglanti.close()
    print(f"açılma: state={durum2} weight={agirlik2} yedek={yedek2} oran=%{oran2}")

    # Temizlik
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("DELETE FROM provider_geo WHERE provider_id = %s", (SAGLAYICI,))
            imlec.execute("DELETE FROM provider WHERE id = %s", (SAGLAYICI,))
    finally:
        baglanti.close()

    basarili = (
        durum == "quarantine" and agirlik == 0 and yedek == 5 and tukendi
        and durum2 == "active" and agirlik2 == 5 and yedek2 is None
    )
    print("SONUÇ: " + ("geçti" if basarili else "kaldı"))
    return 0 if basarili else 1


if __name__ == "__main__":
    raise SystemExit(main())