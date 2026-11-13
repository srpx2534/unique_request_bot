/**
 * Yan menü.
 *
 * Maddeler sabit; daraltma durumu üstte tutulur. Mobilde çekmece olarak
 * aynı bileşen kullanıldığı için kapanma geri çağrısı alır.
 */
import { NavLink } from "react-router-dom";
import {
  Bell,
  ChevronsLeft,
  ChevronsRight,
  LayoutDashboard,
  Network,
  Server,
  ScrollText,
  BarChart3,
  Search,
  Globe,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/sinif";

const maddeler = [
  { yol: "/", ad: "Genel bakış", Ikon: LayoutDashboard },
  { yol: "/siteler", ad: "Siteler", Ikon: Globe },
  { yol: "/kelimeler", ad: "Kelimeler", Ikon: Search },
  { yol: "/saglayicilar", ad: "Sağlayıcılar", Ikon: Network },
  { yol: "/sunucular", ad: "Sunucular", Ikon: Server },
  { yol: "/uyarilar", ad: "Uyarılar", Ikon: Bell },
  { yol: "/loglar", ad: "Loglar", Ikon: ScrollText },
  { yol: "/rapor", ad: "Rapor", Ikon: BarChart3 },
  { yol: "/ayarlar", ad: "Ayarlar", Ikon: Settings },
];

export default function YanMenu({
  dar,
  daraltDegistir,
  kapat,
}: {
  dar: boolean;
  daraltDegistir: () => void;
  kapat?: () => void;
}) {
  return (
    <div className="flex h-full flex-col border-r border-kenar bg-yuzey">
      <div className={cn("flex h-14 items-center border-b border-kenar px-4", dar && "justify-center px-0")}>
        <span className="text-sm font-semibold tracking-tight text-vurgu">
          {dar ? "URB" : "Unique Request Bot"}
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {maddeler.map(({ yol, ad, Ikon }) => (
          <NavLink
            key={yol}
            to={yol}
            end={yol === "/"}
            onClick={kapat}
            title={dar ? ad : undefined}
            className={({ isActive }) =>
              cn(
                "flex h-10 items-center gap-3 rounded-[var(--radius-kutu)] px-3 text-sm transition",
                dar && "justify-center px-0",
                isActive ? "bg-vurgu/12 text-vurgu" : "text-solgun hover:bg-yuzey-2 hover:text-metin",
              )
            }
          >
            <Ikon className="size-4 shrink-0" />
            {dar ? null : <span>{ad}</span>}
          </NavLink>
        ))}
      </nav>

      <button
        type="button"
        onClick={daraltDegistir}
        className="hidden h-11 items-center justify-center border-t border-kenar text-solgun hover:bg-yuzey-2 lg:flex"
        aria-label={dar ? "Menüyü genişlet" : "Menüyü daralt"}
      >
        {dar ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
      </button>
    </div>
  );
}
