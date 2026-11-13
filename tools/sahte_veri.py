"""Ekran sınaması için sahte veri üretir.

İki site, dört kelime, on dört güne yayılmış burst'ler ve çeşitli
uyarılar yazar. Gerçek ölçümü etkilemez; siteler `sahte-` önekiyle
işaretlendiği için `--sil` ile hepsi tek komutla temizlenir.

Kullanım:
    python tools/sahte_veri.py
    python tools/sahte_veri.py --sil
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from tools.db import baglan

SITELER = [("sahte-bir.test", "Deneme Bir"), ("sahte-iki.test", "Deneme İki")]
KELIMELER = [
    ("istanbul veteriner", "province", 34),
    ("ankara veteriner", "province", 6),
    ("veteriner", "national", None),
    ("acil veteriner", "national", None),
]
TURLER = ["captcha", "provider_down", "burst_hata", "quota", "fallback_high", "hedef_yok", "failover"]


def sil(baglanti) -> None:
    """Sahte siteleri ve bağlı satırları siler."""
    with baglanti.cursor() as imlec:
        imlec.execute("DELETE FROM site WHERE domain LIKE 'sahte-%'")
    baglanti.commit()
    print("sahte veri silindi")


def uret(baglanti) -> None:
    """Sahte kayıtları yazar."""
    with baglanti.cursor() as imlec:
        for domain, etiket in SITELER:
            imlec.execute(
                "INSERT INTO site (domain, label) VALUES (%s, %s)"
                " ON DUPLICATE KEY UPDATE label = VALUES(label)",
                (domain, etiket),
            )
        imlec.execute("SELECT id, domain FROM site WHERE domain LIKE 'sahte-%'")
        siteler = dict((d, i) for i, d in imlec.fetchall())

        kelime_idleri = []
        for sira, (metin, kapsam, il) in enumerate(KELIMELER):
            domain = SITELER[sira % len(SITELER)][0]
            site_id = siteler[domain]
            imlec.execute(
                "INSERT INTO keyword (site_id, text, geo_scope, home_geo, volume, state)"
                " VALUES (%s, %s, %s, %s, %s, 'active')"
                " ON DUPLICATE KEY UPDATE state = 'active'",
                (site_id, metin, kapsam, il, random.randint(40, 400)),
            )
            imlec.execute(
                "SELECT id FROM keyword WHERE site_id = %s AND text = %s", (site_id, metin)
            )
            kid = imlec.fetchone()[0]
            kelime_idleri.append((kid, site_id))

            imlec.execute(
                "INSERT INTO campaign (keyword_id, step_size, config) VALUES (%s, %s, %s)",
                (kid, random.choice([30, 45, 60]), "{}"),
            )
            kampanya = imlec.lastrowid

            imlec.execute("SELECT code FROM geo ORDER BY weight DESC LIMIT 5")
            for kod, in imlec.fetchall():
                imlec.execute(
                    "INSERT INTO keyword_geo (keyword_id, geo_code, tier) VALUES (%s, %s, 'core')"
                    " ON DUPLICATE KEY UPDATE tier = 'core'",
                    (kid, kod),
                )
            imlec.execute("SELECT id FROM keyword_geo WHERE keyword_id = %s", (kid,))
            geo_idleri = [g for g, in imlec.fetchall()]

            for gun in range(14):
                for _ in range(random.randint(1, 3)):
                    adet = random.randint(5, 40)
                    ok = random.randint(int(adet * 0.3), adet)
                    captcha = random.randint(0, adet - ok)
                    stats = {"ok": ok, "captcha": captcha,
                             "error": adet - ok - captcha, "not_found": 0, "timeout": 0}
                    imlec.execute(
                        "INSERT INTO burst (campaign_id, keyword_geo_id, step, target_count,"
                        " phase, started_at, ended_at, stats)"
                        " VALUES (%s, %s, %s, %s, %s,"
                        " NOW(3) - INTERVAL %s DAY - INTERVAL %s MINUTE,"
                        " NOW(3) - INTERVAL %s DAY - INTERVAL %s MINUTE, %s)",
                        (kampanya, random.choice(geo_idleri), gun + 1, adet,
                         random.choice(["core", "broad"]), gun, random.randint(0, 600),
                         gun, random.randint(0, 590), json.dumps(stats)),
                    )

        for _ in range(18):
            kid, site_id = random.choice(kelime_idleri)
            imlec.execute(
                "INSERT INTO alert (kind, keyword_id, site_id, message, created_at)"
                " VALUES (%s, %s, %s, %s, NOW(3) - INTERVAL %s HOUR)",
                (random.choice(TURLER), kid, site_id,
                 "sahte uyarı: eşik aşıldı", random.randint(0, 200)),
            )
    baglanti.commit()
    print("sahte veri yazıldı")


def main() -> int:
    ayar = argparse.ArgumentParser(description="Sahte veri üret")
    ayar.add_argument("--sil", action="store_true")
    arg = ayar.parse_args()

    baglanti = baglan()
    try:
        sil(baglanti) if arg.sil else uret(baglanti)
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())