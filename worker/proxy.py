"""Proxy dizesi biçimlendirme.

Sağlayıcı satırındaki ağ geçidi ve kimlik bilgilerinden curl_cffi'nin
anladığı dize üretilir. Hedefleme kullanıcı adına eklenir: ülke, gerekiyorsa
il. Her hit yeni oturum kimliği alır; böylece IP hit başına değişir ama hit
içindeki üç istek (izlenim, tıklama, pogo) aynı IP'den çıkar.

Seçim burada değil, worker/havuz.py içinde yapılır; bu modül yalnızca
biçimlendirir.

Kullanım: worker/havuz.py, tools/proxy_dene.py.
"""

from __future__ import annotations

import secrets

OTURUM_UZUNLUK = 8  # karakter; çakışma olasılığı ihmal edilebilir


def dize(
    gateway: str,
    kullanici: str,
    sifre: str,
    geo_slug: str | None = None,
    oturum: str | None = None,
) -> str:
    """Proxy dizesi kurar.

    Args:
        gateway: host:port.
        kullanici: Sağlayıcı kullanıcı adı (user- öneki hariç).
        sifre: Sağlayıcı şifresi.
        geo_slug: İl slug'ı; verilirse city hedeflemesi eklenir.
        oturum: Oturum kimliği; verilmezse rastgele üretilir.

    Returns:
        http://kullanici:sifre@host:port dizesi.
    """
    ad = f"user-{kullanici}-country-tr"
    if geo_slug:
        # İl hedefleme yalnızca destekleyen sağlayıcıda anlamlı (§5 adım 1).
        ad += f"-city-{geo_slug}"
    ad += f"-session-{oturum or secrets.token_hex(OTURUM_UZUNLUK // 2)}"
    return f"http://{ad}:{sifre}@{gateway}"


def maskele(proxy: str | None) -> str:
    """Şifreyi gizler.

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