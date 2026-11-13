/** Ayarlar: SERP anahtarları ve ölçüm parametreleri. */
import { useEffect, useState } from "react";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { ayarKullan, ayarYaz } from "@/lib/panel";
import { iste } from "@/lib/api";

const ETIKETLER: Record<string, string> = {
  mobil_pencere_sn: "Mobil pencere (sn)",
  olcum_araligi_dk: "Ölçüm aralığı (dk, 0 = kapalı)",
  gunluk_tavan: "Günlük tavan",
  esik_captcha: "CAPTCHA eşiği (%)",
};

const SERP = [
  { anahtar: "serp_decodo", ad: "Decodo", not: "sıralama ölçümü" },
  { anahtar: "serp_serper", ad: "Serper", not: "yedek" },
  { anahtar: "serp_searchapi", ad: "SearchApi", not: "yedek" },
];

const GIZLI = new Set([
  ...SERP.map((s) => s.anahtar),
  "oran_residential",
  "oran_mobil",
  "oran_datacenter",
]);

export default function Ayarlar() {
  const ayarlar = ayarKullan();
  const yaz = ayarYaz();
  const bildir = useBildirim();
  const [degerler, setDegerler] = useState<Record<string, string>>({});
  const [anahtarlar, setAnahtarlar] = useState<Record<string, string>>({});
  const [sinama, setSinama] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!ayarlar.data) return;
    setDegerler(
      Object.fromEntries(
        ayarlar.data.filter((a) => !GIZLI.has(a.anahtar)).map((a) => [a.anahtar, a.deger]),
      ),
    );
  }, [ayarlar.data]);

  /** Kayıtlı değer; sırlar için maskeli gelir. */
  function kayitli(anahtar: string): string {
    return ayarlar.data?.find((a) => a.anahtar === anahtar)?.deger ?? "";
  }

  function anahtarKaydet() {
    const dolu = Object.fromEntries(
      Object.entries(anahtarlar).filter(([, deger]) => deger.trim() !== ""),
    );
    if (Object.keys(dolu).length === 0) {
      bildir("Doldurulmuş anahtar yok", "hata");
      return;
    }
    yaz.mutate(dolu, {
      onSuccess: () => {
        setAnahtarlar({});
        bildir("Anahtarlar kaydedildi");
      },
    });
  }

  /** Anahtarı boşaltır; maskeli değer gönderilmediği için gerçekten silinir. */
  function anahtarTemizle(anahtar: string) {
    yaz.mutate(
      { [anahtar]: "" },
      {
        onSuccess: () => {
          setAnahtarlar((eski) => {
            const yeni = { ...eski };
            delete yeni[anahtar];
            return yeni;
          });
          bildir("Anahtar temizlendi");
        },
      },
    );
  }

  /** Anahtarı tek sorguyla dener ve sonucu satırda gösterir. */
  async function anahtarDene(anahtar: string) {
    setSinama((eski) => ({ ...eski, [anahtar]: "sınanıyor..." }));
    try {
      const sonuc = await iste<{ ok: boolean; organik?: number; kod?: number; hata?: string; sure_ms: number }>(
        "/ayar/serp-dene",
        { method: "POST", body: JSON.stringify({ anahtar }) },
      );
      setSinama((eski) => ({
        ...eski,
        [anahtar]: sonuc.ok
          ? `çalıştı · ${sonuc.organik} sonuç · ${sonuc.sure_ms} ms`
          : `başarısız · ${sonuc.kod ?? sonuc.hata ?? "hata"}`,
      }));
    } catch {
      setSinama((eski) => ({ ...eski, [anahtar]: "istek düştü" }));
    }
  }

  return (
    <div className="space-y-4">
      <Kart
        baslik="SERP anahtarları"
        aciklama="Sıralama bu anahtarlarla okunur. Kayıtlı değer maskelenir; yeni değer yazınca üzerine yazılır."
      >
        <div className="space-y-3">
          {SERP.map((s) => (
            <label key={s.anahtar} className="block text-sm">
              <span className="text-solgun">
                {s.ad} · {s.not}
              </span>
              <div className="mt-1 flex items-center gap-2">
                <Girdi
                  value={anahtarlar[s.anahtar] ?? ""}
                  placeholder={kayitli(s.anahtar) || "tanımlı değil"}
                  onChange={(o) => setAnahtarlar({ ...anahtarlar, [s.anahtar]: o.target.value })}
                  className="max-w-sm"
                />
                <span className={`text-xs ${kayitli(s.anahtar) ? "text-basari" : "text-uyari"}`}>
                  {kayitli(s.anahtar) ? "tanımlı" : "yok"}
                </span>
                {s.anahtar === "serp_decodo" ? (
                  <button
                    type="button"
                    onClick={() => anahtarDene(s.anahtar)}
                    disabled={sinama[s.anahtar] === "sınanıyor..."}
                    className="rounded-full bg-yuzey-2 px-2 py-1 text-xs text-metin hover:bg-kenar"
                  >
                    Dene
                  </button>
                ) : null}
                {kayitli(s.anahtar) ? (
                  <button
                    type="button"
                    onClick={() => anahtarTemizle(s.anahtar)}
                    disabled={yaz.isPending}
                    className="rounded-full bg-yuzey-2 px-2 py-1 text-xs text-metin hover:bg-kenar"
                  >
                    Temizle
                  </button>
                ) : null}
              </div>
              {sinama[s.anahtar] ? (
                <p className="mt-1 text-xs text-solgun">{sinama[s.anahtar]}</p>
              ) : null}
            </label>
          ))}
        </div>
        <Dugme className="mt-4" disabled={yaz.isPending} onClick={anahtarKaydet}>
          Anahtarları kaydet
        </Dugme>
      </Kart>

      <Kart baslik="Ölçüm" aciklama="Değişiklikler bir sonraki turda etkili olur.">
        <div className="space-y-3">
          {Object.keys(degerler).map((k) => (
            <label key={k} className="block text-sm">
              <span className="text-solgun">{ETIKETLER[k] ?? k}</span>
              <Girdi
                value={degerler[k]}
                onChange={(o) => setDegerler({ ...degerler, [k]: o.target.value })}
                className="mt-1 max-w-xs"
              />
            </label>
          ))}
        </div>
        <Dugme
          className="mt-4"
          disabled={yaz.isPending}
          onClick={() => yaz.mutate(degerler, { onSuccess: () => bildir("Ayarlar kaydedildi") })}
        >
          Kaydet
        </Dugme>
      </Kart>
    </div>
  );
}