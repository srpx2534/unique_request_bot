/** Panel uyari uclari (§23.2). */
import { Router } from "express";
import { denetim } from "./denetim.js";
import { sorgu, tek, yaz } from "./veritabani.js";
import { adetOku, aralikKosulu, sayfaOku } from "./panel_ortak.js";

export const yonlendirici = Router();
yonlendirici.get("/", async (istek, yanit) => {
  const kosullar: string[] = [];
  const degerler: unknown[] = [];
  // Durum ve pencere dÄ±ÅŸÄ±ndaki sÃ¼zgeÃ§ler Ã¶zete de uygulanÄ±r: sayaÃ§, listede
  // gÃ¶rÃ¼nen kÃ¼menin aynÄ±sÄ±nÄ± saysÄ±n.
  const ozetKosullar: string[] = [];
  const ozetDegerler: unknown[] = [];

  const ekle = (kosul: string, deger: unknown): void => {
    kosullar.push(kosul);
    degerler.push(deger);
    ozetKosullar.push(kosul);
    ozetDegerler.push(deger);
  };

  const tur = istek.query.tur as string | undefined;
  if (tur) ekle("a.kind = ?", tur);

  const durum = istek.query.durum as string | undefined;
  if (durum === "acik") kosullar.push("a.acknowledged = 0");
  if (durum === "kapali") kosullar.push("a.acknowledged = 1");

  // Pencere yalnÄ±zca kapatÄ±lmÄ±ÅŸ uyarÄ±larÄ± sÃ¼zer: aÃ§Ä±k uyarÄ± ne kadar eski
  // olursa olsun listede kalÄ±r. Aksi halde genel bakÄ±ÅŸtaki sayÄ± ile liste
  // uyuÅŸmaz.
  const aralik = aralikKosulu(istek.query.aralik as string | undefined, "a.created_at");
  if (aralik) kosullar.push(`(a.acknowledged = 0 OR ${aralik})`);

  const ara = (istek.query.q as string | undefined)?.trim();
  if (ara) ekle("a.message LIKE ?", `%${ara}%`);

  const siteAdi = istek.query.site as string | undefined;
  if (siteAdi) ekle("s.domain = ?", siteAdi);

  const kelimeAdi = (istek.query.kelime as string | undefined)?.trim();
  if (kelimeAdi) ekle("k.text LIKE ?", `%${kelimeAdi}%`);

  const nerede = kosullar.length ? `WHERE ${kosullar.join(" AND ")}` : "";
  const adet = adetOku(istek.query.adet, 50);
  const sayfa = sayfaOku(istek.query.sayfa);
  const toplam =
    (
      await tek<{ sayi: number }>(
        `SELECT COUNT(*) AS sayi FROM alert a
           LEFT JOIN keyword k ON k.id = a.keyword_id
           LEFT JOIN site s ON s.id = a.site_id
           ${nerede}`,
        degerler,
      )
    )?.sayi ?? 0;
  const satirlar = await sorgu(
    `SELECT a.id, a.kind, a.ref_id, a.message, a.acknowledged, a.created_at,
            TIMESTAMPDIFF(MINUTE, a.created_at, UTC_TIMESTAMP(3)) AS yas_dk,
            k.text AS kelime, s.domain
       FROM alert a
       LEFT JOIN keyword k ON k.id = a.keyword_id
       LEFT JOIN site s ON s.id = a.site_id
       ${nerede}
      ORDER BY a.acknowledged ASC, a.created_at DESC
      LIMIT ?`,
    [...degerler, adet, (sayfa - 1) * adet],
  );
  const ozetNerede = ozetKosullar.length ? `WHERE ${ozetKosullar.join(" AND ")}` : "";
  const ozet = await tek<Record<string, number>>(
    `SELECT SUM(a.acknowledged = 0) AS acik, SUM(a.acknowledged = 1) AS kapali
       FROM alert a
       LEFT JOIN keyword k ON k.id = a.keyword_id
       LEFT JOIN site s ON s.id = a.site_id
       ${ozetNerede}`,
    ozetDegerler,
  );
  yanit.json({ satirlar, ozet, toplam, sayfa, adet });
});

yonlendirici.post("/tumunu-kapat", async (istek, yanit) => {
  const kosullar = ["acknowledged = 0"];
  const degerler: unknown[] = [];

  const tur = istek.body?.tur as string | undefined;
  if (tur) {
    kosullar.push("kind = ?");
    degerler.push(tur);
  }
  // Pencere burada uygulanmaz: aÃ§Ä±k uyarÄ±larÄ±n hepsi kapanÄ±r, yoksa eski
  // kayÄ±tlar sayaÃ§ta kalÄ±p listeyle uyuÅŸmaz.

  const etkilenen = await yaz(`UPDATE alert SET acknowledged = 1 WHERE ${kosullar.join(" AND ")}`, degerler);
  await denetim(istek, "uyari-tumunu-kapat", "alert", null);
  yanit.json({ kapatilan: etkilenen });
});

yonlendirici.post("/:id/kapat", async (istek, yanit) => {
  const id = Number(istek.params.id);
  if (!Number.isInteger(id)) {
    yanit.status(400).json({ hata: "geÃ§ersiz uyarÄ± kimliÄŸi" });
    return;
  }
  const etkilenen = await yaz("UPDATE alert SET acknowledged = 1 WHERE id = ?", [id]);
  if (etkilenen === 0) {
    yanit.status(404).json({ hata: "uyarÄ± yok" });
    return;
  }
  await denetim(istek, "uyari-kapat", "alert", id);
  yanit.status(204).end();
});

