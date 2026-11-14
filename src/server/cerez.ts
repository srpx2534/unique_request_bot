/**
 * Çerez defteri uçları.
 *
 * Klasör yolu taranır, dosyalar arka planda sırayla aktarılır. Aynı içerik
 * özetten yakalanır ve tekrar aktarılmaz. Aktarım kesilirse `yeni` satırlardan
 * devam eder; düğüm sayısı arttıkça havuz ortak kullanılır.
 *
 * Kullanım: src/server/uygulama.ts
 */
import { promises as fs } from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { Router } from "express";
import { z } from "zod";
import { islem, sorgu, tek, yaz } from "./veritabani.js";
import { dogrula } from "./dogrula.js";

const AZAMI_BOYUT = 2 * 1024 * 1024; // dosya basi bayt
const AZAMI_DOSYA = 300_000; // tarama tavani
const PAKET = 200; // dosya basi islem

const yonlendirici = Router();

/** İlerleme durumu; süreç içinde tutulur. */
const durum = { calisiyor: false, toplam: 0, islenen: 0, mukerrer: 0, hatali: 0 };

type Cerez = {
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

/** Alan adını sadeleştirir: baş nokta ve www. atılır. */
function kok(alan: string): string {
  const ham = alan.trim().toLowerCase().replace(/^\.+/, "");
  return ham.startsWith("www.") ? ham.slice(4) : ham;
}

function zaman(deger: unknown): Date | null {
  const sayi = Number(deger);
  if (!Number.isFinite(sayi) || sayi <= 0) return null;
  const tarih = new Date(sayi * 1000);
  return Number.isNaN(tarih.getTime()) ? null : tarih;
}

function bayrak(deger: unknown): number {
  return ["true", "1", "yes", "evet"].includes(String(deger).toLowerCase()) ? 1 : 0;
}

function kayit(alanlar: Partial<Cerez> & { domain: string; ad: string }): Cerez {
  return {
    deger: "",
    yol: "/",
    sona_erme: null,
    guvenli: 0,
    http_only: 0,
    same_site: null,
    oncelik: null,
    oturumluk: 0,
    boyut: null,
    kaynak_port: null,
    kaynak_sema: null,
    same_party: 0,
    partition_ust: null,
    partition_ata: null,
    host_only: 0,
    ...alanlar,
  };
}

/** JSON biçimini çözer. */
function jsonCoz(metin: string): Cerez[] {
  const veri = JSON.parse(metin) as unknown;
  const ham = Array.isArray(veri)
    ? veri
    : (veri as { cookies?: unknown }).cookies;
  if (!Array.isArray(ham)) throw new Error("cookies dizisi yok");

  const cerezler: Cerez[] = [];
  for (const hamKayit of ham) {
    const k = hamKayit as Record<string, unknown>;
    const ad = String(k.name ?? "").trim();
    const domain = kok(String(k.domain ?? ""));
    if (!ad || !domain) continue;
    const bolum = (k.partitionKey ?? {}) as Record<string, unknown>;
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
  return cerezler;
}

/** Netscape biçimini çözer. */
function netscapeCoz(metin: string): Cerez[] {
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
  if (!cerezler.length) throw new Error("geçerli satır yok");
  return cerezler;
}

/** İçeriğe bakarak biçimi bulur. */
function bicimBul(metin: string): "json" | "netscape" | null {
  if (metin.trimStart().startsWith("{")) return "json";
  for (const satir of metin.split(/\r?\n/)) {
    const ham = satir.trim();
    if (!ham) continue;
    if (ham.startsWith("#HttpOnly_")) return "netscape";
    if (ham.startsWith("#")) continue;
    return ham.split("\t").length >= 7 ? "netscape" : null;
  }
  return null;
}

/** Dosya adından il kodu (1-81). */
function ilBul(ad: string): number | null {
  const bulunan = ad.match(/(?:^|[^0-9])(0?[1-9]|[1-7][0-9]|8[01])(?:[^0-9]|$)/);
  if (!bulunan) return null;
  const kod = Number(bulunan[1]);
  return kod >= 1 && kod <= 81 ? kod : null;
}

/** Klasörü doğrular ve gerçek yolunu döndürür. */
async function yolDogrula(ham: string): Promise<string> {
  const tam = path.resolve(ham);
  const bilgi = await fs.stat(tam);
  if (!bilgi.isDirectory()) throw new Error("yol klasör değil");
  return fs.realpath(tam);
}

/** Klasörü özyinelemeli tarar; yalnızca .json/.txt dosyaları. */
async function dosyalariTopla(kokDizin: string): Promise<string[]> {
  const bulunan: string[] = [];
  const gez = async (dizin: string): Promise<void> => {
    const girdiler = await fs.readdir(dizin, { withFileTypes: true });
    for (const girdi of girdiler) {
      if (bulunan.length >= AZAMI_DOSYA) return;
      const tam = path.join(dizin, girdi.name);
      if (girdi.isDirectory()) await gez(tam);
      else if (/\.(json|txt)$/i.test(girdi.name)) bulunan.push(tam);
    }
  };
  await gez(kokDizin);
  return bulunan;
}

/** İçerik özeti. */
function icerikOzeti(metin: string): string {
  return createHash("sha256").update(metin).digest("hex");
}

/**
 * Tek dosyayı aktarır ve defter satırını yerinde kapatır.
 *
 * `yeni` satır silinip yenisi yazılmaz; aynı satır sonuçla güncellenir.
 * Aynı içerik başka dosyada aktarılmışsa satır `mukerrer` olur ve özeti yol
 * özetine çevrilir, böylece tekil kalır.
 */
async function dosyaAktar(
  id: number,
  tam: string,
  kokDizin: string,
): Promise<"aktarildi" | "mukerrer" | "gecersiz"> {
  const yolOzeti = createHash("sha256").update(tam).digest("hex");
  const kapat = async (
    sonuc: "mukerrer" | "gecersiz",
    hata: string | null,
  ): Promise<"mukerrer" | "gecersiz"> => {
    await yaz("UPDATE cookie_dosya SET durum = ?, hata = ?, ozet = ? WHERE id = ?", [
      sonuc,
      hata,
      yolOzeti,
      id,
    ]).catch(() => {});
    return sonuc;
  };

  const bilgi = await fs.stat(tam).catch(() => null);
  if (!bilgi || bilgi.size === 0 || bilgi.size > AZAMI_BOYUT) {
    return kapat("gecersiz", "boyut sınırı ya da dosya yok");
  }
  const ham = await fs.readFile(tam, "utf8").catch(() => null);
  if (ham === null) return kapat("gecersiz", "okunamadı");

  const bicim = bicimBul(ham);
  if (!bicim) return kapat("gecersiz", "biçim tanınmadı");

  let cerezler: Cerez[];
  try {
    cerezler = bicim === "json" ? jsonCoz(ham) : netscapeCoz(ham);
  } catch (hata) {
    return kapat("gecersiz", (hata as Error).message.slice(0, 255));
  }
  if (!cerezler.length) return kapat("gecersiz", "kullanılabilir çerez yok");

  const ozet = icerikOzeti(ham);
  const ayni = await tek<{ id: number }>(
    "SELECT id FROM cookie_dosya WHERE ozet = ? AND id <> ? AND durum = 'aktarildi' LIMIT 1",
    [ozet, id],
  );
  if (ayni) return kapat("mukerrer", null);

  const enGec = cerezler.reduce<Date | null>((en, c) => {
    if (!c.sona_erme) return en;
    return !en || c.sona_erme > en ? c.sona_erme : en;
  }, null);
  const il = ilBul(path.relative(kokDizin, tam));

  try {
    await islem(async (baglanti) => {
      await baglanti.query(
        `UPDATE cookie_dosya SET tur = ?, boyut = ?, ozet = ?, satir_sayisi = ?,
           il_kodu = ?, durum = 'aktarildi', hata = NULL WHERE id = ?`,
        [bicim, bilgi.size, ozet, cerezler.length, il, id],
      );
      const [profil] = await baglanti.query(
        "INSERT INTO cookie_profil (dosya_id, ad, il_kodu, sona_erme, suresi_gecmis) VALUES (?, ?, ?, ?, ?)",
        [id, path.basename(tam), il, enGec, enGec && enGec.getTime() < Date.now() ? 1 : 0],
      );
      const profilId = (profil as { insertId: number }).insertId;

      for (let i = 0; i < cerezler.length; i += PAKET) {
        const parca = cerezler.slice(i, i + PAKET);
        const yerler = parca.map(() => "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").join(", ");
        await baglanti.query(
          `INSERT INTO cookie (profil_id, domain, ad, deger, yol, sona_erme, guvenli, http_only,
             same_site, oncelik, oturumluk, boyut, kaynak_port, kaynak_sema, same_party, partition_ust)
           VALUES ${yerler}`,
          parca.flatMap((c) => [
            profilId, c.domain, c.ad, c.deger, c.yol, c.sona_erme, c.guvenli, c.http_only,
            c.same_site, c.oncelik, c.oturumluk, c.boyut, c.kaynak_port, c.kaynak_sema,
            c.same_party, c.partition_ust,
          ]),
        );
      }
    });
    return "aktarildi";
  } catch (hata) {
    if ((hata as { code?: string }).code === "ER_DUP_ENTRY") return kapat("mukerrer", null);
    return kapat("gecersiz", (hata as Error).message.slice(0, 255));
  }
}

/** Kuyruğu paketler hâlinde boşaltır; aynı anda tek tur çalışır. */
async function isle(kokDizin: string): Promise<void> {
  if (durum.calisiyor) return;
  durum.calisiyor = true;
  try {
    for (;;) {
      const paket = await sorgu<{ id: number; yol: string }>(
        "SELECT id, yol FROM cookie_dosya WHERE durum = 'yeni' ORDER BY id LIMIT ?",
        [PAKET],
      );
      if (!paket.length) break;
      for (const satir of paket) {
        const sonuc = await dosyaAktar(satir.id, satir.yol, kokDizin);
        durum.islenen += 1;
        if (sonuc === "mukerrer") durum.mukerrer += 1;
        if (sonuc === "gecersiz") durum.hatali += 1;
      }
    }
  } finally {
    durum.calisiyor = false;
  }
}

const yolSemasi = z.object({ yol: z.string().trim().min(1).max(512) });

/** Özet sayılar. */
yonlendirici.get("/cerez", async (_istek, yanit) => {
  const sayim = await tek<Record<string, number>>(
    `SELECT
       (SELECT COUNT(*) FROM cookie_dosya WHERE durum = 'aktarildi') AS dosya,
       (SELECT COUNT(*) FROM cookie_dosya WHERE durum = 'gecersiz') AS gecersiz,
       (SELECT COUNT(*) FROM cookie_dosya WHERE durum = 'mukerrer') AS mukerrer,
       (SELECT COUNT(*) FROM cookie_profil WHERE durum = 'hazir' AND suresi_gecmis = 0) AS aktif,
       (SELECT COUNT(*) FROM cookie_profil WHERE durum = 'hazir' AND suresi_gecmis = 1) AS suresi_gecmis,
       (SELECT COUNT(*) FROM cookie_profil WHERE durum = 'tukendi') AS tukenen,
       (SELECT COUNT(*) FROM cookie_profil WHERE il_kodu IS NOT NULL) AS illi`,
  );
  const hatalilar = await sorgu(
    "SELECT id, ad, hata, created_at FROM cookie_dosya WHERE durum = 'gecersiz' ORDER BY id DESC LIMIT 20",
  );
  yanit.json({ sayim, durum, hatalilar });
});

/** Klasörü sayar; yazmaz. */
yonlendirici.post("/cerez/tara", async (istek, yanit) => {
  const govde = dogrula(yolSemasi, istek.body, yanit);
  if (!govde) return;
  let kokDizin: string;
  try {
    kokDizin = await yolDogrula(govde.yol);
  } catch (hata) {
    yanit.status(400).json({ hata: (hata as Error).message });
    return;
  }
  const dosyalar = await dosyalariTopla(kokDizin);
  const dagilim = { json: 0, txt: 0, illi: 0 };
  for (const tam of dosyalar) {
    if (/\.json$/i.test(tam)) dagilim.json += 1;
    else dagilim.txt += 1;
    if (ilBul(path.relative(kokDizin, tam)) !== null) dagilim.illi += 1;
  }
  yanit.json({ kok: kokDizin, toplam: dosyalar.length, dagilim });
});

/** Dosyaları deftere yazar ve işi başlatır. */
yonlendirici.post("/cerez/aktar", async (istek, yanit) => {
  const govde = dogrula(yolSemasi, istek.body, yanit);
  if (!govde) return;
  let kokDizin: string;
  try {
    kokDizin = await yolDogrula(govde.yol);
  } catch (hata) {
    yanit.status(400).json({ hata: (hata as Error).message });
    return;
  }
  const dosyalar = await dosyalariTopla(kokDizin);
  for (const tam of dosyalar) {
    await yaz(
      "INSERT IGNORE INTO cookie_dosya (yol, ad, tur, boyut, ozet, durum) VALUES (?, ?, 'json', 0, ?, 'yeni')",
      [tam, path.basename(tam), createHash("sha256").update(tam).digest("hex")],
    );
  }
  durum.toplam += dosyalar.length;
  void isle(kokDizin);
  yanit.json({ kuyruk: dosyalar.length, durum });
});

/** İlerleme. */
yonlendirici.get("/cerez/ilerleme", async (_istek, yanit) => {
  const bekleyen = await tek<{ sayi: number }>(
    "SELECT COUNT(*) AS sayi FROM cookie_dosya WHERE durum = 'yeni'",
  );
  yanit.json({ ...durum, bekleyen: bekleyen?.sayi ?? 0 });
});

/** Tüm çerez defterini siler. */
yonlendirici.delete("/cerez", async (_istek, yanit) => {
  await yaz("DELETE FROM cookie_dosya");
  durum.toplam = 0;
  durum.islenen = 0;
  durum.mukerrer = 0;
  durum.hatali = 0;
  yanit.status(204).end();
});

import { execFile } from "node:child_process";
import { promisify } from "node:util";

const calistir = promisify(execFile);

/** Sunucu makinesinde klasör seçici açar; iptalde null döner. */
async function klasorSec(): Promise<string | null> {
  const win = process.platform === "win32";
  const komut = win ? "powershell.exe" : "zenity";
  const argumanlar = win
    ? [
        "-NoProfile",
        "-STA",
        "-Command",
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Add-Type -AssemblyName System.Windows.Forms; $p = New-Object System.Windows.Forms.FolderBrowserDialog; $p.Description = 'Cerez klasorunu sec'; $p.ShowNewFolderButton = $false; if ($p.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Out.Write($p.SelectedPath) }",
      ]
    : ["--file-selection", "--directory", "--title=Cerez klasorunu sec"];
  try {
    const { stdout } = await calistir(komut, argumanlar, { timeout: 300_000, windowsHide: true });
    const secilen = stdout.trim();
    return secilen === "" ? null : secilen;
  } catch (hata) {
    const kod = (hata as { code?: number | string }).code;
    // zenity iptalde 1 ile cikar.
    if (kod === 1 || kod === "1") return null;
    throw hata;
  }
}

yonlendirici.post("/cerez/gozat", async (_istek, yanit) => {
  try {
    const secilen = await klasorSec();
    if (!secilen) {
      yanit.json({ iptal: true });
      return;
    }
    yanit.json({ yol: secilen });
  } catch (hata) {
    const kod = (hata as NodeJS.ErrnoException).code;
    if (kod === "ENOENT") {
      yanit.status(500).json({ hata: "klasör seçici bulunamadı, yolu elle yaz" });
      return;
    }
    console.error("[cerez] gozat hatasi:", (hata as Error).message);
    yanit.status(500).json({ hata: "klasör seçici açılamadı" });
  }
});
export default yonlendirici;