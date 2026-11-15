/** Hit yazimi ve kelime durdurma denetimleri. */
import { sorgu, tek, yaz } from "./veritabani.js";

export type MotorHiti = {
  result: string;
  saglayici_id: number | null;
  geo_mode: string | null;
  http_status: number | null;
  latency_ms: number | null;
  bytes: number | null;
};

const HIT_PARCASI = 500;

/**
 * Hit dizisini toplu yazar.
 *
 * Saglayicisiz hit de yazilir; provider_id NULL olabilir. Parca boyu 500'u
 * gecmez, tek INSERT fazla parametreye carpmaz.
 */
export async function hitYaz(
  burstId: number,
  geoKodu: number,
  hits: MotorHiti[],
): Promise<void> {
  const satirlar = hits.map((h) => [
    burstId, h.saglayici_id, geoKodu, h.geo_mode ?? "tr_fallback",
    h.result, h.http_status, h.latency_ms, h.bytes,
  ]);
  for (let i = 0; i < satirlar.length; i += HIT_PARCASI) {
    const parca = satirlar.slice(i, i + HIT_PARCASI);
    const yerler = parca.map(() => "(?, ?, ?, ?, ?, ?, ?, ?)").join(", ");
    await yaz(
      `INSERT INTO hit (burst_id, provider_id, geo_code, geo_mode, result, http_status, latency_ms, bytes) VALUES ${yerler}`,
      parca.flat(),
    );
  }
}

/** Ust uste kac burst hedef bulamazsa kelime durur (A3). */
export const ARDA_HEDEF_YOK = 3;

/** Ust uste hedef_yok alan kelimeyi durdurur (A3). */
export async function hedefYokDenetle(keywordId: number, geoId: number): Promise<void> {
  // Burst bazinda bakilir: bir burst'un butun hit'leri hedef_yok ise o burst
  // hedefsizdir. Tek tek hit saymak ayni burst'u uc kez sayardi.
  const satirlar = await sorgu<{ hepsi: number }>(
    `SELECT SUM(h.result = 'hedef_yok') = COUNT(*) AS hepsi
       FROM burst b JOIN hit h ON h.burst_id = b.id
      WHERE b.keyword_geo_id = ? AND b.ended_at IS NOT NULL
      GROUP BY b.id ORDER BY b.id DESC LIMIT ?`,
    [geoId, ARDA_HEDEF_YOK],
  );
  if (satirlar.length < ARDA_HEDEF_YOK) return;
  if (!satirlar.every((satir) => Number(satir.hepsi) === 1)) return;

  await yaz("UPDATE keyword SET state = 'paused' WHERE id = ?", [keywordId]);
  await yaz(
    "UPDATE campaign SET stopped_at = UTC_TIMESTAMP(3) WHERE keyword_id = ? AND stopped_at IS NULL",
    [keywordId],
  );
  await yaz("INSERT INTO alert (kind, message) VALUES ('hedef_yok', ?)", [
    `${ARDA_HEDEF_YOK} burst ust uste hedef bulamadi, kelime durdu`,
  ]);
  console.log(`[isci] hedef bulunamadi, kelime durdu: ${keywordId}`);
}

/** Hacim hedefi dolduysa kelimeyi durdurur. */
export async function hedefDenetle(keywordId: number): Promise<void> {
  // Hacim gercek hit ile olculur: burst erken bitse de target_count yazili
  // kaldigi icin SUM(target_count) hedefi planlanan sayiyla sisiriyordu.
  const hedef = await tek<{ volume: number | null; atilan: number }>(
    `SELECT k.volume,
            (SELECT COALESCE(SUM(h.result = 'ok'), 0) FROM hit h
               JOIN burst b ON b.id = h.burst_id
               JOIN keyword_geo g2 ON g2.id = b.keyword_geo_id
              WHERE g2.keyword_id = k.id) AS atilan
       FROM keyword k WHERE k.id = ?`,
    [keywordId],
  );
  if (!hedef?.volume || hedef.atilan < hedef.volume) return;

  await yaz("UPDATE keyword SET state = 'paused' WHERE id = ?", [keywordId]);
  await yaz(
    "UPDATE campaign SET stopped_at = NOW(3) WHERE keyword_id = ? AND stopped_at IS NULL",
    [keywordId],
  );
  console.log(`[isci] hacim doldu, kelime durdu: ${keywordId}`);
}
/** Satiri beklemede birakir ve kisa cooldown verir. */
export async function geriAl(geoId: number, sebep: string): Promise<void> {
  await yaz(
    "UPDATE keyword_geo SET state = 'pending', cooldown_until = DATE_ADD(NOW(3), INTERVAL 2 MINUTE) WHERE id = ?",
    [geoId],
  );
  console.error("[isci]", sebep);
}