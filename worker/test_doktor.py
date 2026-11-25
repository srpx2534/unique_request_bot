"""Doktor karar testleri."""

from worker import doktor

SAGLIKLI = {"webdriver": False, "chrome": True, "webgl": "ANGLE (NVIDIA)", 
            "genislik": 1920, "yukseklik": 1080, "diller": ["tr-TR", "tr"]}


def test_saglikli_makine_sorunsuz():
    assert doktor.karar(SAGLIKLI) == []


def test_webdriver_yakalanir():
    assert "navigator.webdriver acik" in doktor.karar({**SAGLIKLI, "webdriver": True})


def test_chrome_yoklugu_yakalanir():
    assert "window.chrome yok" in doktor.karar({**SAGLIKLI, "chrome": False})


def test_webgl_yoklugu_yakalanir():
    assert "webgl yok" in doktor.karar({**SAGLIKLI, "webgl": ""})


def test_dar_ekran_yakalanir():
    sorunlar = doktor.karar({**SAGLIKLI, "genislik": 800, "yukseklik": 600})
    assert any("ekran dar" in s for s in sorunlar)


def test_turkce_dil_yoklugu_yakalanir():
    assert "diller arasinda tr yok" in doktor.karar({**SAGLIKLI, "diller": ["en-US"]})


def test_bos_veri_sorun_dondurur():
    assert len(doktor.karar({})) == 4