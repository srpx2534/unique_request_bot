/** keyword_geo dağılımı: sözleşme §7 sayıları. */
import { describe, expect, it } from "vitest";
import { dagitim } from "./geo.js";

const kodlar = Array.from({ length: 81 }, (_, i) => i + 1);

describe("dagitim", () => {
  it("national kelimede 81 satır üretir", () => {
    expect(dagitim(kodlar, "national")).toHaveLength(81);
  });

  it("dağılım 10 core, 30 normal, 41 passive olur", () => {
    const sayim = dagitim(kodlar, "national").reduce<Record<string, number>>((acc, s) => {
      acc[s.tier] = (acc[s.tier] ?? 0) + 1;
      return acc;
    }, {});
    expect(sayim).toEqual({ core: 10, normal: 30, passive: 41 });
  });

  it("core dilim ilk 10 ili alır", () => {
    const core = dagitim(kodlar, "national").filter((s) => s.tier === "core");
    expect(core.map((s) => s.kod)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  });

  it("province kelimede tek core satır üretir", () => {
    expect(dagitim(kodlar, "province", 34)).toEqual([{ kod: 34, tier: "core" }]);
  });

  it("province kelimede il yoksa hata verir", () => {
    expect(() => dagitim(kodlar, "province", null)).toThrow(/il zorunlu/);
  });

  it("il listesi 81 değilse hata verir", () => {
    expect(() => dagitim(kodlar.slice(0, 80), "national")).toThrow(/81 il/);
  });
});