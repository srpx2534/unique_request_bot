"""Olcum-B kanali testleri (35)."""

from __future__ import annotations

import json

from worker import olcum_b


class _Imlec:
    def __init__(self, kuyruk: list) -> None:
        self.kuyruk = list(kuyruk)
        self.calismalar: list[tuple] = []
        self.lastrowid = 99

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametre=None):
        self.calismalar.append((" ".join(sql.split()), tuple(parametre or ())))

    def fetchone(self):
        return self.kuyruk.pop(0) if self.kuyruk else None


class _Baglanti:
    def __init__(self, kuyruk: list) -> None:
        self.imlec = _Imlec(kuyruk)
        self.commit_sayisi = 0

    def cursor(self):
        return self.imlec

    def commit(self) -> None:
        self.commit_sayisi += 1

    def close(self) -> None:
        pass


def test_jar_cozer() -> None:
    ham = json.dumps([{"ad": "a", "deger": "1", "domain": ".google.com"}])
    assert olcum_b._jar_coz(ham)[0]["ad"] == "a"


def test_bozuk_jar_bos_doner() -> None:
    assert olcum_b._jar_coz("bozuk") == []
    assert olcum_b._jar_coz("[1, 2]") == []

def test_profil_yoksa_hata_doner(monkeypatch) -> None:
    monkeypatch.setattr(olcum_b, "profil_al", lambda *_a: None)
    sonuc = olcum_b.olcum_b_yap("a", "a.com", 34)
    assert sonuc["result"] == "error"
    assert sonuc["mesaj"] == "profil yok"
    assert sonuc["channel"] == "post_click"


def test_saglayici_yoksa_profil_uretilmez(monkeypatch) -> None:
    baglanti = _Baglanti([None, None])
    monkeypatch.setattr(olcum_b, "_baglan", lambda: baglanti)
    assert olcum_b.profil_al(34) is None


def test_saglayici_varsa_profil_uretilir(monkeypatch) -> None:
    baglanti = _Baglanti([None, (5,)])
    monkeypatch.setattr(olcum_b, "_baglan", lambda: baglanti)
    monkeypatch.setattr(olcum_b.fingerprint, "profil_sec", lambda mobil=False: "chrome124")
    monkeypatch.setattr(olcum_b.fingerprint, "ua", lambda _p: "UA")

    profil = olcum_b.profil_al(34)
    assert profil["id"] == 99
    assert profil["ja3_profile"] == "chrome124"


def test_hedef_bulunursa_tiklanir_ve_pozisyon_yazilir(monkeypatch) -> None:
    profil = {"id": 1, "ja3_profile": "chrome124", "jar": "[]"}
    monkeypatch.setattr(olcum_b, "profil_al", lambda *_a: profil)
    guncellenen: list = []
    monkeypatch.setattr(olcum_b, "profil_guncelle", lambda pid, _o: guncellenen.append(pid))
    monkeypatch.setattr(olcum_b.serp, "serp_getir_html", lambda *a, **k: {
        "result": "ok", "url": "https://www.google.com/search?q=a",
        "organik": [{"position": 3, "link": "https://a.com/x"}]})
    tiklanan: list = []
    monkeypatch.setattr(olcum_b.click, "tikla", lambda url, *_a: (
        tiklanan.append(url) or {"result": "ok", "mesaj": ""}))

    sonuc = olcum_b.olcum_b_yap("a", "a.com", 34)
    assert sonuc["rank"] == 3
    assert sonuc["result"] == "ok"
    assert tiklanan == ["https://a.com/x"]
    assert guncellenen == [1]


def test_hedef_yoksa_tiklanmaz(monkeypatch) -> None:
    monkeypatch.setattr(olcum_b, "profil_al", lambda *_a: {
        "id": 1, "ja3_profile": "chrome124", "jar": "[]"})
    monkeypatch.setattr(olcum_b, "profil_guncelle", lambda *_a: None)
    monkeypatch.setattr(olcum_b.serp, "serp_getir_html", lambda *a, **k: {
        "result": "not_found", "url": None, "organik": []})
    tiklanan: list = []
    monkeypatch.setattr(olcum_b.click, "tikla", lambda *a, **k: tiklanan.append(1) or {"result": "ok"})

    sonuc = olcum_b.olcum_b_yap("a", "yok.com", 34)
    assert sonuc["rank"] is None
    assert tiklanan == []

def test_basarili_olcum_pozisyon_yazar(monkeypatch) -> None:
    monkeypatch.setattr(olcum_b, "profil_al", lambda *_a: {
        "id": 1, "ja3_profile": "chrome124", "jar": "[]"})
    monkeypatch.setattr(olcum_b, "profil_guncelle", lambda *_a: None)
    monkeypatch.setattr(olcum_b.serp, "serp_getir_html", lambda *a, **k: {
        "result": "ok", "url": "u", "organik": [{"position": 2, "link": "https://a.com/x"}]})
    monkeypatch.setattr(olcum_b.click, "tikla", lambda *a, **k: {"result": "ok"})
    yazilan: list = []
    monkeypatch.setattr(olcum_b, "_pozisyon_yaz", lambda kid, rank: yazilan.append((kid, rank)))

    olcum_b.olcum_b_yap("a", "a.com", 34, kelime_id=8)
    assert yazilan == [(8, 2)]


def test_hedefsiz_olcum_pozisyon_yazmaz(monkeypatch) -> None:
    monkeypatch.setattr(olcum_b, "profil_al", lambda *_a: {
        "id": 1, "ja3_profile": "chrome124", "jar": "[]"})
    monkeypatch.setattr(olcum_b, "profil_guncelle", lambda *_a: None)
    monkeypatch.setattr(olcum_b.serp, "serp_getir_html", lambda *a, **k: {
        "result": "not_found", "url": None, "organik": []})
    yazilan: list = []
    monkeypatch.setattr(olcum_b, "_pozisyon_yaz", lambda kid, rank: yazilan.append(kid))

    olcum_b.olcum_b_yap("a", "yok.com", 34, kelime_id=8)
    assert yazilan == []