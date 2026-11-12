"""Tarayıcı parmak izi profilleri.

curl_cffi'nin impersonate değerlerini taşır. Worker her istekte buradan
rastgele bir profil seçer; TLS/JA3 ve başlıklar o profile ait olduğu için
User-Agent elle yazılmaz, impersonate belirler. Böylece art arda aynı
parmak izi tekrarlanmaz (C4).

Kullanım: worker/serp.py, worker/click.py, tools/tls_check.py.
"""

from __future__ import annotations

import random

# Desteklenen profiller. Hepsi curl_cffi 0.7.4 içinde tanımlıdır.
# Sürüm düşük tutulmaz: eski Chrome profilleri TLS'te ayırt edilebilir.
PROFILLER: tuple[str, ...] = (
    "chrome124",
    "chrome120",
    "chrome116",
    "chrome110",
    "edge101",
    "safari17_0",
)

# Profil başına beklenen UA. Yalnızca log ve doğrulama içindir; istekte
# curl_cffi kendi UA'sını yazar, buradaki değer onunla aynı olmalıdır.
BEKLENEN_UA: dict[str, str] = {
    "chrome124": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "chrome120": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "chrome116": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "chrome110": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "edge101": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36 "
               "Edg/101.0.1210.47",
    "safari17_0": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                  "Safari/605.1.15",
}


def profil_sec(haric: str | None = None) -> str:
    """Rastgele bir profil döndürür.

    Args:
        haric: Bir önceki istekte kullanılan profil. Aynı profilin arka
            arkaya gelmemesi için dışarıda bırakılır.

    Returns:
        Profil adı. Havuz boşalmaz; en kötü ihtimalle haric yok sayılır.
    """
    havuz = [p for p in PROFILLER if p != haric]
    if not havuz:
        havuz = list(PROFILLER)
    return random.choice(havuz)


def ua(profil: str) -> str:
    """Profilin beklenen User-Agent değerini döndürür.

    Args:
        profil: PROFILLER içindeki bir ad.

    Returns:
        UA metni. Tanınmayan profil için boş metin.
    """
    return BEKLENEN_UA.get(profil, "")


def dogrula(profil: str) -> None:
    """Profil adı tanımlı mı diye bakar, değilse hata yükseltir.

    Args:
        profil: Denetlenecek ad.

    Raises:
        ValueError: Profil listede yoksa.
    """
    if profil not in PROFILLER:
        raise ValueError(f"tanımsız profil: {profil} · geçerli: {', '.join(PROFILLER)}")