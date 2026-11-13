/**
 * Worker imzası.
 *
 * Kalp ucu oturum ve CSRF dışında olduğu için kimlik, paylaşılan token'ın
 * HMAC'i ile kanıtlanır; IP tek başına taklit edilebilir. Gövde ham bayt
 * olarak imzalanır, böylece Python ve JS'in sayı biçimi farkı sorun olmaz.
 * `ts` alanı tekrar saldırısını iki dakikayla sınırlar.
 *
 * Kullanım: src/server/uygulama.ts.
 */
import { createHmac, timingSafeEqual } from "node:crypto";
import type { RequestHandler } from "express";

const TOKEN = process.env.WORKER_TOKEN ?? "";
const PENCERE_SN = 120; // saniye; saat kayması payı

export const imzaDogrula: RequestHandler = (istek, yanit, sonraki) => {
  if (!TOKEN) {
    yanit.status(500).json({ hata: "WORKER_TOKEN boş" });
    return;
  }

  const gelen = istek.headers["x-imza"];
  const ham = (istek as { rawBody?: Buffer }).rawBody;
  if (typeof gelen !== "string" || !ham) {
    yanit.status(401).json({ hata: "imza yok" });
    return;
  }

  const beklenen = createHmac("sha256", TOKEN).update(ham).digest();
  const verilen = Buffer.from(gelen, "hex");
  if (verilen.length !== beklenen.length || !timingSafeEqual(verilen, beklenen)) {
    yanit.status(401).json({ hata: "imza geçersiz" });
    return;
  }

  const ts = Number((istek.body as { ts?: number }).ts);
  if (!Number.isFinite(ts) || Math.abs(Date.now() / 1000 - ts) > PENCERE_SN) {
    yanit.status(401).json({ hata: "ts penceresi dışında" });
    return;
  }
  sonraki();
};