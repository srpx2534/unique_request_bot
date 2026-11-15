/** Cerez defteri ozet ucu. */
import { Router } from "express";
import { sorgu, tek } from "../veritabani.js";
import { durum } from "./ortak.js";

export const yonlendirici = Router();

yonlendirici.get("/", async (_istek, yanit) => {
  // Sayimlar ortaktir. Kisiye ozel gorunum ileride kullanici yonetiminde
  // admin izni olarak gelecek; suzgec SQL'leri hazir duruyor.
  const kendi = false;
  const suzgec = kendi ? " AND yukleyen = ?" : "";
  const suzgecDeger: unknown[] = [];
  const suzgecProfil = kendi
    ? " AND EXISTS (SELECT 1 FROM cookie_dosya d2 WHERE d2.id = cookie_profil.dosya_id AND d2.yukleyen = ?)"
    : "";

  const sayim = await tek<Record<string, number>>(
    `SELECT
       (SELECT COUNT(*) FROM cookie_dosya WHERE durum = 'aktarildi'${suzgec}) AS dosya,
       (SELECT COUNT(*) FROM cookie_dosya WHERE durum = 'gecersiz'${suzgec}) AS gecersiz,
       (SELECT COUNT(*) FROM cookie_dosya WHERE durum = 'mukerrer'${suzgec}) AS mukerrer,
       (SELECT COUNT(*) FROM cookie_profil WHERE durum = 'hazir' AND suresi_gecmis = 0${suzgecProfil}) AS aktif,
       (SELECT COUNT(*) FROM cookie_profil WHERE durum = 'hazir' AND suresi_gecmis = 1${suzgecProfil}) AS suresi_gecmis,
       (SELECT COUNT(*) FROM cookie_profil WHERE ulke = 'TR'${suzgecProfil}) AS ulke_tr,
       (SELECT COUNT(*) FROM cookie_profil WHERE ulke IS NOT NULL AND ulke <> 'TR'${suzgecProfil}) AS ulke_yabanci,
       (SELECT COUNT(*) FROM cookie_profil WHERE 1 = 1${suzgecProfil}) AS toplam,
       (SELECT COUNT(*) FROM cookie_profil WHERE il_kodu IS NOT NULL${suzgecProfil}) AS illi,
       (SELECT COUNT(*) FROM cookie_profil WHERE mobil = 1${suzgecProfil}) AS mobil,
       (SELECT COUNT(*) FROM cookie_profil WHERE mobil = 0${suzgecProfil}) AS web`,
    suzgecDeger,
  );
  const hatalilar = await sorgu(
    `SELECT id, ad, hata, created_at FROM cookie_dosya
      WHERE durum = 'gecersiz'${suzgec} ORDER BY id DESC LIMIT 20`,
    suzgecDeger,
  );
  yanit.json({ sayim, durum, hatalilar });
});