/**
 * Cerez defteri uclari.
 *
 * Bolumler ayri dosyada: ozet, silme ve yukleme. Montaj sirasi onemlidir;
 * `/cerez/yukleme` oneksi genel `/cerez/:id` yakalamasin diye yukleme
 * yonlendiricisi kendi onekine baglanir.
 *
 * Kullanim: src/server/uygulama.ts
 */
import { Router } from "express";
import { yonlendirici as sayfa } from "./sayfa.js";
import { yonlendirici as silme } from "./silme.js";
import { yonlendirici as yukleme } from "./yukleme.js";

export { kuyrukBaslat, kuyrukKapat } from "./aktarim.js";

const yonlendirici = Router();

yonlendirici.use("/cerez/yukleme", yukleme);
yonlendirici.use("/cerez", sayfa);
yonlendirici.use("/cerez", silme);

export default yonlendirici;