"""Yol ve platform disiplini lint'i (§20, C29).

Sabit yol, os.sep, os.system, fcntl, shell=True ve naive saat kullanimini yakalar.
Hepsi Windows'ta calisip Linux'ta kirilan kaliplardir.

Kullanim: python tools/lint_yol.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
ATLANAN = {"docs", "node_modules", ".venv", "dist", ".git", "db"}
UZANTI = {".py", ".ts", ".tsx"}
# Kural tanimlari kendi dosyasinda geciyor; kendini taramaz.
ATLANAN_DOSYA = {"tools/lint_yol.py"}

KURALLAR = (
    (re.compile(r"C:\\\\|C:/"), "sabit Windows yolu"),
    (re.compile(r'"/home/|"/Users/'), "sabit POSIX yolu"),
    (re.compile(r"\bos\.sep\b"), "os.sep kullanimi"),
    (re.compile(r"\bos\.system\("), "os.system kullanimi"),
    (re.compile(r"\bos\.fork\("), "os.fork kullanimi"),
    (re.compile(r"\bfcntl\."), "fcntl kullanimi"),
    (re.compile(r"datetime\.now\(\)"), "naive datetime.now()"),
    (re.compile(r"datetime\.utcnow\(\)"), "naive datetime.utcnow()"),
    (re.compile(r"shell\s*=\s*True"), "shell=True"),
    (re.compile(r'\+\s*"/"\s*\+'), "elle / birlestirme"),
)

# Yorum satirlari ve doküman metni kuraldan muaftir.
YORUM = re.compile(r"^\s*(#|//|\*|--)")


def dosyalar() -> list[Path]:
    """Taranacak kaynak dosyalari toplar."""
    bulunan: list[Path] = []
    for yol in KOK.rglob("*"):
        if not yol.is_file() or yol.suffix not in UZANTI:
            continue
        if any(parca in ATLANAN for parca in yol.relative_to(KOK).parts):
            continue
        if yol.relative_to(KOK).as_posix() in ATLANAN_DOSYA:
            continue
        bulunan.append(yol)
    return bulunan


def main() -> int:
    """Ihlalleri yazar. Ihlal varsa 1 doner."""
    ihlal = 0
    for yol in dosyalar():
        for numara, satir in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
            if YORUM.match(satir):
                continue
            for desen, ad in KURALLAR:
                if desen.search(satir):
                    goreli = yol.relative_to(KOK)
                    print(f"{goreli}:{numara} · {ad} · {satir.strip()[:90]}")
                    ihlal += 1
    print(f"ihlal: {ihlal}")
    return 1 if ihlal else 0


if __name__ == "__main__":
    sys.exit(main())