/**
 * API davranış testleri.
 *
 * Gerçek veritabanı ve Redis kullanılır; oturum cookie'si ajan üzerinde
 * taşınır. Kimlik bilgileri .env ve seed ile aynı olmalı.
 */
import "dotenv/config";
import request from "supertest";
import { beforeAll, describe, expect, it } from "vitest";
import uygulama from "./uygulama.js";

const EPOSTA = "yonetici@ornek.com";
const PAROLA = "PanelParola2026!";

const ajan = request.agent(uygulama);
let baslik: Record<string, string> = {};

beforeAll(async () => {
  const ilk = await ajan.get("/api/token");
  const giris = await ajan
    .post("/api/giris")
    .set("x-csrf-token", ilk.body.token)
    .send({ eposta: EPOSTA, sifre: PAROLA });
  baslik = { "x-csrf-token": giris.body.token };
});

describe("giriş", () => {
  it("oturumsuz istekte 401 döner", async () => {
    const yanit = await request(uygulama).get("/api/site");
    expect(yanit.status).toBe(401);
  });

  it("yanlış parolada 401 döner", async () => {
    // Ayrı ajan: token'ı kendi oturumunda üretmeli, yoksa 403 düşer.
    const diger = request.agent(uygulama);
    const ilk = await diger.get("/api/token");
    const yanit = await diger
      .post("/api/giris")
      .set("x-csrf-token", ilk.body.token)
      .send({ eposta: EPOSTA, sifre: "yanlisparola" });
    expect(yanit.status).toBe(401);
  });
});

describe("site ve kelime", () => {
  const domain = `test-${Date.now()}.test`;
  let siteId = 0;

  it("site ekler", async () => {
    const yanit = await ajan.post("/api/site").set(baslik).send({ domain });
    expect(yanit.status).toBe(201);
    siteId = yanit.body.id;
  });

  it("aynı alan adında 409 döner", async () => {
    const yanit = await ajan.post("/api/site").set(baslik).send({ domain });
    expect(yanit.status).toBe(409);
  });

  it("national kelimede 81 geo satırı üretir", async () => {
    const yanit = await ajan
      .post("/api/kelime")
      .set(baslik)
      .send({ site_id: siteId, kelime: "national kelime", kapsam: "national" });
    expect(yanit.status).toBe(201);
    expect(yanit.body.geo_adet).toBe(81);
  });

  it("province kelimede il yoksa 400 döner", async () => {
    const yanit = await ajan
      .post("/api/kelime")
      .set(baslik)
      .send({ site_id: siteId, kelime: "ilsiz kelime", kapsam: "province" });
    expect(yanit.status).toBe(400);
    expect(yanit.body.alan).toBe("il");
  });

  it("province kelimede tek satır üretir", async () => {
    const yanit = await ajan
      .post("/api/kelime")
      .set(baslik)
      .send({ site_id: siteId, kelime: "il kelimesi", kapsam: "province", il: 34 });
    expect(yanit.status).toBe(201);
    expect(yanit.body.geo_adet).toBe(1);
  });

  it("siteyi silince kelimeleri de gider", async () => {
    const yanit = await ajan.delete(`/api/site/${siteId}`).set(baslik);
    expect(yanit.status).toBe(204);
  });
});