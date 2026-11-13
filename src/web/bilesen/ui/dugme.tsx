/** Düğme. Görünümler: birincil, ikincil, sade. */
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/sinif";

type Gorunum = "birincil" | "ikincil" | "sade";

const gorunumler: Record<Gorunum, string> = {
  birincil: "bg-vurgu text-vurgu-metin hover:brightness-110",
  ikincil: "border border-kenar bg-yuzey-2 hover:bg-yuzey",
  sade: "hover:bg-yuzey-2",
};

export const Dugme = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { gorunum?: Gorunum }
>(({ className, gorunum = "birincil", type = "button", ...kalan }, ref) => (
  <button
    ref={ref}
    type={type}
    className={cn(
      "inline-flex h-10 items-center justify-center gap-2 rounded-[var(--radius-kutu)] px-4 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
      gorunumler[gorunum],
      className,
    )}
    {...kalan}
  />
));
Dugme.displayName = "Dugme";