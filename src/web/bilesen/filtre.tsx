/** Filtre çubuğu: tarih çipleri, arama ve seçim. */
import type { ReactNode } from "react";
import { cn } from "@/lib/sinif";

export type Aralik = "bugun" | "dun" | "hafta" | "ay" | "hepsi";

const ARALIKLAR: { deger: Aralik; ad: string }[] = [
  { deger: "bugun", ad: "Bugün" },
  { deger: "dun", ad: "Dün" },
  { deger: "hafta", ad: "7 gün" },
  { deger: "ay", ad: "30 gün" },
  { deger: "hepsi", ad: "Tümü" },
];

export function FiltreCubugu({
  aralik,
  aralikDegistir,
  children,
}: {
  aralik: Aralik;
  aralikDegistir: (a: Aralik) => void;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-kutu)] border border-kenar bg-yuzey p-2">
      <div className="flex gap-1">
        {ARALIKLAR.map((a) => (
          <button
            key={a.deger}
            type="button"
            onClick={() => aralikDegistir(a.deger)}
            className={cn(
              "rounded-full px-3 py-1 text-xs transition",
              aralik === a.deger ? "bg-vurgu text-vurgu-metin" : "text-solgun hover:bg-yuzey-2",
            )}
          >
            {a.ad}
          </button>
        ))}
      </div>
      <span className="mx-1 h-5 w-px bg-kenar" />
      {children}
    </div>
  );
}