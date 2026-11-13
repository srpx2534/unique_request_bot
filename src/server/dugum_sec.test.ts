/**
 * Düğüm seçimi testleri.
 *
 * Üç davranış kilitlenir: canlı düğüm seçilir, defter boşken yerel varsayılan
 * döner, kayıtlı ama sessiz düğüm varken null döner (C37, C38).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const tek = vi.fn();

vi.mock("./veritabani.js", () => ({
  tek: (...args: unknown[]) => tek(...args),
  sorgu: vi.fn(),
  yaz: vi.fn(),
  islem: vi.fn(),
}));

const { dugumSec } = await import("./dugum_sec.js");

beforeEach(() => {
  tek.mockReset();
});

describe("dugumSec", () => {
  it("canlı düğümü adres olarak verir", async () => {
    tek.mockResolvedValueOnce({ ip: "10.0.0.5" });
    await expect(dugumSec()).resolves.toBe("http://10.0.0.5:8081");
  });

  it("defter boşken yerel varsayılana düşer", async () => {
    tek.mockResolvedValueOnce(null).mockResolvedValueOnce({ sayi: 0 });
    await expect(dugumSec()).resolves.toBe("http://127.0.0.1:8081");
  });

  it("kayıtlı ama sessiz düğüm varsa null döner", async () => {
    tek.mockResolvedValueOnce(null).mockResolvedValueOnce({ sayi: 3 });
    await expect(dugumSec()).resolves.toBeNull();
  });

  it("WORKER_PORT tanımlıysa onu kullanır", async () => {
    process.env.WORKER_PORT = "9099";
    tek.mockResolvedValueOnce({ ip: "10.0.0.6" });
    await expect(dugumSec()).resolves.toBe("http://10.0.0.6:9099");
    delete process.env.WORKER_PORT;
  });
});