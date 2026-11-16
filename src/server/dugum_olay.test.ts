/**
 * Düğüm ölü uyarısı testleri (E3).
 *
 * Gerçek veritabanı kullanılır. Kalbi kesilmiş düğüm için olay ve uyarı
 * düşer; ikinci turda uyarı tekrarlanmaz.
 */
import "dotenv/config";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { kalpKaybiYaz } from "./dugum_olay.js";
import { ekle, sorgu, tek, yaz } from "./veritabani.js";

const IP = "10.99.0.1";
let id = 0;

beforeAll(async () => {
  await yaz("DELETE FROM dugum WHERE ip = ?", [IP]);
  // yaz etkilenen satırı döndürür; kimlik için ekle kullanılır.
  id = (await ekle(
    "INSERT INTO dugum (ad, ip, son_kalp_at) VALUES (?, ?, UTC_TIMESTAMP(3) - INTERVAL 5 MINUTE)",
    ["olu-dugum", IP],
  )) as number;
});

afterAll(async () => {
  await yaz("DELETE FROM alert WHERE kind = ? AND ref_id = ?", ["dugum_olu", id]);
  await yaz("DELETE FROM dugum WHERE ip = ?", [IP]);
});

describe("ölü düğüm uyarısı", () => {
  it("kalbi kesilen düğüm için olay ve uyarı yazar", async () => {
    await kalpKaybiYaz();
    const olay = await tek<{ sayi: number }>(
      "SELECT COUNT(*) AS sayi FROM dugum_olay WHERE dugum_id = ? AND tur = ?",
      [id, "kalp_kaybi"],
    );
    const uyari = await tek<{ sayi: number }>(
      "SELECT COUNT(*) AS sayi FROM alert WHERE kind = ? AND ref_id = ?",
      ["dugum_olu", id],
    );
    expect(olay?.sayi).toBeGreaterThan(0);
    expect(uyari?.sayi).toBe(1);
  });

  it("ikinci turda uyarı tekrarlanmaz", async () => {
    await kalpKaybiYaz();
    const uyari = await sorgu<{ sayi: number }>(
      "SELECT COUNT(*) AS sayi FROM alert WHERE kind = ? AND ref_id = ?",
      ["dugum_olu", id],
    );
    expect(uyari[0]?.sayi).toBe(1);
  });

  it("durdurulmuş düğüm için uyarı yazmaz", async () => {
    await yaz("UPDATE dugum SET durum = ? WHERE id = ?", ["durduruldu", id]);
    await yaz("DELETE FROM alert WHERE kind = ? AND ref_id = ?", ["dugum_olu", id]);
    await kalpKaybiYaz();
    const uyari = await sorgu<{ sayi: number }>(
      "SELECT COUNT(*) AS sayi FROM alert WHERE kind = ? AND ref_id = ?",
      ["dugum_olu", id],
    );
    expect(uyari[0]?.sayi).toBe(0);
  });
});

