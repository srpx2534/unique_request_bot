/**
 * Üst çubuk.
 *
 * Tema seçimi, bildirim çanı ve kullanıcı menüsü. Açılır paneller
 * <details> ile kuruldu; ek durum tutmaz, klavyeyle de açılır.
 */
import { useNavigate } from "react-router-dom";
import { Bell, LogOut, Menu, Monitor, Moon, Sun } from "lucide-react";
import { cikisKullan, oturumKullan } from "@/lib/oturum";
import { temaOku, temaYaz, type Tema } from "@/lib/tema";
import { useBildirim } from "@/bilesen/ui/bildirim";
import { cn } from "@/lib/sinif";

const temalar: { deger: Tema; ad: string; Ikon: typeof Sun }[] = [
  { deger: "koyu", ad: "Koyu", Ikon: Moon },
  { deger: "acik", ad: "Açık", Ikon: Sun },
  { deger: "sistem", ad: "Sistem", Ikon: Monitor },
];

const ornekUyarilar = [
  { ton: "uyari", metin: "TR havuzunda aday kalmadı", zaman: "3 dk" },
  { ton: "tehlike", metin: "Sağlayıcı devre kesici açık: serper", zaman: "18 dk" },
  { ton: "notr", metin: "Kota %80 doldu", zaman: "1 sa" },
];

export default function UstCubuk({
  baslik,
  cekmeceAc,
}: {
  baslik: string;
  cekmeceAc: () => void;
}) {
  const oturum = oturumKullan();
  const cikis = cikisKullan();
  const bildir = useBildirim();
  const git = useNavigate();
  const tema = temaOku();

  function cikisYap() {
    cikis.mutate(undefined, {
      onSettled: () => {
        bildir("Oturum kapatıldı");
        git("/giris", { replace: true });
      },
    });
  }

  return (
    <header className="flex h-14 items-center gap-3 border-b border-kenar bg-yuzey px-4">
      <button
        type="button"
        onClick={cekmeceAc}
        aria-label="Menüyü aç"
        className="rounded p-1.5 text-solgun hover:bg-yuzey-2 lg:hidden"
      >
        <Menu className="size-5" />
      </button>

      <h1 className="truncate text-sm font-semibold">{baslik}</h1>

      <div className="ml-auto flex items-center gap-1">
        <div className="hidden items-center gap-1 rounded-[var(--radius-kutu)] border border-kenar p-0.5 sm:flex">
          {temalar.map(({ deger, ad, Ikon }) => (
            <button
              key={deger}
              type="button"
              onClick={() => {
                temaYaz(deger);
                git(0 as never, { replace: true });
              }}
              title={ad}
              aria-label={ad}
              className={cn(
                "rounded-[calc(var(--radius-kutu)-2px)] p-1.5",
                tema === deger ? "bg-vurgu/15 text-vurgu" : "text-solgun hover:bg-yuzey-2",
              )}
            >
              <Ikon className="size-4" />
            </button>
          ))}
        </div>

        <details className="relative">
          <summary className="flex cursor-pointer list-none items-center rounded p-2 text-solgun hover:bg-yuzey-2 [&::-webkit-details-marker]:hidden">
            <span className="relative">
              <Bell className="size-4" />
              <span className="absolute -right-0.5 -top-0.5 size-1.5 rounded-full bg-uyari" />
            </span>
          </summary>
          <div className="absolute right-0 top-11 z-40 w-72 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey p-2 shadow-xl">
            <p className="px-2 py-1 text-xs font-medium text-solgun">Son uyarılar</p>
            <ul className="divide-y divide-kenar">
              {ornekUyarilar.map((u) => (
                <li key={u.metin} className="flex items-start gap-2 px-2 py-2 text-xs">
                  <span
                    className={cn(
                      "mt-1 size-1.5 shrink-0 rounded-full",
                      u.ton === "tehlike" ? "bg-tehlike" : u.ton === "uyari" ? "bg-uyari" : "bg-solgun",
                    )}
                  />
                  <span className="flex-1">{u.metin}</span>
                  <span className="text-solgun">{u.zaman}</span>
                </li>
              ))}
            </ul>
          </div>
        </details>

        <details className="relative">
          <summary className="flex cursor-pointer list-none items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-yuzey-2 [&::-webkit-details-marker]:hidden">
            <span className="grid size-7 place-items-center rounded-full bg-vurgu/15 text-xs font-semibold uppercase text-vurgu">
              {oturum.data?.eposta.slice(0, 1) ?? "?"}
            </span>
          </summary>
          <div className="absolute right-0 top-11 z-40 w-56 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey p-2 shadow-xl">
            <p className="truncate px-2 py-1 text-xs text-solgun">{oturum.data?.eposta}</p>
            <button
              type="button"
              onClick={cikisYap}
              className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-yuzey-2"
            >
              <LogOut className="size-4" /> Çıkış yap
            </button>
          </div>
        </details>
      </div>
    </header>
  );
}