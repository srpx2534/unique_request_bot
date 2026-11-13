"""Worker HTTP servisi.

Control plane bu servise burst gönderir. Worker durumsuzdur ve veritabanına
yazmaz; sonucu JSON olarak döndürür (§3). Endpoint paylaşılan token ile
kimlik doğrular, dışarıya kapalıdır.

Eşzamanlılık sunucu başına 12 ile sınırlıdır (§9); fazlası semafor
kuyruğunda bekler, istek düşmez.

Uçlar:
    GET  /health          → 200 {"durum":"ayakta"}
    GET  /durum           → 200 {"sayac", "saglayici"}
    POST /worker/burst    → 200 {"ok","captcha","not_found","timeout","elapsed_ms"}

Kullanım: python -m worker.app
"""

from __future__ import annotations

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from worker import ayar, burst, havuz

ESZAMANLI = 12  # eşzamanlı burst sınırı (§9)
GOVDE_TAVANI = 8_192  # bayt; burst gövdesi küçüktür, büyüğü reddedilir

TOKEN = ayar.oku("WORKER_TOKEN")
PORT = int(ayar.oku("WORKER_PORT", "8081"))
_semafor = threading.BoundedSemaphore(ESZAMANLI)

# Süreç ömrü boyunca biriken sayaçlar. Panel buradan nabız okur.
_sayac = {"burst": 0, "ok": 0, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0}
_kilit = threading.Lock()


class Isleyici(BaseHTTPRequestHandler):
    """Tek isteği karşılar."""

    server_version = "unique_request_bot"

    def log_message(self, bicim: str, *args) -> None:
        """Varsayılan gürültülü günlüğü tek satıra indirir."""
        print(f"{self.address_string()} {bicim % args}")

    def _json(self, kod: int, govde: dict) -> None:
        """JSON yanıt yazar."""
        ham = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(ham)))
        self.end_headers()
        self.wfile.write(ham)

    def _yetkili(self) -> bool:
        """Bearer token doğrular. Sabit süreli karşılaştırma kullanılır."""
        gelen = self.headers.get("Authorization", "")
        if not gelen.startswith("Bearer "):
            return False
        return hmac.compare_digest(gelen[7:].strip(), TOKEN)

    def _govde_oku(self) -> dict | None:
        """Gövdeyi okur ve JSON çözer. Bozuksa None döner."""
        uzunluk = int(self.headers.get("Content-Length", "0"))
        if uzunluk <= 0 or uzunluk > GOVDE_TAVANI:
            return None
        try:
            return json.loads(self.rfile.read(uzunluk).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def do_GET(self) -> None:  # noqa: N802 (stdlib adlandırması)
        """Sağlık ucu."""
        yol = self.path.split("?")[0]
        if yol == "/health":
            self._json(200, {"durum": "ayakta"})
            return
        if yol == "/durum":
            self._durum()
            return
        self._json(404, {"hata": "bilinmeyen uç"})

    def _durum(self) -> None:
        """Sayaçları ve sağlayıcı durumlarını döndürür."""
        with _kilit:
            sayac = dict(_sayac)
        self._json(200, {"sayac": sayac, "saglayici": havuz.durum_sayaci()})

    def do_POST(self) -> None:  # noqa: N802 (stdlib adlandırması)
        """/worker/burst ucunu işler."""
        if self.path.split("?")[0] != "/worker/burst":
            self._json(404, {"hata": "bilinmeyen uç"})
            return
        if not self._yetkili():
            self._json(401, {"hata": "token geçersiz"})
            return

        govde = self._govde_oku()
        if govde is None:
            self._json(400, {"hata": "gövde okunamadı"})
            return

        kelime = str(govde.get("keyword", "")).strip()
        hedef = govde.get("target_url") or govde.get("target_domain")
        if not kelime or not hedef:
            self._json(400, {"hata": "keyword ve target_url/target_domain zorunlu"})
            return

        adet = int(govde.get("size", 1))
        uule = govde.get("uule")
        # İl slug'ı adresten ya da plaka kodundan çözülür; yoksa ulusal kalır.
        geo_slug = govde.get("geo_slug")
        if not geo_slug and govde.get("geo_code"):
            geo_slug = havuz.slug_bul(int(govde["geo_code"]))
        # target_url verilmişse domain türetilir, çözüm için API'ye gidilmez.
        hedef_url = govde.get("target_url")
        domain = govde.get("target_domain") or ""

        with _semafor:
            sonuc = burst.burst_yap(
                kelime, domain, adet, uule=uule, hedef_url=hedef_url, geo_slug=geo_slug
            )

        with _kilit:
            _sayac["burst"] += 1
            for anahtar in ("ok", "captcha", "not_found", "timeout", "error"):
                _sayac[anahtar] += sonuc[anahtar]

        self._json(200, {
            "geo_mode": havuz.son_mod, "ok": sonuc["ok"],
            "captcha": sonuc["captcha"],
            "not_found": sonuc["not_found"],
            "timeout": sonuc["timeout"],
            "error": sonuc["error"],
            "elapsed_ms": sonuc["elapsed_ms"],
        })


def main() -> int:
    """Servisi başlatır. Token boşsa çalışmaz."""
    if not TOKEN:
        print("HATA: .env içinde WORKER_TOKEN boş.")
        return 1
    sunucu = ThreadingHTTPServer(("0.0.0.0", PORT), Isleyici)
    print(f"worker dinliyor: 0.0.0.0:{PORT} · eşzamanlı sınır {ESZAMANLI}")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("kapatılıyor.")
    finally:
        sunucu.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())