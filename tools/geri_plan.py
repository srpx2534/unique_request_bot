"""Migration geri alma planı (E5).

Geri alma, ileri migration'ların elle yazılmış `.down.sql` karşılıklarıyla
koşar. Planlama saftır: veritabanına çıkmaz, bu yüzden test edilebilir.
Geri dosyası eksikse plan üretilmez; yarım geri alma sessizce koşmaz.

Kullanım: tools/migrate.py --geri <n> [--uygula].
"""

from __future__ import annotations

from pathlib import Path


def ifade_var(dosya: Path) -> bool:
    """Geri dosyası en az bir çalıştırılabilir satır taşıyor mu.

    Yalnız yorumdan oluşan geri dosyası sessizce hiçbir şey yapmazdı;
    defterden satır silinip şema eskisinde kalırdı.

    Args:
        dosya: Geri dosyası.

    Returns:
        Çalıştırılabilir satır varsa True.
    """
    for satir in dosya.read_text(encoding="utf-8").splitlines():
        temiz = satir.strip()
        if temiz and not temiz.startswith("--"):
            return True
    return False


def geri_dosyasi(geri_dizini: Path, ad: str) -> Path:
    """Bir migration'ın geri dosyası yolunu verir.

    Args:
        geri_dizini: Geri dosyalarının dizini.
        ad: İleri migration dosya adı (`046_x.sql`).

    Returns:
        Beklenen geri dosyası yolu; var olup olmadığına bakılmaz.
    """
    govde = ad[:-4] if ad.endswith(".sql") else ad
    return geri_dizini / f"{govde}.down.sql"


def geri_plani(uygulanan: set[str], adet: int, geri_dizini: Path) -> tuple[list[dict], list[str]]:
    """Geri alma adımlarını ve engelleri hesaplar.

    Args:
        uygulanan: Defterdeki migration adları.
        adet: Kaç migration geri alınacak.
        geri_dizini: Geri dosyalarının dizini.

    Returns:
        `(adimlar, hatalar)`. Adımlar en yeniden en eskiye sıralıdır;
        hata varsa adımlar boştur ve hiçbir şey koşmaz.
    """
    hatalar: list[str] = []
    if adet <= 0:
        hatalar.append("adet pozitif olmalı")
    # Adlar numarayla başlar; sözlük sırası numara sırasıdır.
    sirali = sorted(uygulanan, reverse=True)
    if adet > len(sirali):
        hatalar.append(f"{adet} istendi, defterde {len(sirali)} migration var")
    secilen = sirali[:max(adet, 0)]
    eksik = [
        ad for ad in secilen
        if not geri_dosyasi(geri_dizini, ad).exists()
        or not ifade_var(geri_dosyasi(geri_dizini, ad))
    ]
    if eksik:
        hatalar.append("geri dosyası yok: " + ", ".join(eksik))
    if hatalar:
        return [], hatalar
    adimlar = [
        {"ad": ad, "dosya": geri_dosyasi(geri_dizini, ad)} for ad in secilen
    ]
    return adimlar, []

