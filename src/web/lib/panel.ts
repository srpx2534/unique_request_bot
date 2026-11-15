/**
 * Panel veri kancaları.
 *
 * Okuma uçları sorgu, yazma uçları mutasyon olarak sarılır. Her yazmadan
 * sonra ilgili sorgu geçersiz kılınır, ekran kendini tazeler.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiHatasi, iste } from "./api";

export type Ozet = {
  aktif_kelime: number;
  toplam_kelime: number;
  aktif_site: number;
  canli_saglayici: number;
  acik_uyari: number;
  gunluk_burst: number;
  son: { id: number; text: string; step: number; target_count: number; started_at: string }[];
  siteler: { id: number; domain: string; label: string | null }[];
  kelimeler: {
    id: number;
    text: string;
    state: string;
    volume: number | null;
    domain: string;
    il_adi: string | null;
    geo_adet: number;
    atilan: number;
    son_burst_at: string | null;
  }[];
  havuz: { canli_tr: number; canli_yabanci: number; olu: number } | null;
  uyarilar: { id: number; kind: string; message: string; yas_dk: number }[];
};

export type Saglayici = {
  id: number;
  name: string;
  kind: string;
  ulke: string;
  state: string;
  weight: number;
  gateway: string | null;
  kullanici: string | null;
  captcha_pct: string;
  quarantine_until: string | null;
};

export type Uyari = {
  id: number;
  kind: string;
  message: string;
  acknowledged: number;
  created_at: string;
  yas_dk: number;
};

export type Ayar = { anahtar: string; deger: string };

export type Log = {
  id: number;
  kelime: string;
  domain: string;
  step: number;
  target_count: number;
  started_at: string;
  ended_at: string | null;
  stats: string;
  geo_code: number;
  tier: string;
};

function tazele(istemci: ReturnType<typeof useQueryClient>, anahtar: string) {
  return () => istemci.invalidateQueries({ queryKey: [anahtar] });
}

export function ozetKullan() {
  return useQuery<Ozet, ApiHatasi>({
    queryKey: ["ozet"],
    queryFn: () => iste<Ozet>("/ozet"),
    refetchInterval: 15_000,
  });
}

export function saglayiciKullan(arama = "") {
  return useQuery<Saglayici[], ApiHatasi>({
    queryKey: ["provider", arama],
    queryFn: () => iste<Saglayici[]>(`/provider${arama ? `?q=${encodeURIComponent(arama)}` : ""}`),
  });
}

export function saglayiciGuncelle() {
  const istemci = useQueryClient();
  return useMutation<unknown, ApiHatasi, { id: number; govde: Record<string, unknown> }>({
    mutationFn: ({ id, govde }) =>
      iste(`/provider/${id}`, { method: "PATCH", body: JSON.stringify(govde) }),
    onSuccess: tazele(istemci, "provider"),
  });
}

/** Çan için yalnızca açık uyarıları verir. */
export function uyariCanli() {
  return useQuery<Uyari[], ApiHatasi>({
    queryKey: ["uyari", "canli"],
    queryFn: async () =>
      (await iste<{ satirlar: Uyari[] }>("/uyari?durum=acik&aralik=hepsi")).satirlar,
    refetchInterval: 20_000,
  });
}

export function uyariKapat() {
  const istemci = useQueryClient();
  return useMutation<void, ApiHatasi, number>({
    mutationFn: (id) => iste<void>(`/uyari/${id}/kapat`, { method: "POST" }),
    onSuccess: tazele(istemci, "uyari"),
  });
}

export function uyariTumunuKapat() {
  const istemci = useQueryClient();
  return useMutation<{ kapatilan: number }, ApiHatasi, { tur?: string; aralik?: string }>({
    mutationFn: (govde) => iste("/uyari/tumunu-kapat", { method: "POST", body: JSON.stringify(govde) }),
    onSuccess: tazele(istemci, "uyari"),
  });
}

export function ayarKullan() {
  return useQuery<Ayar[], ApiHatasi>({
    queryKey: ["ayar"],
    queryFn: () => iste<Ayar[]>("/ayar"),
  });
}

export function ayarYaz() {
  const istemci = useQueryClient();
  return useMutation<Ayar[], ApiHatasi, Record<string, string>>({
    mutationFn: (govde) => iste<Ayar[]>("/ayar", { method: "PATCH", body: JSON.stringify(govde) }),
    onSuccess: tazele(istemci, "ayar"),
  });
}

/** Tür oranlarını yazar: üçü birlikte, toplam 100 olmalı. */
export function oranYaz() {
  const istemci = useQueryClient();
  return useMutation<Ayar[], ApiHatasi, Record<string, string>>({
    mutationFn: (govde) => iste<Ayar[]>("/ayar/oran", { method: "PATCH", body: JSON.stringify(govde) }),
    onSuccess: tazele(istemci, "ayar"),
  });
}
