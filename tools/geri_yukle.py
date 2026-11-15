"""Yedekten geri yukler.

`mysql` istemcisiyle dosyayi akitir; onay ister. Sifre komut satirinda
gorunmesin diye kimlik gecici secenek dosyasindan verilir (17.6).

Kullanim:
    python tools/geri_yukle.py veri/yedek/20260101-030000.sql
    python tools/geri_yukle.py veri/yedek/20260101-030000.sql --evet
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
VARSAYILAN_ARAC = r"C:\xampp\mysql\bin\mysql.exe"


def _env(anahtar: str, varsayilan: str = "") -> str:
    """.env dosyasindan tek deger okur; yoksa ortam degiskenine duser."""
    deger = os.environ.get(anahtar, "")
    if deger:
        return deger
    env_yolu = KOK / ".env"
    if not env_yolu.exists():
        return varsayilan
    for satir in env_yolu.read_text(encoding="utf-8-sig").splitlines():
        if satir.startswith(f"{anahtar}="):
            return satir.split("=", 1)[1].strip()
    return varsayilan


def main() -> int:
    """Yedegi geri yukler. Basarisizsa 1 doner."""
    ayar = argparse.ArgumentParser(description="Yedekten geri yukle")
    ayar.add_argument("dosya", help="geri yuklenecek .sql dosyasi")
    ayar.add_argument("--evet", action="store_true", help="onay sormadan uygula")
    secim = ayar.parse_args()

    kaynak = Path(secim.dosya)
    if not kaynak.exists():
        print(f"HATA: dosya yok: {kaynak}")
        return 1
    if not secim.evet:
        print(f"{kaynak.name} mevcut veritabaninin uzerine yazilacak. Devam? [e/H]")
        if input().strip().lower() not in ("e", "evet", "y"):
            print("vazgecildi")
            return 1

    arac = Path(_env("MYSQL", VARSAYILAN_ARAC))
    if not arac.exists():
        print(f"HATA: mysql istemcisi yok: {arac}")
        return 1

    # Geri yukleme root ile yapilir: dump'taki görünümler DEFINER=root taşır,
    # `request` kullanıcısında SUPER yetkisi yok ve 1227 alınıyordu.
    root_sifre = _env("MYSQL_ROOT_PASSWORD")
    kullanici = "root" if root_sifre else _env("MYSQL_USER", "request")
    sifre = root_sifre or _env("MYSQL_PASSWORD")
    icerik = (
        "[client]\n"
        f"user={kullanici}\n"
        f"password={sifre}\n"
        f"host={_env('MYSQL_HOST', '127.0.0.1')}\n"
        f"port={_env('MYSQL_PORT', '3306')}\n"
    )}\n"
        f"password={_env('MYSQL_PASSWORD')}\n"
        f"host={_env('MYSQL_HOST', '127.0.0.1')}\n"
        f"port={_env('MYSQL_PORT', '3306')}\n"
    )
    tanitici, yol = tempfile.mkstemp(prefix="geri-", suffix=".cnf")
    os.close(tanitici)
    secenek = Path(yol)
    secenek.write_text(icerik, encoding="utf-8")
    try:
        with kaynak.open("rb") as girdi:
            sonuc = subprocess.run(
                [str(arac), f"--defaults-extra-file={secenek}",
                 _env("MYSQL_DATABASE", "unique_request_bot")],
                stdin=girdi, stderr=subprocess.PIPE, shell=False,
            )
    finally:
        secenek.unlink(missing_ok=True)
    if sonuc.returncode != 0:
        print(f"HATA: mysql {sonuc.returncode}: {sonuc.stderr.decode()[:200]}")
        return 1
    print("geri yuklendi")
    return 0


if __name__ == "__main__":
    sys.exit(main())