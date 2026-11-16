/** Canlı akış: tarih, site, kelime ve hata filtresi, sayfalı; süzgeçle silme. */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { Etiket } from "@/bilesen/ui/etiket";
import { Onay } from "@/bilesen/ui/onay";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { FiltreCubugu, type Aralik } from "@/bilesen/filtre";
import { Sayfalayici } from "@/bilesen/sayfalayici";
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

type Cevap = { satirlar: Log[]; toplam: number; sayfa: number; adet: number };

const ADETLER = [25, 50, 100, 200];

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
  const istemci = useQueryClient();
  const bildir = useBildirim();
  const [aralik, setAralik] = useState<Aralik>("bugun");
  const [site, setSite] = useState("");
  const [kelime, setKelime] = useState("");
  const [sadeceHata, setSadeceHata] = useState(false);
  const [sayfa, setSayfa] = useState(1);
  const [adet, setAdet] = useState(50);
  const [silinecek, setSilinecek] = useState(false);

  // Süzgeç metni tek yerde kurulur: liste ve silme aynı kümeyi hedefler.
  const suzgec = `aralik=${aralik}${site ? `&site=${encodeURIComponent(site)}` : ""}${kelime ? `&kelime=${encodeURIComponent(kelime)}` : ""}${sadeceHata ? "&sadece_hata=1" : ""}`;

  const liste = useQuery<Cevap, ApiHatasi>({
    queryKey: ["log", aralik, site, kelime, sadeceHata, sayfa, adet],
    queryFn: () => iste(`/log?${suzgec}&sayfa=${sayfa}&adet=${adet}`),
    refetchInterval: 5_000,
  });

  const sil = useMutation<{ silinen: number }, ApiHatasi>({
    mutationFn: () => iste(`/log?${suzgec}`, { method: "DELETE" }),
    onSuccess: (sonuc) => {
      setSilinecek(false);
      setSayfa(1);
      void istemci.invalidateQueries({ queryKey: ["log"] });
      bildir(`${sonuc.silinen} log kaydı silindi`);
    },
  });

  const satirlar = liste.data?.satirlar ?? [];

  return (
    <div className="space-y-4">
      <FiltreCubugu aralik={aralik} aralikDegistir={(y) => { setAralik(y); setSayfa(1); }}>
        <Girdi value={site} onChange={(o) => { setSite(o.target.value); setSayfa(1); }} placeholder="site" className="h-8 max-w-[12rem]" />
        <Girdi value={kelime} onChange={(o) => { setKelime(o.target.value); setSayfa(1); }} placeholder="kelime" className="h-8 max-w-[12rem]" />
        <button type="button" onClick={() => { setSadeceHata((o) => !o); setSayfa(1); }}
          className={`rounded-full px-3 py-1 text-xs ${sadeceHata ? "bg-tehlike/15 text-tehlike" : "text-solgun hover:bg-yuzey-2"}`}>
          sadece hatalı
        </button>
        <select value={adet} onChange={(o) => { setAdet(Number(o.target.value)); setSayfa(1); }}
          className="ml-auto h-8 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-2 text-xs">
          {ADETLER.map((a) => <option key={a} value={a}>{a}/sayfa</option>)}
        </select>
        <Dugme gorunum="ikincil" className="h-8 px-2 text-xs" disabled={!liste.data?.toplam}
          onClick={() => setSilinecek(true)}>
          logları sil
        </Dugme>
        <span className="text-xs text-solgun">5 sn</span>
      </FiltreCubugu>

      <Kart>
        {satirlar.length ? (
          <ul className="divide-y divide-kenar font-mono text-xs">
            {satirlar.map((l) => {
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
        <div className="mt-3 border-t border-kenar pt-3">
          <Sayfalayici sayfa={sayfa} toplam={liste.data?.toplam ?? 0} adet={adet} degistir={setSayfa} />
        </div>
      </Kart>

      <Onay
        acik={silinecek}
        baslik="Logları sil"
        dugmeEtiketi="Sil"
        metin={`Seçili süzgeçteki ${liste.data?.toplam ?? 0} burst ve bağlı hit kayıtları silinir. Kampanya, kelime ve sıralama kayıtları etkilenmez.`}
        kapat={() => setSilinecek(false)}
        bekle={sil.isPending}
        onayla={() => sil.mutate()}
      />
    </div>
  );
}
