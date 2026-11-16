/**
 * Denetim kaydı.
 *
 * audit_log'a yazar; kayıt tutulamazsa akış kesilmez, yalnızca günlüğe
 * düşer. Aktör oturumdan alınır.
 */
import type { Request } from "express";
import { yaz } from "./veritabani.js";
import { gunluk } from "./gunluk.js";

export async function denetim(
  istek: Request,
  eylem: string,
  varlik: string,
  id: number | null,
): Promise<void> {
  const kimlik = (istek.session as { kullanici?: { eposta: string } }).kullanici;
  try {
    await yaz("INSERT INTO audit_log (actor, action, entity, entity_id) VALUES (?, ?, ?, ?)", [
      kimlik?.eposta ?? "sistem",
      eylem,
      varlik,
      id,
    ]);
  } catch (hata) {
    gunluk.hata("[denetim]", (hata as Error).message);
  }
}
// console testi
