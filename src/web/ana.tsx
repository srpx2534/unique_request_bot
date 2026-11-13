/**
 * Panel giriş noktası.
 *
 * React ağacını kök elemana bağlar. Yönlendirme ve veri katmanı üst
 * bileşende kurulur; bu dosya yalnızca başlatma yapar.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Uygulama from "./uygulama";
import "./stil.css";

const kok = document.getElementById("kok");
if (!kok) throw new Error("kök eleman bulunamadı");

createRoot(kok).render(
  <StrictMode>
    <Uygulama />
  </StrictMode>,
);