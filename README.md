# unique_request_bot

Çok sunuculu request-burst motoru. Sözleşme: `docs/CONTRACT.md`.

## Kural: Windows'ta yaz, Linux'ta çalıştır

Kod Windows'ta yazılır, sunucuda Debian 12 üzerinde çalışır. Yol, satır sonu ve
kabuk kullanımı sözleşmenin §18 maddesine tabidir. Yerel MySQL ve Redis WSL2
içinde Docker ile ayağa kalkar, host'a kurulum yapılmaz.

## Yerel ortam

```bash
cp .env.example .env      # Windows: copy .env.example .env
python tools/gen_uule.py  # 81 il için uule üretir
docker compose up -d      # MySQL + Redis

# Çalışma zamanı
PyMySQL==1.1.1            # saf Python MySQL sürücüsü, Windows'ta derleme gerektirmez
python-dotenv==1.0.1      # .env yükleme

# Fetch katmanı (M2'de kullanılır, şimdi kurulur)
curl_cffi==0.7.4          # TLS/JA3 taklidi

# Test
pytest==8.3.3