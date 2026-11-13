"""Serbest proxy listesini havuza aktarır.

Girdi, proxy sağlayıcılarının verdiği JSON dizisidir: her satırda
`proxy`, `ip`, `port` ve `geolocation.country` bulunur. Ülke kodu iki
harfli değilse `ZZ` yazılır.

Kayıtlar `datacenter` olarak girer ve ağırlığı 1'dir; havuz sırasında
TR olanlar öne geçer, yabancılar son çare kalır.

Kullanım:
    python tools/proxy_ice.py --dosya veri/serbest.json
    python tools/proxy_ice.py --dosya veri/serbest.json --kuru
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from tools.db import baglan


def _ulke(satir: dict) -> str:
    """Ülke kodunu iki harfe indirger, geçersizse ZZ döndürür."""
    kod = str(satir.get("geolocation", {}).get("country", "")).upper()
    return kod if len(kod) == 2 else "ZZ"


def main() -> int:
    """Listeyi okur ve tek işlemde yazar."""
    ayar = argparse.ArgumentParser(description="Serbest proxy listesi aktar")
    ayar.add_argument("--dosya", required=True, help="JSON liste dosyası")
    ayar.add_argument("--kuru", action="store_true", help="yazmadan say")
    arg = ayar.parse_args()

    ham = Path(arg.dosya).read_text(encoding="utf-8-sig").strip()
    if not ham:
        print(f"dosya boş: {arg.dosya}")
        return 1
    try:
        veri = json.loads(ham)
    except json.JSONDecodeError as hata:
        bas = max(0, hata.pos - 60)
        print(f"JSON bozuk: satır {hata.lineno}, kolon {hata.colno} — {hata.msg}")
        print(f"civar: ...{ham[bas:hata.pos + 60]}...")
        return 1
    satirlar = veri.get("proxies") or veri.get("data") if isinstance(veri, dict) else veri
    if not isinstance(satirlar, list):
        print("beklenen biçim: proxy dizisi ya da {proxies: [...]}")
        return 1
    baglanti = baglan()
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT gateway FROM provider")
            mevcut = {s[0] for s in imlec.fetchall()}
            imlec.execute("SELECT COALESCE(MAX(id), 0) FROM provider")
            son = imlec.fetchone()[0]

            eklenecek = []
            for satir in satirlar:
                ip = satir.get("ip")
                port = satir.get("port")
                if not ip or not port:
                    continue
                gateway = f"{ip}:{port}"
                if gateway in mevcut:
                    continue
                mevcut.add(gateway)
                son += 1
                eklenecek.append(
                    (son, f"serbest-{gateway}", "datacenter", _ulke(satir), gateway)
                )

            if arg.kuru:
                for kayit in eklenecek[:10]:
                    print(kayit)
                print(f"eklenecek: {len(eklenecek)}")
                return 0

            imlec.executemany(
                "INSERT INTO provider (id, name, kind, ulke, gateway, weight) "
                "VALUES (%s, %s, %s, %s, %s, 1)",
                eklenecek,
            )
        baglanti.commit()
        print(f"eklendi: {len(eklenecek)}")
        return 0
    finally:
        baglanti.close()


if __name__ == "__main__":
    raise SystemExit(main())