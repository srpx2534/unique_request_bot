"""Zarif boşaltma testleri (E4).

Sinyal gelince yeni istek 503 + Retry-After ile reddedilir, uçan istek
bitene kadar sunucu kapanmaz, ikinci sinyal zorla çıkar. Ağa ve
veritabanına çıkmaz; burst ve kalp sahte.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from worker import app


@pytest.fixture()
def sunucu(monkeypatch):
    """Gerçek sunucu, sahte burst; boşaltma durumu her testte sıfırlanır."""
    monkeypatch.setattr(app, "TOKEN", "test-token")
    monkeypatch.setattr(app.kalp, "duraklatildi", lambda: False)
    app._bosaltiliyor.clear()
    app._ucan = 0
    s = ThreadingHTTPServer(("127.0.0.1", 0), app.Isleyici)
    app._SUNUCU = s
    islec = threading.Thread(target=s.serve_forever, daemon=True)
    islec.start()
    yield s
    if islec.is_alive():
        s.shutdown()
    s.server_close()
    app._SUNUCU = None
    app._bosaltiliyor.clear()
    app._ucan = 0


def _govde(**ek):
    g = {"keyword": "test", "target_url": "https://ornek.test", "ts": int(time.time())}
    g.update(ek)
    return json.dumps(g).encode("utf-8")


def _gonder(s, ham):
    imza = hmac.new(b"test-token", ham, hashlib.sha256).hexdigest()
    istek = urllib.request.Request(
        f"http://127.0.0.1:{s.server_address[1]}/worker/burst",
        data=ham, method="POST",
        headers={"Authorization": "Bearer test-token", "x-imza": imza,
                 "Content-Type": "application/json"},
    )
    return urllib.request.urlopen(istek, timeout=10)


def test_bosaltmada_503_ve_retry_after(sunucu):
    """Boşaltma bayrağı açıkken istek alınmaz, 30 saniye sonra denenir."""
    app._bosaltiliyor.set()
    with pytest.raises(urllib.error.HTTPError) as hata:
        _gonder(sunucu, _govde())
    assert hata.value.code == 503
    assert hata.value.headers.get("Retry-After") == "30"


def test_bosaltma_yokken_normal(monkeypatch, sunucu):
    """Bayrak kapalıyken burst normal işler ve sayaç sıfıra döner."""
    monkeypatch.setattr(app.burst, "burst_yap", lambda *a, **k: {
        "ok": 1, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0,
        "elapsed_ms": 1, "hits": [], "durduruldu": False})
    with _gonder(sunucu, _govde()) as yanit:
        assert yanit.status == 200
    for _ in range(50):
        if app._ucan == 0:
            break
        time.sleep(0.02)
    assert app._ucan == 0


def test_ucan_varken_kapanmaz(monkeypatch):
    """Uçan istek sürerken sunucu kapatılmaz; sayaç sıfırlanınca kapatılır."""
    kapandi = threading.Event()

    class Sahte:
        def shutdown(self):
            kapandi.set()

    monkeypatch.setattr(app, "_SUNUCU", Sahte())
    app._ucan = 1
    threading.Thread(target=app._bosalt_ve_kapat, daemon=True).start()
    time.sleep(0.4)
    assert not kapandi.is_set()
    app._ucan = 0
    assert kapandi.wait(3)


def test_sinyal_bosaltmayi_baslatir(monkeypatch):
    """İlk sinyal bayrağı açar ve bekleme işini başlatır."""
    cagrildi = threading.Event()
    monkeypatch.setattr(app, "_bosalt_ve_kapat", lambda: cagrildi.set())
    app._bosaltiliyor.clear()
    try:
        app._sinyal(15, None)
        assert app._bosaltiliyor.is_set()
        assert cagrildi.wait(2)
    finally:
        app._bosaltiliyor.clear()
