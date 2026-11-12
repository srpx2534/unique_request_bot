"""Proxy parametresinin gerçekten kullanıldığını kanıtlar.

Yerel bir TCP dinleyici açar ve tıklamayı o adrese proxy olarak yönlendirir.
HTTPS hedefe giderken curl önce CONNECT gönderir; dinleyici bu satırı
yakalarsa proxy yolu çalışıyor demektir. Ağ ve sağlayıcı gerekmez, bu
yüzden CI'da da koşabilir.

Kullanım:
    python tools/proxy_kanit.py
"""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from worker import click  # noqa: E402

PORT = 18999  # sabit; çakışma olasılığı düşük
BEKLENEN = "CONNECT"


def dinle(kutu: list[str]) -> None:
    """Tek bağlantı kabul eder ve ilk satırı kutuya yazar."""
    sunucu = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sunucu.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sunucu.bind(("127.0.0.1", PORT))
    sunucu.listen(1)
    sunucu.settimeout(20)
    try:
        istemci, _ = sunucu.accept()
        kutu.append(istemci.recv(2048).decode("latin-1", "replace"))
        # Gövde göndermeden kapatıyoruz: 502 dönmesi yeter, kanıt CONNECT.
        istemci.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
        istemci.close()
    except Exception as hata:  # noqa: BLE001
        kutu.append(f"HATA {hata}")
    finally:
        sunucu.close()


def main() -> int:
    """Kanıtı çalıştırır. CONNECT görülmezse 1 döner."""
    kutu: list[str] = []
    is_parcasi = threading.Thread(target=dinle, args=(kutu,), daemon=True)
    is_parcasi.start()

    sonuc = click.tikla(
        "https://example.com/", proxy=f"http://127.0.0.1:{PORT}", dwell=False
    )
    is_parcasi.join(timeout=25)

    print(f"tik sonucu: {sonuc['result']} · {sonuc['mesaj'][:80]}")
    if not kutu:
        print("HATA: proxy'ye hiç bağlanılmadı.")
        return 1

    ilk = kutu[0].splitlines()[0] if kutu[0].splitlines() else kutu[0]
    print(f"proxy'ye gelen ilk satır: {ilk[:120]}")
    if BEKLENEN in ilk:
        print("KANIT: proxy parametresi kullanılıyor.")
        return 0
    print("HATA: CONNECT görülmedi.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())