/** Henüz yazılmamış ekranların yer tutucusu. */
import { Kart } from "./ui/kart";

export default function YerTutucu({ baslik, aciklama }: { baslik: string; aciklama: string }) {
  return (
    <Kart baslik={baslik} aciklama={aciklama}>
      <p className="text-sm text-solgun">Bu ekran sıradaki adımda bağlanacak.</p>
    </Kart>
  );
}