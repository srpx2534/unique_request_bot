/**
 * Kuyruk işleyicisi.
 *
 * İşi burst kaydına çevirir ve fetch motoruna devreder. Motor cevap
 * vermezse satır beklemede bırakılır, cooldown kısaltılır; böylece
 * sağlayıcı düzelince iş tekrar denenir.
 *
 * Hacim hedefi doluysa kelime kendiliğinden durur ve kampanya kapanır.
 */
import { createHmac } from "node:crypto";
import { Worker } from "bullmq";
import { baglanti, type Is } from "./kuyruk.js";
import { ekle, tek, yaz } from "./veritabani.js";
import { dugumSec } from "./dugum_sec.js";

const TOKEN = process.env.WORKER_TOKEN ?? "";
// 60 hit'lik burst dwell ve pogo ile dakikalar sürebilir; kısa sınır işi ortada keser.
const ZAMAN_ASIMI_MS = 900_000;



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
  captcha?: number;
  not_found?: number;
  timeout?: number;
  error?: number;
  stats?: Record<string, number>;
  hits?: MotorHiti[];
};

const HIT_PARCASI = 500;

/**
 * Hit dizisini toplu yazar.
 *
 * Saglayicisiz hit de yazilir; provider_id NULL olabilir. Parca boyu 500'u
 * gecmez, tek INSERT fazla parametreye carpmaz.
 */
