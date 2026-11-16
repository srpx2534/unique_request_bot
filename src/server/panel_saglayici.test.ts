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
import { kimlik } from "./test_kimlik.js";

const { eposta: EPOSTA, parola: PAROLA } = kimlik();

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
      .send({ name: `Decodo ${Date.now()}`, kind: "residential", gateway: "host:10001" });
    expect(yanit.status).toBe(201);
    expect(yanit.body.id).toBeGreaterThan(0);
    eklenenler.push(yanit.body.id);
  });

  it("eşzamanlı iki ekleme ayrı kimlik alır", async () => {
    const damga = Date.now();
    const [bir, iki] = await Promise.all([
      ajan.post("/api/provider").set(baslik).send({ name: `Cift A ${damga} Decodo`, kind: "mobile", gateway: "host:10002" }),
      ajan.post("/api/provider").set(baslik).send({ name: `Cift B ${damga} Decodo`, kind: "mobile", gateway: "host:10003" }),
    ]);
    expect(bir.status).toBe(201);
    expect(iki.status).toBe(201);
    expect(bir.body.id).not.toBe(iki.body.id);
    eklenenler.push(bir.body.id, iki.body.id);
  });

  it("ad yoksa 400 döner", async () => {
    const yanit = await ajan
      .post("/api/provider")
      .set(baslik)
      .send({ kind: "residential", gateway: "host:10004" });
    expect(yanit.status).toBe(400);
  });

  it("bilinmeyen adla da eklenir", async () => {
    const yanit = await ajan
      .post("/api/provider")
      .set(baslik)
      .send({ name: "Bilinmeyen", kind: "residential", gateway: "host:10005" });
    expect(yanit.status).toBe(201);
    eklenenler.push(yanit.body.id);
  });

  it("gateway yoksa 400 döner", async () => {
    const yanit = await ajan
      .post("/api/provider")
      .set(baslik)
      .send({ name: "Decodo bos", kind: "residential" });
    expect(yanit.status).toBe(400);
    expect(yanit.body.alan).toBe("gateway");
  });

  it("yarım kimlikte 400 döner", async () => {
    const yanit = await ajan
      .post("/api/provider")
      .set(baslik)
      .send({ name: "Decodo yarim", kind: "residential", gateway: "host:10006", kullanici: "k" });
    expect(yanit.status).toBe(400);
    expect(yanit.body.alan).toBe("kullanici");
  });

  it("düzenlemede bilinmeyen ad kabul edilir", async () => {
    const ekle = await ajan
      .post("/api/provider")
      .set(baslik)
      .send({ name: `Decodo duzenle ${Date.now()}`, kind: "residential", gateway: "host:10007" });
    eklenenler.push(ekle.body.id);

    const yanit = await ajan
      .patch(`/api/provider/${ekle.body.id}`)
      .set(baslik)
      .send({ name: "Bilinmeyen" });
    expect(yanit.status).toBe(200);
    expect(yanit.body.name).toBe("Bilinmeyen");
  });
});

