/**
 * Süreç giriş noktası.
 *
 * Uygulamayı 127.0.0.1'e bağlar ve Redis erişimini bir kez sınar.
 * Testler uygulamayı doğrudan `uygulama.ts` üzerinden yükler, dinleme yok.
 */
import "dotenv/config";
import uygulama from "./uygulama.js";
import { redis } from "./redis.js";

const PORT = Number(process.env.PANEL_PORT ?? 8080);
// Konteynerde 127.0.0.1 yalnizca konteyner icinden erisilir; host ezilebilir.
const HOST = process.env.PANEL_HOST ?? "127.0.0.1";

uygulama.listen(PORT, HOST, () => {
  console.log(`panel dinliyor: ${HOST}:${PORT}`);
  redis
    .ping()
    .then(() => console.log("[redis] oturum deposu hazır"))
    .catch(() => console.error("[redis] erişilemiyor: giriş 500 verir"));
});