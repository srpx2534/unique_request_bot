/**
 * Rapor sayaçları: planlanan ile gerçekleşen ayrı mı, kelime tam eşleşiyor mu.
 *
 * `target_count` planlanan sayıdır; erken durdurulan burst'te gerçekleşenden
 * büyük kalır. Toplam hit bu yüzden hit satırlarından sayılmalı, planlanan
 * ayrı dönmeli. Rapor filtresi de seçmeli olduğu için kelime tam eşleşir.
 */
import "dotenv/config";
import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import uygulama from "./uygulama.js";
import { kimlik } from "./test_kimlik.js";
import { ekle, yaz } from "./veritabani.js";
import { hitYaz } from "./isci_durum.js";

const { eposta: EPOSTA, parola: PAROLA } = kimlik();

const ajan = request.agent(uygulama);
let baslik: Record<string, string> = {};
const damga = Date.now();
const domain = `rapor-${damga}.test`;
let siteId = 0;

beforeAll(async () => {
  const ilk = await ajan.get("/api/token");
  const giris = await ajan
    .post("/api/giris")
    .set("x-csrf-token", ilk.body.token)
    .send({ eposta: EPOSTA, sifre: PAROLA });
  baslik = { "x-csrf-token": giris.body.token };

  siteId = await ekle("INSERT INTO site (domain) VALUES (?)", [domain]);
  const kelimeId = await ekle(
    "INSERT INTO keyword (site_id, text, geo_scope) VALUES (?, ?, 'national')",
    [siteId, `rapor testi ${damga}`],
  );
  const geoId = await ekle("INSERT INTO keyword_geo (keyword_id, geo_code) VALUES (?, 34)", [kelimeId]);
  const kampanyaId = await ekle("INSERT INTO campaign (keyword_id, config) VALUES (?, '{}')", [kelimeId]);
  // Planlanan 10, gerçekleşen 2: ikisi ayrışmazsa test kırılır.
  const burstId = await ekle(
    "INSERT INTO burst (campaign_id, keyword_geo_id, step, target_count, phase, stats) VALUES (?, ?, 1, 10, 'core', '{}')",
    [kampanyaId, geoId],
  );
  await hitYaz(burstId, null, [
    { result: "ok", saglayici_id: null, geo_mode: "tr_fallback", tur: null,
      http_status: 200, latency_ms: 100, bytes: 10 },
    { result: "not_found", saglayici_id: null, geo_mode: "tr_fallback", tur: null,
      http_status: 200, latency_ms: 90, bytes: 5 },
  ]);
});

afterAll(async () => {
  if (siteId) await yaz("DELETE FROM site WHERE id = ?", [siteId]);
});

describe("rapor sayaçları", () => {
  it("gerçekleşen hit sayılır, planlanan ayrı döner", async () => {
    const yanit = await ajan.get(`/api/rapor?aralik=hepsi&site=${domain}`).set(baslik);
    expect(yanit.status).toBe(200);
    expect(yanit.body.ozet.hit).toBe(2);
    expect(yanit.body.ozet.ok).toBe(1);
    expect(yanit.body.ozet.not_found).toBe(1);
    expect(yanit.body.ozet.planlanan).toBe(10);
    expect(yanit.body.ozet.burst).toBe(1);
  });

  it("kelime süzgeci tam eşleşir", async () => {
    const tam = await ajan
      .get(`/api/rapor?aralik=hepsi&site=${domain}&kelime=rapor testi ${damga}`)
      .set(baslik);
    expect(tam.body.ozet.hit).toBe(2);
    const parca = await ajan.get(`/api/rapor?aralik=hepsi&site=${domain}&kelime=rapor`).set(baslik);
    expect(parca.body.ozet.hit).toBe(0);
  });
});
