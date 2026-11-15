/** Bolumleme yardimcilari; veritabanina cikmaz. */
import { describe, expect, it } from "vitest";

import { bolumAdi, bolumTanimi, eksikGunler, gunEkle, gunMetni } from "./bolum.js";

const BUGUN = new Date("2026-11-15T03:00:00Z");

describe("bolum adlandirma", () => {
  it("gun metnini ISO biciminde yazar", () => {
    expect(gunMetni(BUGUN)).toBe("2026-11-15");
  });

  it("bolum adini sikistirir", () => {
    expect(bolumAdi(BUGUN)).toBe("p20261115");
  });

  it("gunu ay sinirinda kaydirir", () => {
    expect(gunMetni(gunEkle(new Date("2026-11-30T00:00:00Z"), 1))).toBe("2026-12-01");
  });
});

describe("bolum tanimi", () => {
  it("gunu kendi ust sinirina dahil eder", () => {
    expect(bolumTanimi(BUGUN)).toBe(
      "PARTITION p20261115 VALUES LESS THAN (TO_DAYS('2026-11-15') + 1)",
    );
  });
});

describe("eksik gunler", () => {
  it("var olan gunu atlar", () => {
    const varOlan = new Set(["p20261116"]);
    const eksik = eksikGunler(varOlan, BUGUN, 3).map(bolumAdi);
    expect(eksik).toEqual(["p20261117", "p20261118"]);
  });

  it("hepsi varsa bos doner", () => {
    const varOlan = new Set(["p20261116", "p20261117"]);
    expect(eksikGunler(varOlan, BUGUN, 2)).toEqual([]);
  });

  it("bugunu istemez", () => {
    const eksik = eksikGunler(new Set(), BUGUN, 1).map(bolumAdi);
    expect(eksik).toEqual(["p20261116"]);
  });
});