/**
 * Sayfalı liste uçları: OFFSET gerçekten uygulanıyor mu.
 *
 * Her iki uç `LIMIT ?` yazıp iki değer bağlıyordu; mysql2 fazla değeri
 * sessizce düşürdüğü için OFFSET hiç gönderilmiyor ve her sayfa 1. sayfayı
 * tekrarlıyordu. Burada ikinci sayfanın ayrı satırlar döndürdüğü görülür.
 */
import "dotenv/config";
import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import uygulama from "./uygulama.js";
import { kimlik } from "./test_kimlik.js";
import { ekle, tek, yaz } from "./veritabani.js";
import { hitYaz } from "./isci_durum.js";

const { eposta: EPOSTA, parola: PAROLA } = kimlik();

const ajan = request.agent(uygulama);
let baslik: Record<string, string> = {};
const damga = Date.now();
let siteId = 0;
let ilkBurst = 0;
const uyariIdler: number[] = [];

beforeAll(async () => {
  const ilk = await ajan.get("/api/token");
  const giris = await ajan
    .post("/api/giris")
    .set("x-csrf-token", ilk.body.token)
    .send({ eposta: EPOSTA, sifre: PAROLA });
  baslik = { "x-csrf-token": giris.body.token };

  siteId = await ekle("INSERT INTO site (domain) VALUES (?)", [`sayfa-${damga}.test`]);
  const kelimeId = await ekle(
    "INSERT INTO keyword (site_id, text, geo_scope) VALUES (?, ?, 'national')",
    [siteId, `sayfa testi ${damga}`],
  );
  const geoId = await ekle("INSERT INTO keyword_geo (keyword_id, geo_code) VALUES (?, 34)", [kelimeId]);
  const kampanyaId = await ekle("INSERT INTO campaign (keyword_id, config) VALUES (?, '{}')", [kelimeId]);
  for (let i = 1; i <= 3; i += 1) {
    const burstId = await ekle(
      "INSERT INTO burst (campaign_id, keyword_geo_id, step, target_count, phase, stats) VALUES (?, ?, ?, 10, 'core', '{}')",
      [kampanyaId, geoId, i],
    );
    if (i === 1) ilkBurst = burstId;
  }
  for (let i = 1; i <= 3; i += 1) {
    uyariIdler.push(
      await ekle("INSERT INTO alert (kind, message) VALUES ('failover', ?)", [`sayfa ${damga} ${i}`]),
    );
  }
});

afterAll(async () => {
  for (const id of uyariIdler) await yaz("DELETE FROM alert WHERE id = ?", [id]);
  if (siteId) await yaz("DELETE FROM site WHERE id = ?", [siteId]);
});

describe("log sayfalaması", () => {
  it("ikinci sayfa ilk sayfadan farklı satır verir", async () => {
    const bir = await ajan.get("/api/log?adet=2&sayfa=1&site=sayfa-" + damga + ".test").set(baslik);
    const iki = await ajan.get("/api/log?adet=2&sayfa=2&site=sayfa-" + damga + ".test").set(baslik);
    expect(bir.status).toBe(200);
    expect(iki.status).toBe(200);
    expect(bir.body.satirlar).toHaveLength(2);
    expect(iki.body.satirlar).toHaveLength(1);
    const ilkIdler = bir.body.satirlar.map((s: { id: number }) => s.id);
    const ikinciIdler = iki.body.satirlar.map((s: { id: number }) => s.id);
    expect(ilkIdler.filter((id: number) => ikinciIdler.includes(id))).toHaveLength(0);
    expect(bir.body.toplam).toBe(3);
  });
});

describe("uyarı sayfalaması", () => {
  it("ikinci sayfa ilk sayfadan farklı satır verir", async () => {
    const bir = await ajan.get(`/api/uyari?adet=2&sayfa=1&durum=acik&aralik=hepsi&q=sayfa ${damga}`).set(baslik);
    const iki = await ajan.get(`/api/uyari?adet=2&sayfa=2&durum=acik&aralik=hepsi&q=sayfa ${damga}`).set(baslik);
    expect(bir.status).toBe(200);
    expect(iki.status).toBe(200);
    expect(bir.body.satirlar).toHaveLength(2);
    expect(iki.body.satirlar).toHaveLength(1);
    const ilkIdler = bir.body.satirlar.map((s: { id: number }) => s.id);
    const ikinciIdler = iki.body.satirlar.map((s: { id: number }) => s.id);
    expect(ilkIdler.filter((id: number) => ikinciIdler.includes(id))).toHaveLength(0);
    expect(bir.body.toplam).toBe(3);
  });
});
describe("hit modalitesi", () => {
  it("hitYaz tur degerini yazar", async () => {
    await hitYaz(ilkBurst, 34, [
      {
        result: "ok",
        saglayici_id: null,
        geo_mode: "tr_fallback",
        tur: "mobile",
        http_status: 200,
        latency_ms: 120,
        bytes: 900,
      },
    ]);
    const satir = await tek<{ tur: string }>(
      "SELECT tur FROM hit WHERE burst_id = ? ORDER BY id DESC LIMIT 1",
      [ilkBurst],
    );
    expect(satir?.tur).toBe("mobile");
  });

  it("saglayicisiz hit'te tur NULL kalir", async () => {
    await hitYaz(ilkBurst, 34, [
      {
        result: "error",
        saglayici_id: null,
        geo_mode: null,
        tur: null,
        http_status: null,
        latency_ms: null,
        bytes: null,
      },
    ]);
    const satir = await tek<{ tur: string | null }>(
      "SELECT tur FROM hit WHERE burst_id = ? ORDER BY id DESC LIMIT 1",
      [ilkBurst],
    );
    expect(satir?.tur).toBeNull();
  });
});
