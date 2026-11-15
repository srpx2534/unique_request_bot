/** Cerez dosyasi ayristirici: JSON ve Netscape. */
import { type Cerez, bayrak, kayit, kok, zaman } from "./ortak.js";

/** Ardisik JSON belgelerini ayirir; bazi dosyalar birlestirilmis gelir. */
function jsonParcalari(metin: string): unknown[] {
  const parcalar: unknown[] = [];
  let derinlik = 0;
  let bas = -1;
  let metinIcinde = false;
  let kacis = false;
  for (let i = 0; i < metin.length; i += 1) {
    const karakter = metin[i];
    if (metinIcinde) {
      if (kacis) kacis = false;
      else if (karakter === "\\") kacis = true;
      else if (karakter === '"') metinIcinde = false;
      continue;
    }
    if (karakter === '"') {
      metinIcinde = true;
      continue;
    }
    if (karakter === "{" || karakter === "[") {
      if (derinlik === 0) bas = i;
      derinlik += 1;
      continue;
    }
    if (karakter === "}" || karakter === "]") {
      derinlik -= 1;
      if (derinlik === 0 && bas >= 0) {
        try {
          parcalar.push(JSON.parse(metin.slice(bas, i + 1)));
        } catch {
          // bozuk parca atlanir
        }
        bas = -1;
      }
    }
  }
  return parcalar;
}

/** JSON bicimini cozer; birlestirilmis belgeleri de ayirir. */
export function jsonCoz(metin: string): Cerez[] {
  let kokler: unknown[];
  try {
    kokler = [JSON.parse(metin)];
  } catch {
    kokler = jsonParcalari(metin);
  }

  const cerezler: Cerez[] = [];
  for (const belge of kokler) {
    const ham = Array.isArray(belge) ? belge : (belge as { cookies?: unknown }).cookies;
    if (!Array.isArray(ham)) continue;
    for (const hamKayit of ham) {
      const k = hamKayit as Record<string, unknown>;
      const ad = String(k.name ?? "").trim();
      const domain = kok(String(k.domain ?? ""));
      if (!ad || !domain) continue;
      const hamBolum = k.partitionKey;
      const bolum = (hamBolum && typeof hamBolum === "object" ? hamBolum : {}) as Record<string, unknown>;
      cerezler.push(
        kayit({
          domain,
          ad: ad.slice(0, 191),
          deger: String(k.value ?? ""),
          yol: String(k.path ?? "/").slice(0, 255),
          sona_erme: zaman(k.expires),
          guvenli: bayrak(k.secure),
          http_only: bayrak(k.httpOnly),
          same_site: k.sameSite ? String(k.sameSite).toLowerCase() : null,
          oncelik: k.priority ? String(k.priority).toLowerCase() : null,
          oturumluk: bayrak(k.session),
          boyut: Number.isFinite(Number(k.size)) ? Number(k.size) : null,
          kaynak_port: Number.isFinite(Number(k.sourcePort)) ? Number(k.sourcePort) : null,
          kaynak_sema: k.sourceScheme ? String(k.sourceScheme).toLowerCase() : null,
          same_party: bayrak(k.sameParty),
          partition_ust: bolum.topLevelSite ? String(bolum.topLevelSite).slice(0, 191) : null,
          partition_ata:
            "hasCrossSiteAncestor" in bolum ? Number(Boolean(bolum.hasCrossSiteAncestor)) : null,
          host_only: String(k.domain ?? "").startsWith(".") ? 0 : 1,
        }),
      );
    }
  }
  return cerezler;
}
/** Netscape bicimini cozer. */
export function netscapeCoz(metin: string): Cerez[] {
  const cerezler: Cerez[] = [];
  for (const satir of metin.split(/\r?\n/)) {
    let ham = satir.trim();
    if (!ham) continue;
    let httpOnly = 0;
    if (ham.startsWith("#HttpOnly_")) {
      httpOnly = 1;
      ham = ham.slice("#HttpOnly_".length);
    } else if (ham.startsWith("#")) {
      continue;
    }
    const parca = ham.split("\t");
    if (parca.length < 7) continue;
    const [domain = "", altAlan = "", yol = "/", guvenli = "", bitis = "", ad = "",
      deger = ""] = parca;
    const sadeles = kok(domain);
    if (!ad.trim() || !sadeles) continue;
    cerezler.push(
      kayit({
        domain: sadeles,
        ad: ad.trim().slice(0, 191),
        deger,
        yol: (yol.trim() || "/").slice(0, 255),
        sona_erme: zaman(bitis),
        guvenli: bayrak(guvenli),
        http_only: httpOnly,
        oturumluk: bayrak(altAlan) ? 0 : 1,
        host_only: domain.startsWith(".") ? 0 : 1,
      }),
    );
  }
  if (!cerezler.length) throw new Error("gecerli satir yok");
  return cerezler;
}

/** Icerige bakarak bicimi bulur. */
export function bicimBul(metin: string): "json" | "netscape" | null {
  const bas = metin.trimStart().charAt(0);
  if (bas === "{" || bas === "[") return "json";
  for (const satir of metin.split(/\r?\n/)) {
    const ham = satir.trim();
    if (!ham) continue;
    if (ham.startsWith("#HttpOnly_")) return "netscape";
    if (ham.startsWith("#")) continue;
    return ham.split("\t").length >= 7 ? "netscape" : null;
  }
  return null;
}