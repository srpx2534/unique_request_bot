/** Cerez defterinin ortak tipi ve yardimcilari. */
import { createHash } from "node:crypto";
import type { Request } from "express";
import { tek } from "../veritabani.js";

/** Ilerleme durumu; surec icinde tutulur. */
export const durum = { calisiyor: false, toplam: 0, islenen: 0, mukerrer: 0, hatali: 0 };

export type Cerez = {
  domain: string;
  ad: string;
  deger: string;
  yol: string;
  sona_erme: Date | null;
  guvenli: number;
  http_only: number;
  same_site: string | null;
  oncelik: string | null;
  oturumluk: number;
  boyut: number | null;
  kaynak_port: number | null;
  kaynak_sema: string | null;
  same_party: number;
  partition_ust: string | null;
  partition_ata: number | null;
  host_only: number;
};

/** Alan adini sadelestirir: bas nokta ve www. atilir. */
export function kok(alan: string): string {
  const ham = alan.trim().toLowerCase().replace(/^\.+/, "");
  return ham.startsWith("www.") ? ham.slice(4) : ham;
}

export function zaman(deger: unknown): Date | null {
  const sayi = Number(deger);
  if (!Number.isFinite(sayi) || sayi <= 0) return null;
  const tarih = new Date(sayi * 1000);
  return Number.isNaN(tarih.getTime()) ? null : tarih;
}

export function bayrak(deger: unknown): number {
  return ["true", "1", "yes", "evet"].includes(String(deger).toLowerCase()) ? 1 : 0;
}

export function kayit(alanlar: Partial<Cerez> & { domain: string; ad: string }): Cerez {
  return {
    deger: "", yol: "/", sona_erme: null, guvenli: 0, http_only: 0,
    same_site: null, oncelik: null, oturumluk: 0, boyut: null,
    kaynak_port: null, kaynak_sema: null, same_party: 0,
    partition_ust: null, partition_ata: null, host_only: 0,
    ...alanlar,
  };
}

/** Icerik ozeti. */
export function icerikOzeti(metin: string): string {
  return createHash("sha256").update(metin).digest("hex");
}
/** Cerez alan adlarindan ulke kodu cikarir; bilinmiyorsa null. */
export function ulkeBul(domainler: string[]): string | null {
  for (const domain of domainler) {
    if (domain.split(".").pop() === "tr") return "TR";
  }
  for (const domain of domainler) {
    const son = domain.split(".").pop() ?? "";
    if (son.length === 2) return son.toUpperCase();
  }
  return null;
}

/** Cerez adlarindan tarayici ailesini tahmin eder; isaret yoksa bilinmiyor. */
export function aileBul(cerezler: Cerez[]): string {
  let chrome = false;
  let firefox = false;
  for (const c of cerezler) {
    if (c.ad === "__Secure-BUCKET") firefox = true;
    else if (c.ad === "SIDCC" || c.ad === "__Host-GAPS" || c.ad === "SEARCH_SAMESITE" || c.ad === "AEC") chrome = true;
  }
  if (firefox) return "firefox";
  if (chrome) return "chrome";
  return "bilinmiyor";
}

/**
 * Dosyadan modalite cikarir: mobil cerez mi, web mi.
 *
 * Once JSON icindeki userAgent alani, sonra dosya yolu denenir; isaret yoksa
 * web sayilir.
 */
export function modaliteBul(ham: string, goreli: string): 0 | 1 {
  const ua = /"(?:user_?agent)"\s*:\s*"([^"]{0,300})"/i.exec(ham);
  const metin = `${ua?.[1] ?? ""} ${goreli}`.toLowerCase();
  return /android|iphone|ipad|ipod|mobile|mobil|telefon/.test(metin) ? 1 : 0;
}

/** Dosya adindan il kodu (1-81). */
export function ilBul(ad: string): number | null {
  const bulunan = ad.match(/(?:^|[^0-9])(0?[1-9]|[1-7][0-9]|8[01])(?:[^0-9]|$)/);
  if (!bulunan) return null;
  const kod = Number(bulunan[1]);
  return kod >= 1 && kod <= 81 ? kod : null;
}

/** Oturumdaki kullaniciyi kimlige cevirir. */
export async function yukleyenKimlik(istek: Request): Promise<number | null> {
  const eposta = (istek.session as { kullanici?: { eposta: string } }).kullanici?.eposta;
  if (!eposta) return null;
  const satir = await tek<{ id: number }>(
    "SELECT id FROM kullanici WHERE eposta = ? LIMIT 1",
    [eposta],
  );
  return satir?.id ?? null;
}