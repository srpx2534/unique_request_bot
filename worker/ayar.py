"""Ortam değişkeni erişimi.

.env proje kökünden bir kez yüklenir; worker modülleri ayarları buradan
okur. Böylece sır kod içinde tutulmaz ve her modül kendi yüklemesini
yazmaz (§18.4, C24). Değerler baştaki/sondaki boşluk ve tırnaktan
arındırılır, çünkü elle yapıştırmada bunlar sık geliyor.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Proje kökü: bu dosyanın bir üst dizini.
KOK = Path(__file__).resolve().parents[1]

# .env varsa yüklenir; yoksa ortam değişkenleri olduğu gibi kullanılır.
load_dotenv(KOK / ".env")


def oku(anahtar: str, varsayilan: str = "") -> str:
    """Ortam değişkenini temizleyerek okur.

    Args:
        anahtar: Değişken adı.
        varsayilan: Değişken yoksa dönecek değer.

    Returns:
        Boşluk ve tırnaktan arındırılmış değer.
    """
    ham = os.getenv(anahtar, varsayilan)
    return ham.strip().strip('"').strip("'")


def zorunlu(anahtar: str) -> str:
    """Zorunlu değişkeni okur.

    Args:
        anahtar: Değişken adı.

    Returns:
        Temizlenmiş değer.

    Raises:
        RuntimeError: Değişken boşsa.
    """
    deger = oku(anahtar)
    if not deger:
        raise RuntimeError(f".env içinde {anahtar} boş")
    return deger

def serp_anahtari() -> str:
    """Aktif SERP anahtarını verir.

    Önce ayar tablosu, sonra .env okunur. ayar_db, ayar modülünü içe aktardığı
    için burada gecikmeli içe aktarma yapılır.

    Returns:
        Anahtar; tanımlı değilse boş dize.
    """
    from worker import ayar_db

    return ayar_db.oku("serp_decodo")
