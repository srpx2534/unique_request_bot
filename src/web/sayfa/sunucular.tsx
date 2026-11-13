/** Sunucular: kayıt, arama, canlılık, durdur/başlat, silme. */
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { Etiket } from "@/bilesen/ui/etiket";
import { Modal } from "@/bilesen/ui/pencere";
import { Onay } from "@/bilesen/ui/onay";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { ApiHatasi, iste } from "@/lib/api";

type Dugum = {
  id: number;
  ad: string;
  ip: string;
  durum: string;
  yuk: number;
  cpu: string;
  ram: string;
  surum: string | null;
  son_kalp_at: string | null;
  canli: string;
};

type Olay = { id: number; tur: string; message: string | null; created_at: string };

function kalpYasi(zaman: string | null): string {
  if (!zaman) return "—";
  const sn = Math.floor((Date.now() - new Date(zaman).getTime()) / 1000);
  if (sn < 60) return `${sn} sn`;
  if (sn < 3600) return `${Math.floor(sn / 60)} dk`;
  return `${Math.floor(sn / 3600)} sa`;
}

export default function Sunucular() {
  const istemci = useQueryClient();
  const bildir = useBildirim();
  const [ad, setAd] = useState("");
  const [ip, setIp] = useState("");
  const [arama, setArama] = useState("");
  const [durumSuz, setDurumSuz] = useState("");
  const [kalpSuz, setKalpSuz] = useState("");
  const [silinecek, setSilinecek] = useState<Dugum | null>(null);
  const [olaylar, setOlaylar] = useState<Dugum | null>(null);

  const olayListe = useQuery<{ satirlar: Olay[]; toplam: number }, ApiHatasi>({
    queryKey: ["dugum-olay", olaylar?.id],
    queryFn: () => iste(`/dugum/${olaylar?.id}/olay?adet=100`),
    enabled: olaylar !== null,
  });

  const liste = useQuery<Dugum[], ApiHatasi>({
    queryKey: ["dugum", arama, durumSuz, kalpSuz],
    queryFn: () =>
      iste<Dugum[]>(
        `/dugum?${new URLSearchParams({
          ...(arama ? { q: arama } : {}),
          ...(durumSuz ? { durum: durumSuz } : {}),
          ...(kalpSuz ? { kalp: kalpSuz } : {}),
        }).toString()}`,
      ),
    refetchInterval: 10_000,
  });

  const islem = useMutation<unknown, ApiHatasi, { yol: string; yontem: string; govde?: unknown }>({
    mutationFn: ({ yol, yontem, govde }) =>
      iste(yol, { method: yontem, body: govde ? JSON.stringify(govde) : undefined }),
    onSuccess: () => void istemci.invalidateQueries({ queryKey: ["dugum"] }),
    onError: (hata) => bildir(hata.message, "hata"),
  });

  function ekle(olay: FormEvent) {
    olay.preventDefault();
    islem.mutate(
      { yol: "/dugum", yontem: "POST", govde: { ad: ad.trim(), ip: ip.trim() } },
      { onSuccess: () => { setAd(""); setIp(""); bildir("Sunucu kaydedildi"); } },
    );
  }

  const canli = liste.data?.filter((d) => d.canli === "canli").length ?? 0;
  const sessiz = (liste.data?.length ?? 0) - canli;

  return (
    <div className="space-y-4">
      <Kart baslik="Sunucu kaydet">
        <form onSubmit={ekle} className="flex flex-wrap items-end gap-2">
          <label className="w-56 text-sm"><span className="text-solgun">Ad</span>
            <Girdi value={ad} onChange={(o) => setAd(o.target.value)} className="mt-1" /></label>
          <label className="w-48 text-sm"><span className="text-solgun">IP</span>
            <Girdi value={ip} onChange={(o) => setIp(o.target.value)} placeholder="10.0.0.5" className="mt-1" /></label>
          <Dugme type="submit" disabled={islem.isPending}>Kaydet</Dugme>
        </form>
      </Kart>

      <Kart baslik="Sunucular" aciklama={`${canli} canlı · ${sessiz} sessiz`}>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Girdi value={arama} onChange={(o) => setArama(o.target.value)} placeholder="ad ya da IP ara" className="max-w-sm" />
          <select value={durumSuz} onChange={(o) => setDurumSuz(o.target.value)}
            className="h-10 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
            <option value="">tüm durumlar</option>
            <option value="aktif">aktif</option>
            <option value="durduruldu">durduruldu</option>
          </select>
          <select value={kalpSuz} onChange={(o) => setKalpSuz(o.target.value)}
            className="h-10 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
            <option value="">kalp: hepsi</option>
            <option value="canli">canlı</option>
            <option value="sessiz">sessiz</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-[11px] uppercase tracking-wide text-solgun">
              <tr><th className="py-2">#</th><th>Ad</th><th>IP</th><th>Kalp</th><th>Yük</th><th>CPU</th><th>RAM</th><th>Sürüm</th><th>Durum</th><th /></tr>
            </thead>
            <tbody className="divide-y divide-kenar">
              {liste.data?.map((d) => (
                <tr key={d.id} className={d.canli === "canli" ? undefined : "opacity-60"}>
                  <td className="py-2 text-solgun">{d.id}</td>
                  <td>{d.ad}</td>
                  <td className="font-mono text-xs text-solgun">{d.ip}</td>
                  <td className="text-solgun">{kalpYasi(d.son_kalp_at)}</td>
                  <td className="text-solgun">{d.yuk}</td>
                  <td className="text-solgun">{Number(d.cpu).toFixed(0)}%</td>
                  <td className="text-solgun">{Number(d.ram).toFixed(0)}%</td>
                  <td className="text-solgun">{d.surum ?? "—"}</td>
                  <td>
                    <div className="flex flex-col items-start gap-1">
                      <Etiket ton={d.canli === "canli" ? "basari" : "tehlike"}>
                        {d.canli === "canli" ? "canlı" : "sessiz"}
                      </Etiket>
                      <Etiket ton={d.durum === "aktif" ? "notr" : "uyari"}>{d.durum}</Etiket>
                    </div>
                  </td>
                  <td className="text-right">
                    <div className="flex justify-end gap-1">
                      <Dugme gorunum="ikincil" className="h-8 px-2 text-xs"
                        onClick={() => islem.mutate({ yol: `/dugum/${d.id}`, yontem: "PATCH", govde: { durum: d.durum === "aktif" ? "durduruldu" : "aktif" } })}>
                        {d.durum === "aktif" ? "Durdur" : "Başlat"}
                      </Dugme>
                      <Dugme gorunum="sade" className="h-8 px-2 text-xs" onClick={() => setOlaylar(d)}>Olaylar</Dugme>
                      <Dugme gorunum="sade" className="h-8 px-2 text-xs" onClick={() => setSilinecek(d)}>Sil</Dugme>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!liste.data?.length ? <p className="mt-3 text-sm text-solgun">Kayıt yok.</p> : null}
      </Kart>

      <Modal acik={olaylar !== null} kapat={() => setOlaylar(null)} baslik={`${olaylar?.ad ?? ""} · olaylar`}>
        {olayListe.data?.satirlar.length ? (
          <ul className="max-h-80 divide-y divide-kenar overflow-y-auto text-sm">
            {olayListe.data.satirlar.map((o) => (
              <li key={o.id} className="flex items-start gap-2 py-2">
                <Etiket ton="notr">{o.tur}</Etiket>
                <span className="flex-1 text-solgun">{o.message ?? "—"}</span>
                <span className="text-xs text-solgun">{o.created_at.slice(5, 16).replace("T", " ")}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-4 text-center text-sm text-solgun">Olay yok.</p>
        )}
      </Modal>

      <Onay
        acik={silinecek !== null}
        baslik="Sunucuyu sil"
        metin={`${silinecek?.ad} (${silinecek?.ip}) kayıttan çıkarılacak.`}
        kapat={() => setSilinecek(null)}
        bekle={islem.isPending}
        onayla={() => {
          if (silinecek) islem.mutate({ yol: `/dugum/${silinecek.id}`, yontem: "DELETE" }, { onSuccess: () => setSilinecek(null) });
        }}
      />
    </div>
  );
}