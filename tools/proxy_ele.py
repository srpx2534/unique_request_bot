"""Ölü proxy'leri ayıklar.

Her aktif proxy'ye paralel olarak kısa bir istek atılır. Cevap gelmezse
kayıt `disabled` yapılır, böylece havuz seçicisi ölü IP'ye iş atmaz.
Google 204 ucu kullanılır: gövde indirmez, hızlıdır ve gerçek hedefe
benzer bir yol izler.

Kullanım:
    python tools/proxy_ele.py
    python tools/proxy_ele.py --paralel 16 --zaman-asimi 6
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from curl_cffi import requests as istek  # noqa: E402
from tools.db import baglan  # noqa: E402

TEST_URL = "https://www.google.com/generate_204"
GECERLI = {200, 204, 301, 302}


def dene(gateway: str, zaman_asimi: int) -> bool:
    """Proxy üzerinden test adresine gider; geçerli durum kodu arar."""
    try:
        yanit = istek.get(
            TEST_URL,
            proxies={"https": f"http://{gateway}"},
            impersonate="chrome",
            timeout=zaman_asimi,
        )
        return yanit.status_code in GECERLI
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    """Tüm aktif proxy'leri dener ve ölüleri kapatır."""
    ayar = argparse.ArgumentParser(description="Ölü proxy ayıkla")
    ayar.add_argument("--paralel", type=int, default=12)
    ayar.add_argument("--zaman-asimi", type=int, default=8)
    arg = ayar.parse_args()

    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute(
                "SELECT id, gateway FROM provider "
                "WHERE state = 'active' AND gateway IS NOT NULL"
            )
            adaylar = imlec.fetchall()
    finally:
        baglanti.close()

    if not adaylar:
        print("denenecek proxy yok")
        return 0

    print(f"deneniyor: {len(adaylar)}")
    with ThreadPoolExecutor(max_workers=arg.paralel) as havuz:
        sonuclar = list(havuz.map(lambda s: (s[0], dene(s[1], arg.zaman_asimi)), adaylar))

    canli = [i for i, ok in sonuclar if ok]
    olu = [i for i, ok in sonuclar if not ok]

    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            if olu:
                imlec.executemany(
                    "UPDATE provider SET state = 'disabled' WHERE id = %s",
                    [(i,) for i in olu],
                )
        baglanti.commit()
    finally:
        baglanti.close()

    print(f"canlı: {len(canli)} · ölü: {len(olu)} (kapatıldı)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())