/**
 * Gövde doğrulama yardımcısı.
 *
 * Şema uymazsa 400 yazar ve null döner; çağıran taraf yalnızca null
 * kontrolü yapar. Hata biçimi tek: { hata, alan }.
 */
import type { Response } from "express";
import type { ZodType } from "zod";

export function dogrula<T>(sema: ZodType<T>, govde: unknown, yanit: Response): T | null {
  const sonuc = sema.safeParse(govde);
  if (sonuc.success) return sonuc.data;
  const ilk = sonuc.error.issues[0];
  yanit.status(400).json({ hata: ilk?.message ?? "geçersiz gövde", alan: ilk?.path.join(".") });
  return null;
}