async function hitYaz(
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

async function calistir(is: Is): Promise<void> {
  // Govdenin tamami korunur: dugumSec ve DB adimlari da try icinde kalsin ki
  // hata alan satir sonsuza dek 'running' kalmasin.
  let burstId = 0;
  try {
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
  // Yeniden denemede aynı iş için açık burst varsa yenisi açılmaz; hedef sayısı
  // iki kez sayılmaz ve kota tekrar yakılmaz.
  const acik = await tek<{ id: number }>(
    `SELECT id FROM burst
      WHERE keyword_geo_id = ? AND ended_at IS NULL
        AND started_at > UTC_TIMESTAMP(3) - INTERVAL 10 MINUTE
      ORDER BY id DESC LIMIT 1`,
    [is.keywordGeoId],
  );
  let yeniden = false;
  if (acik) {
    burstId = acik.id;
    yeniden = true;
  } else {
    // Kimlik insertId'den alinir: ayni keyword_geo'ya es zamanli iki burst
    // dusunce "ORDER BY id DESC LIMIT 1" yanlis satiri baglayabiliyordu.
    const yeniId = await ekle(
      "INSERT INTO burst (campaign_id, keyword_geo_id, step, target_count, phase, stats) VALUES (?, ?, ?, ?, ?, ?)",
      [is.campaignId, is.keywordGeoId, adim, adet, satir.burst_count < 3 ? "core" : "broad", "{}"],
    );
    if (!yeniId) return;
    burstId = yeniId;
  }

  // Aynı iş iki kez düşerse satır sahiplenilemez: taze burst silinir, açık burst
  // yeniden sahiplenilir.
  // Sahiplenme damgasi: last_burst_at her seferinde degisir, boylece
  // affectedRows gercekten "bu satiri ben aldim" anlamina gelir. Ayni degeri
  // tekrar yazmak MySQL'de 0 satir dondurur; eski kod bu yuzden her burst'u
  // silip satiri 'running' birakiyordu ve sistem hic hit atmiyordu.
  const sahiplen = await yaz(
    `UPDATE keyword_geo
        SET state = 'running', last_burst_at = UTC_TIMESTAMP(3)
      WHERE id = ? AND state = 'running'
        AND (last_burst_at IS NULL OR last_burst_at < UTC_TIMESTAMP(3) - INTERVAL 5 SECOND)`,
    [is.keywordGeoId],
  );
  if (sahiplen === 0) {
    // Satir 5 saniye icinde baska bir dagitici tarafindan alindi.
    if (!yeniden) {
      await yaz("DELETE FROM burst WHERE id = ?", [burstId]);
      return;
    }
    await yaz(
      `UPDATE keyword_geo
          SET state = 'running', last_burst_at = UTC_TIMESTAMP(3)
        WHERE id = ?`,
      [is.keywordGeoId],
    );
  }

  const adres = await dugumSec();
  if (!adres) {
    // Burst açık kalmasın; panelde "sürüyor" görünüp kaybolmasın.
    await yaz("UPDATE burst SET ended_at = UTC_TIMESTAMP(3), stats = ? WHERE id = ?", [
      JSON.stringify({ hata: "aktif düğüm yok" }),
      burstId,
    ]);
    await geriAl(is.keywordGeoId, "aktif düğüm yok");
    return;
  }

  try {
    // Gövde ham metin olarak imzalanır; worker aynı baytlar üzerinden doğrular.
    const govdeMetni = JSON.stringify({
      burst_id: burstId,
      keyword: is.kelime,
      geo_code: satir.geo_code,
      uule: satir.uule,
      target_domain: satir.domain,
      size: adet,
      ts: Math.floor(Date.now() / 1000),
    });
    const imza = createHmac("sha256", TOKEN).update(govdeMetni).digest("hex");
    const yanit = await fetch(`${adres}/worker/burst`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        Authorization: `Bearer ${TOKEN}`,
        "x-imza": imza,
      },
      body: govdeMetni,
      signal: AbortSignal.timeout(ZAMAN_ASIMI_MS),
    });
    if (!yanit.ok) throw new Error(`motor ${yanit.status}`);

    const govde = (await yanit.json()) as MotorCevabi;
    await hitYaz(burstId, satir.geo_code, govde.hits ?? []);
    // Sayaçlar burst satırına yazılır; log ve rapor buradan okur.
    const sayac = {
      ok: govde.ok ?? 0,
      captcha: govde.captcha ?? 0,
      not_found: govde.not_found ?? 0,
      timeout: govde.timeout ?? 0,
      error: govde.error ?? 0,
    };
    await yaz("UPDATE burst SET ended_at = UTC_TIMESTAMP(3), stats = ? WHERE id = ?", [
      JSON.stringify(sayac),
      burstId,
    ]);
    await yaz(
      "UPDATE keyword_geo SET state = 'pending', burst_count = burst_count + 1, last_burst_at = NOW(3) WHERE id = ?",
      [is.keywordGeoId],
    );
    await hedefDenetle(is.keywordId);
  } catch (hata) {
    await yaz("UPDATE burst SET ended_at = UTC_TIMESTAMP(3), stats = ? WHERE id = ?", [
      JSON.stringify({ hata: (hata as Error).message }),
      burstId,
    ]);
    await geriAl(is.keywordGeoId, `burst ${burstId || "-"}: ${(hata as Error).message}`);
  }
  } catch (hata) {
    // Burst acilmadan once dusen hata: satiri yine de serbest birak.
    const mesaj = (hata as Error).message;
    if (burstId) {
      await yaz("UPDATE burst SET ended_at = UTC_TIMESTAMP(3), stats = ? WHERE id = ?", [
        JSON.stringify({ hata: mesaj }),
        burstId,
      ]).catch(() => {});
    }
    await geriAl(is.keywordGeoId, `burst ${burstId || "-"}: ${mesaj}`).catch(() => {});
  }
}

export const isci = new Worker<Is>("olcum", (is) => calistir(is.data), {
  connection: baglanti,
  concurrency: 4,
  // Kilit, en uzun burst'ten uzun tutulur: süreç yeniden başlarsa iş "stalled"
  // sayılıp bir kez daha denenir, sonsuz döngüye girmez.
  lockDuration: 1_200_000,
  stalledInterval: 30_000,
  maxStalledCount: 2,
});

isci.on("failed", (is, hata) => {
  if (is) void geriAl(is.data.keywordGeoId, `iş ${is.id}: ${hata.message}`);
});
