/**
 * CSRF koruması.
 *
 * Çift gönderim yöntemi: token cookie'de değil oturumda tutulur ve
 * istemci onu `x-csrf-token` başlığıyla geri yollar. Cookie tabanlı
 * oturumda bu olmadan başka siteler adına yazma yapılabilir.
 */
import { csrfSync } from "csrf-sync";
import type { RequestHandler } from "express";

const { csrfSynchronisedProtection } = csrfSync({
  getTokenFromRequest: (istek) => istek.headers["x-csrf-token"] as string | undefined,
});

export const csrf: RequestHandler = csrfSynchronisedProtection;

/** Oturumdaki token'ı istemciye verir. */
export const tokenVer: RequestHandler = (istek, yanit) => {
  yanit.json({ token: (istek as unknown as { csrfToken: () => string }).csrfToken() });
};