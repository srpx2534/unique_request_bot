/**
 * Basamaklı silme: site, kelime ve sağlayıcı.
 *
 * `hit` tablosunda FK yok; bağlı kayıtlar açıkça silinmeli. Sağlayıcı
 * silmede ise ölçüm geçmişi korunur, `provider_id` ve `profile_id` koparılır.
 */
import "dotenv/config";
import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import uygulama from "./uygulama.js";
import { ekle, tek, yaz } from "./veritabani.js";
import { hitYaz } from "./isci_durum.js";

const EPOSTA = "yonetici@ornek.com";
const PAROLA = "PanelParola2026!";

const ajan = request.agent(uygulama);
let baslik: Record<string, string> = {};
const damga = Date.now();
const siteler: number[] = [];
const saglayicilar: number[] = [];

/** Tek satırlık sayım. */
async function say(sql: string, parametreler: unknown[]): Promise<number> {
  return Number((await tek<{ a: number }>(sql, parametreler))?.a ?? 0);
}

/** Site + kelime + geo + kampanya + burst kurar. */
async function kur(etiket: string) {
  const siteId = await ekle("INSERT INTO site (domain) VALUES (?)", [`sil-${etiket}-${damga}.test`]);
  siteler.push(siteId);
  const kelimeId = await ekle(
    "INSERT INTO keyword (site_id, text, geo_scope) VALUES (?, ?, 'national')",
    [siteId, `${etiket} ${damga}`],
  );
  const geoId = await ekle("INSERT INTO keyword_geo (keyword_id, geo_code) VALUES (?, 34)", [kelimeId]);
  const kampanyaId = await ekle("INSERT INTO campaign (keyword_id, config) VALUES (?, '{}')", [kelimeId]);
  const burstId = await ekle(
    "INSERT INTO burst (campaign_id, keyword_geo_id, step, target_count, phase, stats) VALUES (?, ?, 1, 10, 'core', '{}')",
    [kampanyaId, geoId],
  );
  return { siteId, kelimeId, geoId, burstId };
}

/** Tek hit yazar. */
async function hit(burstId: number, saglayiciId: number | null = null): Promise<void> {
  await hitYaz(burstId, 34, [
    {
      result: "ok",
      saglayici_id: saglayiciId,
      geo_mode: "city",
      tur: "residential",
      http_status: 200,
      latency_ms: 100,
      bytes: 10,
    },
  ]);
}

beforeAll(async () => {
  const ilk = await ajan.get("/api/token");
  const giris = await ajan
    .post("/api/giris")
    .set("x-csrf-token", ilk.body.token)
    .send({ eposta: EPOSTA, sifre: PAROLA });
  baslik = { "x-csrf-token": giris.body.token };
});

afterAll(async () => {
  for (const id of siteler) await ajan.delete(`/api/site/${id}`).set(baslik);
  for (const id of saglayicilar) await ajan.delete(`/api/provider/${id}`).set(baslik);
});

describe("kelime silme", () => {
  it("hit, burst, geo ve kampanyayı birlikte götürür", async () => {
    const f = await kur("kelime");
    await hit(f.burstId);

    const cevap = await ajan.delete(`/api/kelime/${f.kelimeId}`).set(baslik);
    expect(cevap.status).toBe(204);
    expect(await say("SELECT COUNT(*) AS a FROM hit WHERE burst_id = ?", [f.burstId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM burst WHERE id = ?", [f.burstId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM keyword_geo WHERE keyword_id = ?", [f.kelimeId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM campaign WHERE keyword_id = ?", [f.kelimeId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM keyword WHERE id = ?", [f.kelimeId])).toBe(0);
  });

  it("olmayan kelimede 404 döner", async () => {
    const cevap = await ajan.delete("/api/kelime/99999999").set(baslik);
    expect(cevap.status).toBe(404);
  });
});

describe("site silme", () => {
  it("bütün kelimeleri ve hit'leri götürür", async () => {
    const bir = await kur("site-a");
    const iki = await kur("site-b");
    await yaz("UPDATE keyword SET site_id = ? WHERE id = ?", [bir.siteId, iki.kelimeId]);
    await hit(bir.burstId);

    const cevap = await ajan.delete(`/api/site/${bir.siteId}`).set(baslik);
    expect(cevap.status).toBe(204);
    expect(await say("SELECT COUNT(*) AS a FROM keyword WHERE site_id = ?", [bir.siteId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM hit WHERE burst_id = ?", [bir.burstId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM site WHERE id = ?", [bir.siteId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM site WHERE id = ?", [iki.siteId])).toBe(1);
  });

  it("olmayan sitede 404 döner", async () => {
    const cevap = await ajan.delete("/api/site/99999999").set(baslik);
    expect(cevap.status).toBe(404);
  });
});

describe("sağlayıcı silme", () => {
  it("hit olsa da siler, hit sağlayıcısız ve profilsiz kalır", async () => {
    const provId = await ekle(
      "INSERT INTO provider (name, kind, gateway) VALUES (?, 'residential', 'sil.test:1000')",
      [`sil-${damga}`],
    );
    saglayicilar.push(provId);
    await ekle("INSERT INTO provider_geo (provider_id, geo_code) VALUES (?, 34)", [provId]);
    const profilId = await ekle(
      "INSERT INTO profile (ua, ja3_profile, cookie_jar, provider_id) VALUES ('ua', 'j', '{}', ?)",
      [provId],
    );
    const f = await kur("saglayici");
    await hit(f.burstId, provId);
    await yaz("UPDATE hit SET profile_id = ? WHERE burst_id = ?", [profilId, f.burstId]);

    const cevap = await ajan.delete(`/api/provider/${provId}`).set(baslik);
    expect(cevap.status).toBe(204);
    expect(await say("SELECT COUNT(*) AS a FROM provider WHERE id = ?", [provId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM provider_geo WHERE provider_id = ?", [provId])).toBe(0);
    expect(await say("SELECT COUNT(*) AS a FROM profile WHERE id = ?", [profilId])).toBe(0);

    const kalan = await tek<{ provider_id: number | null; profile_id: number | null }>(
      "SELECT provider_id, profile_id FROM hit WHERE burst_id = ? LIMIT 1",
      [f.burstId],
    );
    expect(kalan?.provider_id).toBeNull();
    expect(kalan?.profile_id).toBeNull();
  });

  it("olmayan sağlayıcıda 404 döner", async () => {
    const cevap = await ajan.delete("/api/provider/32000").set(baslik);
    expect(cevap.status).toBe(404);
  });
});
