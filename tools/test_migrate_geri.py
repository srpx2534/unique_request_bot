"""Geri alma planı testleri (E5).

Veritabanına çıkmaz: plan saf hesaplanır, dosya varlığı geçici dizinle
kurulur. Sıra, ret ve adet sınırı kilitlenir.
"""

from __future__ import annotations

from pathlib import Path

from geri_plan import geri_dosyasi, geri_plani


def _dizin(tmp_path: Path, adlar: list[str]) -> Path:
    """Verilen adlar için boş geri dosyaları kurar."""
    for ad in adlar:
        geri_dosyasi(tmp_path, ad).write_text("SELECT 1;\n", encoding="utf-8")
    return tmp_path


def test_en_yeniden_eskiye_siralar(tmp_path: Path) -> None:
    """Adımlar ters sırada üretilir; en yeni önce geri alınır."""
    d = _dizin(tmp_path, ["045_a.sql", "046_b.sql"])
    adimlar, hatalar = geri_plani({"045_a.sql", "046_b.sql"}, 2, d)
    assert hatalar == []
    assert [a["ad"] for a in adimlar] == ["046_b.sql", "045_a.sql"]


def test_adet_kadar_geri_alir(tmp_path: Path) -> None:
    """Adet, defterin tamamından fazlaysa ret; kadarsa yalnız o kadarı."""
    adlar = ["043_a.sql", "044_b.sql", "045_c.sql", "046_d.sql"]
    d = _dizin(tmp_path, adlar)
    adimlar, _ = geri_plani(set(adlar), 1, d)
    assert [a["ad"] for a in adimlar] == ["046_d.sql"]
    _, hatalar = geri_plani(set(adlar), 9, d)
    assert hatalar


def test_geri_dosyasi_yoksa_ret(tmp_path: Path) -> None:
    """Eksik geri dosyası planı engeller ve adı söyler."""
    d = _dizin(tmp_path, ["046_b.sql"])
    adimlar, hatalar = geri_plani({"045_a.sql", "046_b.sql"}, 2, d)
    assert adimlar == []
    assert any("045_a.sql" in h for h in hatalar)


def test_sifir_adet_ret(tmp_path: Path) -> None:
    """Sıfır ve negatif adet ret edilir."""
    d = _dizin(tmp_path, ["046_b.sql"])
    for adet in (0, -3):
        _, hatalar = geri_plani({"046_b.sql"}, adet, d)
        assert hatalar


def test_bos_defter_ret(tmp_path: Path) -> None:
    """Defter boşken geri alınacak bir şey yoktur."""
    _, hatalar = geri_plani(set(), 1, tmp_path)
    assert hatalar


def test_dosya_adi_turetme(tmp_path: Path) -> None:
    """Geri dosyası adı `.sql` yerine `.down.sql` taşır."""
    assert geri_dosyasi(tmp_path, "046_x.sql").name == "046_x.down.sql"
    assert geri_dosyasi(tmp_path, "046_x").name == "046_x.down.sql"


def test_bos_geri_dosyasi_ret(tmp_path: Path) -> None:
    """Yalnız yorum taşıyan geri dosyası planı engeller."""
    geri_dosyasi(tmp_path, "046_b.sql").write_text("-- sadece yorum\n", encoding="utf-8")
    adimlar, hatalar = geri_plani({"046_b.sql"}, 1, tmp_path)
    assert adimlar == []
    assert any("046_b.sql" in h for h in hatalar)
