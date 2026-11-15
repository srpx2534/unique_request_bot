"""Proxy dizesi biçimlendirme.

Sağlayıcı satırındaki ağ geçidi ve kimlik bilgilerinden curl_cffi'nin
anladığı dize üretilir. Hedefleme kullanıcı adına eklenir: ülke, gerekiyorsa
il. Her hit yeni oturum kimliği alır; böylece IP hit başına değişir ama hit
içindeki üç istek (izlenim, tıklama, pogo) aynı IP'den çıkar.

Kullanıcı adı biçimi sağlayıcıya göredir: Decodo, Oxylabs ve IPRoyal
`user-` önekiyle, SOAX paket adıyla, Bright Data `brd-customer-` önekiyle,
Webshare düz kullanıcı adıyla (hedefleme parametresi yok) çalışır. Biçim sağlayıcı adından çözülür; tanınmayan ad Decodo sayılır.

Seçim burada değil, worker/havuz.py içinde yapılır; bu modül yalnızca
biçimlendirir.

Kullanım: worker/havuz.py, tools/proxy_dene.py.
"""

from __future__ import annotations

import secrets

OTURUM_UZUNLUK = 8  # karakter; çakışma olasılığı ihmal edilebilir

# Sağlayıcı başına kullanıcı adı kalıbı. {ulke} ve {city} boş olabilir.
BICIMLER = {
    "decodo": "user-{k}{ulke}{city}-session-{s}",
    "oxylabs": "user-{k}{ulke}{city}-session-{s}",
    "iproyal": "user-{k}{ulke}{city}-session-{s}",
    "soax": "{k}{ulke}{city}-session-{s}",
    "brightdata": "brd-customer-{k}{ulke}{city}-session-{s}",
    # Webshare hedefleme parametresi kullanmaz: duz kullanici adi yeter.
    "webshare": "{k}",
}


def bicim_bul(saglayici_adi: str | None) -> str:
    """Sağlayıcı adından kullanıcı adı biçimini çözer.

    Args:
        saglayici_adi: provider.name değeri.

    Returns:
        BICIMLER anahtarı; tanınmayan ad için "decodo".
    """
    ad = (saglayici_adi or "").strip().lower().replace(" ", "")
    for anahtar in BICIMLER:
        # "bright data" gibi boşluklu yazım da yakalanır.
        if anahtar in ad:
            return anahtar
    return "decodo"


def dize(
    gateway: str,
    kullanici: str,
    sifre: str,
    ulke: str | None = "TR",
    geo_slug: str | None = None,
    oturum: str | None = None,
    bicim: str = "decodo",
) -> str:
    """Proxy dizesi kurar.

    Args:
        gateway: host:port.
        kullanici: Sağlayıcı kullanıcı adı (önek hariç).
        sifre: Sağlayıcı şifresi.
        ulke: Çıkış ülkesi kodu; None ise ülke parametresi yazılmaz.
        geo_slug: İl slug'ı; verilirse city hedeflemesi eklenir.
        oturum: Oturum kimliği; verilmezse rastgele üretilir.
        bicim: bicim_bul() sonucu.

    Returns:
        http://kullanici:sifre@host:port dizesi.
    """
    if not kullanici:
        # Ücretsiz düz proxy: kimlik yok, hedefleme de yok.
        return f"http://{gateway}"

    kalip = BICIMLER.get(bicim, BICIMLER["decodo"])
    ad = kalip.format(
        k=kullanici,
        ulke=f"-country-{ulke.lower()}" if ulke else "",
        city=f"-city-{geo_slug}" if geo_slug else "",
        s=oturum or secrets.token_hex(OTURUM_UZUNLUK // 2),
    )
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
    # Kimlik yoksa (duz proxy) iki nokta da yok: "host:***@" yazmak bozuk durur.
    if "@" not in kalan:
        return f"{bas}://{kalan}"
    kimlik, _, host = kalan.partition("@")
    kullanici, ayrac, sifre = kimlik.partition(":")
    if not ayrac or not sifre:
        return f"{bas}://{kullanici}@{host}"
    return f"{bas}://{kullanici}:***@{host}"