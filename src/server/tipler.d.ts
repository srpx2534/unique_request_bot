/**
 * Oturum nesnesine eklenen alanların tipleri.
 *
 * express-session'ın kendi tipi boş bir nesne tanımlar; kimlik bilgisini
 * burada genişletiyoruz ki derleyici tanısın.
 */
import "express-session";

declare module "express-session" {
  interface SessionData {
    kullanici?: { id: number; eposta: string; rol: string };
    son?: number;
  }
}