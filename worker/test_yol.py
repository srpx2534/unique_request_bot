"""Yol disiplini lint'inin temiz gectigini dogrular.

Lint ayri bir surecte kosar; boylece hem burada hem CI'da ayni kural gecer.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]


def test_yol_lint_temiz() -> None:
    sonuc = subprocess.run(
        [sys.executable, str(KOK / "tools" / "lint_yol.py")],
        capture_output=True,
        text=True,
    )
    assert sonuc.returncode == 0, sonuc.stdout + sonuc.stderr