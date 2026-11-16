/**
 * Oturum ara katmanı.
 *
 * Oturum kimliği cookie'de, veri Redis'te tutulur; süreç yeniden başlasa da
 * oturum düşmez. Cookie httpOnly ve SameSite=Lax'tır; Secure HTTPS'te otomatik.
 * Süre 12 saat, hareketsizlikte 8 saat.
 */
import session from "express-session";
import { RedisStore } from "connect-redis";
import type { RequestHandler } from "express";
import { redis } from "./redis.js";
import { gunluk } from "./gunluk.js";

const SURE_MS = 12 * 60 * 60 * 1000; // 12 saat; tam oturum ömrü
const BOSLUK_MS = 8 * 60 * 60 * 1000; // 8 saat; hareketsizlik sınırı

const gizli = process.env.SESSION_SECRET;
if (!gizli) throw new Error(".env içinde SESSION_SECRET boş");
// Kısa sır zayıf imza demek; üretimi durdurmaz ama görünür olsun.
if (gizli.length < 32) gunluk.uyari("[oturum] SESSION_SECRET 32 karakterden kısa");

export const oturum: RequestHandler = session({
  store: new RedisStore({ client: redis, prefix: "oturum:" }),
  secret: gizli,
  name: "urb_oturum",
  resave: false,
  saveUninitialized: false,
  rolling: true,
  cookie: {
    httpOnly: true,
    sameSite: "lax",
    // "auto": HTTPS arkasında Secure, düz HTTP yerelde değil. Sabit true
    // iken http://127.0.0.1 üzerinden giriş cookie yazamıyordu.
    secure: "auto",
    maxAge: SURE_MS,
  },
});

/** Hareketsizlik sınırını uygular; süre dolduysa oturumu kapatır. */
export const boslukDenetimi: RequestHandler = (istek, yanit, sonraki) => {
  const oturumVerisi = istek.session as { son?: number };
  // Yukleme akisi kendi basina canli: uzun surse de oturum dusmesin.
  const yuklemeAkisi = istek.originalUrl.includes("/cerez/yukleme");
  const simdi = Date.now();
  if (!yuklemeAkisi && oturumVerisi.son && simdi - oturumVerisi.son > BOSLUK_MS) {
    istek.session.destroy(() => yanit.status(401).json({ hata: "oturum süresi doldu" }));
    return;
  }
  oturumVerisi.son = simdi;
  sonraki();
};
/** Oturum yoksa 401 döner; giriş gerektiren rotalardan önce gelir. */
export const gerekli: RequestHandler = (istek, yanit, sonraki) => {
  if (!istek.session.kullanici) {
    yanit.status(401).json({ hata: "giriş gerekli" });
    return;
  }
  sonraki();
};

