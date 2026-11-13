/** Uyarılar: tür, durum ve tarih filtreli, sayfalı liste. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { Etiket } from "@/bilesen/ui/etiket";
import { FiltreCubugu, type Aralik } from "@/bilesen/filtre";
import { Sayfalayici } from "@/bilesen/sayfalayici";
import { Modal } from "@/bilesen/ui/pencere";
import { Onay } from "@/bilesen/ui/onay";
import { uyariKapat, uyariTumunuKapat } from "@/lib/panel";
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

type Cevap = {
  satirlar: Uyari[];
  ozet: { acik: number; kapali: number };
  toplam: number;
  sayfa: number;
  adet: number;
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
const ADETLER = [25, 50, 100, 200];

/**
 * Tur rehberi.
 *
 * Her tur icin ne oldugu, neden ciktigi ve ne yapilmasi gerektigi yazilir;
 * ekrani goren kisi sozlugu bilmeden uyariyi yorumlayabilir.
 */
const TUR_BILGI: Record<string, { ad: string; aciklama: string; sebep: string; onlem: string }> = {
  captcha: {
    ad: "Captcha / engel",
    aciklama: "Google bot kontrolu gosterdi, hit sayilmadi.",
    sebep: "Ayni IP'den sIk istek, bayat cookie, datacenter IP veya cok hizli ritim.",
    onlem: "Saglayiciyi karantinaya al, mobile oranini dusur, dwell suresini artir.",
  },
  provider_down: {
    ad: "Saglayici dustu",
    aciklama: "Ust uste basarisiz denemelerden sonra saglayici kullanilamaz sayildi.",
    sebep: "Gateway kapali, kimlik hatasi, kota tukenmesi.",
    onlem: "Saglayicilar ekranindan kimligi dene, agirligi dusur veya kapali tut.",
  },
  queue_lag: {
    ad: "Kuyruk gecikmesi",
    aciklama: "Bekleyen is sayisi esigi asti; isler sirada bekliyor.",
    sebep: "Dugum az, eszamanli sinir dusuk veya motor yavas.",
    onlem: "Dugum ekle, eszamanli siniri yukselt, olcum araligini artir.",
  },
  quota: {
    ad: "Kota / hiz siniri",
    aciklama: "SERP API 429 dondu; arama kotasi veya saniyelik sinir doldu.",
    sebep: "Aylik kota tukendi ya da cok hizli istek atildi.",
    onlem: "Olcum araligini artir, anahtari degistir, gereksiz kelimeleri durdur.",
  },
  fallback_high: {
    ad: "Yedek hat yuksek",
    aciklama: "Hit'lerin buyuk kismi yabanci IP ile atildi; sehir hedefleme tutmadi.",
    sebep: "TR havuzu tukendi veya saglayicilarda sehir hedefleme yok.",
    onlem: "TR saglayici ekle, oran ayarlarini ve karantinadaki saglayicilari gozden gecir.",
  },
  hedef_yok: {
    ad: "Hedef ilk 100'de yok",
    aciklama: "Alan adi SERP'in ilk 100 sirasinda gorunmedi; hit atilmadan burst kapandi.",
    sebep: "Kelime o ilde siralamiyor, il yanlis secilmis veya site cezali.",
    onlem: "Kelime/il ciftini degistir; ust uste tekrarda kelime otomatik durur.",
  },
  failover: {
    ad: "Saglayici degisimi",
    aciklama: "Bir hit sirasinda saglayici degistirildi; hit yine atildi.",
    sebep: "Secilen saglayici o an basarisiz oldu.",
    onlem: "Tekil kayitlar normaldir; siklasirsa saglayiciya bak.",
  },
  burst_hata: {
    ad: "Burst tamamlanmadi",
    aciklama: "Burst'un basari orani esigin altinda kaldi.",
    sebep: "Captcha, timeout veya hata birikimi.",
    onlem: "Loglara bak, saglayici havuzunu ve ritmi gozden gecir.",
  },
};

