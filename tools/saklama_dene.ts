/**
 * Saklama turunu elle çalıştırır.
 *
 * Bölüm düşürme ve süre temizliğini sınamak için; panel beklemeden koşar.
 * Kullanım: npx tsx tools/saklama_dene.ts
 */
import "dotenv/config";
import { saklamaYap } from "../src/server/saklama.js";

saklamaYap()
  .then((n) => {
    console.log(`silinen: ${n}`);
    process.exit(0);
  })
  .catch((h: Error) => {
    console.error(h.message);
    process.exit(1);
  });