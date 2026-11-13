/** Rapor: site ve kelime bazlı hit dökümü, günlük grafik, CSV. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download } from "lucide-react";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { FiltreCubugu, type Aralik } from "@/bilesen/filtre";
import { ApiHatasi, iste } from "@/lib/api";

type Ozet = { hit: number; ok: number; captcha: number; hata: number; burst: number; ort_sn: number };
type SiteSatir = { domain: string; hit: number; ok: number; captcha: number; son: string | null };
type KelimeSatir = { kelime: string; domain: string; il_adi: string | null; hit: number; ok: number; captcha: number; son: string | null };
type Gun = { gun: string; hit: number; ok: number; captcha: number };
type Rapor = { ozet: Ozet; siteler: SiteSatir[]; kelimeler: KelimeSatir[]; gunluk: Gun[] };

function yuzde(pay: number, toplam: number): string {
  if (!toplam) return "—";
  return `%${Math.round((pay / toplam) * 100)}`;
}

function Kpi({ ad, deger, alt, ton }: { ad: string; deger: string; alt?: string; ton?: "tehlike" }) {
  return (
    <div className="rounded-[var(--radius-kutu)] border border-kenar bg-yuzey p-4">
      <p className="text-xs text-solgun">{ad}</p>
      <p className={`mt-1 text-2xl font-semibold ${ton === "tehlike" ? "text-tehlike" : ""}`}>{deger}</p>
      {alt ? <p className="text-xs text-solgun">{alt}</p> : null}
    </div>
  );
}

/** Tabloyu CSV olarak indirir. */
function csvIndir(ad: string, satirlar: (string | number | null)[][], basliklar: string[]) {
  const govde = [basliklar, ...satirlar].map((s) => s.map((h) => `"${String(h ?? "")}"`).join(";")).join("\n");
  const adres = URL.createObjectURL(new Blob([`\ufeff${govde}`], { type: "text/csv;charset=utf-8" }));
  const bag = document.createElement("a");
  bag.href = adres;
  bag.download = `${ad}.csv`;
  bag.click();
  URL.revokeObjectURL(adres);
}

