/**
 * Elle trafik toparlama.
 *
 * Panel kapalıyken ya da geçmiş günler için toparlayıcıyı çalıştırır.
 * Kullanım: npx tsx tools/traffic_toparla.ts 7
 */
import "dotenv/config";
import { toparla } from "../src/server/traffic.js";

const ham = Number(process.argv[2] ?? 2);
const gun = Number.isInteger(ham) && ham > 0 ? ham : 2;

toparla(gun)
  .then((satir) => {
    console.log(`toparlanan satır: ${satir}`);
    process.exit(0);
  })
  .catch((hata: Error) => {
    console.error(hata.message);
    process.exit(1);
  });