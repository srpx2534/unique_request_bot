/** Kelime uclarinin ortak semalari ve geo uretimi (§23.2). */
import { z } from "zod";
import { dagitim } from "./geo.js";
import { islem, sorgu } from "./veritabani.js";

export const SAYFA_VARSAYILAN = 50;
export const SAYFA_UST = 200;

export const eklemeSemasi = z
  .object({
    site_id: z.number().int().positive(),
    kelime: z.string().trim().min(2).max(191),
    kapsam: z.enum(["national", "province"]),
    il: z.number().int().min(1).max(81).nullable().optional(),
    tier: z.number().int().min(1).max(3).nullable().optional(),
    volume: z.number().int().positive().nullable().optional(),
    mobil: z.boolean().optional(),
  })
  .refine((v) => (v.kapsam === "province" ? Boolean(v.il) : !v.il), {
    message: "province icin il zorunlu, national icin bos olmali",
    path: ["il"],
  });

export const guncellemeSemasi = z.object({
  kelime: z.string().trim().min(2).max(191).optional(),
  tier: z.number().int().min(1).max(3).nullable().optional(),
  volume: z.number().int().positive().nullable().optional(),
  mobil: z.boolean().optional(),
});

export function kimlik(deger: string | undefined): number | null {
  const sayi = Number(deger);
  return Number.isInteger(sayi) && sayi > 0 ? sayi : null;
}

/** Geo satirlarini uretir; sira nufus agirligindan gelir. */
export async function geoUret(
  kelimeId: number,
  kapsam: string,
  il: number | null,
): Promise<number> {
  const kodlar = await sorgu<{ code: number }>("SELECT code FROM geo ORDER BY weight DESC, code ASC");
  const satirlar = dagitim(
    kodlar.map((k) => k.code),
    kapsam as "national" | "province",
    il,
  );

  await islem(async (baglanti) => {
    await baglanti.execute("DELETE FROM keyword_geo WHERE keyword_id = ?", [kelimeId]);
    const yerler = satirlar.map(() => "(?, ?, ?)").join(", ");
    await baglanti.query(
      `INSERT INTO keyword_geo (keyword_id, geo_code, tier) VALUES ${yerler}`,
      satirlar.flatMap((s) => [kelimeId, s.kod, s.tier]),
    );
  });

  return satirlar.length;
}