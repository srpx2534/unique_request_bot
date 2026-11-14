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

# SERP anahtar sırası: birincil, sonra yedekler (§8). İlk dolu anahtar döner.
SERP_ANAHTAR_SIRASI = ("serp_decodo", "serp_serper", "serp_searchapi")


def serp_anahtari() -> str:
    """Aktif SERP anahtarını verir.

    Sıra sözleşmededir: Decodo birincil, Serper ve SearchApi yedek. Birincil
    boşsa yedek denenir, böylece tek anahtar bitince ölçüm durmaz.

    Returns:
        Anahtar; hiçbiri tanımlı değilse boş dize.
    """
    from worker import ayar_db

    for anahtar in SERP_ANAHTAR_SIRASI:
        deger = (ayar_db.oku(anahtar) or "").strip()
        if deger:
            return deger
    return ""


def serp_secim() -> tuple[str, str]:
    """Aktif SERP sağlayıcısını ve anahtarını verir.

    Sağlayıcı adı anahtar adından türetilir (`serp_decodo` → `decodo`); uç
    nokta ve gövde biçimi sağlayıcıya göre değiştiği için birlikte döner.

    Returns:
        (sağlayıcı, anahtar); hiçbiri yoksa ("", "").
    """
    from worker import ayar_db

    for anahtar in SERP_ANAHTAR_SIRASI:
        deger = (ayar_db.oku(anahtar) or "").strip()
        if deger:
            return anahtar.removeprefix("serp_"), deger
    return "", ""
