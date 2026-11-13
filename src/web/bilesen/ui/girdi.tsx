/** Metin girdisi; hatalı durumda kenarlık kırmızıya döner. */
import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/sinif";

export const Girdi = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { hatali?: boolean }
>(({ className, hatali, ...kalan }, ref) => (
  <input
    ref={ref}
    className={cn(
      "h-10 w-full rounded-[var(--radius-kutu)] border bg-yuzey px-3 text-sm text-metin placeholder:text-solgun/70",
      hatali ? "border-tehlike" : "border-kenar",
      className,
    )}
    {...kalan}
  />
));
Girdi.displayName = "Girdi";