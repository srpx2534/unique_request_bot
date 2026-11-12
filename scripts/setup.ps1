# Geliştirme makinesi kurulumu (Windows).
# Şifreler .env'den okunur, bu dosyada gizli değer yoktur.
# Yorumlayıcı yoksa veya bir adım düşerse betik durur.
# Docker varsa servisler ayağa kaldırılır, yoksa yerel MySQL kullanılır.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# 1. Zorunlu ortam değişkenleri dolu mu
$gerekli = @("MYSQL_PASSWORD", "WORKER_TOKEN")
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host ".env oluşturuldu. Şu alanları doldur, sonra betiği tekrar çalıştır:"
  $gerekli | ForEach-Object { Write-Host "  $_" }
  exit 0
}
$icerik = Get-Content .env
foreach ($anahtar in $gerekli) {
  $satir = $icerik | Where-Object { $_ -match "^\s*$anahtar\s*=" } | Select-Object -First 1
  $deger = if ($satir) { ($satir -split '=', 2)[1].Trim() } else { "" }
  if ([string]::IsNullOrWhiteSpace($deger)) { Write-Error ".env içinde $anahtar boş."; exit 1 }
}

# 2. Python 3.12+ yorumlayıcısını bul.
# stderr cmd /c ile susturulur; PowerShell 5.1 stderr'i hata kaydına çeviriyor.
$Adaylar = @(
  @{ Exe = "py";      Args = @("-3.14") },
  @{ Exe = "py";      Args = @("-3.13") },
  @{ Exe = "py";      Args = @("-3.12") },
  @{ Exe = "python";  Args = @() },
  @{ Exe = "python3"; Args = @() }
)

$Secili = $null
foreach ($aday in $Adaylar) {
  if (-not (Get-Command $aday.Exe -ErrorAction SilentlyContinue)) { continue }
  $parca = @($aday.Exe) + $aday.Args + @("-c", "import sys;print(sys.version_info[1])")
  $surum = & cmd /c "$($parca -join ' ') 2>nul"
  # Çıktı tek sayı olmalı ve 12 veya üstü olmalı.
  if ($LASTEXITCODE -eq 0 -and "$surum" -match "^\d+$" -and [int]"$surum" -ge 12) {
    $Secili = $aday
    Write-Host "Python bulundu: $($aday.Exe) $($aday.Args -join ' ') · 3.$surum"
    break
  }
}

if (-not $Secili) {
  Write-Error "Python 3.12 veya üstü bulunamadı. Kur: winget install -e --id Python.Python.3.12"
  exit 1
}

# 3. Sanal ortam
if (-not (Test-Path .venv)) {
  & $Secili.Exe @($Secili.Args) -m venv .venv
  if ($LASTEXITCODE -ne 0) { Write-Error "Sanal ortam oluşmadı."; exit 1 }
}
$Py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { Write-Error "Sanal ortam bulunamadı: $Py"; exit 1 }

# 4. Bağımlılıklar
& $Py -m pip install --upgrade pip; if ($LASTEXITCODE -ne 0) { exit 1 }
& $Py -m pip install -r requirements.txt; if ($LASTEXITCODE -ne 0) { exit 1 }
npm install; if ($LASTEXITCODE -ne 0) { exit 1 }

# 5. Servisler: Docker varsa ayağa kaldırılır, yoksa yerel MySQL kullanılır.
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker compose up -d; if ($LASTEXITCODE -ne 0) { exit 1 }
  Write-Host "MySQL bekleniyor..."
  $kimlik = (docker compose ps -q mysql).Trim()
  $durum = "yok"
  for ($i = 0; $i -lt 60; $i++) {
    $durum = docker inspect --format "{{.State.Health.Status}}" $kimlik 2>$null
    if ($durum -eq "healthy") { break }
    Start-Sleep -Seconds 2
  }
  if ($durum -ne "healthy") { Write-Error "MySQL sağlıklı duruma gelmedi."; exit 1 }
} else {
  Write-Host "Docker yok, yerel MySQL kullanılacak."
}

# 6. uule dosyası, şema, kullanıcı, yetki
& $Py tools/gen_uule.py; if ($LASTEXITCODE -ne 0) { exit 1 }
& $Py tools/bootstrap.py; if ($LASTEXITCODE -ne 0) { exit 1 }

# 7. Tablolar ve seed
& $Py tools/migrate.py --status; if ($LASTEXITCODE -ne 0) { exit 1 }
& $Py tools/migrate.py;          if ($LASTEXITCODE -ne 0) { exit 1 }
& $Py tools/seed.py;             if ($LASTEXITCODE -ne 0) { exit 1 }

# 8. Doğrulama
& $Py -c "from db import baglan; c=baglan(); k=c.cursor(); k.execute('SELECT COUNT(*), COUNT(uule) FROM geo'); print('geo dogrulama:', k.fetchone()); c.close()"
Write-Host "Kurulum bitti."