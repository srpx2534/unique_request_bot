/** Sağlayıcılar: ekleme, tam düzenleme, aç/kapat, silme, arama ve tür oranı. */
import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { Etiket } from "@/bilesen/ui/etiket";
import { Modal } from "@/bilesen/ui/pencere";
import { Onay } from "@/bilesen/ui/onay";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { ayarKullan, ayarYaz, saglayiciGuncelle, saglayiciKullan, type Saglayici } from "@/lib/panel";
import { ApiHatasi, iste } from "@/lib/api";

const DURUM_TON: Record<string, "basari" | "uyari" | "notr"> = {
  active: "basari",
  quarantine: "uyari",
  disabled: "notr",
};

type Form = { name: string; kind: string; ulke: string; gateway: string; kullanici: string; sifre: string; weight: string };
const BOS: Form = { name: "", kind: "residential", ulke: "TR", gateway: "", kullanici: "", sifre: "", weight: "1" };

export default function Saglayicilar() {
  const [arama, setArama] = useState("");
  const liste = saglayiciKullan(arama);
  const ayarlar = ayarKullan();
  const guncelle = saglayiciGuncelle();
  const yaz = ayarYaz();
  const bildir = useBildirim();
  const istemci = useQueryClient();
  const [oranlar, setOranlar] = useState<Record<string, string>>({});
  const [yeni, setYeni] = useState<Form>(BOS);
  const [duzenlenen, setDuzenlenen] = useState<(Form & { id: number }) | null>(null);
  const [silinecek, setSilinecek] = useState<Saglayici | null>(null);

  useEffect(() => {
    if (ayarlar.data) setOranlar(Object.fromEntries(ayarlar.data.map((a) => [a.anahtar, a.deger])));
  }, [ayarlar.data]);

  const ekle = useMutation<unknown, ApiHatasi, Record<string, unknown>>({
    mutationFn: (govde) => iste("/provider", { method: "POST", body: JSON.stringify(govde) }),
    onSuccess: () => {
      void istemci.invalidateQueries({ queryKey: ["provider"] });
      setYeni(BOS);
      bildir("Sağlayıcı eklendi");
    },
    onError: (hata) => bildir(hata.message, "hata"),
  });

  const sil = useMutation<unknown, ApiHatasi, number>({
    mutationFn: (id) => iste(`/provider/${id}`, { method: "DELETE" }),
    onSuccess: () => void istemci.invalidateQueries({ queryKey: ["provider"] }),
    onError: (hata) => bildir(hata.message, "hata"),
  });

  function oranKaydet() {
        if (toplam !== 100) {
      bildir(`Oranlar 100 olmalı, şu an ${toplam}`, "hata");
      return;
    }
    yaz.mutate(oranlar, { onSuccess: () => bildir("Oranlar kaydedildi") });
  }

  function ekleGonder(olay: FormEvent) {
    olay.preventDefault();
    ekle.mutate({
      name: yeni.name,
      kind: yeni.kind,
      ulke: yeni.ulke,
      gateway: yeni.gateway || null,
      kullanici: yeni.kullanici || null,
      sifre: yeni.sifre || null,
      weight: Number(yeni.weight) || 1,
    });
  }

  function duzenleAc(s: Saglayici) {
    setDuzenlenen({
      id: s.id,
      name: s.name,
      kind: s.kind,
      ulke: s.ulke,
      gateway: s.gateway ?? "",
      kullanici: s.kullanici ?? "",
      sifre: "",
      weight: String(s.weight),
    });
  }

  const toplam = ["oran_residential", "oran_mobil", "oran_datacenter"].reduce(
    (t, k) => t + (Number(oranlar[k]) || 0),
    0,
  );
  return (
    <div className="space-y-4">
      <Kart baslik="Tür oranı" aciklama="Toplam 100 olmalı. Havuz bu orana göre tür çeker.">
        <div className="flex flex-wrap items-end gap-3">
          {["oran_residential", "oran_mobil", "oran_datacenter"].map((k) => (
            <label key={k} className="w-32 text-sm">
              <span className="text-solgun">{k.replace("oran_", "")}</span>
              <Girdi value={oranlar[k] ?? ""} onChange={(o) => setOranlar({ ...oranlar, [k]: o.target.value })} className="mt-1" />
            </label>
          ))}
                    <span className={toplam === 100 ? "text-sm text-solgun" : "text-sm text-hata"}>
            toplam: {toplam}
          </span>
<Dugme onClick={oranKaydet} disabled={yaz.isPending}>Kaydet</Dugme>
        </div>
      </Kart>

      <Modal acik={duzenlenen !== null} kapat={() => setDuzenlenen(null)} baslik="Sağlayıcıyı düzenle">
        {duzenlenen ? (
          <div>
            <p className="mb-3 text-xs text-solgun">Şifre boş bırakılırsa değişmez.</p>
          <div className="flex flex-wrap items-end gap-2">
            <label className="w-40 text-sm"><span className="text-solgun">Ad</span><Girdi value={duzenlenen.name} onChange={(o) => setDuzenlenen({ ...duzenlenen, name: o.target.value })} className="mt-1" /></label>
            <label className="w-36 text-sm">
              <span className="text-solgun">Tür</span>
              <select value={duzenlenen.kind} onChange={(o) => setDuzenlenen({ ...duzenlenen, kind: o.target.value })} className="mt-1 block h-10 w-full rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
                <option value="residential">residential</option>
                <option value="mobile">mobile</option>
                <option value="datacenter">datacenter</option>
              </select>
            </label>
            <label className="w-16 text-sm"><span className="text-solgun">Ülke</span><Girdi value={duzenlenen.ulke} onChange={(o) => setDuzenlenen({ ...duzenlenen, ulke: o.target.value })} className="mt-1" /></label>
            <label className="w-48 text-sm"><span className="text-solgun">Ağ geçidi</span><Girdi value={duzenlenen.gateway} onChange={(o) => setDuzenlenen({ ...duzenlenen, gateway: o.target.value })} className="mt-1" /></label>
            <label className="w-32 text-sm"><span className="text-solgun">Kullanıcı</span><Girdi value={duzenlenen.kullanici} onChange={(o) => setDuzenlenen({ ...duzenlenen, kullanici: o.target.value })} className="mt-1" /></label>
            <label className="w-32 text-sm"><span className="text-solgun">Şifre</span><Girdi type="password" value={duzenlenen.sifre} onChange={(o) => setDuzenlenen({ ...duzenlenen, sifre: o.target.value })} className="mt-1" /></label>
            <label className="w-20 text-sm"><span className="text-solgun">Ağırlık</span><Girdi value={duzenlenen.weight} onChange={(o) => setDuzenlenen({ ...duzenlenen, weight: o.target.value })} className="mt-1" /></label>
            <Dugme disabled={guncelle.isPending}
              onClick={() => {
                const govde: Record<string, unknown> = {
                  name: duzenlenen.name,
                  kind: duzenlenen.kind,
                  ulke: duzenlenen.ulke,
                  gateway: duzenlenen.gateway || null,
                  kullanici: duzenlenen.kullanici || null,
                  weight: Number(duzenlenen.weight) || 1,
                };
                if (duzenlenen.sifre) govde.sifre = duzenlenen.sifre;
                guncelle.mutate({ id: duzenlenen.id, govde }, { onSuccess: () => setDuzenlenen(null) });
              }}>
              Kaydet
            </Dugme>
            <Dugme gorunum="sade" onClick={() => setDuzenlenen(null)}>Vazgeç</Dugme>
          </div>
          </div>
        ) : null}
      </Modal>

      <Onay
        acik={silinecek !== null}
        baslik="Sağlayıcıyı sil"
        metin={`${silinecek?.name} havuzdan kaldırılacak. Hit kaydı varsa silinmez, kapatılır.`}
        kapat={() => setSilinecek(null)}
        bekle={sil.isPending}
        onayla={() => {
          if (silinecek) sil.mutate(silinecek.id, { onSuccess: () => setSilinecek(null) });
        }}
      />

      <Kart baslik="Sağlayıcı ekle">
        <form onSubmit={ekleGonder} className="flex flex-wrap items-end gap-2">
          <label className="w-40 text-sm"><span className="text-solgun">Ad</span><Girdi value={yeni.name} onChange={(o) => setYeni({ ...yeni, name: o.target.value })} className="mt-1" /></label>
          <label className="w-36 text-sm">
            <span className="text-solgun">Tür</span>
            <select value={yeni.kind} onChange={(o) => setYeni({ ...yeni, kind: o.target.value })} className="mt-1 block h-10 w-full rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-3 text-sm">
              <option value="residential">residential</option>
              <option value="mobile">mobile</option>
              <option value="datacenter">datacenter</option>
            </select>
          </label>
          <label className="w-16 text-sm"><span className="text-solgun">Ülke</span><Girdi value={yeni.ulke} onChange={(o) => setYeni({ ...yeni, ulke: o.target.value })} className="mt-1" /></label>
          <label className="w-48 text-sm"><span className="text-solgun">Ağ geçidi</span><Girdi value={yeni.gateway} onChange={(o) => setYeni({ ...yeni, gateway: o.target.value })} placeholder="host:port" className="mt-1" /></label>
          <label className="w-32 text-sm"><span className="text-solgun">Kullanıcı</span><Girdi value={yeni.kullanici} onChange={(o) => setYeni({ ...yeni, kullanici: o.target.value })} className="mt-1" /></label>
          <label className="w-32 text-sm"><span className="text-solgun">Şifre</span><Girdi type="password" value={yeni.sifre} onChange={(o) => setYeni({ ...yeni, sifre: o.target.value })} className="mt-1" /></label>
          <label className="w-20 text-sm"><span className="text-solgun">Ağırlık</span><Girdi value={yeni.weight} onChange={(o) => setYeni({ ...yeni, weight: o.target.value })} className="mt-1" /></label>
          <Dugme type="submit" disabled={ekle.isPending}>Ekle</Dugme>
        </form>
      </Kart>

      <Kart baslik="Havuz" aciklama={`${liste.data?.length ?? 0} kayıt`}>
        <Girdi value={arama} onChange={(o) => setArama(o.target.value)} placeholder="ad, ağ geçidi ya da ülke ara" className="mb-3 max-w-sm" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-solgun">
              <tr><th className="py-2">Ad</th><th>Tür</th><th>Ülke</th><th>Ağ geçidi</th><th>Ağırlık</th><th>CAPTCHA</th><th>Durum</th><th /></tr>
            </thead>
            <tbody className="divide-y divide-kenar">
              {liste.data?.map((s) => (
                <tr key={s.id}>
                  <td className="py-2 pr-2">{s.name}</td>
                  <td className="text-solgun">{s.kind}</td>
                  <td className="text-solgun">{s.ulke}</td>
                  <td className="text-solgun">{s.gateway ?? "—"}</td>
                  <td className="text-solgun">{s.weight}</td>
                  <td className="text-solgun">{Number(s.captcha_pct).toFixed(1)}%</td>
                  <td><Etiket ton={DURUM_TON[s.state] ?? "notr"}>{s.state}</Etiket></td>
                  <td className="text-right">
                    <div className="flex justify-end gap-1">
                      <Dugme gorunum="sade" className="h-8 px-2 text-xs" onClick={() => duzenleAc(s)}>Düzenle</Dugme>
                      <Dugme gorunum="ikincil" className="h-8 px-2 text-xs"
                        onClick={() => guncelle.mutate({ id: s.id, govde: { state: s.state === "active" ? "disabled" : "active" } })}>
                        {s.state === "active" ? "Kapat" : "Aç"}
                      </Dugme>
                      <Dugme gorunum="sade" className="h-8 px-2 text-xs" onClick={() => setSilinecek(s)}>Sil</Dugme>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Kart>
    </div>
  );
}