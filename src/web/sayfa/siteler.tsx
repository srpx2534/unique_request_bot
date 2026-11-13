/** Siteler: ekleme, düzenleme (modal), aç/kapat, silme, arama. */
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

type Site = { id: number; domain: string; label: string | null; active: number; kelime_adet: number };

export default function Siteler() {
  const istemci = useQueryClient();
  const bildir = useBildirim();
  const [domain, setDomain] = useState("");
  const [etiket, setEtiket] = useState("");
  const [arama, setArama] = useState("");
  const [duzenlenen, setDuzenlenen] = useState<Site | null>(null);
  const [silinecek, setSilinecek] = useState<Site | null>(null);

  const liste = useQuery<{ satirlar: Site[] }, ApiHatasi>({
    queryKey: ["site", arama],
    queryFn: () => iste<{ satirlar: Site[] }>(`/site${arama ? `?q=${encodeURIComponent(arama)}` : ""}`),
  });

  const islem = useMutation<unknown, ApiHatasi, { yol: string; yontem: string; govde?: unknown }>({
    mutationFn: ({ yol, yontem, govde }) =>
      iste(yol, { method: yontem, body: govde ? JSON.stringify(govde) : undefined }),
    onSuccess: () => {
      void istemci.invalidateQueries({ queryKey: ["site"] });
      setDuzenlenen(null);
    },
    onError: (hata) => bildir(hata.message, "hata"),
  });

  function ekle(olay: FormEvent) {
    olay.preventDefault();
    islem.mutate(
      { yol: "/site", yontem: "POST", govde: { domain: domain.trim(), label: etiket.trim() || undefined } },
      { onSuccess: () => { setDomain(""); setEtiket(""); bildir("Site eklendi"); } },
    );
  }

  return (
    <div className="space-y-4">
      <Kart baslik="Site ekle">
        <form onSubmit={ekle} className="flex flex-wrap items-end gap-2">
          <label className="w-96 text-sm">
            <span className="text-solgun">Alan adı</span>
            <Girdi value={domain} onChange={(o) => setDomain(o.target.value)} placeholder="ornek.com" className="mt-1" />
          </label>
          <label className="w-48 text-sm">
            <span className="text-solgun">Etiket</span>
            <Girdi value={etiket} onChange={(o) => setEtiket(o.target.value)} className="mt-1" />
          </label>
          <Dugme type="submit" disabled={islem.isPending}>Ekle</Dugme>
        </form>
      </Kart>

      <Kart baslik="Siteler" aciklama={`${liste.data?.satirlar.length ?? 0} kayıt`}>
        <Girdi value={arama} onChange={(o) => setArama(o.target.value)} placeholder="alan adı ya da etiket ara" className="mb-3 max-w-sm" />
        <ul className="divide-y divide-kenar text-sm">
          {liste.data?.satirlar.map((s) => (
            <li key={s.id} className="flex items-center gap-2 py-2">
              <span className="w-72 truncate">{s.domain}</span>
              <span className="w-48 truncate text-solgun">{s.label ?? "—"}</span>
              <span className="flex-1 text-xs text-solgun">{s.kelime_adet} kelime</span>
              <Etiket ton={s.active ? "basari" : "notr"}>{s.active ? "açık" : "kapalı"}</Etiket>
              <Dugme gorunum="sade" className="h-8 px-2 text-xs" onClick={() => setDuzenlenen(s)}>Düzenle</Dugme>
              <Dugme gorunum="ikincil" className="h-8 px-2 text-xs"
                onClick={() => islem.mutate({ yol: `/site/${s.id}`, yontem: "PATCH", govde: { active: s.active !== 1 } })}>
                {s.active ? "Kapat" : "Aç"}
              </Dugme>
              <Dugme gorunum="sade" className="h-8 px-2 text-xs"
                onClick={() => setSilinecek(s)}>
                Sil
              </Dugme>
            </li>
          ))}
        </ul>
        {!liste.data?.satirlar.length ? <p className="mt-3 text-sm text-solgun">Kayıt yok.</p> : null}
      </Kart>

      <Modal acik={duzenlenen !== null} kapat={() => setDuzenlenen(null)} baslik="Siteyi düzenle">
        {duzenlenen ? (
          <div className="space-y-3">
            <label className="block text-sm">
              <span className="text-solgun">Alan adı</span>
              <Girdi value={duzenlenen.domain} className="mt-1"
                onChange={(o) => setDuzenlenen({ ...duzenlenen, domain: o.target.value })} />
            </label>
            <label className="block text-sm">
              <span className="text-solgun">Etiket</span>
              <Girdi value={duzenlenen.label ?? ""} className="mt-1"
                onChange={(o) => setDuzenlenen({ ...duzenlenen, label: o.target.value })} />
            </label>
            <div className="flex gap-2">
              <Dugme disabled={islem.isPending}
                onClick={() => islem.mutate({ yol: `/site/${duzenlenen.id}`, yontem: "PATCH", govde: { domain: duzenlenen.domain, label: duzenlenen.label || null } })}>
                Kaydet
              </Dugme>
              <Dugme gorunum="sade" onClick={() => setDuzenlenen(null)}>Vazgeç</Dugme>
            </div>
          </div>
        ) : null}
      </Modal>

      <Onay
        acik={silinecek !== null}
        baslik="Siteyi sil"
        metin={`${silinecek?.domain} ve altındaki ${silinecek?.kelime_adet ?? 0} kelime kalıcı olarak silinecek.`}
        kapat={() => setSilinecek(null)}
        bekle={islem.isPending}
        onayla={() => {
          if (silinecek) islem.mutate({ yol: `/site/${silinecek.id}`, yontem: "DELETE" }, { onSuccess: () => setSilinecek(null) });
        }}
      />
    </div>
  );
}