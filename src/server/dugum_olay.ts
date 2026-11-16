/**
 * Düğüm olay defteri.
 *
 * Kayıt, durdur/başlat, silme ve kalp kaybı buraya yazılır; durum değişiminin
 * ne zaman olduğu sonradan okunabilir (§6.1). Kalp kaybı taraması idempotenttir:
 * son kalpten sonra aynı düğüm için ikinci kez yazılmaz.
 *
 * Kullanım: src/server/dugum.ts, src/server/zamanlayici.ts.
 */
import { yaz } from "./veritabani.js";

export type OlayTuru = "kayit" | "kalp_kaybi" | "durdur" | "baslat" | "sil";

/**
 * Tek olay yazar.
 *
 * @param dugumId İlgili düğüm.
 * @param tur Olay türü.
 * @param mesaj Okunur açıklama.
 */
export async function olay(dugumId: number, tur: OlayTuru, mesaj?: string): Promise<void> {
  await yaz("INSERT INTO dugum_olay (dugum_id, tur, message) VALUES (?, ?, ?)", [
    dugumId,
    tur,
    mesaj ?? null,
  ]);
}

/**
 * Kalbi kesilen düğüm için olay ve panel uyarısı düşer (E3).
 *
 * Ölçüt son kalp atışıdır: kalp geri gelirse sonraki kayıp yeniden yazılır.
 *
 * @returns Eklenen satır sayısı.
 */
export async function kalpKaybiYaz(): Promise<number> {
  const sayi = await yaz(
    `INSERT INTO dugum_olay (dugum_id, tur, message)
     SELECT d.id, 'kalp_kaybi', 'kalp 45 saniyeyi gecti'
       FROM dugum d
      WHERE d.durum = 'aktif'
        AND (d.son_kalp_at IS NULL OR d.son_kalp_at < UTC_TIMESTAMP(3) - INTERVAL 45 SECOND)
        AND NOT EXISTS (
              SELECT 1 FROM dugum_olay o
               WHERE o.dugum_id = d.id AND o.tur = 'kalp_kaybi'
                 AND (d.son_kalp_at IS NULL OR o.created_at > d.son_kalp_at))`,
  );
  // Uyari 90 saniyede duser: 45 saniyelik esik tek bir gecikmede otmesin.
  // Dugum basina 30 dakika sessizlik var; acik uyari varken yenisi yazilmaz.
  await yaz(
    `INSERT INTO alert (kind, ref_id, message)
     SELECT 'dugum_olu', d.id, LEFT(CONCAT('dugum kalbi kesildi: ', d.ad), 500)
       FROM dugum d
      WHERE d.durum = 'aktif'
        AND (d.son_kalp_at IS NULL OR d.son_kalp_at < UTC_TIMESTAMP(3) - INTERVAL 90 SECOND)
        AND NOT EXISTS (
              SELECT 1 FROM alert a
               WHERE a.kind = 'dugum_olu' AND a.ref_id = d.id
                 AND a.acknowledged = 0
                 AND a.created_at > UTC_TIMESTAMP(3) - INTERVAL 30 MINUTE)`,
  );
  return sayi;
}
