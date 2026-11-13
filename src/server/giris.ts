/**
 * Giriş, çıkış ve oturum sorgulama rotaları.
 *
 * Parola bcrypt ile doğrulanır. Beş başarısız denemede hesap 15 dakika
 * kilitlenir; kilit sayacı Redis'te tutulur, süreç yeniden başlasa da
 * sıfırlanmaz.
 */
import { Router } from "express";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { redis } from "./redis.js";
import { tek, yaz } from "./veritabani.js";

const KILIT_SINIR = 5; // deneme; üstünde kilit
// Karsilastirma icin gecerli bir ozet gerekir; sabit metin bcrypt tarafindan
// reddedilebiliyordu. Bir kez uretilir, maliyeti acilista 100 ms.
const SAHTE_OZET = bcrypt.hashSync("gecersiz-parola", 12);
const KILIT_SN = 15 * 60; // saniye; kilit süresi

const govdeSemasi = z.object({
  eposta: z.string().email().max(191),
  sifre: z.string().min(8).max(128),
});

type Kullanici = {
  id: number;
  eposta: string;
  sifre_hash: string;
  rol: string;
  aktif: number;
};

const yonlendirici = Router();

yonlendirici.post("/giris", async (istek, yanit) => {
  const cozum = govdeSemasi.safeParse(istek.body);
  if (!cozum.success) {
    yanit.status(400).json({ hata: "e-posta veya şifre biçimi hatalı" });
    return;
  }
  const { eposta, sifre } = cozum.data;
  const kilitAnahtar = `kilit:${eposta}`;

  const deneme = Number((await redis.get(kilitAnahtar)) ?? 0);
  if (deneme >= KILIT_SINIR) {
    yanit.status(429).json({ hata: "çok fazla deneme, 15 dakika bekle" });
    return;
  }

  const kullanici = await tek<Kullanici>(
    "SELECT id, eposta, sifre_hash, rol, aktif FROM kullanici WHERE eposta = ?",
    [eposta],
  );

  // Kullanıcı yoksa da bcrypt çalıştırılır; yanıt süresi bilgi sızdırmasın.
  const ozet = kullanici?.sifre_hash ?? SAHTE_OZET;
  const dogru = await bcrypt.compare(sifre, ozet);

  if (!kullanici || !dogru || kullanici.aktif !== 1) {
    // TTL yalnizca ilk denemede kurulur; her denemede kurulsa kilit hic dolmaz.
    const denemeSayisi = await redis.incr(kilitAnahtar);
    if (denemeSayisi === 1) await redis.expire(kilitAnahtar, KILIT_SN);
    yanit.status(401).json({ hata: "e-posta veya şifre hatalı" });
    return;
  }

  await redis.del(kilitAnahtar);
  istek.session.regenerate((hata) => {
    if (hata) {
      yanit.status(500).json({ hata: "oturum kurulamadı" });
      return;
    }
    istek.session.kullanici = { id: kullanici.id, eposta: kullanici.eposta, rol: kullanici.rol };
    void yaz("UPDATE kullanici SET son_giris_at = NOW(3) WHERE id = ?", [kullanici.id]);
    void yaz(
      "INSERT INTO audit_log (actor, action, entity, entity_id) VALUES (?, ?, ?, ?)",
      [kullanici.eposta, "giris", "kullanici", kullanici.id],
    );
    // Oturum yenilendiği için eski CSRF token'ı düştü; yenisini üretip veriyoruz.
    const yeniToken = (istek as unknown as { csrfToken: () => string }).csrfToken();
    istek.session.save(() => {
      yanit.json({ id: kullanici.id, eposta: kullanici.eposta, rol: kullanici.rol, token: yeniToken });
    });
  });
});

yonlendirici.post("/cikis", (istek, yanit) => {
  istek.session.destroy(() => yanit.status(204).end());
});

yonlendirici.get("/ben", (istek, yanit) => {
  const kimlik = istek.session.kullanici;
  if (!kimlik) {
    yanit.status(401).json({ hata: "giriş yok" });
    return;
  }
  yanit.json(kimlik);
});

export default yonlendirici;