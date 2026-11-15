/**
 * Metrik ucu (E6).
 *
 * Panelin tek bakista gormesi gereken isletim sayilari burada toplanir: hit
 * sonuc dagilimi, modalite, saglayici sagligi, kuyruk, dugum canliligi,
 * gecikme ve son yedek. Oranlar yuzde; payda sifirsa null doner.
 *
 * Redis ve yedek klasoru erisilemezse yalnizca ilgili blok null olur, uc
 * dusmez: metrik ekrani bir bagimlilik yuzunden bos kalmamali.
 */
import { Router } from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { sorgu, tek } from "./veritabani.js";
import { kuyruk } from "./kuyruk.js";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const YEDEK = path.join(KOK, "veri", "yedek");

export const yonlendirici = Router();
export default yonlendirici;

/** Yuzde hesabi; payda sifirsa null. */
function yuzde(pay: number, payda: number): number | null {
  return payda > 0 ? Number(((pay / payda) * 100).toFixed(2)) : null;
}

/** Son yedek dosyasinin adi ve yasi; klasor okunamazsa null. */
function yedekDurumu(): { adet: number; son_ad: string | null; son_yas_dk: number | null } | null {
  try {
    const dosyalar = fs.readdirSync(YEDEK).filter((ad) => ad.endsWith(".sql"));
    if (dosyalar.length === 0) return { adet: 0, son_ad: null, son_yas_dk: null };
    let son = dosyalar[0] ?? "";
    let sonZaman = 0;
    for (const ad of dosyalar) {
      const zaman = fs.statSync(path.join(YEDEK, ad)).mtimeMs;
      if (zaman > sonZaman) {
        sonZaman = zaman;
        son = ad;
      }
    }
    return {
      adet: dosyalar.length,
      son_ad: son || null,
      son_yas_dk: Math.round((Date.now() - sonZaman) / 60_000),
    };
  } catch {
    return null;
  }
}

/** Verilen dakika penceresi icin hit blogu. */
async function hitBlogu(dakika: number) {
  const satir = await tek<Record<string, string>>(
    `SELECT COUNT(*) AS toplam,
            SUM(result = 'ok') AS ok,
            SUM(result = 'captcha') AS captcha,
            SUM(result = 'not_found') AS not_found,
            SUM(result = 'timeout') AS timeout,
            SUM(result = 'error') AS error,
            SUM(geo_mode = 'tr_fallback') AS yedek,
            SUM(tur = 'mobile') AS mobil,
            SUM(tur = 'residential') AS residential,
            SUM(tur = 'datacenter') AS datacenter,
            AVG(latency_ms) AS ort_ms,
            MAX(latency_ms) AS azami_ms
       FROM hit
      WHERE created_at >= UTC_TIMESTAMP(3) - INTERVAL ? MINUTE`,
    [dakika],
  );
  const say = (k: string) => Number(satir?.[k] ?? 0);
  const toplam = say("toplam");
  const turler = say("mobil") + say("residential") + say("datacenter");
  return {
    toplam,
    ok: say("ok"),
    captcha: say("captcha"),
    not_found: say("not_found"),
    timeout: say("timeout"),
    error: say("error"),
    yedek: say("yedek"),
    ok_oran: yuzde(say("ok"), toplam),
    captcha_oran: yuzde(say("captcha"), toplam),
    yedek_oran: yuzde(say("yedek"), toplam),
    tur: {
      mobile: say("mobil"),
      residential: say("residential"),
      datacenter: say("datacenter"),
      tanimsiz: toplam - turler,
    },
    gecikme_ms: {
      ortalama: satir?.ort_ms ? Number(satir.ort_ms) : null,
      azami: say("azami_ms"),
    },
  };
}

/** Son 24 saatin p95 gecikmesi; ornek yoksa null. */
async function p95Gecikme(): Promise<number | null> {
  const sayi = await tek<{ adet: number }>(
    `SELECT COUNT(*) AS adet FROM hit
      WHERE created_at >= UTC_TIMESTAMP(3) - INTERVAL 24 HOUR AND latency_ms IS NOT NULL`,
  );
  const adet = Number(sayi?.adet ?? 0);
  if (adet === 0) return null;
  const atla = Math.max(0, Math.floor(adet * 0.95) - 1);
  const satir = await tek<{ latency_ms: number }>(
    `SELECT latency_ms FROM hit
      WHERE created_at >= UTC_TIMESTAMP(3) - INTERVAL 24 HOUR AND latency_ms IS NOT NULL
      ORDER BY latency_ms LIMIT 1 OFFSET ?`,
    [atla],
  );
  return satir ? Number(satir.latency_ms) : null;
}

