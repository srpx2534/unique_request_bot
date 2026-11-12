"""Kelime ve keyword_geo satırlarını veritabanına ekler.

Sözleşme §7'deki otomatik üretimi uygular: kelime kaydedilince
keyword_geo satırları da yazılır. Tier dağılımı worker/tier.py'den gelir,
burada yalnızca veritabanı işi yapılır.

Site yoksa oluşturulur. Kelime zaten varsa keyword_geo yenilenir.

Kullanım:
    python tools/keyword_ekle.py --site ornek.com --kelime "veteriner" --kapsam national
    python tools/keyword_ekle.py --site ornek.com --kelime "veteriner" --kapsam province --il 34
    python tools/keyword_ekle.py --kelime "veteriner" --sil
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "tools"))

from db import baglan  # noqa: E402

from worker import tier  # noqa: E402


def _site_id(imlec, domain: str) -> int:
    """Siteyi bulur, yoksa oluşturur."""
    imlec.execute("SELECT id FROM site WHERE domain=%s", (domain,))
    satir = imlec.fetchone()
    if satir:
        return satir[0]
    imlec.execute("INSERT INTO site (domain, label) VALUES (%s, %s)", (domain, domain))
    return imlec.lastrowid


def ekle(domain: str, kelime: str, kapsam: str, il: int | None) -> int:
    """Kelimeyi ve keyword_geo satırlarını yazar. Satır sayısını döndürür."""
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT code FROM geo ORDER BY weight DESC, code ASC"
            )
            kodlar = [s[0] for s in imlec.fetchall()]

            ciftler = tier.dagitim(kodlar, kapsam, il)

            site = _site_id(imlec, domain)
            imlec.execute(
                "INSERT INTO keyword (site_id, text, geo_scope, home_geo) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE geo_scope=VALUES(geo_scope), "
                "home_geo=VALUES(home_geo), state='idle'",
                (site, kelime, kapsam, il),
            )
            imlec.execute("SELECT id FROM keyword WHERE site_id=%s AND text=%s",
                          (site, kelime))
            kelime_id = imlec.fetchone()[0]

            # Yeniden eklemede eski dağılım kalmasın diye önce silinir.
            imlec.execute("DELETE FROM keyword_geo WHERE keyword_id=%s", (kelime_id,))
            imlec.executemany(
                "INSERT INTO keyword_geo (keyword_id, geo_code, tier) "
                "VALUES (%s, %s, %s)",
                [(kelime_id, kod, etiket) for kod, etiket in ciftler],
            )
        return len(ciftler)
    finally:
        baglanti.close()


def sil(kelime: str) -> int:
    """Kelimeyi ve bağlı satırları siler. Silinen kelime sayısını döndürür."""
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("DELETE FROM keyword WHERE text=%s", (kelime,))
            return imlec.rowcount
    finally:
        baglanti.close()


def main() -> int:
    """Komut satırını işler."""
    ayar = argparse.ArgumentParser(description="Kelime ekle")
    ayar.add_argument("--site", help="alan adı")
    ayar.add_argument("--kelime", required=True)
    ayar.add_argument("--kapsam", default="national",
                      choices=["national", "province"])
    ayar.add_argument("--il", type=int, help="province kapsamında il kodu")
    ayar.add_argument("--sil", action="store_true")
    secim = ayar.parse_args()

    if secim.sil:
        print(f"silinen kelime: {sil(secim.kelime)}")
        return 0

    if not secim.site:
        print("HATA: --site zorunlu.")
        return 1

    try:
        adet = ekle(secim.site, secim.kelime, secim.kapsam, secim.il)
    except ValueError as hata:
        print(f"HATA: {hata}")
        return 1
    print(f"eklendi: {adet} keyword_geo satırı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())