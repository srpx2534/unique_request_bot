/** Yüzey kartı; başlık ve açıklama isteğe bağlı. */
import type { ReactNode } from "react";
import { cn } from "@/lib/sinif";

export function Kart({
  baslik,
  aciklama,
  children,
  className,
}: {
  baslik?: string;
  aciklama?: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-[var(--radius-kutu)] border border-kenar bg-yuzey p-5", className)}>
      {baslik ? <h2 className="text-sm font-semibold">{baslik}</h2> : null}
      {aciklama ? <p className="mt-1 text-sm text-solgun">{aciklama}</p> : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}