export default function Rapor() {
  const [aralik, setAralik] = useState<Aralik>("hafta");
  const [site, setSite] = useState("");
  const [kelime, setKelime] = useState("");

  const rapor = useQuery<Rapor, ApiHatasi>({
    queryKey: ["rapor", aralik, site, kelime],
    queryFn: () =>
      iste(`/rapor?aralik=${aralik}${site ? `&site=${encodeURIComponent(site)}` : ""}${kelime ? `&kelime=${encodeURIComponent(kelime)}` : ""}`),
  });

  const o = rapor.data?.ozet;
  const grafik = (rapor.data?.gunluk ?? []).map((g) => ({ ...g, gun: g.gun.slice(5) }));

  return (
    <div className="space-y-4">
      <FiltreCubugu aralik={aralik} aralikDegistir={setAralik}>
        <Girdi value={site} onChange={(e) => setSite(e.target.value)} placeholder="site" className="h-8 max-w-[12rem]" />
        <Girdi value={kelime} onChange={(e) => setKelime(e.target.value)} placeholder="kelime" className="h-8 max-w-[12rem]" />
      </FiltreCubugu>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi ad="Toplam hit" deger={String(o?.hit ?? 0)} alt={`${o?.burst ?? 0} burst`} />
        <Kpi ad="Başarılı" deger={String(o?.ok ?? 0)} alt={yuzde(o?.ok ?? 0, o?.hit ?? 0)} />
        <Kpi ad="CAPTCHA" deger={yuzde(o?.captcha ?? 0, o?.hit ?? 0)} alt={`${o?.captcha ?? 0} hit`} ton="tehlike" />
        <Kpi ad="Ortalama burst" deger={`${Math.round(o?.ort_sn ?? 0)} sn`} alt={`${o?.hata ?? 0} hata`} />
      </div>

      <Kart baslik="Günlük hit" aciklama="Başarılı ve CAPTCHA dağılımı.">
        {grafik.length ? (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={grafik}>
                <CartesianGrid stroke="var(--color-kenar)" vertical={false} />
                <XAxis dataKey="gun" tick={{ fontSize: 11, fill: "var(--color-solgun)" }} />
                <YAxis tick={{ fontSize: 11, fill: "var(--color-solgun)" }} width={32} />
                <Tooltip
                  contentStyle={{ background: "var(--color-yuzey)", border: "1px solid var(--color-kenar)", fontSize: 12 }}
                  labelStyle={{ color: "var(--color-metin)" }}
                />
                <Bar dataKey="ok" name="başarılı" stackId="a" fill="var(--color-basari)" />
                <Bar dataKey="captcha" name="captcha" stackId="a" fill="var(--color-tehlike)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="py-8 text-center text-sm text-solgun">Bu aralıkta veri yok.</p>
        )}
      </Kart>

      <Kart baslik="Site bazlı" aciklama="Site başına gönderilen hit.">
        <div className="mb-2 flex justify-end">
          <Dugme gorunum="ikincil" className="h-8 px-2 text-xs"
            onClick={() => csvIndir("site-raporu", (rapor.data?.siteler ?? []).map((s) => [s.domain, s.hit, s.ok, s.captcha, s.son]), ["site", "hit", "basarili", "captcha", "son"])}>
            <Download className="size-3.5" /> CSV
          </Dugme>
        </div>
        {rapor.data?.siteler.length ? (
          <table className="w-full text-sm">
            <thead className="text-left text-[11px] uppercase tracking-wide text-solgun">
              <tr><th className="py-2">Site</th><th>Hit</th><th>Başarılı</th><th>CAPTCHA</th><th>Son</th></tr>
            </thead>
            <tbody className="divide-y divide-kenar">
              {rapor.data.siteler.map((s) => (
                <tr key={s.domain}>
                  <td className="py-2">{s.domain}</td>
                  <td>{s.hit}</td>
                  <td className="text-basari">{s.ok}</td>
                  <td className="text-tehlike">{yuzde(s.captcha, s.hit)}</td>
                  <td className="text-solgun">{s.son ? s.son.slice(5, 16).replace("T", " ") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="py-6 text-center text-sm text-solgun">Kayıt yok.</p>
        )}
      </Kart>

      <Kart baslik="Kelime bazlı" aciklama="Kelime başına gönderilen hit.">
        <div className="mb-2 flex justify-end">
          <Dugme gorunum="ikincil" className="h-8 px-2 text-xs"
            onClick={() => csvIndir("kelime-raporu", (rapor.data?.kelimeler ?? []).map((k) => [k.kelime, k.domain, k.il_adi, k.hit, k.ok, k.captcha]), ["kelime", "site", "il", "hit", "basarili", "captcha"])}>
            <Download className="size-3.5" /> CSV
          </Dugme>
        </div>
        {rapor.data?.kelimeler.length ? (
          <table className="w-full text-sm">
            <thead className="text-left text-[11px] uppercase tracking-wide text-solgun">
              <tr><th className="py-2">Kelime</th><th>Site</th><th>İl</th><th>Hit</th><th>Başarılı</th><th>CAPTCHA</th></tr>
            </thead>
            <tbody className="divide-y divide-kenar">
              {rapor.data.kelimeler.map((k) => (
                <tr key={`${k.domain}-${k.kelime}`}>
                  <td className="py-2">{k.kelime}</td>
                  <td className="text-solgun">{k.domain}</td>
                  <td className="text-solgun">{k.il_adi ?? "—"}</td>
                  <td>{k.hit}</td>
                  <td className="text-basari">{k.ok}</td>
                  <td className="text-tehlike">{yuzde(k.captcha, k.hit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="py-6 text-center text-sm text-solgun">Kayıt yok.</p>
        )}
      </Kart>
    </div>
  );
}