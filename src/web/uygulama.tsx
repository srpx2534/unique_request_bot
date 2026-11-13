/**
 * Uygulama kökü.
 *
 * Veri istemcisi, bildirim sağlayıcısı ve yönlendirici burada kurulur.
 * /giris dışındaki tüm yollar oturum ister; oturum yoksa girişe atılır.
 */
import { useEffect, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { BildirimSaglayici } from "@/bilesen/ui/bildirim";
import Kabuk from "@/kabuk/kabuk";
import Giris from "@/sayfa/giris";
import Bulunamadi from "@/sayfa/bulunamadi";
import Panel from "@/sayfa/panel";
import Siteler from "@/sayfa/siteler";
import Kelimeler from "@/sayfa/kelimeler";
import Saglayicilar from "@/sayfa/saglayicilar";
import Sunucular from "@/sayfa/sunucular";
import Uyarilar from "@/sayfa/uyarilar";
import Loglar from "@/sayfa/loglar";
import Rapor from "@/sayfa/rapor";
import Ayarlar from "@/sayfa/ayarlar";
import { oturumKullan } from "@/lib/oturum";
import { temaBaslat } from "@/lib/tema";

const istemci = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function Yukleniyor() {
  return (
    <div className="grid min-h-full place-items-center">
      <Loader2 className="size-5 animate-spin text-solgun" />
    </div>
  );
}

function KorumaliRota({ children }: { children: ReactNode }) {
  const oturum = oturumKullan();
  if (oturum.isPending) return <Yukleniyor />;
  if (!oturum.data) return <Navigate to="/giris" replace />;
  return <>{children}</>;
}

export default function Uygulama() {
  useEffect(() => temaBaslat(), []);

  return (
    <QueryClientProvider client={istemci}>
      <BildirimSaglayici>
        <BrowserRouter>
          <Routes>
            <Route path="/giris" element={<Giris />} />
            <Route
              element={
                <KorumaliRota>
                  <Kabuk />
                </KorumaliRota>
              }
            >
              <Route index element={<Panel />} />
              <Route path="siteler" element={<Siteler />} />
              <Route path="kelimeler" element={<Kelimeler />} />
              <Route path="saglayicilar" element={<Saglayicilar />} />
              <Route path="sunucular" element={<Sunucular />} />
              <Route path="uyarilar" element={<Uyarilar />} />
              <Route path="loglar" element={<Loglar />} />
              <Route path="rapor" element={<Rapor />} />
              <Route path="ayarlar" element={<Ayarlar />} />
            </Route>
            <Route path="*" element={<Bulunamadi />} />
          </Routes>
        </BrowserRouter>
      </BildirimSaglayici>
    </QueryClientProvider>
  );
}