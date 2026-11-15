/** Kelime bazlı kilit: sahiplenme, bırakma, çakışma uyarısı, bayat temizleme. */
import { beforeEach, describe, expect, it, vi } from "vitest";

const sorgu = vi.fn();
const yaz = vi.fn();
const tek = vi.fn();
const ayarOku = vi.fn();

vi.mock("./veritabani.js", () => ({ sorgu, yaz, tek }));
vi.mock("./ayar.js", () => ({ ayarOku }));

const {
  SAHIP, bayatDenetle, cakismaYaz, devral, kilitSuresiDk, sahiplen,
} = await import("./kilit.js");

beforeEach(() => {
  sorgu.mockReset();
  yaz.mockReset();
  tek.mockReset();
  ayarOku.mockReset();
  ayarOku.mockResolvedValue("30");
});

describe("kilit süresi", () => {
  it("ayar boşsa varsayılan 30 dakika", async () => {
    ayarOku.mockResolvedValue("");
    expect(await kilitSuresiDk()).toBe(30);
  });

  it("ayar sıfırsa varsayılana düşer", async () => {
    ayarOku.mockResolvedValue("0");
    expect(await kilitSuresiDk()).toBe(30);
  });

  it("kesirli ayar en az bir dakikaya yuvarlanır", async () => {
    ayarOku.mockResolvedValue("0.4");
    expect(await kilitSuresiDk()).toBe(1);
  });
});

describe("sahiplenme", () => {
  it("satır alınırsa true döner ve sahip yazılır", async () => {
    yaz.mockResolvedValue(1);
    expect(await sahiplen(5, 25)).toBe(true);
    const [sql, p] = yaz.mock.calls[0]!;
    expect(String(sql)).toContain("kilit_at < UTC_TIMESTAMP(3)");
    expect(p[0]).toBe(SAHIP);
    expect(p[1]).toBe(25);
    expect(p[3]).toBe(1800);
  });

  it("taze kilit varsa false döner", async () => {
    yaz.mockResolvedValue(0);
    expect(await sahiplen(5, 25)).toBe(false);
  });
});

describe("devralma", () => {
  it("beş saniyelik eşik ve sahip tazelemesi korunur", async () => {
    yaz.mockResolvedValue(1);
    await devral(9);
    const [sql] = yaz.mock.calls[0]!;
    expect(String(sql)).toContain("INTERVAL 5 SECOND");
    expect(String(sql)).toContain("kilit_dugum = ?");
  });

  it("alınamazsa false döner", async () => {
    yaz.mockResolvedValue(0);
    expect(await devral(9)).toBe(false);
  });
});

describe("çakışma uyarısı", () => {
  it("sahip verilmezse satırdan okur", async () => {
    tek.mockResolvedValueOnce({ sayi: 0 }).mockResolvedValueOnce({ kilit_dugum: "baska:9" });
    await cakismaYaz(4, null);
    const [, p] = yaz.mock.calls[0]!;
    expect(p[1]).toContain("baska:9");
  });

  it("açık uyarı varsa sessiz kalır", async () => {
    tek.mockResolvedValue({ sayi: 2 });
    await cakismaYaz(4, "baska:9");
    expect(yaz).not.toHaveBeenCalled();
  });
});

describe("bayat temizleme", () => {
  it("önce ölü burstleri kapatır", async () => {
    sorgu.mockResolvedValue([]);
    await bayatDenetle();
    const [sql] = yaz.mock.calls[0]!;
    expect(String(sql)).toContain("UPDATE burst");
    expect(String(sql)).toContain("ended_at = UTC_TIMESTAMP(3)");
  });

  it("açık bursti olan satırı sıfırlamaz", async () => {
    sorgu.mockResolvedValue([]);
    await bayatDenetle();
    const [sql] = sorgu.mock.calls[0]!;
    expect(String(sql)).toContain("NOT EXISTS");
  });

  it("bayat satırları geri alır ve uyarır", async () => {
    sorgu.mockResolvedValue([{ id: 11 }, { id: 12 }]);
    tek.mockResolvedValue({ sayi: 0 });
    yaz.mockResolvedValue(2);
    expect(await bayatDenetle()).toBe(2);
    const [sql, p] = yaz.mock.calls[1]!;
    expect(String(sql)).toContain("state = 'pending'");
    expect(String(sql)).toContain("kilit_dugum = NULL");
    expect(p).toEqual([11, 12]);
    expect(yaz).toHaveBeenCalledTimes(3);
  });
});