/**
 * Giriş ekranı.
 *
 * Solda marka paneli, sağda form. Alan hatası alanın altında, 401 ve 429
 * form üstünde gösterilir. Gönderim sırasında düğme kilitlidir; başarıda
 * kimlik önbelleğe yazılır ve panel açılır.
 */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, ShieldCheck } from "lucide-react";
import { Dugme } from "@/bilesen/ui/dugme";
import { Girdi } from "@/bilesen/ui/girdi";
import { girisKullan, oturumKullan } from "@/lib/oturum";

export default function Giris() {
  const oturum = oturumKullan();
  const giris = girisKullan();
  const git = useNavigate();
  const epostaRef = useRef<HTMLInputElement>(null);

  const [eposta, setEposta] = useState("");
  const [sifre, setSifre] = useState("");
  const [goster, setGoster] = useState(false);
  const [alanHatasi, setAlanHatasi] = useState<string | null>(null);

  useEffect(() => {
    epostaRef.current?.focus();
  }, []);

  if (oturum.data) return <Navigate to="/" replace />;

  const durum = giris.error?.durum;
  const ustHata =
    durum === 429
      ? "Çok fazla deneme. Hesap 15 dakika kilitli."
      : durum === 401
        ? "E-posta veya parola hatalı."
        : giris.isError
          ? "Giriş yapılamadı, tekrar dene."
          : null;

  function gonder(olay: FormEvent) {
    olay.preventDefault();
    if (!eposta.includes("@")) {
      setAlanHatasi("Geçerli bir e-posta yaz.");
      return;
    }
    if (sifre.length < 8) {
      setAlanHatasi("Parola en az 8 karakter.");
      return;
    }
    setAlanHatasi(null);
    giris.mutate({ eposta: eposta.trim(), sifre }, { onSuccess: () => git("/", { replace: true }) });
  }

  return (
    <main className="grid min-h-full lg:grid-cols-2">
      <section className="relative hidden flex-col justify-between overflow-hidden border-r border-kenar bg-yuzey p-10 lg:flex">
        <div
          aria-hidden
          className="pointer-events-none absolute -left-24 top-1/3 size-[28rem] rounded-full bg-vurgu/15 blur-3xl"
        />
        <div className="relative">
          <p className="text-sm font-semibold tracking-tight text-vurgu">unique_request_bot</p>
          <h1 className="mt-6 max-w-sm text-3xl font-semibold leading-tight">
            Sıralamayı ölç, gürültüyü ayıkla.
          </h1>
          <p className="mt-4 max-w-sm text-sm text-solgun">
            Kelime bazlı sıralama izleme, sağlayıcı havuzu ve uyarı paneli tek yerde.
          </p>
        </div>
        <ul className="relative space-y-3 text-sm text-solgun">
          <li className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-vurgu" /> Oturum cookie tabanlı, token CSRF korumalı
          </li>
          <li className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-vurgu" /> Beş hatalı denemede hesap kilitlenir
          </li>
        </ul>
      </section>

      <section className="grid place-items-center p-6">
        <div className="w-full max-w-sm">
          <h2 className="text-xl font-semibold">Panele gir</h2>
          <p className="mt-1 text-sm text-solgun">Yönetici hesabıyla devam et.</p>

          {ustHata ? (
            <p
              role="alert"
              className="mt-4 rounded-[var(--radius-kutu)] border border-tehlike/40 bg-tehlike/10 px-3 py-2 text-sm text-tehlike"
            >
              {ustHata}
            </p>
          ) : null}

          <form onSubmit={gonder} className="mt-5 space-y-4" noValidate>
            <div className="space-y-1.5">
              <label htmlFor="eposta" className="text-sm font-medium">
                E-posta
              </label>
              <Girdi
                id="eposta"
                ref={epostaRef}
                type="email"
                autoComplete="username"
                value={eposta}
                hatali={Boolean(alanHatasi) && !eposta.includes("@")}
                onChange={(o) => setEposta(o.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="sifre" className="text-sm font-medium">
                Parola
              </label>
              <div className="relative">
                <Girdi
                  id="sifre"
                  type={goster ? "text" : "password"}
                  autoComplete="current-password"
                  value={sifre}
                  className="pr-10"
                  onChange={(o) => setSifre(o.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setGoster((o) => !o)}
                  aria-label={goster ? "Parolayı gizle" : "Parolayı göster"}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1.5 text-solgun hover:bg-yuzey-2"
                >
                  {goster ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {alanHatasi ? <p className="text-xs text-tehlike">{alanHatasi}</p> : null}
            </div>

            <Dugme type="submit" disabled={giris.isPending} className="w-full">
              {giris.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
              Giriş yap
            </Dugme>
          </form>
        </div>
      </section>
    </main>
  );
}