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
import YerTutucu from "@/bilesen/yer-tutucu";
import Kabuk from "@/kabuk/kabuk";
import Giris from "@/sayfa/giris";
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
              <Route index element={<YerTutucu baslik="Genel bakış" aciklama="Sıralama özeti, sağlık ve kota göstergeleri." />} />
              <Route path="kelimeler" element={<YerTutucu baslik="Kelimeler" aciklama="Kelime listesi ve sıralama eğrisi." />} />
              <Route path="saglayicilar" element={<YerTutucu baslik="Sağlayıcılar" aciklama="Havuz, tür oranı, devre kesici." />} />
              <Route path="uyarilar" element={<YerTutucu baslik="Uyarılar" aciklama="Coğrafi ve genel eşik uyarıları." />} />
              <Route path="loglar" element={<YerTutucu baslik="Loglar" aciklama="Canlı hit akışı." />} />
              <Route path="ayarlar" element={<YerTutucu baslik="Ayarlar" aciklama="Ölçüm aralığı, kuyruk ve oturum ayarları." />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </BildirimSaglayici>
    </QueryClientProvider>
  );
}