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

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

const uygulama = express();
uygulama.disable("x-powered-by");
uygulama.set("trust proxy", 1);
uygulama.use(helmet());
uygulama.use(express.json({ limit: "256kb" }));

// Genel hız sınırı: panel tek kullanıcı, dakikada 300 istek fazlasıyla yeter.
uygulama.use(
  rateLimit({ windowMs: 60_000, limit: 300, standardHeaders: "draft-7" }),
);

uygulama.get("/saglik", (_istek, yanit) => {
  yanit.json({ durum: "ayakta" });
});

uygulama.use(oturum);
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

uygulama.use(express.static(path.join(KOK, "dist", "web")));

uygulama.use((_istek, yanit) => {
  yanit.status(404).json({ hata: "bilinmeyen uç" });
});

uygulama.use(
  (hata: Error, _istek: express.Request, yanit: express.Response, sonraki: express.NextFunction) => {
    console.error("[hata]", hata.message);
    // Yanıtın bir kısmı gitmişse başlıklar yeniden yazılamaz; Express'e bırakılır.
    if (yanit.headersSent) {
      sonraki(hata);
      return;
    }
    yanit.status(500).json({ hata: "sunucu hatası", ayrinti: process.env.NODE_ENV === "production" ? undefined : hata.message });
  },
);

export default uygulama;
