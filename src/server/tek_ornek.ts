/**
 * Tek örnek kilidi.
 *
 * Aynı makinede iki panel süreci açılırsa zamanlayıcı iki kez iş üretir,
 * kuyruk şişer ve kelime iki kez sahiplenilir. Kilit `veri/panel.pid`
 * dosyasıdır; içinde süreç kimliği durur. Dosya varsa ve o kimlik canlıysa
 * ikinci süreç dinlemeye geçmez. Kimlik ölüyse dosya devralınır.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
/** Kilit dosyasının dizini; testler geçici dizin verir. */
export const KILIT_DIZINI = path.join(KOK, "veri");

/**
 * Süreç canlı mı.
 *
 * Sinyal göndermeden yalnız varlık sınanır; 0 sinyali süreci öldürmez.
 *
 * @param pid Sınanacak süreç kimliği.
 * @returns Canlıysa true.
 */
function canliMi(pid: number): boolean {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

/**
 * Kilidi alır.
 *
 * Dosya `wx` ile yaratılır: iki süreç aynı anda denese de yalnız biri
 * yaratabilir. Dosya zaten varsa sahibi canlı mı diye bakılır; canlıysa
 * hata yükselir, ölüyse dosya silinip bir kez daha denenir.
 *
 * @param dizin Kilit dizini; varsayılan `veri/`.
 * @returns Kilit dosyasının tam yolu.
 * @throws Sahibi canlıysa ya da dosya iki denemede de alınamazsa.
 */
export function kilitAl(dizin: string = KILIT_DIZINI): string {
  fs.mkdirSync(dizin, { recursive: true });
  const dosya = path.join(dizin, "panel.pid");
  for (let deneme = 0; deneme < 2; deneme += 1) {
    try {
      const tanitici = fs.openSync(dosya, "wx");
      fs.writeFileSync(tanitici, String(process.pid));
      fs.closeSync(tanitici);
      // Çıkış yolu ne olursa olsun dosya bırakılır; SIGKILL dışında temizlenir.
      process.once("exit", () => kilitBirak(dizin));
      return dosya;
    } catch (hata) {
      if ((hata as NodeJS.ErrnoException).code !== "EEXIST") throw hata;
      const eski = Number(fs.readFileSync(dosya, "utf8").trim());
      if (canliMi(eski)) {
        throw new Error(`başka bir panel süreci çalışıyor (pid ${eski})`);
      }
      // Sahibi ölmüş: dosya devralınır, ikinci turda yeniden yaratılır.
      fs.unlinkSync(dosya);
    }
  }
  throw new Error("kilit dosyası alınamadı");
}

/**
 * Kilidi bırakır.
 *
 * Dosya başka bir sürece aitse dokunulmaz; devralınmış kilidi yanlışlıkla
 * silmemek için sahiplik kimlikle karşılaştırılır.
 *
 * @param dizin Kilit dizini; varsayılan `veri/`.
 */
export function kilitBirak(dizin: string = KILIT_DIZINI): void {
  const dosya = path.join(dizin, "panel.pid");
  try {
    const sahip = Number(fs.readFileSync(dosya, "utf8").trim());
    if (sahip === process.pid) fs.unlinkSync(dosya);
  } catch {
    // Dosya yoksa ya da okunamıyorsa yapılacak bir şey yok.
  }
}
