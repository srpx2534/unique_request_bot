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

uygulama.listen(PORT, "127.0.0.1", () => {
  console.log(`panel dinliyor: 127.0.0.1:${PORT}`);
  redis
    .ping()
    .then(() => console.log("[redis] oturum deposu hazır"))
    .catch(() => console.error("[redis] erişilemiyor: giriş 500 verir"));
});