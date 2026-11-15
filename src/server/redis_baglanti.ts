/**
 * Redis baglanti secenekleri.
 *
 * Parola URL icine gomulmez: `REDIS_PASSWORD`'dan okunur ve ioredis'e ayri
 * alan olarak verilir. Boylece `&`, `%`, `@` gibi karakterler adresi bozmaz
 * (`%df` gecerli bir kacis olmadigi icin acilista "URI malformed" aliniyordu)
 * ve adres gunluge yazildiginda parola gorunmez.
 *
 * URL'den yalnizca host, port ve db okunur; kimlik bilgisi her zaman
 * REDIS_PASSWORD'den gelir. Kodda parola sabiti tutulmaz.
 */
export type RedisBaglanti = {
  host: string;
  port: number;
  db: number;
  password?: string;
};

const VARSAYILAN = { host: "127.0.0.1", port: 6379, db: 0 };

/** Baglanti seceneklerini kurar; URL okunamazsa varsayilana duser. */
export function redisBaglanti(
  ham = process.env.REDIS_URL ?? "",
  parola = process.env.REDIS_PASSWORD ?? "",
): RedisBaglanti {
  const sonuc: RedisBaglanti = { ...VARSAYILAN };

  let adres: URL | null = null;
  try {
    adres = new URL(ham.trim());
  } catch {
    adres = null;
  }

  if (adres) {
    if (adres.hostname) sonuc.host = adres.hostname;
    const port = Number(adres.port);
    if (Number.isInteger(port) && port > 0) sonuc.port = port;
    const db = Number(adres.pathname.replace(/^\//, ""));
    if (Number.isInteger(db) && db >= 0) sonuc.db = db;
  }

  const sifre = parola.trim();
  if (sifre) sonuc.password = sifre;
  return sonuc;
}

/** Gunluge yazilabilir parolasiz adres. */
export function redisEtiket(baglanti: RedisBaglanti): string {
  return `${baglanti.host}:${baglanti.port}/${baglanti.db}`;
}
