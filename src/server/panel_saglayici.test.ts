/**
 * Sağlayıcı ekleme: kimlik veritabanından gelir.
 *
 * provider.id AUTO_INCREMENT değilken INSERT kimliksiz kalıyordu; strict modda
 * 1364 ile 500 dönüyor, gevşek modda id = 0 yazılıp ikinci eklemede
 * ER_DUP_ENTRY alınıyordu. Burada art arda ve eşzamanlı eklemelerin ayrı kimlik
 * aldığı görülür.
 */
import "dotenv/config";
import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import uygulama from "./uygulama.js";

const EPOSTA = "yonetici@ornek.com";
const PAROLA = "PanelParola2026!";

const ajan = request.agent(uygulama);
let baslik: Record<string, string> = {};
const eklenenler: number[] = [];

beforeAll(async () => {
  const ilk = await ajan.get("/api/token");
  const giris = await ajan
    .post("/api/giris")
    .set("x-csrf-token", ilk.body.token)
    .send({ eposta: EPOSTA, sifre: PAROLA });
  baslik = { "x-csrf-token": giris.body.token };
});

afterAll(async () => {
  for (const id of eklenenler) {
    await ajan.delete(`/api/provider/${id}`).set(baslik);
  }
});

describe("sağlayıcı ekleme", () => {
  it("kimlik göndermeden 201 döner ve kimlik üretir", async () => {
    const yanit = await ajan
      .post("/api/provider")
      .set(baslik)
      .send({ name: `Deneme ${Date.now()}`, kind: "residential" });
    expect(yanit.status).toBe(201);
    expect(yanit.body.id).toBeGreaterThan(0);
    eklenenler.push(yanit.body.id);
  });

  it("eşzamanlı iki ekleme ayrı kimlik alır", async () => {
    const damga = Date.now();
    const [bir, iki] = await Promise.all([
      ajan.post("/api/provider").set(baslik).send({ name: `Cift A ${damga}`, kind: "mobile" }),
      ajan.post("/api/provider").set(baslik).send({ name: `Cift B ${damga}`, kind: "mobile" }),
    ]);
    expect(bir.status).toBe(201);
    expect(iki.status).toBe(201);
    expect(bir.body.id).not.toBe(iki.body.id);
    eklenenler.push(bir.body.id, iki.body.id);
  });

  it("ad yoksa 400 döner", async () => {
    const yanit = await ajan.post("/api/provider").set(baslik).send({ kind: "residential" });
    expect(yanit.status).toBe(400);
  });
});