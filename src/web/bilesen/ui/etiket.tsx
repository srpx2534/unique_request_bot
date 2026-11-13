/** Küçük durum etiketi. */
import type { ReactNode } from "react";
import { cn } from "@/lib/sinif";

type Ton = "notr" | "basari" | "uyari" | "tehlike" | "vurgu";

const tonlar: Record<Ton, string> = {
  notr: "border-kenar text-solgun",
  basari: "border-basari/40 text-basari",
  uyari: "border-uyari/40 text-uyari",
  tehlike: "border-tehlike/40 text-tehlike",
  vurgu: "border-vurgu/40 text-vurgu",
};

export function Etiket({ ton = "notr", children }: { ton?: Ton; children: ReactNode }) {
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs", tonlar[ton])}>
      {children}
    </span>
  );
}