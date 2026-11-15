/** Redis baglanti secenekleri: parola URL'den degil ortamdan gelir. */
import { describe, expect, it } from "vitest";
import { redisBaglanti, redisEtiket } from "./redis_baglanti.js";

describe("redisBaglanti", () => {
  it("varsayilanlara duser", () => {
    expect(redisBaglanti("", "")).toEqual({ host: "127.0.0.1", port: 6379, db: 0 });
  });

  it("host, port ve db'yi adresten okur", () => {
    expect(redisBaglanti("redis://10.0.0.5:6380/2", "")).toEqual({ host: "10.0.0.5", port: 6380, db: 2 });
  });

  it("parolayi yalnizca REDIS_PASSWORD'den alir", () => {
    expect(redisBaglanti("redis://:adreste-yazan@127.0.0.1:6379/0", "ortamdan").password).toBe("ortamdan");
  });

  it("parola yoksa alan eklemez", () => {
    expect(redisBaglanti("redis://127.0.0.1:6379/0", "")).not.toHaveProperty("password");
  });

  it("bozuk yuzde kacisi acilisi bozmaz", () => {
    expect(() => redisBaglanti("redis://:a%dfb@127.0.0.1:6379/0", "")).not.toThrow();
  });

  it("etiket parola tasimaz", () => {
    expect(redisEtiket({ host: "127.0.0.1", port: 6379, db: 0, password: "gizli" })).toBe("127.0.0.1:6379/0");
  });
});