export default function Uyarilar() {
  const [aralik, setAralik] = useState<Aralik>("hafta");
  const [tur, setTur] = useState("");
  const [durum, setDurum] = useState("acik");
  const [arama, setArama] = useState("");
  const [site, setSite] = useState("");
  const [kelime, setKelime] = useState("");
  const [sayfa, setSayfa] = useState(1);
  const [adet, setAdet] = useState(50);
  const [tumunuOnay, setTumunuOnay] = useState(false);
  const [rehber, setRehber] = useState(false);
  const kapat = uyariKapat();
  const tumunuKapat = uyariTumunuKapat();

  const liste = useQuery<Cevap, ApiHatasi>({
    queryKey: ["uyari", aralik, tur, durum, arama, site, kelime, sayfa, adet],
    queryFn: () =>
      iste(
        `/uyari?aralik=${aralik}${tur ? `&tur=${tur}` : ""}${durum ? `&durum=${durum}` : ""}${arama ? `&q=${encodeURIComponent(arama)}` : ""}${site ? `&site=${encodeURIComponent(site)}` : ""}${kelime ? `&kelime=${encodeURIComponent(kelime)}` : ""}&sayfa=${sayfa}&adet=${adet}`,
      ),
  });

  const satirlar = liste.data?.satirlar ?? [];
  const gunler = satirlar.reduce<Record<string, Uyari[]>>((acc, u) => {
    const gun = u.created_at.slice(0, 10);
    (acc[gun] ??= []).push(u);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <FiltreCubugu aralik={aralik} aralikDegistir={(y) => { setAralik(y); setSayfa(1); }}>
        <Girdi value={arama} onChange={(o) => { setArama(o.target.value); setSayfa(1); }} placeholder="mesajda ara" className="h-8 max-w-[12rem]" />
        <Girdi value={site} onChange={(o) => { setSite(o.target.value); setSayfa(1); }} placeholder="site" className="h-8 max-w-[10rem]" />
        <Girdi value={kelime} onChange={(o) => { setKelime(o.target.value); setSayfa(1); }} placeholder="kelime" className="h-8 max-w-[10rem]" />
        <select value={tur} onChange={(o) => { setTur(o.target.value); setSayfa(1); }}
          className="h-8 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-2 text-xs">
          <option value="">tüm türler</option>
          {TURLER.map((t) => <option key={t} value={t}>{TUR_BILGI[t]?.ad ?? t}</option>)}
        </select>
        <select value={durum} onChange={(o) => { setDurum(o.target.value); setSayfa(1); }}
          className="h-8 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-2 text-xs">
          <option value="acik">açık</option>
          <option value="kapali">kapatılmış</option>
          <option value="">hepsi</option>
        </select>
        <button type="button" onClick={() => setRehber(true)}
          className="rounded-full border border-kenar px-3 py-1 text-xs text-metin hover:bg-yuzey-2">
          tur rehberi
        </button>
        <button type="button" onClick={() => setTumunuOnay(true)}
          disabled={tumunuKapat.isPending}
          className="ml-auto rounded-full bg-yuzey-2 px-3 py-1 text-xs text-metin hover:bg-kenar">
          tümünü kapat
        </button>
        <select value={adet} onChange={(o) => { setAdet(Number(o.target.value)); setSayfa(1); }}
          className="h-8 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey px-2 text-xs">
          {ADETLER.map((a) => <option key={a} value={a}>{a}/sayfa</option>)}
        </select>
        <span className="text-xs text-solgun">
          açık {liste.data?.ozet?.acik ?? 0} · kapatılmış {liste.data?.ozet?.kapali ?? 0}
        </span>
      </FiltreCubugu>

      <Onay
        acik={tumunuOnay}
        baslik="Uyarıları kapat"
        dugmeEtiketi="Kapat"
        metin="Filtreye uyan tüm açık uyarılar kapatılacak. Kapatılan uyarı geri açılmaz."
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
            {Object.entries(gunler).map(([gun, gunSatirlari]) => (
              <div key={gun}>
                <p className="mb-2 text-xs font-medium text-solgun">
                  {new Date(gun).toLocaleDateString("tr-TR", { day: "numeric", month: "long", weekday: "short" })} · {gunSatirlari.length}
                </p>
                <ul className="divide-y divide-kenar text-sm">
                  {gunSatirlari.map((u) => (
                    <li key={u.id} className="flex items-start gap-3 py-2">
                      <span className="flex w-40 shrink-0 flex-col items-start gap-0.5">
                        <Etiket ton={TON[u.kind] ?? "notr"}>{TUR_BILGI[u.kind]?.ad ?? u.kind}</Etiket>
                        <code className="text-[10px] text-solgun">{u.kind}</code>
                      </span>
                      <div className="flex-1">
                        <p>{u.message}</p>
                        <p className="mt-0.5 text-xs text-solgun">
                          {u.domain ?? "site yok"} · {u.kelime ?? "kelime yok"}
                        </p>
                      </div>
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
        <div className="mt-3 border-t border-kenar pt-3">
          <Sayfalayici sayfa={sayfa} toplam={liste.data?.toplam ?? 0} adet={adet} degistir={setSayfa} />
        </div>
      </Kart>

      <Modal acik={rehber} kapat={() => setRehber(false)} baslik="Uyari turleri ne anlama gelir">
        <p className="mb-3 text-xs text-solgun">
          Bu ekran hangi uyarinin ne oldugunu, neden ciktigini ve ne yapilmasi gerektigini anlatir.
        </p>
        <ul className="max-h-[60vh] space-y-3 overflow-y-auto pr-1 text-sm">
          {TURLER.map((t) => (
            <li key={t} className="rounded-[var(--radius-kutu)] border border-kenar p-3">
              <div className="flex items-center gap-2">
                <Etiket ton={TON[t] ?? "notr"}>{TUR_BILGI[t]?.ad ?? t}</Etiket>
                <code className="text-[10px] text-solgun">{t}</code>
              </div>
              <p className="mt-2">{TUR_BILGI[t]?.aciklama}</p>
              <p className="mt-1 text-xs text-solgun">Sebep: {TUR_BILGI[t]?.sebep}</p>
              <p className="mt-1 text-xs text-solgun">Onlem: {TUR_BILGI[t]?.onlem}</p>
            </li>
          ))}
        </ul>
      </Modal>
    </div>
  );
}