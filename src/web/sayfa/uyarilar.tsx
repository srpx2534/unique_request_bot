/** Uyarılar: tür, durum ve tarih filtreli liste. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { Etiket } from "@/bilesen/ui/etiket";
import { FiltreCubugu, type Aralik } from "@/bilesen/filtre";
import { uyariKapat, uyariTumunuKapat } from "@/lib/panel";
import { Onay } from "@/bilesen/ui/onay";
import { ApiHatasi, iste } from "@/lib/api";

type Uyari = {
  id: number;
  kind: string;
  message: string;
  acknowledged: number;
  created_at: string;
  yas_dk: number;
  kelime: string | null;
  domain: string | null;
};

const TURLER = ["captcha", "provider_down", "queue_lag", "quota", "fallback_high", "hedef_yok", "failover", "burst_hata"];
const TON: Record<string, "tehlike" | "uyari" | "notr" | "vurgu"> = {
  captcha: "tehlike",
  provider_down: "tehlike",
  burst_hata: "tehlike",
  quota: "uyari",
  fallback_high: "uyari",
  hedef_yok: "uyari",
  queue_lag: "vurgu",
  failover: "notr",
};

export default function Uyarilar() {
  const [aralik, setAralik] = useState<Aralik>("hafta");
  const [tur, setTur] = useState("");
  const [durum, setDurum] = useState("acik");
  const [arama, setArama] = useState("");
  const [site, setSite] = useState("");
  const [kelime, setKelime] = useState("");
  const kapat = uyariKapat();
  const tumunuKapat = uyariTumunuKapat();
  const [tumunuOnay, setTumunuOnay] = useState(false);
  const [adet, setAdet] = useState(100);

  const liste = useQuery<{ satirlar: Uyari[]; ozet: { acik: number; kapali: number } }, ApiHatasi>({
    queryKey: ["uyari", aralik, tur, durum, arama, site, kelime, adet],
    queryFn: () =>
      iste(
        `/uyari?aralik=${aralik}${tur ? `&tur=${tur}` : ""}${durum ? `&durum=${durum}` : ""}${arama ? `&q=${encodeURIComponent(arama)}` : ""}${site ? `&site=${encodeURIComponent(site)}` : ""}${kelime ? `&kelime=${encodeURIComponent(kelime)}` : ""}&adet=${adet}`,
      ),
  });

  const gunler = (liste.data?.satirlar ?? []).reduce<Record<string, Uyari[]>>((acc, u) => {
    const gun = u.created_at.slice(0, 10);
    (acc[gun] ??= []).push(u);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <FiltreCubugu aralik={aralik} aralikDegistir={setAralik}>
        <Girdi value={arama} onChange={(o) => setArama(o.target.value)} placeholder="mesajda ara" className="h-8 max-w-[12rem]" />
        <Girdi value={site} onChange={(o) => setSite(o.target.value)} placeholder="site" className="h-8 max-w-[10rem]" />
        <Girdi value={kelime} onChange={(o) => setKelime(o.target.value)} placeholder="kelime" className="h-8 max-w-[10rem]" />
        <select value={tur} onChange={(o) => setTur(o.target.value)}
          className="h-8 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-2 text-xs">
          <option value="">tüm türler</option>
          {TURLER.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={durum} onChange={(o) => setDurum(o.target.value)}
          className="h-8 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-2 text-xs">
          <option value="acik">açık</option>
          <option value="kapali">kapatılmış</option>
          <option value="">hepsi</option>
        </select>
        <button type="button" onClick={() => setTumunuOnay(true)}
          disabled={tumunuKapat.isPending}
          className="ml-auto rounded-full bg-yuzey-2 px-3 py-1 text-xs text-metin hover:bg-kenar">
          tümünü kapat
        </button>
        <button type="button" onClick={() => setAdet((o) => o + 100)}
          disabled={(liste.data?.satirlar.length ?? 0) < adet}
          className="rounded-full bg-yuzey-2 px-3 py-1 text-xs hover:bg-kenar">
          daha fazla
        </button>
        <span className="text-xs text-solgun">
          açık {liste.data?.ozet?.acik ?? 0} · kapatılmış {liste.data?.ozet?.kapali ?? 0}
        </span>
      </FiltreCubugu>

      <Onay
        acik={tumunuOnay}
        baslik="Uyarilari kapat"
        dugmeEtiketi="Kapat"
        metin="Filtreye uyan tum acik uyarilar kapatilacak. Kapatilan uyari geri acilmaz."
        kapat={() => setTumunuOnay(false)}
        bekle={tumunuKapat.isPending}
        onayla={() =>
          tumunuKapat.mutate(
            { tur: tur || undefined, aralik },
            { onSuccess: () => setTumunuOnay(false) },
          )
        }
      />

      <Kart>
        {Object.keys(gunler).length ? (
          <div className="space-y-5">
            {Object.entries(gunler).map(([gun, satirlar]) => (
              <div key={gun}>
                <p className="mb-2 text-xs font-medium text-solgun">
                  {new Date(gun).toLocaleDateString("tr-TR", { day: "numeric", month: "long", weekday: "short" })} · {satirlar.length}
                </p>
                <ul className="divide-y divide-kenar text-sm">
                  {satirlar.map((u) => (
                    <li key={u.id} className="flex items-start gap-3 py-2">
                      <Etiket ton={TON[u.kind] ?? "notr"}>{u.kind}</Etiket>
                      <div className="flex-1">
                        <p>{u.message}</p>
                        <p className="mt-0.5 text-xs text-solgun">
                          {u.domain ?? "site yok"} · {u.kelime ?? "kelime yok"}
                        </p>
                      </div>
                      <button type="button" onClick={() => setAdet((o) => o + 100)}
          disabled={(liste.data?.satirlar.length ?? 0) < adet}
          className="rounded-full bg-yuzey-2 px-3 py-1 text-xs hover:bg-kenar">
          daha fazla
        </button>
        <span className="text-xs text-solgun">{u.created_at.slice(11, 16)}</span>
                      {!u.acknowledged ? (
                        <Dugme gorunum="sade" className="h-7 px-2 text-xs" onClick={() => kapat.mutate(u.id)}>Kapat</Dugme>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-solgun">Bu filtrede uyarı yok.</p>
        )}
      </Kart>
    </div>
  );
}