"""Yedek saklama suresi testleri.

Dosya sistemi ve saat sahte; mysqldump cagrilmaz.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tools import yedek


def _dosya(dizin: Path, ad: str, gun_once: int) -> Path:
    yol = dizin / ad
    yol.write_text("-- yedek", encoding="utf-8")
    zaman = (datetime.now(UTC) - timedelta(days=gun_once)).timestamp()
    os.utime(yol, (zaman, zaman))
    return yol


def test_eski_yedekler_silinir(tmp_path) -> None:
    eski = _dosya(tmp_path, "eski.sql", 9)
    taze = _dosya(tmp_path, "taze.sql", 1)

    silinen = yedek.eskileri_sil(tmp_path, 7)

    assert silinen == [eski]
    assert not eski.exists()
    assert taze.exists()


def test_tut_sifirsa_hepsi_silinir(tmp_path) -> None:
    _dosya(tmp_path, "a.sql", 1)
    _dosya(tmp_path, "b.sql", 2)

    assert len(yedek.eskileri_sil(tmp_path, 0)) == 2


def test_sql_disi_dosyaya_dokunulmaz(tmp_path) -> None:
    diger = tmp_path / "not.txt"
    diger.write_text("x", encoding="utf-8")
    zaman = (datetime.now(UTC) - timedelta(days=30)).timestamp()
    os.utime(diger, (zaman, zaman))

    assert yedek.eskileri_sil(tmp_path, 7) == []
    assert diger.exists()