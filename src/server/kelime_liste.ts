/** Kelime listesi ucu (§23.2). */
import { Router } from "express";
import { sorgu, tek } from "./veritabani.js";
import { SAYFA_UST, SAYFA_VARSAYILAN, kimlik } from "./kelime_ortak.js";

export const yonlendirici = Router();
yonlendirici.get("/", async (istek, yanit) => {
  const kosullar: string[] = [];
  const degerler: unknown[] = [];

  const siteId = kimlik(istek.query.site as string | undefined);
  if (siteId !== null) {
    kosullar.push("k.site_id = ?");
    degerler.push(siteId);
  }
  const durum = istek.query.durum as string | undefined;
  if (durum) {
    kosullar.push("k.state = ?");
    degerler.push(durum);
  }
  const ara = (istek.query.q as string | undefined)?.trim();
  if (ara) {
    kosullar.push("(k.text LIKE ? OR s.domain LIKE ?)");
    degerler.push(`%${ara}%`, `%${ara}%`);
  }
  const nerede = kosullar.length > 0 ? `WHERE ${kosullar.join(" AND ")}` : "";

  const sayfa = Math.max(1, Number(istek.query.sayfa ?? 1) || 1);
  const adet = Math.min(SAYFA_UST, Math.max(1, Number(istek.query.adet ?? SAYFA_VARSAYILAN) || SAYFA_VARSAYILAN));

  const toplam = await tek<{ sayi: number }>(`SELECT COUNT(*) AS sayi FROM keyword k JOIN site s ON s.id = k.site_id ${nerede}`, degerler);
  const satirlar = await sorgu(
    `SELECT k.id, k.site_id, s.domain, k.text, k.geo_scope, k.home_geo, k.tier, k.mobil, k.state,
            k.created_at,
            (SELECT COUNT(*) FROM keyword_geo g WHERE g.keyword_id = k.id) AS geo_adet,
            (SELECT p.rank FROM position p WHERE p.keyword_id = k.id AND p.channel = 'clean'
              ORDER BY p.checked_at DESC LIMIT 1) AS son_sira,
            (SELECT COUNT(*) FROM position p WHERE p.keyword_id = k.id AND p.channel = 'clean') AS olcum_adet,
            il.name AS il_adi, s.active AS site_active
       FROM keyword k
       JOIN site s ON s.id = k.site_id
       LEFT JOIN geo il ON il.code = k.home_geo
       ${nerede}
      ORDER BY k.id DESC
      LIMIT ? OFFSET ?`,
    [...degerler, adet, (sayfa - 1) * adet],
  );

  yanit.json({ toplam: toplam?.sayi ?? 0, sayfa, adet, satirlar });
});


