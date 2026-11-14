/**
 * Çerezler: klasör yolu, tarama, aktarım, ilerleme.
 *
 * Dosyalar sunucuda durur; panel yalnızca yol verir. Aktarım arka planda
 * sürer, ilerleme çekilir. Havuz boşken sistem çerezsiz çalışmaya devam eder.
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { Etiket } from "@/bilesen/ui/etiket";
import { Onay } from "@/bilesen/ui/onay";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { ApiHatasi, iste } from "@/lib/api";

type Sayim = {
  dosya: number;
  gecersiz: number;
  mukerrer: number;
  aktif: number;
  suresi_gecmis: number;
  tukenen: number;
  illi: number;
};

type Ozet = {
  sayim: Sayim;
  durum: { calisiyor: boolean; toplam: number; islenen: number; mukerrer: number; hatali: number };
  hatalilar: { id: number; ad: string; hata: string | null; created_at: string }[];
};

type Tarama = { kok: string; toplam: number; dagilim: { json: number; txt: number; illi: number } };

export default function Cerezler() {
  const istemci = useQueryClient();
  const bildir = useBildirim();
  const [yol, setYol] = useState("");
  const [tarama, setTarama] = useState<Tarama | null>(null);
  const [silinecek, setSilinecek] = useState(false);

  const ozet = useQuery<Ozet, ApiHatasi>({
    queryKey: ["cerez"],
    queryFn: () => iste("/cerez"),
    refetchInterval: (sorgu) => (sorgu.state.data?.durum.calisiyor ? 2_000 : 10_000),
  });

  const ilerleme = useQuery<{ bekleyen: number; calisiyor: boolean }, ApiHatasi>({
    queryKey: ["cerez-ilerleme"],
    queryFn: () => iste("/cerez/ilerleme"),
    refetchInterval: 2_000,
  });

  const tara = useMutation<Tarama, ApiHatasi, string>({
    mutationFn: (ham) =>
      iste("/cerez/tara", { method: "POST", body: JSON.stringify({ yol: ham }) }),
    onSuccess: (sonuc) => setTarama(sonuc),
    onError: (hata) => bildir(hata.message, "hata"),
  });

  const gozat = useMutation<{ yol?: string; iptal?: boolean }, ApiHatasi>({
    mutationFn: () => iste("/cerez/gozat", { method: "POST", body: JSON.stringify({}) }),
    onSuccess: (sonuc) => {
      if (sonuc.yol) setYol(sonuc.yol);
    },
    onError: (hata) => bildir(hata.message, "hata"),
  });
  const aktar = useMutation<{ kuyruk: number }, ApiHatasi, string>({
    mutationFn: (ham) =>
      iste("/cerez/aktar", { method: "POST", body: JSON.stringify({ yol: ham }) }),
    onSuccess: (sonuc) => {
      bildir(`${sonuc.kuyruk} dosya kuyruğa alındı`);
      void istemci.invalidateQueries({ queryKey: ["cerez"] });
    },
    onError: (hata) => bildir(hata.message, "hata"),
  });

  const temizle = useMutation<unknown, ApiHatasi>({
    mutationFn: () => iste("/cerez", { method: "DELETE" }),
    onSuccess: () => {
      setSilinecek(false);
      setTarama(null);
      void istemci.invalidateQueries({ queryKey: ["cerez"] });
      bildir("Çerez defteri silindi");
    },
  });

  useEffect(() => {
    if (ozet.data && !ozet.data.durum.calisiyor) {
      void istemci.invalidateQueries({ queryKey: ["cerez-ilerleme"] });
    }
  }, [ozet.data, istemci]);

  const sayim = ozet.data?.sayim;
  const calisiyor = ozet.data?.durum.calisiyor ?? false;
  const bekleyen = ilerleme.data?.bekleyen ?? 0;

  return (
    <div className="space-y-4">
      <Kart
        baslik="Çerez yükle"
        aciklama="Sunucudaki klasör yolunu yaz. .json ve .txt dosyaları taranır; aynı içerik iki kez aktarılmaz."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Girdi
            value={yol}
            onChange={(o) => setYol(o.target.value)}
            placeholder="/srv/cerezler"
            className="min-w-[18rem] flex-1"
          />
          <Dugme
            gorunum="ikincil"
            disabled={gozat.isPending}
            onClick={() => gozat.mutate()}
          >
            {gozat.isPending ? "Seçiliyor" : "Gözat"}
          </Dugme>          <Dugme
            gorunum="ikincil"
            disabled={!yol.trim() || tara.isPending}
            onClick={() => tara.mutate(yol.trim())}
          >
            Tara
          </Dugme>
          <Dugme
            disabled={!yol.trim() || aktar.isPending}
            onClick={() => aktar.mutate(yol.trim())}
          >
            Yükle
          </Dugme>
        </div>

        {tarama ? (
          <div className="mt-3 rounded-[var(--radius-kutu)] border border-kenar p-3 text-xs">
            <p className="text-metin">{tarama.toplam} dosya bulundu</p>
            <p className="mt-1 text-solgun">
              json {tarama.dagilim.json} · txt {tarama.dagilim.txt} · il eşleşen {tarama.dagilim.illi}
            </p>
            <p className="mt-1 break-all text-solgun">{tarama.kok}</p>
          </div>
        ) : null}
      </Kart>

      <Kart baslik="Havuz" aciklama="Önce süresi dolmamış çerezler kullanılır; ayar açıksa süresi geçmişler de devreye girer.">
        <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs text-solgun">aktif</p>
            <p className="text-lg font-medium text-basari">{sayim?.aktif ?? 0}</p>
          </div>
          <div>
            <p className="text-xs text-solgun">süresi geçmiş</p>
            <p className="text-lg font-medium text-uyari">{sayim?.suresi_gecmis ?? 0}</p>
          </div>
          <div>
            <p className="text-xs text-solgun">tükenen</p>
            <p className="text-lg font-medium text-solgun">{sayim?.tukenen ?? 0}</p>
          </div>
          <div>
            <p className="text-xs text-solgun">il eşleşen</p>
            <p className="text-lg font-medium text-solgun">{sayim?.illi ?? 0}</p>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-solgun">
          <Etiket ton={calisiyor ? "vurgu" : "notr"}>{calisiyor ? "aktarım sürüyor" : "beklemede"}</Etiket>
          <span>kuyrukta {bekleyen}</span>
          <span>· işlenen {ozet.data?.durum.islenen ?? 0}</span>
          <span>· mükerrer {sayim?.mukerrer ?? 0}</span>
          <span>· hatalı {sayim?.gecersiz ?? 0}</span>
          <button
            type="button"
            onClick={() => setSilinecek(true)}
            className="ml-auto rounded-full bg-yuzey-2 px-3 py-1 text-metin hover:bg-kenar"
          >
            temizle
          </button>
        </div>
      </Kart>

      <Kart baslik="Hatalı dosyalar" aciklama="Biçim tanınmayan, boş ya da bozuk dosyalar.">
        {ozet.data?.hatalilar.length ? (
          <ul className="divide-y divide-kenar text-xs">
            {ozet.data.hatalilar.map((h) => (
              <li key={h.id} className="flex items-start gap-2 py-1.5">
                <span className="flex-1 truncate" title={h.ad}>{h.ad}</span>
                <span className="text-solgun">{h.hata ?? "sebep yok"}</span>
                <span className="text-solgun">{h.created_at.slice(11, 16)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-3 text-sm text-solgun">Hatalı dosya yok.</p>
        )}
      </Kart>

      <Onay
        acik={silinecek}
        baslik="Çerez defterini sil"
        dugmeEtiketi="Sil"
        metin="Tüm dosya ve profil kayıtları silinir, diskteki dosyalar durur. Aktarım sürüyorsa durur."
        kapat={() => setSilinecek(false)}
        bekle={temizle.isPending}
        onayla={() => temizle.mutate()}
      />
    </div>
  );
}