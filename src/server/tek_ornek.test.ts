/**
 * Tek örnek kilidi testleri.
 *
 * Gerçek dosya sistemi geçici dizinde kullanılır; veritabanına ve ağa
 * çıkılmaz. Sahiplik, devralma ve bırakma davranışı kilitlenir.
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { kilitAl, kilitBirak } from "./tek_ornek.js";

let dizin = "";

beforeEach(() => {
  dizin = fs.mkdtempSync(path.join(os.tmpdir(), "kilit-"));
});

afterEach(() => {
  fs.rmSync(dizin, { recursive: true, force: true });
});

describe("tek örnek kilidi", () => {
  it("kilidi alır ve kimliği yazar", () => {
    const dosya = kilitAl(dizin);
    expect(fs.readFileSync(dosya, "utf8").trim()).toBe(String(process.pid));
  });

  it("canlı sahipte ikinci alımı reddeder", () => {
    kilitAl(dizin);
    expect(() => kilitAl(dizin)).toThrow(/başka bir panel süreci/);
  });

  it("ölü sahibin kilidini devralır", () => {
    fs.writeFileSync(path.join(dizin, "panel.pid"), "999999");
    const dosya = kilitAl(dizin);
    expect(fs.readFileSync(dosya, "utf8").trim()).toBe(String(process.pid));
  });

  it("bırakınca dosya silinir", () => {
    const dosya = kilitAl(dizin);
    kilitBirak(dizin);
    expect(fs.existsSync(dosya)).toBe(false);
  });

  it("başkasının kilidini bırakmaz", () => {
    const dosya = path.join(dizin, "panel.pid");
    fs.writeFileSync(dosya, "123456");
    kilitBirak(dizin);
    expect(fs.existsSync(dosya)).toBe(true);
  });

  it("olmayan kilidi bırakmak hata vermez", () => {
    expect(() => kilitBirak(dizin)).not.toThrow();
  });
});
