/**
 * Ayarlar: SERP anahtarları ve ölçüm eşikleri.
 *
 * Alanlar bildirimsel listeden üretilir. Tabloda olup listede olmayan
 * anahtarlar (oran_* gibi) burada görünmez; oranlar Sağlayıcılar ekranında
 * düzenlenir. Her kart kendi alanlarını aralıkla doğrular ve yalnızca onları
 * yazar, böylece tek hatalı alan diğerlerini kilitlemez.
 */
import { useState } from "react";
import { Kart } from "@/bilesen/ui/kart";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { ayarKullan, ayarYaz } from "@/lib/panel";
import { iste } from "@/lib/api";

type MantiksalAlan = { anahtar: string; etiket: string; aciklama: string };

type SayisalAlan = {
  anahtar: string;
  etiket: string;
  aciklama: string;
  min: number;
  max: number;
  varsayilan: number;
};

const OLCUM_ALANLARI: SayisalAlan[] = [
  {
    anahtar: "olcum_araligi_dk",
    etiket: "Ölçüm aralığı (dk)",
    aciklama: "0 = yalnızca cooldown sırası. Boşluk 15 dakikayı geçemez.",
    min: 0,
    max: 15,
    varsayilan: 0,
  },
  {
    anahtar: "esik_captcha",
    etiket: "CAPTCHA eşiği (%)",
    aciklama: "Aşılınca sağlayıcı 2 saat karantinaya alınır. En az 10 örnek beklenir.",
    min: 1,
    max: 100,
    varsayilan: 20,
  },
];

const KUYRUK_ALANLARI: SayisalAlan[] = [
  {
    anahtar: "kuyruk_esik",
    etiket: "Kuyruk eşiği (iş)",
    aciklama: "Bekleyen iş sayısı bu değeri aşarsa queue_lag uyarısı düşer.",
    min: 1,
    max: 100000,
    varsayilan: 200,
  },
];

const CEREZ_ALANLARI: MantiksalAlan[] = [
  {
    anahtar: "cerez_kullan",
    etiket: "Çerez kullan",
    aciklama: "Kapatılırsa hit'ler çerezsiz gider. Havuz boşken sistem zaten çerezsiz çalışır.",
  },
  {
    anahtar: "cerez_suresiz_kullan",
    etiket: "Süresi geçmiş çerezleri de kullan",
    aciklama: "Önce süresi dolmamış çerezler denenir; tükendiyse süresi geçmişler kullanılır.",
  },
  {
    anahtar: "esik_captcha",
    etiket: "Sağlayıcı CAPTCHA eşiği (%)",
    aciklama: "Sağlayıcı genel CAPTCHA oranı bu yüzdeyi geçerse 2 saat karantinaya girer.",
  },
  {
    anahtar: "esik_geo",
    etiket: "İl çifti CAPTCHA eşiği (%)",
    aciklama: "Bir sağlayıcı-il çifti bu yüzdeyi geçerse 60 dakika tükenmiş sayılır.",
  },
  {
    anahtar: "asgari_ornek",
    etiket: "En az örnek",
    aciklama: "Eşik, bu sayıda hit toplanmadan değerlendirilmez.",
  },];

const SERP = [
  { anahtar: "serp_decodo", ad: "Decodo", not: "sıralama ölçümü · birincil" },
  { anahtar: "serp_serper", ad: "Serper", not: "yedek" },
  { anahtar: "serp_searchapi", ad: "SearchApi", not: "yedek" },
];

const GIZLI = new Set(SERP.map((s) => s.anahtar));

