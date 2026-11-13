/** Sayfa gezinme çubuğu: aralık, toplam ve önceki/sonraki düğmeleri. */
type Props = {
  sayfa: number;
  toplam: number;
  adet: number;
  degistir: (sayfa: number) => void;
};

export function Sayfalayici({ sayfa, toplam, adet, degistir }: Props) {
  const sonSayfa = Math.max(1, Math.ceil(toplam / adet));
  const bas = toplam === 0 ? 0 : (sayfa - 1) * adet + 1;
  const son = Math.min(sayfa * adet, toplam);

  return (
    <div className="flex items-center gap-3 text-xs text-solgun">
      <span>
        {bas}–{son} / {toplam}
      </span>
      <button
        type="button"
        onClick={() => degistir(sayfa - 1)}
        disabled={sayfa <= 1}
        className="rounded-full bg-yuzey-2 px-3 py-1 text-metin hover:bg-kenar disabled:opacity-40"
      >
        önceki
      </button>
      <span>
        {sayfa} / {sonSayfa}
      </span>
      <button
        type="button"
        onClick={() => degistir(sayfa + 1)}
        disabled={sayfa >= sonSayfa}
        className="rounded-full bg-yuzey-2 px-3 py-1 text-metin hover:bg-kenar disabled:opacity-40"
      >
        sonraki
      </button>
    </div>
  );
}