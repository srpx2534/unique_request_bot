/**
 * Kısa bildirim.
 *
 * Sağ altta yığılır, dört saniye sonra kalkar. Kalıcı kayıt tutmaz;
 * kalıcı olaylar uyarı tablosunda durur.
 */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

type Tur = "bilgi" | "hata";
type Kayit = { id: number; metin: string; tur: Tur };

const Baglam = createContext<(metin: string, tur?: Tur) => void>(() => {});

export function BildirimSaglayici({ children }: { children: ReactNode }) {
  const [kayitlar, setKayitlar] = useState<Kayit[]>([]);

  const ekle = useCallback((metin: string, tur: Tur = "bilgi") => {
    const id = Date.now() + Math.random();
    setKayitlar((onceki) => [...onceki, { id, metin, tur }]);
    setTimeout(() => setKayitlar((onceki) => onceki.filter((k) => k.id !== id)), 4000);
  }, []);

  const deger = useMemo(() => ekle, [ekle]);

  return (
    <Baglam.Provider value={deger}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
        {kayitlar.map((k) => (
          <div
            key={k.id}
            role="status"
            className={`rounded-[var(--radius-kutu)] border bg-yuzey px-4 py-3 text-sm ${
              k.tur === "hata" ? "border-tehlike/50 text-tehlike" : "border-kenar"
            }`}
          >
            {k.metin}
          </div>
        ))}
      </div>
    </Baglam.Provider>
  );
}

export function useBildirim() {
  return useContext(Baglam);
}