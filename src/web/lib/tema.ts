/**
 * Tema tercihi.
 *
 * Seçim localStorage'da tutulur; "sistem" seçiliyken işletim sistemi
 * tercihi izlenir. html elemanına data-tema yazılır, renkler CSS'te döner.
 */
export type Tema = "koyu" | "acik" | "sistem";

const ANAHTAR = "urb_tema";

export function temaOku(): Tema {
  const deger = localStorage.getItem(ANAHTAR);
  return deger === "acik" || deger === "koyu" || deger === "sistem" ? deger : "koyu";
}

function uygula(tema: Tema): void {
  const acik =
    tema === "acik" ||
    (tema === "sistem" && matchMedia("(prefers-color-scheme: light)").matches);
  document.documentElement.dataset.tema = acik ? "acik" : "koyu";
}

export function temaYaz(tema: Tema): void {
  localStorage.setItem(ANAHTAR, tema);
  uygula(tema);
}

/** Açılışta çağrılır; sistem tercihi değişirse yeniden uygular. */
export function temaBaslat(): () => void {
  uygula(temaOku());
  const medya = matchMedia("(prefers-color-scheme: light)");
  const dinle = () => {
    if (temaOku() === "sistem") uygula("sistem");
  };
  medya.addEventListener("change", dinle);
  return () => medya.removeEventListener("change", dinle);
}