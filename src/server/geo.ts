/**
 * keyword_geo dağılımı (sözleşme §7).
 *
 * national kelime 81 satır üretir: ilk 10 core, sonraki 30 normal,
 * kalan 41 passive. province kelime tek satır üretir ve o satır core'dur.
 * Sıra nüfus ağırlığından gelir; liste dışarıdan verilir ki veritabanı
 * olmadan test edilebilsin.
 */
export const CORE_ADET = 10;
export const NORMAL_ADET = 30;
export const BEKLENEN_IL = 81;

export type Kapsam = "national" | "province";
export type GeoSatir = { kod: number; tier: "core" | "normal" | "passive" };

export function dagitim(
  siraliKodlar: number[],
  kapsam: Kapsam,
  il: number | null = null,
): GeoSatir[] {
  if (kapsam === "province") {
    if (il === null) throw new Error("province kapsamında il zorunlu");
    return [{ kod: il, tier: "core" }];
  }
  if (siraliKodlar.length !== BEKLENEN_IL) {
    throw new Error(`${BEKLENEN_IL} il bekleniyordu, ${siraliKodlar.length} geldi`);
  }
  return siraliKodlar.map((kod, sira) => ({
    kod,
    tier: sira < CORE_ADET ? "core" : sira < CORE_ADET + NORMAL_ADET ? "normal" : "passive",
  }));
}