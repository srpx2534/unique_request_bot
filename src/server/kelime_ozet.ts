/** Kelime ozet ucu: sirasi ve ilerlemesi (§23.2). */
import { Router } from "express";
import { sorgu, tek } from "./veritabani.js";
import { kimlik } from "./kelime_ortak.js";

export const yonlendirici = Router();

yonlendirici.get("/:id/ozet", async (istek, yanit) => {
  const id = kimlik(istek.params.id);
  if (id === null) {
    yanit.status(400).json({ hata: "gecersiz kelime kimligi" });
    return;
  }
  const kelime = await tek<{ text: string; state: string; volume: number | null }>(
    "SELECT text, state, volume FROM keyword WHERE id = ?",
    [id],
  );
  if (!kelime) {
    yanit.status(404).json({ hata: "kelime yok" });
    return;
  }

  // Siralama gecmisi: en eski ve en yeni kayit; trend bu ikisinden cikar.
  const gecmis = await sorgu<{ rank: number | null; checked_at: string }>(
    `SELECT rank, checked_at FROM position WHERE keyword_id = ? AND channel = 'clean'
      ORDER BY checked_at ASC LIMIT 500`,
    [id],
  );
  const olcum = gecmis.filter((g) => g.rank !== null);
  const ilk = olcum[0] ?? null;
  const son = olcum[olcum.length - 1] ?? null;

  const hitler = await tek<{ ok: number; fail: number; toplam: number }>(
    `SELECT
       (SELECT COUNT(*) FROM hit h JOIN burst b ON b.id = h.burst_id
          JOIN keyword_geo g ON g.id = b.keyword_geo_id
         WHERE g.keyword_id = ? AND h.result = 'ok') AS ok,
       (SELECT COUNT(*) FROM hit h JOIN burst b ON b.id = h.burst_id
          JOIN keyword_geo g ON g.id = b.keyword_geo_id
         WHERE g.keyword_id = ? AND h.result <> 'ok') AS fail,
       (SELECT COUNT(*) FROM burst b JOIN keyword_geo g ON g.id = b.keyword_geo_id
         WHERE g.keyword_id = ?) AS toplam`,
    [id, id, id],
  );

  const burstlar = await sorgu(
    `SELECT b.id, b.step, b.target_count, b.phase, b.started_at, b.ended_at
       FROM burst b JOIN keyword_geo g ON g.id = b.keyword_geo_id
      WHERE g.keyword_id = ? ORDER BY b.id DESC LIMIT 20`,
    [id],
  );

  yanit.json({
    kelime: kelime.text,
    state: kelime.state,
    volume: kelime.volume,
    olcum_sayisi: olcum.length,
    ilk_sira: ilk?.rank ?? null,
    ilk_at: ilk?.checked_at ?? null,
    son_sira: son?.rank ?? null,
    son_at: son?.checked_at ?? null,
    trend:
      ilk && son && ilk.rank !== null && son.rank !== null
        ? ilk.rank === son.rank
          ? "sabit"
          : son.rank < ilk.rank
            ? "yukari"
            : "asagi"
        : "yok",
    hit_ok: hitler?.ok ?? 0,
    hit_fail: hitler?.fail ?? 0,
    burst_adet: hitler?.toplam ?? 0,
    burstlar,
    seri: gecmis.slice(-60),
  });
});