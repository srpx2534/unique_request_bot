/** Canlı akış: tarih, site, kelime ve hata filtresiyle. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Girdi } from "@/bilesen/ui/girdi";
import { Etiket } from "@/bilesen/ui/etiket";
import { FiltreCubugu, type Aralik } from "@/bilesen/filtre";
import { ApiHatasi, iste } from "@/lib/api";

type Log = {
  id: number;
  kelime: string;
  domain: string;
  step: number;
  target_count: number;
  started_at: string;
  ended_at: string | null;
  stats: string;
  tier: string;
  il_adi: string | null;
};

function ozet(stats: string): { metin: string; hata: boolean } {
  try {
    const g = JSON.parse(stats) as Record<string, number>;
    const hata = Boolean(g.hata) || (g.error ?? 0) > 0;
    const parcalar = Object.entries(g).filter(([, v]) => v > 0).map(([k, v]) => `${k} ${v}`);
    return { metin: parcalar.length ? parcalar.join(" · ") : "boş", hata };
  } catch {
    return { metin: "boş", hata: false };
  }
}

export default function Loglar() {
  const [aralik, setAralik] = useState<Aralik>("bugun");
  const [site, setSite] = useState("");
  const [kelime, setKelime] = useState("");
  const [sadeceHata, setSadeceHata] = useState(false);

  const liste = useQuery<Log[], ApiHatasi>({
    queryKey: ["log", aralik, site, kelime, sadeceHata],
    queryFn: () =>
      iste(
        `/log?aralik=${aralik}${site ? `&site=${encodeURIComponent(site)}` : ""}${kelime ? `&kelime=${encodeURIComponent(kelime)}` : ""}${sadeceHata ? "&sadece_hata=1" : ""}`,
      ),
    refetchInterval: 5_000,
  });

  return (
    <div className="space-y-4">
      <FiltreCubugu aralik={aralik} aralikDegistir={setAralik}>
        <Girdi value={site} onChange={(o) => setSite(o.target.value)} placeholder="site" className="h-8 max-w-[12rem]" />
        <Girdi value={kelime} onChange={(o) => setKelime(o.target.value)} placeholder="kelime" className="h-8 max-w-[12rem]" />
        <button type="button" onClick={() => setSadeceHata((o) => !o)}
          className={`rounded-full px-3 py-1 text-xs ${sadeceHata ? "bg-tehlike/15 text-tehlike" : "text-solgun hover:bg-yuzey-2"}`}>
          sadece hatalı
        </button>
        <span className="ml-auto text-xs text-solgun">{liste.data?.length ?? 0} kayıt · 5 sn</span>
      </FiltreCubugu>

      <Kart>
        {liste.data?.length ? (
          <ul className="divide-y divide-kenar font-mono text-xs">
            {liste.data.map((l) => {
              const s = ozet(l.stats);
              return (
                <li key={l.id} className="flex items-start gap-2 py-2">
                  <span className="pt-0.5 text-solgun">{l.started_at.slice(5, 16).replace("T", " ")}</span>
                  <Etiket ton={l.ended_at ? "notr" : "vurgu"}>{l.ended_at ? "bitti" : "sürüyor"}</Etiket>
                  <div className="min-w-0 flex-1">
                    <p className="truncate">{l.kelime}</p>
                    <p className="truncate text-solgun">{l.domain} · {l.il_adi ?? l.tier}</p>
                  </div>
                  <span className={s.hata ? "text-tehlike" : "text-solgun"}>{s.metin}</span>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="py-6 text-center text-sm text-solgun">Bu filtrede kayıt yok.</p>
        )}
      </Kart>
    </div>
  );
}