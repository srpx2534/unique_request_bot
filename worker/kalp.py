"""Kalp atışı.

Panelin sunucuyu canlı görebilmesi için on beş saniyede bir durum bildirir:
yük, cpu, ram, sürüm. Panel cevabındaki `durum` "durduruldu" ise worker yeni
iş almaz; kalp atmaya devam eder, böylece panelden tekrar açılabilir.

CPU yüzdesi psutil'de ilk çağrıda 0 döner; bu yüzden açılışta bir kez
ısıtılır, sonra ölçüm anlık okunur. psutil yoksa cpu/ram sıfır kalır.
"""

from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request

from worker import ayar

ARALIK_SN = 15
SURUM = "0.1.0"

yuk_kaynagi = lambda: 0  # app.py gerçek doluluk sayacını bağlar
_durum = "aktif"
_zaman: threading.Timer | None = None
_psutil = None


def _ip() -> str:
    """Düğümün yerel IP'sini bulur; bulunamazsa 127.0.0.1 döner."""
    tanimli = ayar.oku("DUGUM_IP")
    if tanimli:
        return tanimli
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _kaynak() -> tuple[float, float]:
    """CPU ve RAM yüzdesini verir; psutil yoksa sıfır döner."""
    if _psutil is None:
        return 0.0, 0.0
    try:
        return _psutil.cpu_percent(interval=0.3), _psutil.virtual_memory().percent
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def duraklatildi() -> bool:
    """Panel düğümü durdurdu mu."""
    return _durum == "durduruldu"


def _at() -> None:
    """Tek kalp gönderir ve cevabı işler."""
    global _durum, _zaman

    cpu, ram = _kaynak()
    govde = json.dumps(
        {"ip": _ip(), "yuk": yuk_kaynagi(), "cpu": cpu, "ram": ram, "surum": SURUM}
    ).encode("utf-8")
    adres = ayar.oku("PANEL_ADRES", "http://127.0.0.1:8080") + "/api/worker/kalp"
    istek = urllib.request.Request(
        adres, data=govde, headers={"content-type": "application/json"}
    )
    try:
        with urllib.request.urlopen(istek, timeout=8) as yanit:
            _durum = json.loads(yanit.read().decode("utf-8")).get("durum", "aktif")
    except urllib.error.HTTPError as hata:
        if hata.code == 404:
            print("[kalp] düğüm kayıtlı değil, Sunucular ekranından ekle")
    except Exception as hata:  # noqa: BLE001
        print(f"[kalp] gönderilemedi: {hata}")

    _zaman = threading.Timer(ARALIK_SN, _at)
    _zaman.daemon = True
    _zaman.start()


def baslat() -> None:
    """Kalp döngüsünü başlatır; CPU ölçümünü ısıtır."""
    global _psutil
    try:
        import psutil  # type: ignore[import-not-found]

        psutil.cpu_percent(interval=None)  # ilk ölçüm referansı
        _psutil = psutil
    except Exception:  # noqa: BLE001
        print("[kalp] psutil yok, cpu/ram 0 kalacak")

    print(f"[kalp] başladı: {_ip()}")
    _at()


def durdur() -> None:
    """Döngüyü kapatır."""
    if _zaman:
        _zaman.cancel()