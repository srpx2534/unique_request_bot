/**
 * Oturum sorgusu, giriş ve çıkış.
 *
 * Kimlik /api/ben'den okunur; 401 hata değil "giriş yok" sayılır.
 * Giriş oturumu yenilediği için sunucu taze CSRF token'ı da döner,
 * istemci onu bundan sonraki yazmalarda kullanır.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiHatasi, iste, tokenAyarla, tokenSifirla } from "./api";

export type Kimlik = { id: number; eposta: string; rol: string };
export type GirisSonuc = Kimlik & { token: string };

export function oturumKullan() {
  return useQuery<Kimlik, ApiHatasi>({
    queryKey: ["ben"],
    queryFn: () => iste<Kimlik>("/ben"),
    retry: false,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function girisKullan() {
  const istemci = useQueryClient();
  return useMutation<GirisSonuc, ApiHatasi, { eposta: string; sifre: string }>({
    mutationFn: (govde) => iste<GirisSonuc>("/giris", { method: "POST", body: JSON.stringify(govde) }),
    onSuccess: ({ token, ...kimlik }) => {
      tokenAyarla(token);
      istemci.setQueryData(["ben"], kimlik);
    },
  });
}

export function cikisKullan() {
  const istemci = useQueryClient();
  return useMutation<void, ApiHatasi>({
    mutationFn: () => iste<void>("/cikis", { method: "POST" }),
    onSettled: () => {
      tokenSifirla();
      istemci.removeQueries({ queryKey: ["ben"] });
    },
  });
}