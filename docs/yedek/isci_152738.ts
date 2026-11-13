/**
 * Kuyruk işleyicisi.
 *
 * İşi burst kaydına çevirir ve fetch motoruna devreder. Motor cevap
 * vermezse satır beklemede bırakılır, cooldown kısaltılır; böylece
 * sağlayıcı düzelince iş tekrar denenir.
 *
 * Hacim hedefi doluysa kelime kendiliğinden durur ve kampanya kapanır.
 */
import { Worker } from "bullmq";
import { baglanti, type Is } from "./kuyruk.js";
import { tek, yaz } from "./veritabani.js";

const TOKEN = process.env.WORKER_TOKEN ?? "";
const ZAMAN_ASIMI_MS = 120_000;

/**
 * İş atılacak düğümü seçer.
 *
 * Kayıtlı ve aktif düğüm varsa yalnızca onlar arasından, en az yüklü olanı
 * seçer; 45 saniyeden eski kalbi olan sessiz düğüm atlanır. Kayıt defteri
 * boşsa yerel düğüm varsayılır: 127.0.0.1:WORKER_PORT.
 */
async function dugumSec(): Promise<string | null> {
  const satir = await tek<{ ip: string }>(
    `SELECT ip FROM dugum
      WHERE durum = 'aktif' AND son_kalp_at > UTC_TIMESTAMP(3) - INTERVAL 45 SECOND
      ORDER BY yuk ASC, id ASC LIMIT 1`,
  );
  if (satir) return `http://${satir.ip}:${process.env.WORKER_PORT ?? 8081}`;

  const kayitli = await tek<{ sayi: number }>("SELECT COUNT(*) AS sayi FROM dugum");
  if ((kayitli?.sayi ?? 0) === 0) {
    return `http://127.0.0.1:${process.env.WORKER_PORT ?? 8081}`;
  }
  return null;
}

type MotorHiti = {
  result: string;
  saglayici_id: number | null;
  geo_mode: string | null;
  http_status: number | null;
  latency_ms: number | null;
  bytes: number | null;
};

type MotorCevabi = {
  ok?: number;
  stats?: Record<string, number>;
  hits?: MotorHiti[];
};

const HIT_PARCASI = 500;

/**
 * Hit dizisini toplu yazar.
 *
 * Saglayicisi olmayan satir atlanir; hit.provider_id zorunludur. Parca
 * boyu 500'u gecmez, tek INSERT fazla parametreye carpmaz.
 */
async function hitYaz(
  burstId: number,
  geoKodu: number,
  hits: MotorHiti[],
): Promise<void> {
  const satirlar = hits
    .filter((h) => h.saglayici_id !== null)
    .map((h) => [
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

/** Satırı beklemede bırakır ve kısa cooldown verir. */
async function geriAl(geoId: number, sebep: string): Promise<void> {
  await yaz(
    "UPDATE keyword_geo SET state = 'pending', cooldown_until = DATE_ADD(NOW(3), INTERVAL 2 MINUTE) WHERE id = ?",
    [geoId],
  );
  console.error("[isci]", sebep);
}

/** Hacim hedefi dolduysa kelimeyi durdurur. */
async function hedefDenetle(keywordId: number): Promise<void> {
  const hedef = await tek<{ volume: number | null; atilan: number }>(
    `SELECT k.volume,
            (SELECT COALESCE(SUM(b.target_count), 0) FROM burst b
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

async function calistir(is: Is): Promise<void> {
  const satir = await tek<{
    burst_count: number;
    uule: string | null;
    domain: string;
    geo_code: number;
    step_size: number;
  }>(
    `SELECT g.burst_count, geo.uule, s.domain, g.geo_code, c.step_size
       FROM keyword_geo g
       JOIN geo ON geo.code = g.geo_code
       JOIN keyword k ON k.id = g.keyword_id
       JOIN site s ON s.id = k.site_id
       JOIN campaign c ON c.id = ?
      WHERE g.id = ?`,
    [is.campaignId, is.keywordGeoId],
  );
  if (!satir) return;

  // Basamak büyüdükçe burst büyür: 5, 10, 15 ... tavan 60 ve kampanya sınırı.
  const adim = satir.burst_count + 1;
  const tavan = Math.min(satir.step_size, 60);
  const adet = Math.min(adim * 5, tavan);
  await yaz(
    "INSERT INTO burst (campaign_id, keyword_geo_id, step, target_count, phase, stats) VALUES (?, ?, ?, ?, ?, ?)",
    [is.campaignId, is.keywordGeoId, adim, adet, satir.burst_count < 3 ? "core" : "broad", "{}"],
  );
  const burst = await tek<{ id: number }>(
    "SELECT id FROM burst WHERE keyword_geo_id = ? ORDER BY id DESC LIMIT 1",
    [is.keywordGeoId],
  );
  if (!burst) return;

  const adres = await dugumSec();
  if (!adres) {
    await geriAl(is.keywordGeoId, "aktif düğüm yok");
    return;
  }

  try {
    const yanit = await fetch(`${adres}/worker/burst`, {
      method: "POST",
      headers: { "content-type": "application/json", Authorization: `Bearer ${TOKEN}` },
      body: JSON.stringify({
        burst_id: burst.id,
        keyword: is.kelime,
        geo_code: satir.geo_code,
        uule: satir.uule,
        target_domain: satir.domain,
        size: adet,
      }),      signal: AbortSignal.timeout(ZAMAN_ASIMI_MS),
    });
    if (!yanit.ok) throw new Error(`motor ${yanit.status}`);

    const govde = (await yanit.json()) as MotorCevabi;
    await hitYaz(burst.id, satir.geo_code, govde.hits ?? []);
    await yaz("UPDATE burst SET ended_at = NOW(3), stats = ? WHERE id = ?", [
      JSON.stringify(govde.stats ?? {}),
      burst.id,
    ]);
    await yaz(
      "UPDATE keyword_geo SET state = 'pending', burst_count = burst_count + 1, last_burst_at = NOW(3) WHERE id = ?",
      [is.keywordGeoId],
    );
    await hedefDenetle(is.keywordId);
  } catch (hata) {
    await yaz("UPDATE burst SET ended_at = NOW(3), stats = ? WHERE id = ?", [
      JSON.stringify({ hata: (hata as Error).message }),
      burst.id,
    ]);
    await geriAl(is.keywordGeoId, `burst ${burst.id}: ${(hata as Error).message}`);
  }
}

export const isci = new Worker<Is>("olcum", (is) => calistir(is.data), {
  connection: baglanti,
  concurrency: 4,
});

isci.on("failed", (is, hata) => {
  if (is) void geriAl(is.data.keywordGeoId, `iş ${is.id}: ${hata.message}`);
});