"""Veritabanini mysqldump ile yedekler.

Yedek `veri/yedek` altina UTC damgasiyla yazilir; 7 gunden eski dosyalar
silinir (17.6). Sifre komut satirinda gorunmesin diye kimlik gecici bir
secenek dosyasindan verilir, islem bitince dosya silinir.

Kullanim:
    python tools/yedek.py
    python tools/yedek.py --tut 14
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
YEDEK_DIZINI = KOK / "veri" / "yedek"
VARSAYILAN_TUT = 7  # gun; sozlesme 17.6
VARSAYILAN_ARAC = r"C:\xampp\mysql\bin\mysqldump.exe"


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


def _secenek_dosyasi() -> Path:
    """Kimligi tasiyan gecici mysqldump secenek dosyasini yazar."""
    icerik = (
        "[client]\n"
        f"user={_env('MYSQL_USER', 'request')}\n"
        f"password={_env('MYSQL_PASSWORD')}\n"
        f"host={_env('MYSQL_HOST', '127.0.0.1')}\n"
        f"port={_env('MYSQL_PORT', '3306')}\n"
    )
    tanitici, yol = tempfile.mkstemp(prefix="yedek-", suffix=".cnf")
    os.close(tanitici)
    dosya = Path(yol)
    dosya.write_text(icerik, encoding="utf-8")
    return dosya


def eskileri_sil(dizin: Path, tut: int, simdi: datetime | None = None) -> list[Path]:
    """`tut` gunden eski yedekleri siler ve silinenleri dondurur.

    Args:
        dizin: Yedek klasoru.
        tut: Kac gun saklanacagi.
        simdi: Test icin sabitlenebilir zaman.

    Returns:
        Silinen dosya yollari.
    """
    sinir = (simdi or datetime.now(UTC)) - timedelta(days=tut)
    silinen: list[Path] = []
    for dosya in sorted(dizin.glob("*.sql")):
        if datetime.fromtimestamp(dosya.stat().st_mtime, UTC) < sinir:
            dosya.unlink()
            silinen.append(dosya)
    return silinen


def main() -> int:
    """Yedegi alir. Basarisizsa 1 doner."""
    ayar = argparse.ArgumentParser(description="Veritabani yedegi al")
    ayar.add_argument("--tut", type=int, default=VARSAYILAN_TUT)
    secim = ayar.parse_args()

    arac = Path(_env("MYSQLDUMP", VARSAYILAN_ARAC))
    if not arac.exists():
        print(f"HATA: mysqldump yok: {arac}")
        return 1

    YEDEK_DIZINI.mkdir(parents=True, exist_ok=True)
    hedef = YEDEK_DIZINI / f"{datetime.now(UTC):%Y%m%d-%H%M%S}.sql"
    secenek = _secenek_dosyasi()
    try:
        komut = [
            str(arac),
            f"--defaults-extra-file={secenek}",
            "--single-transaction",
            "--quick",
            "--no-tablespaces",
            "--routines",
            _env("MYSQL_DATABASE", "unique_request_bot"),
        ]
        with hedef.open("wb") as cikti:
            sonuc = subprocess.run(komut, stdout=cikti, stderr=subprocess.PIPE, shell=False)
        if sonuc.returncode != 0:
            print(f"HATA: mysqldump {sonuc.returncode}: {sonuc.stderr.decode()[:200]}")
            hedef.unlink(missing_ok=True)
            return 1
    finally:
        secenek.unlink(missing_ok=True)

    for dosya in eskileri_sil(YEDEK_DIZINI, secim.tut):
        print(f"silindi: {dosya.name}")
    print(f"yedek: {hedef} ({hedef.stat().st_size} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())