/**
 * Yapılandırılmış günlük.
 *
 * Tek satır JSON: zaman, seviye, bağlam ve mesaj. Üretimde satırlar makineyle
 * okunur, geliştirmede de gözle seçilir. `console` yalnız burada kullanılır;
 * başka modül doğrudan yazmaz.
 *
 * Seviye eşiği `GUNLUK_SEVIYE` ile verilir (varsayılan `bilgi`). Hata ve uyarı
 * stderr`e, bilgi ve ayrıntı stdout`a gider.
 */

export type Seviye = "hata" | "uyari" | "bilgi" | "ayrinti";

// Sayı küçüldükçe önem artar; eşikten büyük olan satır basılmaz.
const SIRALAMA: Record<Seviye, number> = { hata: 0, uyari: 1, bilgi: 2, ayrinti: 3 };
const VARSAYILAN = 2; // bilgi

/** Eşiği ortamdan okur; tanınmayan değerde `bilgi` geçerli. */
function esik(): number {
  const ham = process.env.GUNLUK_SEVIYE as Seviye | undefined;
  return ham && ham in SIRALAMA ? SIRALAMA[ham] : VARSAYILAN;
}

/**
 * Satırı kurar.
 *
 * İlk parça `[etiket]` biçimindeyse bağlam alanına taşınır, mesajdan düşer;
 * böylece çağrılar `[modul]` önekiyle okunur kalır. `Error` nesnesi mesajıyla
 * yazılır, yığın izi ayrıntı seviyesinde eklenir.
 *
 * @param seviye Satır seviyesi.
 * @param parcalar Etiket ve mesaj parçaları.
 * @returns JSON satırı.
 */
function satir(seviye: Seviye, parcalar: unknown[]): string {
  const ham = parcalar.map((p) => (p instanceof Error ? p.message : String(p ?? "")));
  let baglam = "";
  // Etiket mesajin basindaysa da alinir: "[redis] bagli" gibi cagrilar var.
  const etiket = /^\[([^\]]+)\]\s*/.exec(ham[0] ?? "");
  if (etiket) {
    baglam = etiket[1]!;
    ham[0] = (ham[0] ?? "").slice(etiket[0].length);
  }
  const kayit: Record<string, string> = {
    z: new Date().toISOString(),
    s: seviye,
    b: baglam,
    m: ham.join(" ").trim(),
  };
  const hata = parcalar.find((p) => p instanceof Error) as Error | undefined;
  if (hata?.stack && seviye === "hata") kayit.i = hata.stack.split("\\n").slice(0, 4).join(" | ");
  return JSON.stringify(kayit);
}

/**
 * Satırı seviyeye göre yazar.
 *
 * @param seviye Satır seviyesi.
 * @param parcalar Etiket ve mesaj parçaları.
 */
function yaz(seviye: Seviye, parcalar: unknown[]): void {
  if (SIRALAMA[seviye] > esik()) return;
  const metin = satir(seviye, parcalar);
  if (seviye === "hata" || seviye === "uyari") console.error(metin);
  else console.log(metin);
}

/** Günlük yüzeyi; modüller bunu kullanır. */
export const gunluk = {
  /** Kurtarılabilir hata. */
  hata: (...parcalar: unknown[]): void => yaz("hata", parcalar),
  /** Dikkat gerektiren ama işi durdurmayan durum. */
  uyari: (...parcalar: unknown[]): void => yaz("uyari", parcalar),
  /** Olağan bilgi. */
  bilgi: (...parcalar: unknown[]): void => yaz("bilgi", parcalar),
  /** Teşhis ayrıntısı; varsayılan eşikte basılmaz. */
  ayrinti: (...parcalar: unknown[]): void => yaz("ayrinti", parcalar),
};


