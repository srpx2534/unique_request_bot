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
                   → 503 {"hata":"boşaltılıyor"} + Retry-After: 30 (boşaltma)


Kullanım: python -m worker.app
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from worker import ayar, burst, durum, kalp, havuz, olcum_b

ESZAMANLI = 12  # eşzamanlı burst sınırı (§9)
GOVDE_TAVANI = 8_192  # bayt; burst gövdesi küçüktür, büyüğü reddedilir
PENCERE_SN = 120  # imza tekrar penceresi; ts bu kadar sapabilir

TOKEN = ayar.oku("WORKER_TOKEN")
PORT = int(ayar.oku("WORKER_PORT", "8081"))
# Konteynerde 0.0.0.0 sart; tek makinede 127.0.0.1 ile disariya kapanir.
HOST = ayar.oku("WORKER_HOST", "0.0.0.0")
_semafor = threading.BoundedSemaphore(ESZAMANLI)
kalp.yuk_kaynagi = lambda: ESZAMANLI - _semafor._value  # doluluk

# Süreç ömrü boyunca biriken sayaçlar. Panel buradan nabız okur.
_sayac = {"burst": 0, "ok": 0, "captcha": 0, "not_found": 0, "timeout": 0, "error": 0}
_kilit = threading.Lock()

# Zarif boşaltma: sinyal gelince yeni istek alınmaz, uçan burst'ler beklenir.
_bosaltiliyor = threading.Event()
_ucan = 0  # işlenmekte olan POST sayısı
_ucan_kilit = threading.Lock()
BOSALTMA_BEKLEME_SN = 900  # saniye; en uzun burst zaman aşımıyla aynı
_SUNUCU: ThreadingHTTPServer | None = None


