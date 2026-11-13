/**
 * Panel kabuğu.
 *
 * Masaüstünde sabit menü, mobilde çekmece. Daraltma tercihi
 * localStorage'da tutulur; Escape çekmeceyi kapatır.
 */
import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { X } from "lucide-react";
import YanMenu from "./yan-menu";
import UstCubuk from "./ust-cubuk";
import { cn } from "@/lib/sinif";

const basliklar: Record<string, string> = {
  "/": "Genel bakış",
  "/siteler": "Siteler",
  "/kelimeler": "Kelimeler",
  "/saglayicilar": "Sağlayıcılar",
  "/sunucular": "Sunucular",
  "/uyarilar": "Uyarılar",
  "/loglar": "Loglar",
  "/rapor": "Rapor",
  "/ayarlar": "Ayarlar",
};

export default function Kabuk() {
  const { pathname } = useLocation();
  const [dar, setDar] = useState(() => localStorage.getItem("urb_dar") === "1");
  const [cekmece, setCekmece] = useState(false);

  useEffect(() => {
    setCekmece(false);
  }, [pathname]);

  useEffect(() => {
    const dinle = (o: KeyboardEvent) => {
      if (o.key === "Escape") setCekmece(false);
    };
    window.addEventListener("keydown", dinle);
    return () => window.removeEventListener("keydown", dinle);
  }, []);

  function daraltDegistir() {
    setDar((o) => {
      localStorage.setItem("urb_dar", o ? "0" : "1");
      return !o;
    });
  }

  return (
    <div className="grid min-h-full grid-cols-1 lg:grid-cols-[auto_1fr]">
      <aside className={cn("hidden lg:block", dar ? "w-16" : "w-56")}>
        <YanMenu dar={dar} daraltDegistir={daraltDegistir} />
      </aside>

      {cekmece ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setCekmece(false)} />
          <div className="absolute inset-y-0 left-0 w-60">
            <YanMenu dar={false} daraltDegistir={daraltDegistir} kapat={() => setCekmece(false)} />
            <button
              type="button"
              onClick={() => setCekmece(false)}
              aria-label="Menüyü kapat"
              className="absolute -right-11 top-3 rounded p-2 text-white/80 hover:bg-white/10"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-col">
        <UstCubuk baslik={basliklar[pathname] ?? "Panel"} cekmeceAc={() => setCekmece(true)} />
        <main className="flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}