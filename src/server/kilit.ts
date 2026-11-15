/**
 * Kelime bazlı kilit (lease).
 *
 * Aynı keyword_geo satırını iki control plane'in aynı anda işlemesini engeller.
 * Sahip ve zaman veritabanında tutulur; süreç ölürse kilit süresi dolunca satır
 * kendiliğinden başkasına geçer, elle müdahale gerekmez.
 *
 * Çakışma hata değildir: iş atlanır, uyarı yazılır, çalışan tur devam eder.
 *
 * Kullanım: src/server/zamanlayici.ts, src/server/isci.ts.
 */
import os from "node:os";
import { ayarOku } from "./ayar.js";
import { sorgu, tek, yaz } from "./veritabani.js";

const VARSAYILAN_SURE_DK = 30; // burst zaman aşımı 15 dk; kilit ondan uzun kalmalı
const YENILE_SN = 5; // aynı düğümde art arda düşen ikinci iş bu pencereye takılır
const SESSIZLIK_DK = 30; // aynı tür çakışma uyarısı için sessizlik penceresi
const TARAMA_SINIRI = 100; // tek bakım turunda geri alınacak en çok satır
const OLU_BURST_DK = 20; // fetch zaman aşımı 15 dk; bunu aşan burst kesin ölüdür

/** Bu sürecin sahip kimliği: ana makine ve süreç kimliği birlikte yazılır. */
export const SAHIP = `${os.hostname()}:${process.pid}`.slice(0, 64);

/**
 * Kilit süresini dakika olarak verir.
 *
 * Ayar boşsa sözleşme varsayılanı geçerlidir. Kesirli ayar en az bir dakikaya
 * yuvarlanır; sıfır dakika kilidi anında bayatlatırdı.
 *
 * @returns en az 1 olan tam sayı dakika
 */
export async function kilitSuresiDk(): Promise<number> {
  const ham = Number(await ayarOku("kilit_suresi_dk", String(VARSAYILAN_SURE_DK)));
  return ham > 0 ? Math.max(1, Math.round(ham)) : VARSAYILAN_SURE_DK;
}

/** Son sessizlik penceresinde açık çakışma uyarısı var mı. */
async function sonUyariVar(): Promise<boolean> {
  const satir = await tek<{ sayi: number }>(
    `SELECT COUNT(*) AS sayi FROM alert
      WHERE kind = 'kilit_cakismasi' AND acknowledged = 0
        AND created_at > UTC_TIMESTAMP(3) - INTERVAL ? MINUTE`,
    [SESSIZLIK_DK],
  );
  return (satir?.sayi ?? 0) > 0;
}

/**
 * Dağıtıcı tarafında satırı sahiplenir.
 *
 * Satır serbestse ya da kilidi süresi dolmuşsa alınır; taze kilitliyse alınmaz.
 * Cooldown burada yazılır ki satır aynı turda yeniden seçilmesin.
 *
 * @param geoId keyword_geo kimliği
 * @param cooldownDk bir sonraki denemeye kadar beklenecek dakika
 * @returns sahiplenildiyse true
 */
export async function sahiplen(geoId: number, cooldownDk: number): Promise<boolean> {
  const sure = await kilitSuresiDk();
  const satir = await yaz(
    `UPDATE keyword_geo
        SET state = 'running', kilit_dugum = ?, kilit_at = UTC_TIMESTAMP(3),
            cooldown_until = DATE_ADD(UTC_TIMESTAMP(3), INTERVAL ? MINUTE)
      WHERE id = ?
        AND (state <> 'running' OR kilit_at IS NULL
             OR kilit_at < UTC_TIMESTAMP(3) - INTERVAL ? SECOND)`,
    [SAHIP, cooldownDk, geoId, sure * 60],
  );
  return satir > 0;
}

