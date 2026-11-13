/** Genel bakış: durum şeridi, aktif kelimeler, uyarılar ve son burst'ler. */
import { Link } from "react-router-dom";
import { ArrowUpRight, Plus } from "lucide-react";
import { Kart } from "@/bilesen/ui/kart";
import { Etiket } from "@/bilesen/ui/etiket";
import { Dugme } from "@/bilesen/ui/dugme";
import { ozetKullan } from "@/lib/panel";

/** Göreli zaman: "3 dk", "2 sa", "—". */
function gecen(zaman: string | null): string {
  if (!zaman) return "—";
  const dk = Math.floor((Date.now() - new Date(zaman).getTime()) / 60_000);
  if (dk < 1) return "şimdi";
  if (dk < 60) return `${dk} dk`;
  if (dk < 1440) return `${Math.floor(dk / 60)} sa`;
  return `${Math.floor(dk / 1440)} gün`;
}

function Kart2({ ad, deger, alt }: { ad: string; deger?: number; alt?: string }) {
  return (
    <div className="rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-solgun">{ad}</p>
      <p className="text-lg font-semibold">{deger ?? "—"}</p>
      {alt ? <p className="text-[11px] text-solgun">{alt}</p> : null}
    </div>
  );
}

export default function Panel() {
  const ozet = ozetKullan();
  const h = ozet.data?.havuz;
  const toplam = (h?.canli_tr ?? 0) + (h?.canli_yabanci ?? 0) + (h?.olu ?? 0) || 1;
  const trOran = Math.round(((h?.canli_tr ?? 0) / toplam) * 100);

  return (
    <div className="space-y-4">
      <section className="rounded-[var(--radius-kutu)] border border-kenar bg-yuzey p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1">
            <p className="text-xs text-solgun">Havuz sağlığı</p>
            <div className="mt-1.5 flex h-2 overflow-hidden rounded-full bg-yuzey-2">
              <span className="bg-basari" style={{ width: `${(h?.canli_tr ?? 0) / toplam * 100}%` }} />
              <span className="bg-uyari" style={{ width: `${(h?.canli_yabanci ?? 0) / toplam * 100}%` }} />
              <span className="bg-tehlike/60" style={{ width: `${(h?.olu ?? 0) / toplam * 100}%` }} />
            </div>
            <p className="mt-1.5 text-xs text-solgun">
              TR {h?.canli_tr ?? 0} · yabancı {h?.canli_yabanci ?? 0} · ölü {h?.olu ?? 0}
              {trOran === 0 ? <span className="text-tehlike"> — TR IP yok, sıralama TR'den gelmiyor</span> : null}
            </p>
          </div>
          <Link to="/uyarilar" className="rounded-[var(--radius-kutu)] border border-kenar px-3 py-2 text-sm hover:bg-yuzey-2">
            Açık uyarı <span className={ozet.data?.acik_uyari ? "font-semibold text-uyari" : "text-solgun"}>{ozet.data?.acik_uyari ?? 0}</span>
          </Link>
          <Link to="/kelimeler">
            <Dugme><Plus className="size-4" /> Kelime ekle</Dugme>
          </Link>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kart2 ad="Aktif site" deger={ozet.data?.aktif_site} />
        <Kart2 ad="Aktif kelime" deger={ozet.data?.aktif_kelime} />
        <Kart2 ad="Son 24 saat burst" deger={ozet.data?.gunluk_burst} />
        <Kart2 ad="Toplam kelime" deger={ozet.data?.toplam_kelime} alt="arşiv dahil" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Kart baslik="Aktif kelimeler" aciklama="Hedefe göre ilerleme; durdurmak için Kelimeler ekranı.">
          {ozet.data?.kelimeler.length ? (
            <table className="w-full text-sm">
              <thead className="text-left text-[11px] uppercase tracking-wide text-solgun">
                <tr><th className="py-2">Kelime</th><th>İl</th><th>Hacim</th><th className="w-32">Hedef</th><th>Son hit</th></tr>
              </thead>
              <tbody className="divide-y divide-kenar">
                {ozet.data.kelimeler.map((k) => {
                  const oran = k.volume ? Math.min(100, Math.round((k.atilan / k.volume) * 100)) : 0;
                  return (
                    <tr key={k.id}>
                      <td className="py-2">
                        <div className="flex items-center gap-2">
                          <span className="size-1.5 rounded-full bg-basari" />
                          <span className="truncate">{k.text}</span>
                        </div>
                        <p className="pl-3.5 text-xs text-solgun">{k.domain} · {k.geo_adet} geo</p>
                      </td>
                      <td className="text-solgun">{k.il_adi ?? "TR geneli"}</td>
                      <td className="text-solgun">{k.volume ?? "∞"}</td>
                      <td>
                        {k.volume ? (
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-yuzey-2">
                              <span className="block h-full bg-vurgu" style={{ width: `${oran}%` }} />
                            </div>
                            <span className="text-[11px] text-solgun">{oran}%</span>
                          </div>
                        ) : (
                          <span className="text-[11px] text-solgun">sınırsız</span>
                        )}
                      </td>
                      <td className="text-solgun">{gecen(k.son_burst_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="py-6 text-center">
              <p className="text-sm text-solgun">Çalışan kelime yok.</p>
              <Link to="/kelimeler" className="mt-2 inline-block text-sm text-vurgu hover:underline">Kelime ekle</Link>
            </div>
          )}
        </Kart>

        <div className="space-y-4">
          <Kart baslik="Uyarılar" aciklama="Kapatmak için Uyarılar ekranı.">
            {ozet.data?.uyarilar.length ? (
              <ul className="divide-y divide-kenar text-sm">
                {ozet.data.uyarilar.map((u) => (
                  <li key={u.id} className="py-2">
                    <div className="flex items-center gap-2">
                      <Etiket ton="uyari">{u.kind}</Etiket>
                      <span className="ml-auto text-[11px] text-solgun">{u.yas_dk} dk</span>
                    </div>
                    <p className="mt-1">{u.message}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-solgun">Açık uyarı yok.</p>
            )}
          </Kart>

          <Kart baslik="Aktif siteler">
            {ozet.data?.siteler.length ? (
              <ul className="divide-y divide-kenar text-sm">
                {ozet.data.siteler.map((s) => (
                  <li key={s.id} className="flex items-center gap-2 py-2">
                    <span className="truncate">{s.domain}</span>
                    <span className="ml-auto truncate text-xs text-solgun">{s.label ?? ""}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-solgun">Aktif site yok.</p>
            )}
          </Kart>

          <Kart baslik="Son burst'ler">
            {ozet.data?.son.length ? (
              <ul className="divide-y divide-kenar text-sm">
                {ozet.data.son.map((b) => (
                  <li key={b.id} className="flex items-center gap-2 py-1.5">
                    <span className="text-[11px] text-solgun">#{b.id}</span>
                    <span className="flex-1 truncate">{b.text}</span>
                    <span className="text-[11px] text-solgun">{b.target_count} hit</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-solgun">Henüz burst yok.</p>
            )}
          </Kart>
        </div>
      </div>

      <p className="flex items-center gap-1 text-xs text-solgun">
        <ArrowUpRight className="size-3" /> Veriler 15 saniyede bir tazelenir.
      </p>
    </div>
  );
}