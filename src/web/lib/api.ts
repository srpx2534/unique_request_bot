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
/** Govdesi FormData olan yukleme; gercek gonderim yuzdesini bildirir. */

export function dosyaYukle<T>(yol: string, govde: FormData, yuzde: (oran: number) => void): Promise<T> {
  return new Promise<T>((cozum, red) => {
    void (async () => {
      let baslik: string;
      try {
        baslik = await tokenAl();
      } catch (hata) {
        red(hata);
        return;
      }
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${TABAN}${yol}`);
      xhr.withCredentials = true;
      xhr.setRequestHeader("x-csrf-token", baslik);
      xhr.upload.onprogress = (olay) => {
        if (olay.lengthComputable) yuzde(olay.loaded / olay.total);
      };
      xhr.onload = () => {
        if (xhr.status === 401) tokenSifirla();
        if (xhr.status >= 200 && xhr.status < 300) {
          cozum((xhr.responseText ? JSON.parse(xhr.responseText) : {}) as T);
          return;
        }
        let mesaj: string | undefined;
        try {
          mesaj = (JSON.parse(xhr.responseText) as { hata?: string }).hata;
        } catch {
          mesaj = undefined;
        }
        red(new ApiHatasi(xhr.status, mesaj ?? "yükleme başarısız"));
      };
      xhr.onerror = () => red(new ApiHatasi(0, "bağlantı koptu"));
      xhr.send(govde);
    })();
  });
}
/** Sunucudan gelen taze token'ı yazar; giriş sonrası oturum yenilendiğinde gerekir. */
export function tokenAyarla(deger: string): void {
  token = deger;
}
