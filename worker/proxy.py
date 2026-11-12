"""Proxy dizesi üretimi (Decodo residential).

Hedefleme kullanıcı adına eklenir: ülke ve gerekiyorsa il. Her hit yeni bir
oturum kimliği alır; böylece IP hit başına değişir, ama hit içindeki üç
istek (izlenim, tıklama, pogo) aynı IP'den çıkar. Bu bütünlük olmadan
Google tıklamayı ayrı bir ziyaret sayar.

Kimlik bilgileri .env'den okunur: DECODO_USER, DECODO_PASS, DECODO_GATEWAY.
Bilgi yoksa None döner ve hat doğrudan bağlantıya düşer (§5 adım 2).

Kullanım: worker/burst.py, tools/proxy_dene.py.
"""

from __future__ import annotations

import secrets

from worker import ayar

VARSAYILAN_GATEWAY = "tr.decodo.com:10001"  # 10001 = oturum boyunca sabit IP
OTURUM_UZUNLUK = 8  # karakter; çakışma olasılığı ihmal edilebilir


def var_mi() -> bool:
    """Proxy kimlik bilgileri tanımlı mı."""
    return bool(ayar.oku("DECODO_USER") and ayar.oku("DECODO_PASS"))


def _gateway() -> str:
    """Ağ geçidini döndürür; tanımlı değilse varsayılanı kullanır."""
    return ayar.oku("DECODO_GATEWAY", VARSAYILAN_GATEWAY) or VARSAYILAN_GATEWAY


def proxy_uret(geo_slug: str | None = None, oturum: str | None = None) -> str | None:
    """Tek kullanımlık proxy dizesi üretir.

    Args:
        geo_slug: İl slug'ı (ör. istanbul). None ise ülke hedeflenir.
        oturum: Oturum kimliği. None ise rastgele üretilir.

    Returns:
        http://kullanici:sifre@host:port dizesi; kimlik yoksa None.
    """
    if not var_mi():
        return None

    kullanici = f"user-{ayar.oku('DECODO_USER')}-country-tr"
    if geo_slug:
        # İl hedefleme yalnızca destekleyen sağlayıcıda anlamlı (§5 adım 1).
        kullanici += f"-city-{geo_slug}"
    kullanici += f"-session-{oturum or secrets.token_hex(OTURUM_UZUNLUK // 2)}"

    return f"http://{kullanici}:{ayar.oku('DECODO_PASS')}@{_gateway()}"


def varsayilan_secici(geo_slug: str | None = None):
    """Her çağrıda yeni proxy üreten kapanış döndürür.

    Args:
        geo_slug: Sabitlenecek il slug'ı.

    Returns:
        Parametresiz çağrılabilir; proxy ya da None döndürür.
    """
    return lambda: proxy_uret(geo_slug)


def maskele(proxy: str | None) -> str:
    """Proxy dizesindeki şifreyi gizler.

    Args:
        proxy: Ham proxy dizesi.

    Returns:
        Şifresi yıldızlanmış dize.
    """
    if not proxy:
        return "(yok)"
    bas, _, kalan = proxy.partition("://")
    kimlik, _, host = kalan.partition("@")
    kullanici, _, _ = kimlik.partition(":")
    return f"{bas}://{kullanici}:***@{host}"