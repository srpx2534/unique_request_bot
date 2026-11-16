/**
 * Günlük modülü testleri.
 *
 * Ağa ve veritabanına çıkmaz; çıktı yakalanır. Seviye eşiği, etiketin
 * bağlama taşınması ve hata nesnesinin mesajı kilitlenir.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { gunluk } from "./gunluk.js";

let cikti: string[] = [];

beforeEach(() => {
  cikti = [];
  vi.spyOn(console, "log").mockImplementation((s: string) => void cikti.push(s));
  vi.spyOn(console, "error").mockImplementation((s: string) => void cikti.push(s));
  delete process.env.GUNLUK_SEVIYE;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("günlük", () => {
  it("JSON satırı ve bağlam üretir", () => {
    gunluk.bilgi("[isci]", "iş bitti");
    const kayit = JSON.parse(cikti[0]!);
    expect(kayit.s).toBe("bilgi");
    expect(kayit.b).toBe("isci");
    expect(kayit.m).toBe("iş bitti");
    expect(kayit.z).toMatch(/^\d{4}-/);
  });

  it("hata nesnesini mesajıyla yazar", () => {
    gunluk.hata("[redis]", new Error("bağlantı yok"));
    const kayit = JSON.parse(cikti[0]!);
    expect(kayit.m).toBe("bağlantı yok");
  });

  it("ayrıntı varsayılan eşikte basılmaz", () => {
    gunluk.ayrinti("[x]", "gizli ayrıntı");
    expect(cikti).toHaveLength(0);
  });

  it("eşik düşürülünce ayrıntı basılır", () => {
    process.env.GUNLUK_SEVIYE = "ayrinti";
    gunluk.ayrinti("[x]", "ayrıntı");
    expect(cikti).toHaveLength(1);
  });

  it("eşik yükseltilince bilgi basılmaz", () => {
    process.env.GUNLUK_SEVIYE = "hata";
    gunluk.bilgi("[x]", "bilgi");
    expect(cikti).toHaveLength(0);
  });

  it("etiket yoksa bağlam boş kalır", () => {
    gunluk.bilgi("düz mesaj");
    expect(JSON.parse(cikti[0]!).b).toBe("");
  });
});
