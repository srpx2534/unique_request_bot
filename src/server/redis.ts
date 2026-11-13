/**
 * Redis istemcisi.
 *
 * Oturum deposu ile kuyruk aynı bağlantıyı paylaşamaz; burada yalnızca
 * oturum ve genel amaçlı istemci tutulur. Bağlantı yokken süreç ölmez:
 * deneme aralığı sınırlanır, aynı hata üst üste yazılmaz.
 */
import { Redis } from "ioredis";

const adres = process.env.REDIS_URL ?? "redis://127.0.0.1:6379/0";

let sonHata = "";

export const redis = new Redis(adres, {
  maxRetriesPerRequest: 3,
  // 250 ms'den başlar, 3 sn'de durur; sonsuz sık deneme günlüğü boğmaz.
  retryStrategy: (deneme) => Math.min(250 * deneme, 3000),
});

redis.on("error", (hata) => {
  if (hata.message === sonHata) return;
  sonHata = hata.message;
  console.error("[redis]", hata.message);
});

redis.on("ready", () => {
  sonHata = "";
  console.log("[redis] bağlı:", adres);
});