export default function Ayarlar() {
  const ayarlar = ayarKullan();
  const yaz = ayarYaz();
  const bildir = useBildirim();
  const [anahtarlar, setAnahtarlar] = useState<Record<string, string>>({});
  const [degerler, setDegerler] = useState<Record<string, string>>({});
  const [sinama, setSinama] = useState<Record<string, string>>({});

  /** Kayıtlı değer; sırlar için maskeli gelir. */
  function kayitli(anahtar: string): string {
    return ayarlar.data?.find((a) => a.anahtar === anahtar)?.deger ?? "";
  }

  /** Alanın gösterilecek değeri: düzenlenen ya da kayıtlı. */
  function alanDegeri(alan: SayisalAlan): string {
    return degerler[alan.anahtar] ?? (kayitli(alan.anahtar) || String(alan.varsayilan));
  }

  /** Kart alanlarını aralıkla doğrular, hata varsa null döner. */
  function dogrula(alanlar: SayisalAlan[]): Record<string, string> | null {
    const govde: Record<string, string> = {};
    for (const alan of alanlar) {
      const ham = alanDegeri(alan).trim();
      const sayi = Number(ham);
      if (!Number.isInteger(sayi) || sayi < alan.min || sayi > alan.max) {
        bildir(`${alan.etiket}: ${alan.min}-${alan.max} arası tam sayı yaz`, "hata");
        return null;
      }
      govde[alan.anahtar] = String(sayi);
    }
    return govde;
  }

  function sayisalKaydet(alanlar: SayisalAlan[]) {
    const govde = dogrula(alanlar);
    if (!govde) return;
    yaz.mutate(govde, {
      onSuccess: () => {
        setDegerler({});
        bildir("Kaydedildi");
      },
    });
  }

  /** Çerez anahtarlarını onay kutularından yazar. */
  function mantiksalKaydet() {
    const govde: Record<string, string> = {};
    for (const alan of CEREZ_ALANLARI) {
      const acik = (degerler[alan.anahtar] ?? (kayitli(alan.anahtar) || "1")) === "1";
      govde[alan.anahtar] = acik ? "1" : "0";
    }
    yaz.mutate(govde, {
      onSuccess: () => {
        setDegerler({});
        bildir("Kaydedildi");
      },
    });
  }

  function anahtarKaydet() {
    const dolu = Object.fromEntries(
      Object.entries(anahtarlar).filter(([, d]) => d.trim() !== ""),
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

  /** Tek sayısal alanı çizer. */
  function sayisalGirdi(alan: SayisalAlan) {
    return (
      <label key={alan.anahtar} className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">{alan.etiket}</span>
        <Girdi
          inputMode="numeric"
          value={alanDegeri(alan)}
          onChange={(o) => setDegerler({ ...degerler, [alan.anahtar]: o.target.value })}
          className="max-w-[8rem]"
        />
        <span className="text-xs leading-relaxed text-solgun">{alan.aciklama}</span>
      </label>
    );
  }

  return (
    <div className="space-y-4">
      <Kart
        baslik="SERP anahtarları"
        aciklama="Sıralama bu anahtarlarla okunur. Kayıtlı değer maskelenir; yeni değer yazınca üzerine yazılır."
      >
        <div className="space-y-4">
          {SERP.map((s) => (
            <div key={s.anahtar} className="rounded-[var(--radius-kutu)] border border-kenar p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">{s.ad}</span>
                <span className="text-xs text-solgun">{s.not}</span>
                <span className={`ml-auto text-xs ${kayitli(s.anahtar) ? "text-basari" : "text-uyari"}`}>
                  {kayitli(s.anahtar) ? "tanımlı" : "yok"}
                </span>
                {s.anahtar === "serp_decodo" ? (
                  <button
                    type="button"
                    onClick={() => anahtarDene(s.anahtar)}
                    disabled={sinama[s.anahtar] === "sınanıyor..."}
                    className="rounded-full bg-yuzey-2 px-2.5 py-1 text-xs text-metin hover:bg-kenar disabled:opacity-50"
                  >
                    Dene
                  </button>
                ) : null}
                {kayitli(s.anahtar) ? (
                  <button
                    type="button"
                    onClick={() => anahtarTemizle(s.anahtar)}
                    disabled={yaz.isPending}
                    className="rounded-full bg-yuzey-2 px-2.5 py-1 text-xs text-metin hover:bg-kenar disabled:opacity-50"
                  >
                    Temizle
                  </button>
                ) : null}
              </div>
              <Girdi
                value={anahtarlar[s.anahtar] ?? ""}
                placeholder={kayitli(s.anahtar) || "tanımlı değil"}
                onChange={(o) => setAnahtarlar({ ...anahtarlar, [s.anahtar]: o.target.value })}
                className="mt-2"
              />
              {sinama[s.anahtar] ? (
                <p className="mt-1.5 text-xs text-solgun">{sinama[s.anahtar]}</p>
              ) : null}
            </div>
          ))}
        </div>
        <Dugme className="mt-4" disabled={yaz.isPending} onClick={anahtarKaydet}>
          Anahtarları kaydet
        </Dugme>
      </Kart>

      <Kart baslik="Ölçüm" aciklama="Değişiklik bir sonraki turda etkili olur.">
        <div className="grid gap-5 sm:grid-cols-2">
          {OLCUM_ALANLARI.map(sayisalGirdi)}
        </div>
        <Dugme
          className="mt-4"
          disabled={yaz.isPending}
          onClick={() => sayisalKaydet(OLCUM_ALANLARI)}
        >
          Ölçümü kaydet
        </Dugme>
      </Kart>

      <Kart baslik="Kuyruk" aciklama="Birikme eşiği; aşılınca uyarı üretilir.">
        <div className="grid gap-5 sm:grid-cols-2">
          {KUYRUK_ALANLARI.map(sayisalGirdi)}
        </div>
        <Dugme
          className="mt-4"
          disabled={yaz.isPending}
          onClick={() => sayisalKaydet(KUYRUK_ALANLARI)}
        >
          Kuyruğu kaydet
        </Dugme>
      </Kart>

      <Kart baslik="Çerez" aciklama="Çerez yalnızca aynı ülke proxy'siyle kullanılır; profil başına tek kullanım.">
        <div className="space-y-4">
          {CEREZ_ALANLARI.map((alan) => {
            const acik = (degerler[alan.anahtar] ?? (kayitli(alan.anahtar) || "1")) === "1";
            return (
              <label key={alan.anahtar} className="flex items-start gap-2.5">
                <input
                  type="checkbox"
                  checked={acik}
                  onChange={(o) =>
                    setDegerler({ ...degerler, [alan.anahtar]: o.target.checked ? "1" : "0" })
                  }
                  className="mt-0.5 size-4"
                />
                <span className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium">{alan.etiket}</span>
                  <span className="text-xs leading-relaxed text-solgun">{alan.aciklama}</span>
                </span>
              </label>
            );
          })}
        </div>
        <Dugme className="mt-4" disabled={yaz.isPending} onClick={mantiksalKaydet}>
          Çerezi kaydet
        </Dugme>
      </Kart>
    </div>
  );
}