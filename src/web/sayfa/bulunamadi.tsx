/** Bilinmeyen yol: sessiz yönlendirme yerine açıklama ve dönüş bağlantısı. */
import { Link } from "react-router-dom";
import { Kart } from "@/bilesen/ui/kart";

export default function Bulunamadi() {
  return (
    <Kart baslik="Sayfa bulunamadı" aciklama="Adres yanlış ya da sayfa taşınmış olabilir.">
      <Link to="/" className="text-sm text-vurgu underline">
        Genel bakışa dön
      </Link>
    </Kart>
  );
}