class Isleyici(BaseHTTPRequestHandler):
    """Tek isteği karşılar."""

    server_version = "unique_request_bot"

    def log_message(self, bicim: str, *args) -> None:
        """Varsayılan gürültülü günlüğü tek satıra indirir."""
        print(f"{self.address_string()} {bicim % args}")

    def _json(self, kod: int, govde: dict, retry: int = 0) -> None:
        """JSON yanıt yazar."""
        ham = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if retry:
            self.send_header("Retry-After", str(retry))
        self.send_header("Content-Length", str(len(ham)))
        self.end_headers()
        self.wfile.write(ham)

    def _yetkili(self) -> bool:
        """Bearer token doğrular. Sabit süreli karşılaştırma kullanılır."""
        gelen = self.headers.get("Authorization", "")
        if not gelen.startswith("Bearer "):
            return False
        return hmac.compare_digest(gelen[7:].strip(), TOKEN)

    def _ham_oku(self) -> bytes | None:
        """Gövdeyi ham bayt olarak okur. Boş veya aşırı büyükse None döner."""
        uzunluk = int(self.headers.get("Content-Length", "0"))
        if uzunluk <= 0 or uzunluk > GOVDE_TAVANI:
            return None
        return self.rfile.read(uzunluk)

    def _imza_dogrula(self, ham: bytes) -> bool:
        """x-imza başlığını ham gövde üzerinden doğrular.

        Gövde ham bayt imzalanır; sayı biçimi farkı uyuşmazlık yaratmaz.
        """
        gelen = self.headers.get("x-imza", "")
        if not gelen:
            return False
        beklenen = hmac.new(TOKEN.encode("utf-8"), ham, hashlib.sha256).hexdigest()
        return hmac.compare_digest(gelen, beklenen)

    def do_GET(self) -> None:  # noqa: N802 (stdlib adlandırması)
        """Sağlık ucu."""
        yol = self.path.split("?")[0]
        if yol == "/health":
            # §7.2: surum ve doluluk doner; token istemez, dis izleyici kullanir.
            self._json(200, {
                "durum": "ayakta", "surum": kalp.SURUM,
                "doluluk": ESZAMANLI - _semafor._value,
                "bosaltiliyor": _bosaltiliyor.is_set(),
            })
            return
        if yol == "/durum":
            # Sayac ve saglayici durumu disariya acilir; token yoksa verilmez.
            if not self._yetkili():
                self._json(401, {"hata": "token geçersiz"})
                return
            self._durum()
            return
        self._json(404, {"hata": "bilinmeyen uç"})

    def _durum(self) -> None:
        """Sayaçları ve sağlayıcı durumlarını döndürür."""
        with _kilit:
            sayac = dict(_sayac)
        self._json(200, {"sayac": sayac, "saglayici": havuz.durum_sayaci()})

    def do_POST(self) -> None:  # noqa: N802 (stdlib adlandırması)
        """Boşaltma kapısı; uçan istek sayacını tutup gövdeyi _post'a devreder."""
        global _ucan
        if _bosaltiliyor.is_set():
            # Gövde okunmadan yanıt verilir; bağlantı bozulmasın diye boşaltılır.
            self._ham_oku()
            self._json(503, {"hata": "boşaltılıyor"}, retry=30)
            return
        with _ucan_kilit:
            _ucan += 1
        try:
            self._post()
        finally:
            with _ucan_kilit:
                _ucan -= 1

    def _post(self) -> None:
        """/worker/burst ve /worker/olcum_b uçlarını işler."""
        yol = self.path.split("?")[0]
        if yol not in ("/worker/burst", "/worker/olcum_b"):
            self._json(404, {"hata": "bilinmeyen uç"})
            return
        if not self._yetkili():
            self._json(401, {"hata": "token geçersiz"})
            return

        if kalp.duraklatildi():
            self._json(503, {"hata": "düğüm durduruldu"})
            return

        ham = self._ham_oku()
        if ham is None:
            self._json(400, {"hata": "gövde okunamadı"})
            return
        if not self._imza_dogrula(ham):
            self._json(401, {"hata": "imza geçersiz"})
            return
        try:
            govde = json.loads(ham.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._json(400, {"hata": "gövde okunamadı"})
            return
        if abs(time.time() - int(govde.get("ts") or 0)) > PENCERE_SN:
            self._json(401, {"hata": "ts penceresi dışında"})
            return

        if yol == "/worker/olcum_b":
            self._olcum_b(govde)
            return

        # Sozlesme adlari esastir; eski isci kelime/domain/adet gonderiyordu.
        kelime = str(govde.get("keyword") or govde.get("kelime") or "").strip()
        hedef = (govde.get("target_url") or govde.get("target_domain")
                 or govde.get("domain"))
        if not kelime or not hedef:
            self._json(400, {"hata": "keyword ve target_url/target_domain zorunlu"})
            return

        adet = int(govde.get("size") or govde.get("adet") or 1)
        uule = govde.get("uule")
        # İl slug'ı yalnız il kapsamlı kelimede çözülür. Ulusal kelimede
        # proxy'ye il yazılmaz, yalnız TR sorgulanır; UULE yine ilin kalır.
        geo_slug = govde.get("geo_slug")
        if (not geo_slug and govde.get("geo_code")
                and govde.get("geo_scope") == "province"):
            geo_slug = havuz.slug_bul(int(govde["geo_code"]))
            geo_slug = havuz.slug_bul(int(govde["geo_code"]))
        # target_url verilmişse domain türetilir, çözüm için API'ye gidilmez.
        hedef_url = govde.get("target_url")
        domain = govde.get("target_domain") or ""

        with _semafor:
            sonuc = burst.burst_yap(
                kelime, domain, adet, uule=uule, hedef_url=hedef_url,
                geo_slug=geo_slug, devam=lambda: durum.keyword_aktif_mi(kelime, domain),
            )

        with _kilit:
            _sayac["burst"] += 1
            for anahtar in ("ok", "captcha", "not_found", "timeout", "error"):
                _sayac[anahtar] += sonuc[anahtar]

        ilk_mod = sonuc["hits"][0]["geo_mode"] if sonuc["hits"] else None
        self._json(200, {
            # Mod hit basina degisebilir; ozet icin ilk hit'in modu verilir.
            "geo_mode": ilk_mod or havuz.son_mod, "ok": sonuc["ok"],
            "hits": sonuc["hits"],            "captcha": sonuc["captcha"],
            "not_found": sonuc["not_found"],
            "timeout": sonuc["timeout"],
            "error": sonuc["error"],
            "elapsed_ms": sonuc["elapsed_ms"],
            "durduruldu": sonuc["durduruldu"],
        })


    def _olcum_b(self, govde: dict) -> None:
        """/worker/olcum_b: kalici jar'li B kanali olcumu (C20)."""
        kelime = str(govde.get("keyword") or "").strip()
        domain = str(govde.get("target_domain") or govde.get("domain") or "").strip()
        if not kelime or not domain:
            self._json(400, {"hata": "keyword ve target_domain zorunlu"})
            return
        geo = govde.get("geo_code")
        kelime_id = govde.get("keyword_id")
        with _semafor:
            sonuc = olcum_b.olcum_b_yap(
                kelime, domain,
                int(geo) if geo else None,
                int(kelime_id) if kelime_id else None,
            )
        self._json(200, sonuc)

def _sinyal(sn: int, _cerceve) -> None:
    """SIGTERM/SIGINT: yeni istek almaz, uçan burst'ler biter, sonra çıkılır."""
    if _bosaltiliyor.is_set():
        print("ikinci sinyal: zorla çıkılıyor.")
        os._exit(0)
    print("boşaltılıyor: yeni istek alınmıyor.")
    _bosaltiliyor.set()
    threading.Thread(target=_bosalt_ve_kapat, daemon=True).start()


def _bosalt_ve_kapat() -> None:
    """Uçan istekler bitene kadar (en çok BOSALTMA_BEKLEME_SN) bekler, kapatır."""
    bitis = time.monotonic() + BOSALTMA_BEKLEME_SN
    while time.monotonic() < bitis:
        with _ucan_kilit:
            if _ucan == 0:
                break
        time.sleep(0.2)
    sunucu = _SUNUCU
    if sunucu is not None:
        sunucu.shutdown()


def main() -> int:
    """Servisi başlatır. Token boşsa çalışmaz."""
    if not TOKEN:
        print("HATA: .env içinde WORKER_TOKEN boş.")
        return 1
    global _SUNUCU
    kalp.baslat()
    sunucu = ThreadingHTTPServer((HOST, PORT), Isleyici)
    _SUNUCU = sunucu
    signal.signal(signal.SIGTERM, _sinyal)
    signal.signal(signal.SIGINT, _sinyal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _sinyal)
    print(f"worker dinliyor: {HOST}:{PORT} · eşzamanlı sınır {ESZAMANLI}")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("kapatılıyor.")
    finally:
        kalp.durdur()
        sunucu.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



