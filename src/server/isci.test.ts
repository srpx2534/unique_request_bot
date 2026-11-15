/** Ust uste hedef_yok ile otomatik durma (A3). */
import { beforeEach, describe, expect, it, vi } from "vitest";

const sorgu = vi.fn();
const yaz = vi.fn();

vi.mock("./veritabani.js", () => ({ sorgu, yaz, tek: vi.fn(), ekle: vi.fn() }));
vi.mock("./kuyruk.js", () => ({ baglanti: {}, kuyruk: {} }));
vi.mock("./dugum_sec.js", () => ({ dugumSec: vi.fn() }));

const { hedefYokDenetle } = await import("./isci.js");

function say(desen: string): number {
  return yaz.mock.calls.filter(([sql]) => String(sql).includes(desen)).length;
}

beforeEach(() => {
  sorgu.mockReset();
  yaz.mockReset();
});

describe("hedef yok denetimi", () => {
  it("esik altinda durdurmaz", async () => {
    sorgu.mockResolvedValue([{ hepsi: 1 }, { hepsi: 1 }]);
    await hedefYokDenetle(7, 3);
    expect(say("state = 'paused'")).toBe(0);
  });

  it("arada basarili burst varsa durdurmaz", async () => {
    sorgu.mockResolvedValue([{ hepsi: 1 }, { hepsi: 0 }, { hepsi: 1 }]);
    await hedefYokDenetle(7, 3);
    expect(say("state = 'paused'")).toBe(0);
  });

  it("ust uste hedefsizse durdurur", async () => {
    sorgu.mockResolvedValue([{ hepsi: 1 }, { hepsi: 1 }, { hepsi: 1 }]);
    await hedefYokDenetle(7, 3);
    expect(say("state = 'paused'")).toBe(1);
    expect(say("stopped_at")).toBe(1);
    expect(say("'hedef_yok'")).toBe(1);
  });
});