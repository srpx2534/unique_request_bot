/**
 * Süreç giriş noktası.
 *
 * Uygulamayı 127.0.0.1'e bağlar ve Redis erişimini bir kez sınar.
 * Testler uygulamayı doğrudan `uygulama.ts` üzerinden yükler, dinleme yok.
 */
import "dotenv/config";
import uygulama from "./uygulama.js";
import { redis } from "./redis.js";
import { isci } from "./isci.js";
import { zamanlayiciBaslat, zamanlayiciDurdur } from "./zamanlayici.js";

const PORT = Number(process.env.PANEL_PORT ?? 8080);
// Konteynerde 127.0.0.1 yalnizca konteyner icinden erisilir; host ezilebilir.
const HOST = process.env.PANEL_HOST ?? "127.0.0.1";

const sunucu = uygulama.listen(PORT, HOST, () => {
  console.log(`panel dinliyor: ${HOST}:${PORT}`);
  redis
    .ping()
    .then(() => console.log("[redis] oturum deposu hazır"))
    .catch(() => console.error("[redis] erişilemiyor: giriş 500 verir"));

  // Zamanlayıcı ve kuyruk tüketicisi yalnızca sunucu sürecinde başlar;
  // testler uygulamayı doğrudan yüklediği için ikisi de dışarıda kalır.
  zamanlayiciBaslat();
});

// Port doluysa ikinci süreç sessizce ölmesin: hangi sürecin çalıştığı belli olsun.
sunucu.on("error", (hata: NodeJS.ErrnoException) => {
  if (hata.code === "EADDRINUSE") {
    console.error(`[panel] ${HOST}:${PORT} dolu, başka bir panel süreci çalışıyor`);
  } else {
    console.error(`[panel] dinleme hatası: ${hata.message}`);
  }
  process.exit(1);
});

/** Kapanışta zamanlayıcı ve kuyruk tüketicisi düzgün kapatılır. */
async function kapat(): Promise<void> {
  zamanlayiciDurdur();
  await isci.close();
  process.exit(0);
}

process.on("SIGINT", () => void kapat());
process.on("SIGTERM", () => void kapat());