/**
 * İşçi tarafında sahiplenir ve kilidi tazeler.
 *
 * Aynı satıra iki iş düşerse ikincisi düşsün diye `last_burst_at` beş saniyelik
 * eşikle korunur; kilit bu davranışı bozmaz. Başka düğümün taze kilidi varsa
 * satır alınmaz.
 *
 * @param geoId keyword_geo kimliği
 * @returns sahiplenildiyse true
 */
export async function devral(geoId: number): Promise<boolean> {
  const sure = await kilitSuresiDk();
  const satir = await yaz(
    `UPDATE keyword_geo
        SET kilit_dugum = ?, kilit_at = UTC_TIMESTAMP(3), last_burst_at = UTC_TIMESTAMP(3)
      WHERE id = ? AND state = 'running'
        AND (last_burst_at IS NULL
             OR last_burst_at < UTC_TIMESTAMP(3) - INTERVAL ${YENILE_SN} SECOND)
        AND (kilit_dugum = ? OR kilit_at IS NULL
             OR kilit_at < UTC_TIMESTAMP(3) - INTERVAL ? SECOND)`,
    [SAHIP, geoId, SAHIP, sure * 60],
  );
  return satir > 0;
}

/**
 * Kilit çakışması uyarısı yazar.
 *
 * Aynı türden açık uyarı son sessizlik penceresinde varsa tekrar yazılmaz.
 * Sahip verilmediyse satırdan okunur ki uyarı "bilinmiyor" demesin.
 *
 * @param geoId keyword_geo kimliği
 * @param sahip satırı tutan düğüm; bilinmiyorsa null
 */
export async function cakismaYaz(geoId: number, sahip: string | null): Promise<void> {
  if (await sonUyariVar()) return;
  const satir = sahip
    ? null
    : await tek<{ kilit_dugum: string | null }>(
        "SELECT kilit_dugum FROM keyword_geo WHERE id = ?",
        [geoId],
      );
  const tutan = sahip ?? satir?.kilit_dugum ?? "bilinmiyor";
  await yaz("INSERT INTO alert (kind, ref_id, message) VALUES ('kilit_cakismasi', ?, ?)", [
    geoId,
    `keyword_geo ${geoId} başka düğümde çalışıyor: ${tutan}`.slice(0, 500),
  ]);
}

/**
 * Sahibi kaybolmuş satırları geri alır.
 *
 * Önce ölü burst'ler kapatılır: açık burst'i olan satır canlı sayılır ve
 * sıfırlanmaz, yoksa aynı satıra ikinci burst düşer.
 *
 * @returns geri alınan satır sayısı
 */
export async function bayatDenetle(): Promise<number> {
  const sure = await kilitSuresiDk();
  await yaz(
    `UPDATE burst SET ended_at = UTC_TIMESTAMP(3),
            stats = JSON_OBJECT('hata', 'kilit sahibi kayboldu')
      WHERE ended_at IS NULL
        AND started_at < UTC_TIMESTAMP(3) - INTERVAL ${OLU_BURST_DK} MINUTE`,
  );
  const bayat = await sorgu<{ id: number }>(
    `SELECT k.id FROM keyword_geo k
      WHERE k.state = 'running'
        AND (k.kilit_at IS NULL
             OR k.kilit_at < UTC_TIMESTAMP(3) - INTERVAL ? SECOND)
        AND NOT EXISTS (SELECT 1 FROM burst b
                         WHERE b.keyword_geo_id = k.id AND b.ended_at IS NULL)
      LIMIT ${TARAMA_SINIRI}`,
    [sure * 60],
  );
  if (bayat.length === 0) return 0;
  const idler = bayat.map((s) => s.id);
  await yaz(
    `UPDATE keyword_geo SET state = 'pending', kilit_dugum = NULL, kilit_at = NULL
      WHERE id IN (${idler.map(() => "?").join(",")})`,
    idler,
  );
  if (!(await sonUyariVar())) {
    await yaz("INSERT INTO alert (kind, message) VALUES ('kilit_cakismasi', ?)", [
      `${bayat.length} satırın kilit sahibi kayboldu, geri alındı`.slice(0, 500),
    ]);
  }
  return bayat.length;
}