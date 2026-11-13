/**
 * Worker imza testleri.
 *
 * Kalp ucu kimlik doğrulamasını HMAC ile yapar; imza yoksa, yanlışsa ya da
 * `ts` penceresi dışındaysa 401 dönmelidir. Doğru imzada zincir devam eder.
 */
import { beforeAll, describe, expect, it, vi } from "vitest";
import { createHmac } from "node:crypto";
import type { RequestHandler } from "express";

const TOKEN = "test-token";
let imzaDogrula: RequestHandler;

beforeAll(async () => {
  vi.stubEnv("WORKER_TOKEN", TOKEN);
  vi.resetModules();
  ({ imzaDogrula } = await import("./worker_imza.js"));
});

type SahteYanit = { kod: number; govde: unknown };

function calistir(govde: Record<string, unknown>, imza?: string) {
  const ham = Buffer.from(JSON.stringify(govde));
  const yanit: SahteYanit = { kod: 0, govde: null };
  const sahteYanit = {
    status(kod: number) {
      yanit.kod = kod;
      return this;
    },
    json(g: unknown) {
      yanit.govde = g;
      return this;
    },
  };
  const istek = { body: govde, rawBody: ham, headers: imza ? { "x-imza": imza } : {} };
  let gecti = false;
  imzaDogrula(
    istek as never,
    sahteYanit as never,
    (() => {
      gecti = true;
    }) as never,
  );
  return { gecti, yanit };
}

function imzala(govde: Record<string, unknown>): string {
  return createHmac("sha256", TOKEN).update(Buffer.from(JSON.stringify(govde))).digest("hex");
}

const taze = () => Math.floor(Date.now() / 1000);

describe("imzaDogrula", () => {
  it("doğru imzayı geçirir", () => {
    const govde = { ip: "10.0.0.5", ts: taze() };
    const { gecti } = calistir(govde, imzala(govde));
    expect(gecti).toBe(true);
  });

  it("imza yoksa 401 döner", () => {
    const { gecti, yanit } = calistir({ ip: "10.0.0.5", ts: taze() });
    expect(gecti).toBe(false);
    expect(yanit.kod).toBe(401);
  });

  it("bozuk imzada 401 döner", () => {
    const { gecti, yanit } = calistir({ ip: "10.0.0.5", ts: taze() }, "00".repeat(32));
    expect(gecti).toBe(false);
    expect(yanit.kod).toBe(401);
  });

  it("eski ts reddedilir", () => {
    const govde = { ip: "10.0.0.5", ts: taze() - 600 };
    const { gecti, yanit } = calistir(govde, imzala(govde));
    expect(gecti).toBe(false);
    expect(yanit.kod).toBe(401);
  });

  it("gövde değişirse imza tutmaz", () => {
    const imza = imzala({ ip: "10.0.0.5", ts: taze() });
    const { gecti } = calistir({ ip: "10.0.0.9", ts: taze() }, imza);
    expect(gecti).toBe(false);
  });
});