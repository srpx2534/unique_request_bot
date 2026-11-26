"""Proxy dizesi bicimlendirme.

Saglayici satirindaki ag gecidi ve kimlik bilgilerinden curl_cffi'nin
anladigi dize uretilir. Hedefleme kullanici adina eklenir: ulke, gerekiyorsa
il. Her hit yeni oturum kimligi alir; boylece IP hit basina degisir ama hit
icindeki uc istek (izlenim, tik, pogo) ayni IP'den cikar.

Kullanici adi bicimi saglayiciya goredir: Decodo, Oxylabs ve IPRoyal
`user-` onekiyle, SOAX paket adiyla, Bright Data `brd-customer-` onekiyle,
Webshare duz kullanici adiyla (hedefleme parametresi yok) calisir. Geonode
taban kullanici adi zaten `geonode_` ile baslar: `user-` oneki 407 verdirir,
ulke kucuk harf, tip `-type-residential`, siki eslesme `-strict-on` yazilir.
Bicim saglayici adindan cozulur; taninmayan ad Decodo sayilir.

Geonode oturum eki yalnizca sticky portta gecerlidir (rotasyon 9000-9010,
sticky 10000-10010); bu yuzden oturum varken port kaydirilir. Rotasyonlu
portta `-session-` gondermek 403 verir.

Secim burada degil, worker/havuz.py icinde yapilir; bu modul yalnizca
bicimlendirir.

Kullanim: worker/havuz.py, tools/proxy_dene.py.
"""

from __future__ import annotations

import secrets

OTURUM_UZUNLUK = 8  # karakter; cakisma olasiligi ihmal edilebilir
STICKY_KAYMA = 1000  # 9000-9010 rotasyon portu 10000-10010 sticky olur
ROTASYON_PORTLARI = range(9000, 9011)

# Saglayici basina kullanici adi kalibi. {ulke} ve {city} bos olabilir.
BICIMLER = {
    "decodo": "user-{k}{ulke}{city}-session-{s}",
    "oxylabs": "user-{k}{ulke}{city}-session-{s}",
    "iproyal": "user-{k}{ulke}{city}-session-{s}",
    "soax": "{k}{ulke}{city}-session-{s}",
    "brightdata": "brd-customer-{k}{ulke}{city}-session-{s}",
    # Webshare hedefleme parametresi kullanmaz: duz kullanici adi yeter.
    "webshare": "{k}",
    # DataImpulse parametreleri __ ve ; ile ayirir: __cr.tr, ;city.x, ;sessid.y.
    "dataimpulse": "{k}",
    # Geonode kendi kalibiyla kurulur (bkz. _geonode).
    "geonode": "{k}",
}


def bicim_bul(saglayici_adi: str | None) -> str:
    """Saglayici adindan kullanici adi bicimini cozer.

    Args:
        saglayici_adi: provider.name degeri.

    Returns:
        BICIMLER anahtari; taninmayan ad icin "decodo".
    """
    ad = (saglayici_adi or "").strip().lower().replace(" ", "")
    for anahtar in BICIMLER:
        # "bright data" gibi bosluklu yazim da yakalanir.
        if anahtar in ad:
            return anahtar
    return "decodo"


def cekirdek(gateway: str | None, *fazla) -> str:
    """Ag gecidi metnini host:port'a indirger.

    Panelden gelen deger sema, sonda iki nokta, bastaki/sondaki bosluk ya da
    egik cizgi tasiyabilir; curl_cffi bunlari reddeder. Fazladan konum
    argumanlari yok sayilir, boylece cagiran taraf degisse de bozulmaz.

    Args:
        gateway: Ham ag gecidi metni.
        *fazla: Yok sayilan ek argumanlar.

    Returns:
        host:port; metin bossa bos dize.
    """
    ham = (gateway or "").strip()
    if "://" in ham:
        ham = ham.split("://", 1)[1]
    ham = ham.strip().strip("/").rstrip(":").strip()
    return ham.split("/", 1)[0]


def _sticky(gateway: str) -> str:
    """Rotasyonlu portu sticky karsiligina cevirir.

    Args:
        gateway: host:port.

    Returns:
        Port 9000-9010 araligindaysa 1000 fazlasi, degilse ayni gecit.
    """
    host, ayrac, port = gateway.rpartition(":")
    if not ayrac or not port.isdigit():
        return gateway
    numara = int(port)
    if numara in ROTASYON_PORTLARI:
        return f"{host}:{numara + STICKY_KAYMA}"
    return gateway


