/**
 * Redis istemcisi.
 *
 * Oturum deposu ile kuyruk aynı bağlantıyı paylaşamaz; burada yalnızca
 * oturum ve genel amaçlı istemci tutulur. Bağlantı yokken süreç ölmez:
 * deneme aralığı sınırlanır, aynı hata üst üste yazılmaz.
 *
 * Adres ile parola ayrı gelir; parola URL'e gömülmez (`redis_baglanti`).
 */
import { Redis } from "ioredis";
import { redisBaglanti, redisEtiket } from "./redis_baglanti.js";

const baglanti = redisBaglanti();

let sonHata = "";

export const redis = new Redis({
  ...baglanti,
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
  console.log("[redis] bağlı:", redisEtiket(baglanti));
});
