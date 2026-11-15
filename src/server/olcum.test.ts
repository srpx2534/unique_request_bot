/** Olcum araligi 15 dakikayi asmaz (C12). */
import { describe, expect, it, vi } from "vitest";

const ayarOku = vi.fn();
vi.mock("./veritabani.js", () => ({ sorgu: vi.fn(), yaz: vi.fn(), tek: vi.fn() }));
vi.mock("./ayar.js", () => ({ ayarOku, serpSecim: vi.fn() }));

const { aralikDk } = await import("./olcum.js");

describe("olcum araligi", () => {
  it("ayar yoksa 15 dk", async () => {
    ayarOku.mockResolvedValue("0");
    expect(await aralikDk()).toBe(15);
  });

  it("kucuk deger korunur", async () => {
    ayarOku.mockResolvedValue("5");
    expect(await aralikDk()).toBe(5);
  });

  it("buyuk deger 15e kirpilir", async () => {
    ayarOku.mockResolvedValue("60");
    expect(await aralikDk()).toBe(15);
  });

  it("negatif deger 15 sayilir", async () => {
    ayarOku.mockResolvedValue("-3");
    expect(await aralikDk()).toBe(15);
  });
});