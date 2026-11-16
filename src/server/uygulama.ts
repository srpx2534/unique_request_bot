/**
 * Express uygulaması.
 *
 * Sıra önemlidir: güvenlik başlıkları, gövde sınırı, oturum, CSRF ve
 * hız sınırı rotalardan önce kurulur; hata yakalayıcı en sonda durur.
 * Panel derlemesi üretimde buradan servis edilir.
 */
import express from "express";
import helmet from "helmet";
import path from "node:path";
import rateLimit from "express-rate-limit";
import { fileURLToPath } from "node:url";
import "dotenv/config";
import { boslukDenetimi, gerekli, oturum } from "./oturum.js";
import { csrf, tokenVer } from "./csrf.js";
import girisYonlendirici from "./giris.js";
import siteYonlendirici from "./site.js";
import kelimeYonlendirici from "./kelime.js";
import panelYonlendirici from "./panel.js";
import metrikYonlendirici from "./panel_metrik.js";
import raporYonlendirici from "./rapor.js";
import dugumYonlendirici, { kalpIsleyici } from "./dugum.js";
import cerezYonlendirici from "./cerez/index.js";
import { imzaDogrula } from "./worker_imza.js";
import { gunluk } from "./gunluk.js";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

const uygulama = express();
uygulama.disable("x-powered-by");
// Ters proxy sayısı ortamdan ezilebilir; panel tek başına 127.0.0.1'de dinler.
uygulama.set("trust proxy", Number(process.env.TRUST_PROXY ?? 1));
uygulama.use(helmet());
// Ham gövde saklanır: worker kalbi bu baytların HMAC'i ile imzalanır.
uygulama.use(
  express.json({
    limit: "256kb",
    verify: (istek, _yanit, tampon) => {
      (istek as { rawBody?: Buffer }).rawBody = Buffer.from(tampon);
    },
  }),
);

// Genel hız sınırı: panel tek kullanıcı, dakikada 300 istek fazlasıyla yeter.
uygulama.use(
  rateLimit({ windowMs: 60_000, limit: 300, standardHeaders: "draft-7" }),
);

uygulama.get("/saglik", (_istek, yanit) => {
  yanit.json({ durum: "ayakta" });
});

uygulama.use(oturum);
// Kalp ucu oturum ve CSRF istemez; worker''ın çerezi yok.
uygulama.post("/api/worker/kalp", imzaDogrula, kalpIsleyici);

uygulama.use("/api", csrf);

// CSRF doğrulaması düşerse hata yakalayıcıya gitmeden 403 döner.
uygulama.use("/api", (hata: Error, _istek: express.Request, yanit: express.Response, sonraki: express.NextFunction) => {
  if (hata.message.toLowerCase().includes("csrf")) {
    yanit.status(403).json({ hata: "güvenlik token'ı geçersiz, sayfayı yenile" });
    return;
  }
  sonraki(hata);
});
uygulama.get("/api/token", tokenVer);
uygulama.use("/api", girisYonlendirici);

// Giriş gerektiren rotalar buradan sonra eklenir.
uygulama.use("/api", boslukDenetimi);
uygulama.use("/api", gerekli);
uygulama.use("/api", siteYonlendirici);
uygulama.use("/api", kelimeYonlendirici);
uygulama.use("/api", panelYonlendirici);
uygulama.use("/api", metrikYonlendirici);
uygulama.use("/api", raporYonlendirici);
uygulama.use("/api", dugumYonlendirici);
uygulama.use("/api", cerezYonlendirici);

uygulama.use(express.static(path.join(KOK, "dist", "web")));

// /api disindaki bilinmeyen yol SPA'ya duser: /kelimeler adresini yenileyen
// kullanici JSON 404 ekrani degil uygulamayi gormeli (C42).
uygulama.use((istek, yanit) => {
  if (istek.path.startsWith("/api/") || istek.path === "/api") {
    yanit.status(404).json({ hata: "bilinmeyen uç" });
    return;
  }
  yanit.status(404).sendFile(path.join(KOK, "dist", "web", "index.html"));
});

uygulama.use(
  (hata: Error, _istek: express.Request, yanit: express.Response, sonraki: express.NextFunction) => {
    gunluk.hata("[hata]", hata.message);
    // Yanıtın bir kısmı gitmişse başlıklar yeniden yazılamaz; Express'e bırakılır.
    if (yanit.headersSent) {
      sonraki(hata);
      return;
    }
    yanit.status(500).json({ hata: "sunucu hatası", ayrinti: process.env.NODE_ENV === "production" ? undefined : hata.message });
  },
);

export default uygulama;

