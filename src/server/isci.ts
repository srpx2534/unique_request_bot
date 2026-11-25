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
import { ekle, sorgu, tek, yaz } from "./veritabani.js";
import {
  type MotorHiti, geriAl, hedefDenetle, hedefYokDenetle, hitYaz,
} from "./isci_durum.js";
export { hedefYokDenetle } from "./isci_durum.js";
import { dugumSec } from "./dugum_sec.js";
import { SAHIP, cakismaYaz, devral } from "./kilit.js";

const TOKEN = process.env.WORKER_TOKEN ?? "";
// 60 hit'lik burst dwell ve pogo ile dakikalar sürebilir; kısa sınır işi ortada keser.
const ZAMAN_ASIMI_MS = 900_000;




type MotorCevabi = {
  ok?: number;
  captcha?: number;
  not_found?: number;
  hedef_yok?: number;
  timeout?: number;
  error?: number;
  stats?: Record<string, number>;
  hits?: MotorHiti[];
};

/** Havuz boş uyarısı; 30 dakika sessizlikle tek satır yazılır. */
async function havuzBosUyar(): Promise<void> {
  const acik = await tek<{ adet: number }>(
    `SELECT COUNT(*) AS adet FROM alert
      WHERE kind = 'provider_down' AND acknowledged = 0
        AND message LIKE 'havuz boş%'
        AND created_at > UTC_TIMESTAMP(3) - INTERVAL 30 MINUTE`,
  );
  if (acik?.adet) return;
  await yaz("INSERT INTO alert (kind, message) VALUES ('provider_down', ?)", [
    "havuz boş: kullanılabilir sağlayıcı yok, işler bekliyor",
  ]);
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
    geo_scope: string;
  }>(
    `SELECT g.burst_count, geo.uule, s.domain, g.geo_code, c.step_size, k.geo_scope
       FROM keyword_geo g
       JOIN geo ON geo.code = g.geo_code
       JOIN keyword k ON k.id = g.keyword_id
       JOIN site s ON s.id = k.site_id
       JOIN campaign c ON c.id = ?
      WHERE g.id = ?`,
    [is.campaignId, is.keywordGeoId],
  );
  if (!satir) return;

  // Havuzda kullanılabilir sağlayıcı yoksa iş başlamaz (C69): kelime boşuna
  // dönmesin, satır beklemede kalsın ve tek bir uyarı düşsün.
  const havuz = await tek<{ adet: number }>(
    `SELECT COUNT(*) AS adet FROM provider
      WHERE state = 'active' AND gateway IS NOT NULL
        AND (quarantine_until IS NULL OR quarantine_until < UTC_TIMESTAMP(3))`,
  );
  if (!havuz?.adet) {
    await havuzBosUyar();
    await geriAl(is.keywordGeoId, "kullanılabilir sağlayıcı yok");
    return;
  }

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
  // yeniden sahiplenilir. Sahiplik ve süre kilit modülünde; başka düğümün taze
  // kilidi varsa iş atlanır, uyarı yazılır, işçi durmaz.
  const alindi = await devral(is.keywordGeoId);
  if (!alindi) {
    if (!yeniden) {
      await yaz("DELETE FROM burst WHERE id = ?", [burstId]);
      await cakismaYaz(is.keywordGeoId, null);
      return;
    }
    await yaz(
      `UPDATE keyword_geo
          SET state = 'running', kilit_dugum = ?, kilit_at = UTC_TIMESTAMP(3),
              last_burst_at = UTC_TIMESTAMP(3)
        WHERE id = ?`,
      [SAHIP, is.keywordGeoId],
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
      geo_scope: satir.geo_scope,
      uule: satir.geo_scope === "province" ? satir.uule : null,
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
    // Boşaltma ya da durdurma 503'ü hata değildir: burst kapanır, iş kısa süre
    // sonra yeniden denenir; sağlayıcı sağlık sayacı bu yüzden artmaz (E4).
    // 503 kontrolü `!yanit.ok`'tan ÖNCE gelir: 503 de `ok` değildir, aksi
    // hâlde aşağıdaki blok ölü kod kalıyor ve iş hata gibi kapanıyordu.
    if (yanit.status === 503) {
      const govde503 = (await yanit.json().catch(() => ({}))) as { hata?: string };
      const sebep = govde503.hata ?? "düğüm meşgul";
      await yaz("UPDATE burst SET ended_at = UTC_TIMESTAMP(3), stats = ? WHERE id = ?", [
        JSON.stringify({ hata: sebep }), burstId,
      ]);
      await geriAl(is.keywordGeoId, `düğüm 503: ${sebep}`);
      return;
    }

    // 503 disindaki basarisiz yanit gercek hatadir; 503 yukarida ele alindi.
    if (!yanit.ok) throw new Error(`motor ${yanit.status}`);
    const govde = (await yanit.json()) as MotorCevabi;
    // Ulusal kelimede il kolonu bos kalir; il yalniz il kapsaminda yazilir.
    await hitYaz(burstId, satir.geo_scope === "province" ? satir.geo_code : null, govde.hits ?? []);
    // Sayaçlar burst satırına yazılır; log ve rapor buradan okur.
    const sayac = {
      ok: govde.ok ?? 0,
      captcha: govde.captcha ?? 0,
      not_found: govde.not_found ?? 0,
      hedef_yok: govde.hedef_yok ?? 0,
      timeout: govde.timeout ?? 0,
      error: govde.error ?? 0,
    };
    await yaz("UPDATE burst SET ended_at = UTC_TIMESTAMP(3), stats = ? WHERE id = ?", [
      JSON.stringify(sayac),
      burstId,
    ]);
    await yaz(
      "UPDATE keyword_geo SET state = 'pending', kilit_dugum = NULL, kilit_at = NULL, burst_count = burst_count + 1, last_burst_at = NOW(3) WHERE id = ?",
      [is.keywordGeoId],
    );
    await hedefDenetle(is.keywordId);
    await hedefYokDenetle(is.keywordId, is.keywordGeoId);
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


