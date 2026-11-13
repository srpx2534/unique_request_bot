/**
 * Yönetici kullanıcısı ekler veya parolasını günceller.
 *
 * Panelde kayıt ekranı yok; ilk kullanıcı bu betikle kurulur.
 * Kullanım: npm run kullanici:ekle -- eposta@ornek.com "parola"
 */
import bcrypt from "bcryptjs";
import "dotenv/config";
import { yaz } from "./veritabani.js";

const TUR = 12; // bcrypt maliyet turu; 12 altı zayıf sayılır

async function main(): Promise<void> {
  const [eposta, sifre] = process.argv.slice(2);
  if (!eposta || !sifre) {
    console.error("kullanım: npm run kullanici:ekle -- eposta@ornek.com parola");
    process.exit(1);
  }
  if (sifre.length < 8) {
    console.error("parola en az 8 karakter olmalı");
    process.exit(1);
  }

  const ozet = await bcrypt.hash(sifre, TUR);
  await yaz(
    "INSERT INTO kullanici (eposta, sifre_hash) VALUES (?, ?)"
    + " ON DUPLICATE KEY UPDATE sifre_hash = VALUES(sifre_hash), aktif = 1",
    [eposta, ozet],
  );
  console.log(`kullanıcı hazır: ${eposta}`);
  process.exit(0);
}

void main();