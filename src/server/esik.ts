/**
 * Eşik uyarıları.
 *
 * Panelin sessiz kalmaması gereken iki durum: kuyruk birikmesi ve yedek oranı
 * yükselmesi (§10). İkisi de son 30 dakikada aynı türden açık uyarı varsa
 * tekrar yazılmaz; birikme gürültüye dönüşmez.
 *
 * Kullanım: src/server/zamanlayici.ts.
 */
import { kuyruk } from "./kuyruk.js";
import { ayarOku } from "./ayar.js";
import { sorgu, tek, yaz } from "./veritabani.js";

const TEKRAR_DK = 30; // dakika; aynı tür için sessizlik penceresi
const YEDEK_ESIK = 30; // yüzde; yedek oranı bu değeri geçerse uyarı
const VARSAYILAN_KUYRUK_ESIK = 200;

/** Son pencere içinde aynı türden açık uyarı var mı. */
async function varMi(kind: string): Promise<boolean> {
  const satir = await tek<{ sayi: number }>(
    `SELECT COUNT(*) AS sayi FROM alert
      WHERE kind = ? AND acknowledged = 0
        AND created_at > UTC_TIMESTAMP(3) - INTERVAL ? MINUTE`,
    [kind, TEKRAR_DK],
  );
  return (satir?.sayi ?? 0) > 0;
}

/** Kuyruk birikmesini denetler. */
export async function kuyrukDenetle(): Promise<void> {
  const esik = Number(await ayarOku("kuyruk_esik", String(VARSAYILAN_KUYRUK_ESIK))) || VARSAYILAN_KUYRUK_ESIK;
  const bekleyen = await kuyruk.getWaitingCount() + (await kuyruk.getDelayedCount());
  if (bekleyen < esik) return;
  if (await varMi("queue_lag")) return;
  await yaz("INSERT INTO alert (kind, message) VALUES ('queue_lag', ?)", [
    `kuyruk ${bekleyen} iş, eşik ${esik}`.slice(0, 500),
  ]);
}

/** Son 24 saatte yedek oranı eşiği aştı mı diye bakar. */
export async function yedekOraniDenetle(): Promise<void> {
  const satir = await tek<{ yedek: number; toplam: number }>(
    `SELECT COALESCE(SUM(fallback_count), 0) AS yedek,
            COALESCE(SUM(hits_ok + hits_fail), 0) AS toplam
       FROM traffic_daily
      WHERE day >= UTC_DATE() - INTERVAL 1 DAY`,
  );
  const toplam = satir?.toplam ?? 0;
  if (toplam < 20) return; // küçük örnekte oran yanıltır
  const oran = Math.round(((satir?.yedek ?? 0) * 100) / toplam);
  if (oran <= YEDEK_ESIK) return;
  if (await varMi("fallback_high")) return;
  await yaz("INSERT INTO alert (kind, message) VALUES ('fallback_high', ?)", [
    `yedek oranı %${oran} (24 saat, ${toplam} hit)`.slice(0, 500),
  ]);
}

/** İkisini sırayla çalıştırır; biri düşse diğeri koşar. */
export async function esikDenetle(): Promise<void> {
  await kuyrukDenetle().catch((hata: Error) => console.error("[esik] kuyruk", hata.message));
  await yedekOraniDenetle().catch((hata: Error) => console.error("[esik] yedek", hata.message));
}