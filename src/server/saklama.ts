/**
 * Saklama süreleri.
 *
 * Sözleşme §6.3 süreleri uygulanır: hit 30 gün, burst 90, alert 90,
 * dugum_olay 90, audit_log 1 yıl. Silme parçalı yapılır (LIMIT), böylece tek
 * büyük DELETE tabloyu kilitlemez. Saatte bir koşar; her turda koşmak gereksiz
 * yük olur.
 *
 * hit satırlarının burst'a yabancı anahtarı yok; burst silinmeden önce hit
 * ayrıca temizlenir, aksi halde öksüz satır kalır.
 *
 * Kullanım: src/server/zamanlayici.ts.
 */
import { sorgu, tek, yaz } from "./veritabani.js";

const ARALIK_DK = 60; // dakika; iki saklama turu arası
const PARCA = 20_000; // satır; tek DELETE boyu
const TUR_TAVANI = 10; // parça; bir turda en fazla

// Süreler gün cinsinden; sözleşme §6.3.
const HIT_GUN = 30;
const BURST_GUN = 90;
const ALERT_GUN = 90;
const OLAY_GUN = 90;
const AUDIT_GUN = 365;

let sonCalisma = 0;

/**
 * Saklama süresi dolmuş gün bölümlerini düşürür.
 *
 * Bölüm adı `pYYYYMMDD`, üst sınırı TO_DAYS'tır; sınırı SQL'den okuruz ki
 * Python/JS takvim farkı karışmasın. Bölüm yoksa sessizce 0 döner.
 */
async function bolumDus(): Promise<number> {
  const satirlar = await sorgu<{ ad: string; ust: number }>(
    `SELECT PARTITION_NAME AS ad, PARTITION_DESCRIPTION AS ust
       FROM information_schema.PARTITIONS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hit'
        AND PARTITION_NAME REGEXP '^p[0-9]{8}$'`,
  );
  const sinirSatir = await tek<{ sinir: number }>(
    "SELECT TO_DAYS(UTC_DATE() - INTERVAL ? DAY) AS sinir",
    [HIT_GUN],
  );
  const sinir = Number(sinirSatir?.sinir ?? 0);
  if (!sinir) return 0;

  // Adlar şemadan gelir ama yine de desenle süzülür; DROP parametre almaz.
  const eski = satirlar
    .filter((s) => Number(s.ust) <= sinir && /^p[0-9]{8}$/.test(s.ad))
    .map((s) => s.ad);
  if (eski.length === 0) return 0;
  await yaz(`ALTER TABLE hit DROP PARTITION ${eski.join(", ")}`);
  return eski.length;
}

/**
 * Parçalı siler; etkilenen satır parça boyundan azsa durur.
 *
 * `limitli` false ise tek seferde silinir: alt sorgulu biçimde MariaDB
 * `LIMIT` kabul etmiyor, orada parçalama yapılamaz.
 */
async function parcaliSil(sql: string, gun: number, limitli = true): Promise<number> {
  if (!limitli) return yaz(sql, [gun]);
  let toplam = 0;
  for (let tur = 0; tur < TUR_TAVANI; tur += 1) {
    const etkilenen = await yaz(`${sql} LIMIT ${PARCA}`, [gun]);
    toplam += etkilenen;
    if (etkilenen < PARCA) break;
  }
  return toplam;
}

/**
 * Süresi geçmiş satırları siler.
 *
 * @returns Silinen toplam satır sayısı.
 */
export async function saklamaYap(): Promise<number> {
  let toplam = 0;

  // Bolumlu tabloda once butun gun duser: DELETE yukunu metadata'ya cevirir.
  toplam += await bolumDus();
  toplam += await parcaliSil(
    "DELETE FROM hit WHERE created_at < UTC_TIMESTAMP(3) - INTERVAL ? DAY", HIT_GUN,
  );
  // Alt sorgulu bicimde LIMIT verilemez; tek seferde silinir. burst 90 gunluk
  // oldugu icin IN listesi sinirlidir.
  toplam += await parcaliSil(
    `DELETE FROM hit WHERE burst_id IN
      (SELECT id FROM burst WHERE started_at < UTC_TIMESTAMP(3) - INTERVAL ? DAY)`,
    BURST_GUN,
    false,
  );
  toplam += await parcaliSil(
    "DELETE FROM burst WHERE started_at < UTC_TIMESTAMP(3) - INTERVAL ? DAY", BURST_GUN,
  );
  toplam += await parcaliSil(
    "DELETE FROM alert WHERE created_at < UTC_TIMESTAMP(3) - INTERVAL ? DAY", ALERT_GUN,
  );
  toplam += await parcaliSil(
    "DELETE FROM dugum_olay WHERE created_at < UTC_TIMESTAMP(3) - INTERVAL ? DAY", OLAY_GUN,
  );
  toplam += await parcaliSil(
    "DELETE FROM audit_log WHERE created_at < UTC_TIMESTAMP(3) - INTERVAL ? DAY", AUDIT_GUN,
  );
  return toplam;
}

/** Saatte bir koşar; tur içinde çağrıldığında çoğu kez hemen döner. */
export async function saklamaDenetle(): Promise<void> {
  const simdi = Date.now();
  if (simdi - sonCalisma < ARALIK_DK * 60_000) return;
  sonCalisma = simdi;
  try {
    const silinen = await saklamaYap();
    if (silinen > 0) console.log(`[saklama] ${silinen} satır silindi`);
  } catch (hata) {
    console.error("[saklama]", (hata as Error).message);
  }
}