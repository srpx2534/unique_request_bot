/**
 * Oturum ara katmanı.
 *
 * Oturum kimliği cookie'de, veri Redis'te tutulur; süreç yeniden başlasa da
 * oturum düşmez. Cookie httpOnly ve SameSite=Lax'tır, üretimde Secure olur.
 * Süre 12 saat, hareketsizlikte 2 saat.
 */
import session from "express-session";
import { RedisStore } from "connect-redis";
import type { RequestHandler } from "express";
import { redis } from "./redis.js";

const SURE_MS = 12 * 60 * 60 * 1000; // 12 saat; tam oturum ömrü
const BOSLUK_MS = 2 * 60 * 60 * 1000; // 2 saat; hareketsizlik sınırı

const gizli = process.env.SESSION_SECRET;
if (!gizli) throw new Error(".env içinde SESSION_SECRET boş");

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
    secure: process.env.NODE_ENV === "production",
    maxAge: SURE_MS,
  },
});

/** Hareketsizlik sınırını uygular; süre dolduysa oturumu kapatır. */
export const boslukDenetimi: RequestHandler = (istek, yanit, sonraki) => {
  const oturumVerisi = istek.session as { son?: number };
  const simdi = Date.now();
  if (oturumVerisi.son && simdi - oturumVerisi.son > BOSLUK_MS) {
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
