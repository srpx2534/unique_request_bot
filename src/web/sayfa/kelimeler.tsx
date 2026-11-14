/** Kelime listesi: ekleme, modal düzenleme, başlat/durdur, silme, arama. */
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

type Site = { id: number; domain: string };
type Il = { code: number; name: string };
type Kelime = {
  id: number;
  text: string;
  domain: string;
  geo_scope: string;
  il_adi: string | null;
  volume: number | null;
  mobil: number;
  state: string;
  geo_adet: number;
  site_active: number;
};

const DURUM_TON: Record<string, "basari" | "uyari" | "notr"> = {
  active: "basari",
  paused: "uyari",
  idle: "notr",
  retired: "notr",
};

export default function Kelimeler() {
  const istemci = useQueryClient();
  const bildir = useBildirim();
  const [siteId, setSiteId] = useState<number | null>(null);
  const [metin, setMetin] = useState("");
  const [kapsam, setKapsam] = useState<"national" | "province">("national");
  const [il, setIl] = useState("34");

  const [hacim, setHacim] = useState("");
  const [arama, setArama] = useState("");
  const [duzenlenen, setDuzenlenen] = useState<Kelime | null>(null);
  const [silinecek, setSilinecek] = useState<Kelime | null>(null);

  const siteler = useQuery<{ satirlar: Site[] }, ApiHatasi>({ queryKey: ["site"], queryFn: () => iste<{ satirlar: Site[] }>("/site") });
  const iller = useQuery<Il[], ApiHatasi>({ queryKey: ["geo"], queryFn: () => iste<Il[]>("/geo"), staleTime: 600_000 });
  const liste = useQuery<{ satirlar: Kelime[]; toplam: number }, ApiHatasi>({
    queryKey: ["kelime", siteId, arama],
    queryFn: () =>
      iste(`/kelime?adet=200${siteId ? `&site=${siteId}` : ""}${arama ? `&q=${encodeURIComponent(arama)}` : ""}`),
  });

  const islem = useMutation<unknown, ApiHatasi, { yol: string; yontem: string; govde?: unknown }>({
    mutationFn: ({ yol, yontem, govde }) =>
      iste(yol, { method: yontem, body: govde ? JSON.stringify(govde) : undefined }),
    onSuccess: () => {
      void istemci.invalidateQueries({ queryKey: ["kelime"] });
      setDuzenlenen(null);
    },
    onError: (hata) => bildir(hata.message, "hata"),
  });

  const [mobil, setMobil] = useState(false);

  function ekle(olay: FormEvent) {
    olay.preventDefault();
    if (!siteId) {
      bildir("Önce site seç", "hata");
      return;
    }
    islem.mutate(
      { yol: "/kelime", yontem: "POST", govde: { site_id: siteId, kelime: metin, kapsam, il: kapsam === "province" ? Number(il) : null, volume: hacim ? Number(hacim) : null, mobil } },
      { onSuccess: () => setMetin("") },
    );
  }

  return (
    <div className="space-y-4">
      <Kart baslik="Kelime ekle">
        <form onSubmit={ekle} className="flex flex-wrap items-end gap-2">
          <label className="w-72 shrink-0 text-sm">
            <span className="text-solgun">Site</span>
            <select value={siteId ?? ""} onChange={(o) => setSiteId(o.target.value ? Number(o.target.value) : null)}
              className="mt-1 block h-10 w-full rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
              <option value="">seç</option>
              {siteler.data?.satirlar.map((s) => <option key={s.id} value={s.id}>{s.domain}</option>)}
            </select>
          </label>
          <label className="w-56 text-sm">
            <span className="text-solgun">Kelime</span>
            <Girdi value={metin} onChange={(o) => setMetin(o.target.value)} className="mt-1" />
          </label>
          <label className="w-24 text-sm">
            <span className="text-solgun">Mod</span>
            <select value={mobil ? "1" : "0"} onChange={(o) => setMobil(o.target.value === "1")}
              className="mt-1 block h-10 w-full rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
              <option value="0">Web</option>
              <option value="1">Mobil</option>
            </select>
          </label>
          <label className="w-32 text-sm">
            <span className="text-solgun">Kapsam</span>
            <select value={kapsam} onChange={(o) => setKapsam(o.target.value as "national" | "province")}
              className="mt-1 block h-10 w-full rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
              <option value="national">national</option>
              <option value="province">province</option>
            </select>
          </label>
          {kapsam === "province" ? (
            <label className="w-52 text-sm">
              <span className="text-solgun">İl</span>
              <select value={il} onChange={(o) => setIl(o.target.value)}
                className="mt-1 block h-10 w-full rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
                {iller.data?.map((x) => <option key={x.code} value={x.code}>{x.name}</option>)}
              </select>
            </label>
          ) : null}
          <label className="w-32 text-sm">
            <span className="text-solgun">Aylık hacim</span>
            <Girdi value={hacim} onChange={(o) => setHacim(o.target.value)} className="mt-1" />
          </label>

          <Dugme type="submit" disabled={islem.isPending}>Ekle</Dugme>
        </form>
      </Kart>

      <Kart baslik="Kelimeler" aciklama={`${liste.data?.toplam ?? 0} kayıt`}>
        <Girdi value={arama} onChange={(o) => setArama(o.target.value)} placeholder="kelime ya da site ara" className="mb-3 max-w-sm" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-solgun">
              <tr><th className="py-2">Kelime</th><th>Site</th><th>Kapsam</th><th>İl</th><th>Geo</th><th>Hacim</th><th>Mod</th><th>Durum</th><th /></tr>
            </thead>
            <tbody className="divide-y divide-kenar">
              {liste.data?.satirlar.map((k) => (
                <tr key={k.id} className={k.site_active === 1 ? undefined : "opacity-60"}>
                  <td className="py-2 pr-2">{k.text}</td>
                  <td className="text-solgun">{k.domain}</td>
                  <td className="text-solgun">{k.geo_scope}</td>
                  <td className="text-solgun">{k.il_adi ?? "—"}</td>
                  <td className="text-solgun">{k.geo_adet}</td>
                  <td className="text-solgun">{k.volume ?? "—"}</td>
                  <td>
                    <Dugme
                      gorunum="sade"
                      className="h-8 px-2 text-xs"
                      onClick={() => islem.mutate({ yol: `/kelime/${k.id}`, yontem: "PATCH", govde: { mobil: k.mobil !== 1 } })}
                    >
                      {k.mobil === 1 ? "Mobil" : "Web"}
                    </Dugme>
                  </td>
                  <td>
                    <div className="flex flex-col items-start gap-1">
                      <Etiket ton={DURUM_TON[k.state] ?? "notr"}>{k.state}</Etiket>
                      {k.site_active === 1 ? null : <Etiket ton="tehlike">site kapalı</Etiket>}
                    </div>
                  </td>
                  <td className="text-right">
                    <div className="flex justify-end gap-1">
                      <Dugme gorunum="sade" className="h-8 px-2 text-xs" onClick={() => setDuzenlenen(k)}>Düzenle</Dugme>
                      {k.state === "active" ? (
                        <Dugme gorunum="ikincil" className="h-8 px-2 text-xs" onClick={() => islem.mutate({ yol: `/kelime/${k.id}/durdur`, yontem: "POST" })}>Durdur</Dugme>
                      ) : (
                        <Dugme gorunum="ikincil" className="h-8 px-2 text-xs" onClick={() => islem.mutate({ yol: `/kelime/${k.id}/baslat`, yontem: "POST" })}>Başlat</Dugme>
                      )}
                      <Dugme gorunum="sade" className="h-8 px-2 text-xs" onClick={() => setSilinecek(k)}>Sil</Dugme>
                    </div>
                  </td>
                </tr>
              ))}            </tbody>
          </table>
        </div>
        {!liste.data?.satirlar.length ? <p className="mt-3 text-sm text-solgun">Kayıt yok.</p> : null}
      </Kart>

      <Modal acik={duzenlenen !== null} kapat={() => setDuzenlenen(null)} baslik="Kelimeyi düzenle">
        {duzenlenen ? (
          <div className="space-y-3">
            <p className="text-xs text-solgun">
              Durum: <Etiket ton={DURUM_TON[duzenlenen.state] ?? "notr"}>{duzenlenen.state}</Etiket> — buradan değişmez, listeden başlat/durdur. Mobil kelime mobil IP ve android profil ister; mobil IP yoksa normal proxy kullanılır.
            </p>
            <label className="block text-sm">
              <span className="text-solgun">Kelime</span>
              <Girdi value={duzenlenen.text} className="mt-1"
                onChange={(o) => setDuzenlenen({ ...duzenlenen, text: o.target.value })} />
            </label>
            <label className="block text-sm">
              <span className="text-solgun">Aylık hacim</span>
              <Girdi value={duzenlenen.volume ?? ""} className="mt-1"
                onChange={(o) => setDuzenlenen({ ...duzenlenen, volume: o.target.value ? Number(o.target.value) : null })} />
            </label>
            <label className="block text-sm">
              <span className="text-solgun">Mod</span>
              <select value={duzenlenen.mobil === 1 ? "1" : "0"}
                onChange={(o) => setDuzenlenen({ ...duzenlenen, mobil: o.target.value === "1" ? 1 : 0 })}
                className="mt-1 block h-10 w-full rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
                <option value="0">Web</option>
                <option value="1">Mobil</option>
              </select>
            </label>
            <div className="flex gap-2">
              <Dugme disabled={islem.isPending}
                onClick={() => islem.mutate({ yol: `/kelime/${duzenlenen.id}`, yontem: "PATCH", govde: { kelime: duzenlenen.text, volume: duzenlenen.volume, mobil: duzenlenen.mobil === 1 } })}>
                Kaydet
              </Dugme>
              <Dugme gorunum="sade" onClick={() => setDuzenlenen(null)}>Vazgeç</Dugme>
            </div>
          </div>
        ) : null}
      </Modal>

      <Onay
        acik={silinecek !== null}
        baslik="Kelimeyi sil"
        metin={`"${silinecek?.text}" ve ${silinecek?.geo_adet ?? 0} geo satırı kalıcı olarak silinecek.`}
        kapat={() => setSilinecek(null)}
        bekle={islem.isPending}
        onayla={() => {
          if (silinecek) islem.mutate({ yol: `/kelime/${silinecek.id}`, yontem: "DELETE" }, { onSuccess: () => setSilinecek(null) });
        }}
      />
    </div>
  );
}