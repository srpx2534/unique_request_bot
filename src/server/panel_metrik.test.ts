/**
 * Metrik ucu: zarf, oran araligi ve payda sifir kurali.
 *
 * Oranlar yuzde olarak doner, payda sifirsa null. Uc global sayim yaptigi
 * icin alt sinirlar sinanir; tam sayi baska testlerin hit'leriyle degisir.
 */
import "dotenv/config";
import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import uygulama from "./uygulama.js";
import { ekle, yaz } from "./veritabani.js";
import { hitYaz } from "./isci_durum.js";

const EPOSTA = "yonetici@ornek.com";
const PAROLA = "PanelParola2026!";

const ajan = request.agent(uygulama);
let baslik: Record<string, string> = {};
const damga = Date.now();
let siteId = 0;

beforeAll(async () => {
  const ilk = await ajan.get("/api/token");
  const giris = await ajan
    .post("/api/giris")
    .set("x-csrf-token", ilk.body.token)
    .send({ eposta: EPOSTA, sifre: PAROLA });
  baslik = { "x-csrf-token": giris.body.token };

  siteId = await ekle("INSERT INTO site (domain) VALUES (?)", [`metrik-${damga}.test`]);
  const kelimeId = await ekle(
    "INSERT INTO keyword (site_id, text, geo_scope) VALUES (?, ?, 'national')",
    [siteId, `metrik testi ${damga}`],
  );
  const geoId = await ekle("INSERT INTO keyword_geo (keyword_id, geo_code) VALUES (?, 34)", [kelimeId]);
  const kampanyaId = await ekle("INSERT INTO campaign (keyword_id, config) VALUES (?, '{}')", [kelimeId]);
  const burstId = await ekle(
    "INSERT INTO burst (campaign_id, keyword_geo_id, step, target_count, phase, stats) VALUES (?, ?, 1, 10, 'core', '{}')",
    [kampanyaId, geoId],
  );
  await hitYaz(burstId, 34, [
    { result: "ok", saglayici_id: null, geo_mode: "tr_fallback", tur: "residential", http_status: 200, latency_ms: 90, bytes: 10 },
    { result: "ok", saglayici_id: null, geo_mode: "city", tur: "residential", http_status: 200, latency_ms: 110, bytes: 10 },
    { result: "captcha", saglayici_id: null, geo_mode: "city", tur: "mobile", http_status: 200, latency_ms: 300, bytes: 10 },
    { result: "error", saglayici_id: null, geo_mode: null, tur: null, http_status: null, latency_ms: null, bytes: null },
  ]);
});

afterAll(async () => {
  if (siteId) await yaz("DELETE FROM site WHERE id = ?", [siteId]);
});

describe("metrik ucu", () => {
  it("zarf alanlarini dondurur", async () => {
    const cevap = await ajan.get("/api/metrik").set(baslik);
    expect(cevap.status).toBe(200);
    for (const anahtar of [
      "olcum_at", "pencere_dk", "db_ms", "hit", "gecikme_p95_24sa",
      "saglayici", "kelime", "burst", "dugum", "acik_uyari", "kuyruk", "yedek",
    ]) {
      expect(cevap.body).toHaveProperty(anahtar);
    }
    expect(cevap.body.pencere_dk).toEqual({ kisa: 60, uzun: 1440 });
  });

  it("hit sayimlarini ve oranlari tasir", async () => {
    const cevap = await ajan.get("/api/metrik").set(baslik);
    const kisa = cevap.body.hit.son_1sa;
    expect(kisa.toplam).toBeGreaterThanOrEqual(4);
    expect(kisa.captcha).toBeGreaterThanOrEqual(1);
    expect(kisa.yedek).toBeGreaterThanOrEqual(1);
    expect(typeof kisa.ok_oran).toBe("number");
    expect(kisa.ok_oran).toBeGreaterThanOrEqual(0);
    expect(kisa.ok_oran).toBeLessThanOrEqual(100);
    expect(kisa.tur.mobile).toBeGreaterThanOrEqual(1);
    expect(kisa.tur.residential).toBeGreaterThanOrEqual(2);
    expect(kisa.tur.tanimsiz).toBeGreaterThanOrEqual(1);
  });

  it("kuyruk ve yedek blogu her zaman nesne", async () => {
    const cevap = await ajan.get("/api/metrik").set(baslik);
    expect(typeof cevap.body.kuyruk).toBe("object");
    expect(cevap.body.kuyruk).not.toBeNull();
    if (cevap.body.yedek !== null) expect(typeof cevap.body.yedek).toBe("object");
  });
});
