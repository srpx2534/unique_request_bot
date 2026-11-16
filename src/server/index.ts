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
import { kuyrukBaslat, kuyrukKapat } from "./cerez/index.js";
import { kilitAl, kilitBirak } from "./tek_ornek.js";
import { gunluk } from "./gunluk.js";

const PORT = Number(process.env.PANEL_PORT ?? 8080);
// Konteynerde 127.0.0.1 yalnizca konteyner icinden erisilir; host ezilebilir.
const HOST = process.env.PANEL_HOST ?? "127.0.0.1";

// İkinci süreç aynı veritabanına ikinci zamanlayıcı açmasın: kilit alınmadan
// dinlemeye geçilmez. Port denetimi farklı portu yakalamaz, kilit yakalar.
try {
  kilitAl();
} catch (hata) {
  gunluk.hata(`[panel] ${(hata as Error).message}`);
  process.exit(1);
}

const sunucu = uygulama.listen(PORT, HOST, () => {
  gunluk.bilgi(`panel dinliyor: ${HOST}:${PORT}`);
  redis
    .ping()
    .then(() => gunluk.bilgi("[redis] oturum deposu hazır"))
    .catch(() => gunluk.hata("[redis] erişilemiyor: giriş 500 verir"));

  // Zamanlayıcı ve kuyruk tüketicisi yalnızca sunucu sürecinde başlar;
  // testler uygulamayı doğrudan yüklediği için ikisi de dışarıda kalır.
  zamanlayiciBaslat();
  void kuyrukBaslat().catch((hata: Error) => gunluk.hata("[panel] kuyruk:", hata));
});

// Yukleme uzun surer; varsayilan govde suresi ve keep-alive yetmez.
sunucu.requestTimeout = 15 * 60 * 1000;
sunucu.headersTimeout = 65 * 1000;
sunucu.keepAliveTimeout = 65 * 1000;

// Port doluysa ikinci süreç sessizce ölmesin: hangi sürecin çalıştığı belli olsun.
sunucu.on("error", (hata: NodeJS.ErrnoException) => {
  if (hata.code === "EADDRINUSE") {
    gunluk.hata(`[panel] ${HOST}:${PORT} dolu, başka bir panel süreci çalışıyor`);
  } else {
    gunluk.hata(`[panel] dinleme hatası: ${hata.message}`);
  }
  process.exit(1);
});

/**
 * Kapanışta zamanlayıcı, kuyruk tüketicisi, Redis ve HTTP sunucusu kapatılır.
 *
 * Sıra önemli: önce yeni iş alımı kesilir, sonra bağlantılar bırakılır,
 * en son süreç çıkar. Aksi halde Redis bağlantısı açık kalıp süreç asılı kalır.
 */
async function kapat(): Promise<void> {
  zamanlayiciDurdur();
  await isci.close().catch(() => undefined);
  await kuyrukKapat().catch(() => undefined);
  await new Promise<void>((cozum) => sunucu.close(() => cozum()));
  await redis.quit().catch(() => undefined);
  // Kilit en sonda bırakılır: kuyruk ve sunucu kapandıktan sonra.
  kilitBirak();
  process.exit(0);
}

// Beklenmeyen hata sureci oldurmesin: panel ayakta kalsin, sebep loglansin.
process.on("unhandledRejection", (sebep) => {
  gunluk.hata("[panel] islenmeyen reddetme:", sebep);
});
process.on("uncaughtException", (hata) => {
  gunluk.hata("[panel] yakalanmayan istisna:", hata);
});

process.on("SIGINT", () => void kapat());
process.on("SIGTERM", () => void kapat());