/** Kuyruk sayimlari; Redis yoksa ulasildi false. */
async function kuyrukDurumu() {
  try {
    const sayim = await kuyruk.getJobCounts("waiting", "active", "delayed", "failed");
    return { ulasildi: true, ...sayim };
  } catch {
    return { ulasildi: false };
  }
}

yonlendirici.get("/metrik", async (_istek, yanit) => {
  const basladi = process.hrtime.bigint();
  await tek("SELECT 1 AS t");
  const db_ms = Number(process.hrtime.bigint() - basladi) / 1e6;

  const saglayici = await tek<Record<string, string>>(
    `SELECT COUNT(*) AS toplam,
            SUM(state = 'active') AS aktif,
            SUM(state = 'quarantine') AS karantina,
            SUM(state = 'disabled') AS kapali,
            SUM(hata_sayac > 0) AS hatali,
            SUM(state = 'active' AND gateway IS NOT NULL) AS kullanilabilir
       FROM provider`,
  );
  const sorunlu = await sorgu(
    `SELECT id, name, state, hata_sayac, captcha_pct, quarantine_until
       FROM provider WHERE state <> 'active' OR hata_sayac > 0
      ORDER BY hata_sayac DESC, id LIMIT 5`,
  );

  const kelime = await tek<Record<string, string>>(
    "SELECT COUNT(*) AS toplam, SUM(state = 'active') AS aktif, SUM(state = 'paused') AS duraklatilmis FROM keyword",
  );
  const kelimeToplam = Number(kelime?.toplam ?? 0);
  const kelimeAktif = Number(kelime?.aktif ?? 0);
  const kelimeDurak = Number(kelime?.duraklatilmis ?? 0);

  const burst = await tek<Record<string, string>>(
    `SELECT SUM(started_at >= UTC_TIMESTAMP(3) - INTERVAL 1 HOUR) AS son_saat,
            SUM(ended_at IS NULL) AS acik,
            AVG(TIMESTAMPDIFF(SECOND, started_at, ended_at)) AS ort_sn
       FROM burst WHERE started_at >= UTC_TIMESTAMP(3) - INTERVAL 24 HOUR`,
  );

  const dugum = await tek<Record<string, string>>(
    `SELECT COUNT(*) AS toplam,
            SUM(durum = 'aktif') AS aktif,
            SUM(son_kalp_at >= UTC_TIMESTAMP(3) - INTERVAL 5 MINUTE) AS canli,
            AVG(yuk) AS ort_yuk
       FROM dugum`,
  );

  const acikUyari = await tek<{ adet: number }>("SELECT COUNT(*) AS adet FROM alert WHERE acknowledged = 0");

  yanit.json({
    olcum_at: new Date().toISOString(),
    pencere_dk: { kisa: 60, uzun: 1440 },
    db_ms: Number(db_ms.toFixed(2)),
    hit: { son_1sa: await hitBlogu(60), son_24sa: await hitBlogu(1440) },
    gecikme_p95_24sa: await p95Gecikme(),
    saglayici: {
      toplam: Number(saglayici?.toplam ?? 0),
      aktif: Number(saglayici?.aktif ?? 0),
      karantina: Number(saglayici?.karantina ?? 0),
      kapali: Number(saglayici?.kapali ?? 0),
      hatali: Number(saglayici?.hatali ?? 0),
      kullanilabilir: Number(saglayici?.kullanilabilir ?? 0),
      sorunlu,
    },
    kelime: {
      toplam: kelimeToplam,
      aktif: kelimeAktif,
      duraklatilmis: kelimeDurak,
      durdurulmus: Math.max(0, kelimeToplam - kelimeAktif - kelimeDurak),
    },
    burst: {
      son_saat: Number(burst?.son_saat ?? 0),
      acik: Number(burst?.acik ?? 0),
      ortalama_sn: burst?.ort_sn ? Number(burst.ort_sn) : null,
    },
    dugum: {
      toplam: Number(dugum?.toplam ?? 0),
      aktif: Number(dugum?.aktif ?? 0),
      canli_5dk: Number(dugum?.canli ?? 0),
      ortalama_yuk: dugum?.ort_yuk ? Number(dugum.ort_yuk) : null,
    },
    acik_uyari: Number(acikUyari?.adet ?? 0),
    kuyruk: await kuyrukDurumu(),
    yedek: yedekDurumu(),
  });
});