def _geonode(gateway: str, kullanici: str, sifre: str, ulke: str | None,
             geo_slug: str | None, oturum: str) -> str:
    """Geonode dizesini kurar: hedefleme kullanici adinda, oturum sticky portta.

    Args:
        gateway: host:port.
        kullanici: Taban kullanici adi; zaten -country-xx tasiyabilir.
        sifre: Saglayici sifresi.
        ulke: Cikis ulkesi kodu; None ise yazilmaz.
        geo_slug: Il slug'i; verilirse city hedeflemesi eklenir.
        oturum: Oturum kimligi.

    Returns:
        http://kullanici:sifre@host:sticky_port dizesi.
    """
    ad = kullanici
    # Taban kullanici adi zaten ulke tasiyorsa ikinci kez yazilmaz.
    if ulke and f"-country-{ulke.lower()}" not in ad.lower():
        ad += f"-country-{ulke.lower()}"
    # Geonode il adini kucuk harf ve harf/rakamla bekler; bos ya da bosluklu
    # slug kullanici adini sessizce 407'ye dusuruyordu (88).
    il = "".join(c for c in (geo_slug or "").lower() if c.isalnum())
    if il and len(il) <= 24:
        ad += f"-city-{il}"
    ad += "-type-residential"
    ad += f"-session-{oturum}"
    return f"http://{ad}:{sifre}@{_sticky(gateway)}"


def _dataimpulse(gateway: str, kullanici: str, sifre: str, ulke: str | None,
                 geo_slug: str | None, oturum: str) -> str:
    """DataImpulse dizesini kurar.

    Parametreler `__` ile ayrilir ve nokta ile deger alir: `__cr.tr`; coklu
    parametre `;` ile eklenir. Oturum eki `;sessid.<deger>` sticky IP verir,
    port degismez (823 hem rotasyon hem oturum icin gecerlidir).

    Args:
        gateway: host:port.
        kullanici: Taban kullanici adi; zaten __cr.xx tasiyabilir.
        sifre: Saglayici sifresi.
        ulke: Cikis ulkesi kodu; None ise yazilmaz.
        geo_slug: Il slug'i; verilirse ;city eki eklenir.
        oturum: Oturum kimligi.

    Returns:
        http://kullanici:sifre@host:port dizesi.
    """
    ad = kullanici
    # Taban kullanici adi zaten ulke tasiyorsa ikinci kez yazilmaz.
    if ulke and "__cr." not in ad.lower():
        ad += f"__cr.{ulke.lower()}"
    if geo_slug:
        ad += f";city.{geo_slug}"
    ad += f";sessid.{oturum}"
    return f"http://{ad}:{sifre}@{gateway}"


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
        gateway: host:port; sema ve artik karakter varsa temizlenir.
        kullanici: Saglayici kullanici adi (onek haric).
        sifre: Saglayici sifresi.
        ulke: Cikis ulkesi kodu; None ise ulke parametresi yazilmaz.
        geo_slug: Il slug'i; verilirse city hedeflemesi eklenir.
        oturum: Oturum kimligi; verilmezse rastgele uretilir.
        bicim: bicim_bul() sonucu.

    Returns:
        http://kullanici:sifre@host:port dizesi.
    """
    gateway = cekirdek(gateway)
    if not kullanici:
        # Ucretsiz duz proxy: kimlik yok, hedefleme de yok.
        return f"http://{gateway}"

    oturum = oturum or secrets.token_hex(OTURUM_UZUNLUK // 2)
    # Kullanici adi __cr. tasiyorsa saglayici DataImpulse demektir; ad
    # taninmasa da bicim buradan duzeltilir.
    if bicim == "decodo" and "__cr." in kullanici.lower():
        bicim = "dataimpulse"
    if bicim == "geonode":
        return _geonode(gateway, kullanici, sifre, ulke, geo_slug, oturum)
    if bicim == "dataimpulse":
        return _dataimpulse(gateway, kullanici, sifre, ulke, geo_slug, oturum)

    # Taban kullanici adi ulkeyi zaten tasiyorsa ulke eki yazilmaz.
    ulke_eki = ""
    if ulke and f"-country-{ulke.lower()}" not in kullanici.lower():
        ulke_eki = f"-country-{ulke.lower()}"
    kalip = BICIMLER.get(bicim, BICIMLER["decodo"])
    ad = kalip.format(
        k=kullanici,
        ulke=ulke_eki,
        city=f"-city-{geo_slug}" if geo_slug else "",
        s=oturum,
    )
    return f"http://{ad}:{sifre}@{gateway}"


def maskele(proxy: str | None) -> str:
    """Sifreyi gizler.

    Args:
        proxy: Ham proxy dizesi.

    Returns:
        Sifresi yildizlanmis dize.
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
