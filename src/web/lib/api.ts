/**
 * API istemcisi.
 *
 * CSRF token'ı ilk yazma isteğinden önce alınır ve bellekte tutulur.
 * 401 oturumun düştüğü anlamına gelir; token sıfırlanır, çağıran taraf
 * girişe yönlendirir. Token hiçbir yerde kalıcı saklanmaz.
 */
const TABAN = "/api";

let token: string | null = null;

export class ApiHatasi extends Error {
  constructor(
    readonly durum: number,
    mesaj: string,
  ) {
    super(mesaj);
  }
}

/** Token'ı getirir, yoksa bir kez alır. */
async function tokenAl(): Promise<string> {
  if (token) return token;
  const yanit = await fetch(`${TABAN}/token`, { credentials: "same-origin" });
  if (!yanit.ok) throw new ApiHatasi(yanit.status, "güvenlik token'ı alınamadı");
  token = ((await yanit.json()) as { token: string }).token;
  return token;
}

export function tokenSifirla(): void {
  token = null;
}

export async function iste<T>(yol: string, secenek: RequestInit = {}): Promise<T> {
  const yontem = (secenek.method ?? "GET").toUpperCase();
  const basliklar = new Headers(secenek.headers);
  if (secenek.body) basliklar.set("content-type", "application/json");
  if (yontem !== "GET" && yontem !== "HEAD") basliklar.set("x-csrf-token", await tokenAl());

  const yanit = await fetch(`${TABAN}${yol}`, {
    ...secenek,
    method: yontem,
    headers: basliklar,
    credentials: "same-origin",
  });

  if (yanit.status === 401) tokenSifirla();
  if (!yanit.ok) {
    const govde = (await yanit.json().catch(() => ({}))) as { hata?: string };
    throw new ApiHatasi(yanit.status, govde.hata ?? "istek başarısız");
  }
  if (yanit.status === 204) return undefined as T;
  return (await yanit.json()) as T;
}
/** Sunucudan gelen taze token'ı yazar; giriş sonrası oturum yenilendiğinde gerekir. */
export function tokenAyarla(deger: string): void {
  token = deger;
}
