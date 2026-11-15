/**
 * Kilit çakışma denemesi.
 *
 * Ayrı süreçler aynı keyword_geo satırını aynı anda sahiplenmeye çalışır; tam
 * olarak biri kazanmalıdır. Gerçek süreç, gerçek veritabanı, gerçek kilit.
 *
 * Kullanım: npx tsx tools/kilit_cakisma_dene.ts <keyword_geo_id> [sahip|devral]
 */
import "dotenv/config";
import { SAHIP, cakismaYaz, devral, sahiplen } from "../src/server/kilit.js";
import { havuz } from "../src/server/veritabani.js";

const id = Number(process.argv[2]);
const tur = process.argv[3] ?? "sahip";
if (tur === "uyari") {
  await cakismaYaz(id, null);
  console.log(`UYARI ${SAHIP}`);
  await havuz.end();
  process.exit(0);
}
const kazandi = tur === "devral" ? await devral(id) : await sahiplen(id, 25);
console.log(`${kazandi ? "KAZANDI" : "KAYBETTI"} ${SAHIP}`);
await havuz.end();