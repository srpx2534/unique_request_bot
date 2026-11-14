/**
 * Çerezler: tarayıcıdan klasör yükleme, yükleme ve aktarım ilerlemesi.
 *
 * Dosyalar kullanıcının bilgisayarından partiler hâlinde gönderilir; sunucuda
 * geçici klasöre yazılır, aktarım bitince silinir. Havuz boşken sistem
 * çerezsiz çalışmaya devam eder.
 */
import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Etiket } from "@/bilesen/ui/etiket";
import { Onay } from "@/bilesen/ui/onay";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { ApiHatasi, dosyaYukle, iste } from "@/lib/api";

const PARTI = 200;

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

type Secim = { toplam: number; json: number; txt: number; boyut: number };
type Islem = {
  durum: string;
  dosya_sayisi: number;
  bekleyen: number;
  aktarildi: number;
  mukerrer: number;
  gecersiz: number;
};

function boyutYaz(bayt: number): string {
  if (bayt < 1024) return `${bayt} B`;
  if (bayt < 1024 * 1024) return `${(bayt / 1024).toFixed(0)} KB`;
  return `${(bayt / 1024 / 1024).toFixed(1)} MB`;
}

export default function Cerezler() {
  const istemci = useQueryClient();
  const bildir = useBildirim();
  const secici = useRef<HTMLInputElement>(null);
  const iptal = useRef(false);

  const [dosyalar, setDosyalar] = useState<File[]>([]);
  const [secim, setSecim] = useState<Secim | null>(null);
  const [asama, setAsama] = useState<"bos" | "hazir" | "yukleniyor" | "aktarim" | "bitti">("bos");
  const [oran, setOran] = useState(0);
  const [gonderilen, setGonderilen] = useState(0);
  const [islemId, setIslemId] = useState<number | null>(null);
  const [islem, setIslem] = useState<Islem | null>(null);
  const [silinecek, setSilinecek] = useState(false);

  const ozet = useQuery<Ozet, ApiHatasi>({
    queryKey: ["cerez"],
    queryFn: () => iste("/cerez"),
    refetchInterval: (sorgu) => (sorgu.state.data?.durum.calisiyor ? 2_000 : 10_000),
  });

  const temizle = useMutation<unknown, ApiHatasi>({
    mutationFn: () => iste("/cerez", { method: "DELETE" }),
    onSuccess: () => {
      setSilinecek(false);
      void istemci.invalidateQueries({ queryKey: ["cerez"] });
      bildir("Çerez defteri silindi");
    },
  });

  useEffect(() => {
    if (asama !== "aktarim" || !islemId) return;
    let acik = true;
    const cek = async (): Promise<void> => {
      try {
        const veri = await iste<Islem>(`/cerez/yukleme/${islemId}`);
        if (!acik) return;
        setIslem(veri);
        if (veri.durum === "bitti") {
          setAsama("bitti");
          void istemci.invalidateQueries({ queryKey: ["cerez"] });
        }
      } catch {
        // işlem kaydı düşene kadar sessiz kalınır.
      }
    };
    void cek();
    const zaman = window.setInterval(() => void cek(), 1_500);
    return () => {
      acik = false;
      window.clearInterval(zaman);
    };
  }, [asama, islemId, istemci]);

  function secildi(olay: ChangeEvent<HTMLInputElement>): void {
    const liste = Array.from(olay.target.files ?? []).filter((dosya) =>
      /\.(json|txt)$/i.test(dosya.name),
    );
    setDosyalar(liste);
    setIslem(null);
    ilerlemeSifirla();
    const ilk = liste[0]?.webkitRelativePath ?? "";
    setKlasorAdi(ilk.includes("/") ? ilk.slice(0, ilk.indexOf("/")) : liste[0]?.name ?? "");
    if (!liste.length) {
      setSecim(null);
      setAsama("bos");
      return;
    }
    setSecim({
      toplam: liste.length,
      json: liste.filter((dosya) => /\.json$/i.test(dosya.name)).length,
      txt: liste.filter((dosya) => /\.txt$/i.test(dosya.name)).length,
      boyut: liste.reduce((toplam, dosya) => toplam + dosya.size, 0),
    });
    setAsama("hazir");
  }

  function ilerlemeSifirla(): void {
    setOran(0);
    setGonderilen(0);
    setIslemId(null);
  }

  async function yukle(): Promise<void> {
    if (!dosyalar.length) return;
    iptal.current = false;
    setAsama("yukleniyor");
    ilerlemeSifirla();
    try {
      const acilis = await iste<{ id: number }>("/cerez/yukleme", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setIslemId(acilis.id);
      for (let i = 0; i < dosyalar.length; i += PARTI) {
        if (iptal.current) {
          await iste(`/cerez/yukleme/${acilis.id}`, { method: "DELETE" });
          setAsama("hazir");
          bildir("Yükleme iptal edildi");
          return;
        }
        const dilim = dosyalar.slice(i, i + PARTI);
        const govde = new FormData();
        govde.append("yollar", JSON.stringify(dilim.map((dosya) => dosya.webkitRelativePath || dosya.name)));
        for (const dosya of dilim) govde.append("dosyalar", dosya, dosya.name);
        await dosyaYukle(`/cerez/yukleme/${acilis.id}/parti`, govde, (bolum) =>
          setOran((i + bolum * dilim.length) / dosyalar.length),
        );
        setGonderilen(i + dilim.length);
      }
      setOran(1);
      await iste(`/cerez/yukleme/${acilis.id}/baslat`, { method: "POST", body: JSON.stringify({}) });
      setAsama("aktarim");
    } catch (hata) {
      bildir((hata as ApiHatasi).message, "hata");
      setAsama("hazir");
    }
  }

  const sayim = ozet.data?.sayim;
  const calisiyor = ozet.data?.durum.calisiyor ?? false;
  const mesgul = asama === "yukleniyor" || asama === "aktarim";

  return (
    <div className="space-y-4">
      <Kart
        baslik="Çerez yükle"
        aciklama="Kendi bilgisayarından klasör seç. Dosyalar sunucuya gönderilir; yalnızca .json ve .txt alınır, aynı içerik iki kez aktarılmaz."
      >
        <input
          ref={secici}
          type="file"
          multiple
          className="hidden"
          onChange={secildi}
          {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Dugme
            gorunum="ikincil"
            disabled={mesgul}
            onClick={() => {
              if (secici.current) secici.current.value = "";
              secici.current?.click();
            }}
          >
            Klasör seç
          </Dugme>
          <Dugme disabled={!dosyalar.length || mesgul} onClick={() => void yukle()}>
            Yükle
          </Dugme>
          {mesgul ? (
            <Dugme
              gorunum="ikincil"
              onClick={() => {
                iptal.current = true;
              }}
            >
              İptal
            </Dugme>
          ) : null}
        </div>

        {secim ? (
          <div className="mt-3 rounded-[var(--radius-kutu)] border border-kenar p-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <Etiket ton="basari">seçildi</Etiket>
              <span className="break-all font-medium text-metin">{klasorAdi}</span>
              <button
                type="button"
                disabled={mesgul}
                onClick={temizleSecim}
                className="ml-auto rounded-full bg-yuzey-2 px-3 py-1 text-metin hover:bg-kenar"
              >
                kaldır
              </button>
            </div>
            <p className="mt-2 text-metin">
              {secim.toplam} dosya · {boyutYaz(secim.boyut)}
            </p>
            <p className="mt-1 text-solgun">
              json {secim.json} · txt {secim.txt}
            </p>
            <p className="mt-1 text-solgun">
              Klasör adı tarayıcıdan gelir; tam yol tarayıcıya kapalıdır.
            </p>
          </div>
        ) : (
          <p className="mt-3 text-xs text-solgun">Henüz klasör seçilmedi.</p>
        )}

        {asama === "yukleniyor" ? (
          <div className="mt-3 space-y-2">
            <div className="h-2 overflow-hidden rounded-full bg-yuzey-2">
              <div
                className="h-full bg-vurgu"
                style={{ width: `${Math.round(oran * 100)}%` }}
              />
            </div>
            <p className="text-xs text-solgun">
              {gonderilen} / {dosyalar.length} dosya gönderildi · %{Math.round(oran * 100)}
            </p>
          </div>
        ) : null}

        {asama === "aktarim" || asama === "bitti" ? (
          <div className="mt-3 space-y-2 text-xs">
            <div className="h-2 overflow-hidden rounded-full bg-yuzey-2">
              <div
                className="h-full bg-basari"
                style={{
                  width: `${
                    islem && islem.dosya_sayisi
                      ? Math.round(
                          ((islem.aktarildi + islem.mukerrer + islem.gecersiz) / islem.dosya_sayisi) * 100,
                        )
                      : 0
                  }%`,
                }}
              />
            </div>
            <p className="text-solgun">
              aktarılan {islem?.aktarildi ?? 0} · mükerrer {islem?.mukerrer ?? 0} · hatalı{" "}
              {islem?.gecersiz ?? 0} · bekleyen {islem?.bekleyen ?? 0}
            </p>
            {asama === "bitti" ? (
              <p className="text-basari">Aktarım bitti, geçici klasör silindi.</p>
            ) : null}
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
            {ozet.data.hatalilar.map((hata) => (
              <li key={hata.id} className="flex items-start gap-2 py-1.5">
                <span className="flex-1 truncate" title={hata.ad}>{hata.ad}</span>
                <span className="text-solgun">{hata.hata ?? "sebep yok"}</span>
                <span className="text-solgun">{hata.created_at.slice(11, 16)}</span>
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
        metin="Tüm dosya ve profil kayıtları silinir. Aktarım sürüyorsa durur."
        kapat={() => setSilinecek(false)}
        bekle={temizle.isPending}
        onayla={() => temizle.mutate()}
      />
    </div>
  );
}