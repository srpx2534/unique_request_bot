/** Panel uclarinin ortak yardimcilari (§23.2). */

/** Tarih araligi cipini SQL kosuluna cevirir. */
export function aralikKosulu(aralik: string | undefined, kolon: string): string | null {
  switch (aralik) {
    case "bugun":
      return `DATE(${kolon}) = UTC_DATE()`;
    case "dun":
      return `DATE(${kolon}) = UTC_DATE() - INTERVAL 1 DAY`;
    case "hafta":
      return `${kolon} >= UTC_TIMESTAMP(3) - INTERVAL 7 DAY`;
    case "ay":
      return `${kolon} >= UTC_TIMESTAMP(3) - INTERVAL 30 DAY`;
    default:
      return null;
  }
}

/** Sayfa boyunu sinirlar: 1-500 arasi, gecersizse varsayilan. */
export function adetOku(ham: unknown, varsayilan = 100): number {
  const sayi = Number(ham);
  return Number.isInteger(sayi) && sayi > 0 ? Math.min(sayi, 500) : varsayilan;
}

/** Sayfa numarasini 1'den baslatir. */
export function sayfaOku(ham: unknown): number {
  const sayi = Number(ham);
  return Number.isInteger(sayi) && sayi > 0 ? sayi : 1;
}

export const GIZLI_AYARLAR = new Set(["serp_decodo", "serp_serper", "serp_searchapi"]);

/** Sir ayarlari son dort hane disinda maskeler. */
export function ayarMaskele(satirlar: { anahtar: string; deger: string }[]) {
  return satirlar.map((satir) =>
    GIZLI_AYARLAR.has(satir.anahtar) && satir.deger
      ? { anahtar: satir.anahtar, deger: `••••${satir.deger.slice(-4)}` }
      : satir,
  );
}