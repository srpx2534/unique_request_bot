#!/usr/bin/env bash
# Geliştirme ve sunucu kurulumu (Linux).
# Şifreler .env'den okunur, bu dosyada gizli değer yoktur.
set -euo pipefail

cd "$(dirname "$0")/.."

# 1. Zorunlu değişkenler dolu mu
if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env oluşturuldu. Şunları doldur, sonra tekrar çalıştır:"
  echo "  MYSQL_PASSWORD  MYSQL_ROOT_PASSWORD  WORKER_TOKEN"
  exit 0
fi
for anahtar in MYSQL_PASSWORD MYSQL_ROOT_PASSWORD WORKER_TOKEN; do
  deger=$(grep -E "^\s*${anahtar}\s*=" .env | head -1 | cut -d= -f2- | tr -d '[:space:]')
  [ -n "$deger" ] || { echo ".env içinde ${anahtar} boş." >&2; exit 1; }
done

# 2. Python 3.12
PYBIN=""
for aday in python3.12 python3; do
  if command -v "$aday" >/dev/null 2>&1 && "$aday" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'; then
    PYBIN="$aday"; break
  fi
done
[ -n "$PYBIN" ] || { echo "Python 3.12 bulunamadı." >&2; exit 1; }

[ -d .venv ] || "$PYBIN" -m venv .venv
PY=".venv/bin/python"

"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt
npm install

# 3. Servisler
docker compose up -d

# 4. MySQL sağlıklı olana kadar bekle
echo "MySQL bekleniyor..."
kimlik=$(docker compose ps -q mysql)
for _ in $(seq 1 60); do
  durum=$(docker inspect --format '{{.State.Health.Status}}' "$kimlik" 2>/dev/null || echo "yok")
  [ "$durum" = "healthy" ] && break
  sleep 2
done
[ "$durum" = "healthy" ] || { echo "MySQL sağlıklı duruma gelmedi." >&2; exit 1; }

# 5. Şema, kullanıcı, yetki
"$PY" tools/bootstrap.py

# 6. Tablolar ve seed
"$PY" tools/migrate.py --status
"$PY" tools/migrate.py
"$PY" tools/seed.py

# 7. Doğrulama
docker compose exec -T mysql sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT COUNT(*) AS il, COUNT(uule) AS uule_dolu FROM geo;"'
echo "Kurulum bitti."