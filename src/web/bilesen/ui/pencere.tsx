/** Modal pencere. Radix Dialog üzerine kurulu, Escape ve dış tık ile kapanır. */
import * as Pencere from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { X } from "lucide-react";

export function Modal({
  acik,
  kapat,
  baslik,
  children,
}: {
  acik: boolean;
  kapat: () => void;
  baslik: string;
  children: ReactNode;
}) {
  return (
    <Pencere.Root open={acik} onOpenChange={(o) => !o && kapat()}>
      <Pencere.Portal>
        <Pencere.Overlay className="fixed inset-0 z-50 bg-black/60" />
        <Pencere.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[min(44rem,92vw)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[var(--radius-kutu)] border border-kenar bg-yuzey p-5 shadow-2xl">
          <div className="mb-4 flex items-center justify-between">
            <Pencere.Title className="text-sm font-semibold">{baslik}</Pencere.Title>
            <Pencere.Close className="rounded p-1 text-solgun hover:bg-yuzey-2">
              <X className="size-4" />
            </Pencere.Close>
          </div>
          {children}
        </Pencere.Content>
      </Pencere.Portal>
    </Pencere.Root>
  );
}