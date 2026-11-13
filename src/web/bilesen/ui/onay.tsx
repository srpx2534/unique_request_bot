/** Silme onayı. Onaylanmadan işlem yapılmaz. */
import { Dugme } from "./dugme";
import { Modal } from "./pencere";

export function Onay({
  acik,
  baslik,
  metin,
  kapat,
  onayla,
  bekle,
  dugmeEtiketi,
}: {
  acik: boolean;
  baslik: string;
  metin: string;
  kapat: () => void;
  onayla: () => void;
  bekle?: boolean;
  dugmeEtiketi?: string;
}) {
  return (
    <Modal acik={acik} kapat={kapat} baslik={baslik}>
      <p className="text-sm text-solgun">{metin}</p>
      <div className="mt-4 flex gap-2">
        <Dugme onClick={onayla} disabled={bekle}>{dugmeEtiketi ?? "Sil"}</Dugme>
        <Dugme gorunum="sade" onClick={kapat}>Vazgeç</Dugme>
      </div>
    </Modal>
  );
}