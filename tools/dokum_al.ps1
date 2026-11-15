# Istenen dosyalari tek dokumde toplar; konsola ve docs/dokum_<damga>.md'ye yazar.
# Kullanim: .\tools\dokum_al.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$kok = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
Set-Location $kok

$yollar = @(
  'docs/CONTRACT.md'
  'docs/EKSIKLER.md'
  'docs/DURUM.md'
  'src/server/panel_uyari.ts'
  'src/server/kelime_liste.ts'
  'src/web/sayfa/uyarilar.tsx'
  'src/server/panel_ayar.ts'
  'src/server/panel_saglayici.ts'
  'src/server/panel.ts'
  'db/migrations/001_schema.sql'
  'db/migrations/003_geo.sql'
  'tools/bootstrap.py'
  'tools/serp_dene.py'
  'tools/tls_check.py'
  'src/server/cerez/aktarim.ts'
)

$utf8 = New-Object System.Text.UTF8Encoding($false)
$damga = Get-Date -Format 'yyyyMMdd-HHmmss'
$cikti = Join-Path $kok "docs/dokum_$damga.md"
$parcalar = New-Object System.Collections.Generic.List[string]
$bas = (git rev-parse --short HEAD 2>$null)
$parcalar.Add("# Dokum $damga · HEAD $bas")
foreach ($y in $yollar) {
  $tam = Join-Path $kok $y
  $parcalar.Add('')
  $parcalar.Add("===== DOSYA: $y =====")
  if (-not (Test-Path -LiteralPath $tam)) { $parcalar.Add('YOK'); continue }
  $icerik = [System.IO.File]::ReadAllText($tam)
  $satir = ($icerik -split "`n").Count
  $parcalar.Add(("satir: {0} · bayt: {1}" -f $satir, $icerik.Length))
  if ($icerik.Length -gt 60000) { $parcalar.Add('UYARI: 60 KB uzeri') }
  $parcalar.Add($icerik.TrimEnd())
}
$parcalar.Add('')
$parcalar.Add('===== SON =====')
[System.IO.File]::WriteAllText($cikti, ($parcalar -join "`r`n"), $utf8)
Write-Host ("dokum yazildi: {0} ({1} bayt)" -f $cikti, ([System.IO.FileInfo]$cikti).Length)
Write-Host '--- basliyor ---'
Get-Content -Raw -Encoding UTF8 -LiteralPath $cikti