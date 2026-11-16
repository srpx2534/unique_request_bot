/**
 * Tür oranı ucu: üç değer birlikte yazılır, toplam 100 olmak zorunda.
 *
 * Oranlar `ayar` tablosunda satır olarak durur, arayüzü Sağlayıcılar
 * ekranındadır. Genel PATCH /ayar oran_* anahtarlarını atladığı için ekrandan
 * kaydetme sessizce boşa gidiyordu: istek 200 dönüyor, tablo değişmiyordu.
 */
import "dotenv/config";
import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import uygulama from "./uygulama.js";
import { kimlik } from "./test_kimlik.js";
import { sorgu, yaz } from "./veritabani.js";

const { eposta: EPOSTA, parola: PAROLA } = kimlik();
const ANAHTARLAR = ["oran_residential", "oran_mobil", "oran_datacenter"];

const ajan = request.agent(uygulama);
let baslik: Record<string, string> = {};
let onceki: Record<string, string> = {};

async function oku(): Promise<Record<string, string>> {
  const satirlar = await sorgu<{ anahtar: string; deger: string }>(
    `SELECT anahtar, deger FROM ayar WHERE anahtar IN (${ANAHTARLAR.map(() => "?").join(",")})`,
    ANAHTARLAR,
  );
  return Object.fromEntries(satirlar.map((s) => [s.anahtar, s.deger]));
}

beforeAll(async () => {
  const ilk = await ajan.get("/api/token");
  const giris = await ajan
    .post("/api/giris")
    .set("x-csrf-token", ilk.body.token)
    .send({ eposta: EPOSTA, sifre: PAROLA });
  baslik = { "x-csrf-token": giris.body.token };
  onceki = await oku();
});

afterAll(async () => {
  for (const anahtar of ANAHTARLAR) {
    if (onceki[anahtar] === undefined) {
      await yaz("DELETE FROM ayar WHERE anahtar = ?", [anahtar]);
      continue;
    }
    await yaz("UPDATE ayar SET deger = ? WHERE anahtar = ?", [onceki[anahtar], anahtar]);
  }
});

describe("tür oranı", () => {
  it("toplam 100 ise üçünü birlikte yazar", async () => {
    const yanit = await ajan
      .patch("/api/ayar/oran")
      .set(baslik)
      .send({ oran_residential: 60, oran_mobil: 30, oran_datacenter: 10 });
    expect(yanit.status).toBe(200);
    expect(await oku()).toMatchObject({
      oran_residential: "60",
      oran_mobil: "30",
      oran_datacenter: "10",
    });
  });

  it("toplam 100 değilse 400 döner ve yazmaz", async () => {
    const yanit = await ajan
      .patch("/api/ayar/oran")
      .set(baslik)
      .send({ oran_residential: 50, oran_mobil: 0, oran_datacenter: 0 });
    expect(yanit.status).toBe(400);
    expect(yanit.body.alan).toBe("oran");
    expect((await oku()).oran_residential).toBe("60");
  });

  it("değer metin olarak da kabul edilir", async () => {
    const yanit = await ajan
      .patch("/api/ayar/oran")
      .set(baslik)
      .send({ oran_residential: "10", oran_mobil: "10", oran_datacenter: "80" });
    expect(yanit.status).toBe(200);
    expect((await oku()).oran_datacenter).toBe("80");
  });

  it("satırlar yokken yazar ve satırları doğurur", async () => {
    await yaz(`DELETE FROM ayar WHERE anahtar IN (${ANAHTARLAR.map(() => "?").join(",")})`, ANAHTARLAR);
    expect(await oku()).toEqual({});
    const yanit = await ajan
      .patch("/api/ayar/oran")
      .set(baslik)
      .send({ oran_residential: 70, oran_mobil: 20, oran_datacenter: 10 });
    expect(yanit.status).toBe(200);
    expect(await oku()).toMatchObject({ oran_residential: "70", oran_mobil: "20" });
  });

  it("genel PATCH oranlara dokunmaz", async () => {
    const yanit = await ajan.patch("/api/ayar").set(baslik).send({ oran_mobil: "99" });
    expect(yanit.status).toBe(200);
    expect((await oku()).oran_mobil).toBe("20");
  });
});
