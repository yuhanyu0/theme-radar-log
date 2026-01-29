<# 
daily_run_and_publish.ps1 (final stable)
========================================
One-command: run FULL theme radar + publish to website repo.

Fixes:
- Force radar outputs to a single global outdir: C:\Users\80686\outputs
- After radar finishes, pick newest folder under that outdir: theme_radar_full_*
- Call daily_publish.ps1 to publish, commit, push

Usage:
  powershell -ExecutionPolicy Bypass -File C:\Users\80686\Desktop\theme_radar_log_site_template\daily_run_and_publish.ps1

Optional overrides:
  -RadarScript "C:\Users\80686\Downloads\macro_theme_radar_v3_full.py"
  -PythonExe "C:/Python313/python.exe"
  -Corr "sample"  (or "lw" if scikit-learn installed)
  -Windows "126,63"
  -MinCoverage 0.60
  -Tags "daily,full"
  -OutDir "C:\Users\80686\outputs"
#>

param(
  [string]$PythonExe = "C:/Python313/python.exe",
  [string]$RadarScript = "C:\Users\80686\Downloads\macro_theme_radar_v3_full.py",
  [string]$Corr = "sample",
  [string]$Windows = "126,63",
  [double]$MinCoverage = 0.60,
  [int]$TopN = 10,
  [string]$Tags = "daily,full",
  [string]$OutDir = "C:\Users\80686\outputs"
)

$ErrorActionPreference = "Stop"

# Repo root = folder where this script lives
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "RepoRoot:     $RepoRoot"
Write-Host "PythonExe:    $PythonExe"
Write-Host "RadarScript:  $RadarScript"
Write-Host "Corr:         $Corr"
Write-Host "Windows:      $Windows"
Write-Host "MinCoverage:  $MinCoverage"
Write-Host "OutDir:       $OutDir"
Write-Host "Tags:         $Tags"
Write-Host ""

# Ensure OutDir exists
if (-not (Test-Path $OutDir)) {
  New-Item -ItemType Directory -Path $OutDir | Out-Null
}

# 1) Run radar (no output capture)
$radarArgs = @(
  "$RadarScript",
  "--corr", "$Corr",
  "--windows", "$Windows",
  "--min_coverage", "$MinCoverage",
  "--outdir", "$OutDir"
)

Write-Host "Running radar..." -ForegroundColor Cyan
& $PythonExe @radarArgs
Write-Host "Radar finished." -ForegroundColor Cyan

# 2) Determine run directory from OutDir (robust)
$Newest = Get-ChildItem $OutDir -Directory -Filter "theme_radar_full_*" | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $Newest) {
  throw "No '$OutDir\theme_radar_full_*' folder found after radar run."
}
$RunDir = $Newest.FullName

Write-Host ""
Write-Host "Using newest run dir: $RunDir" -ForegroundColor Green
Write-Host ""

# 3) Publish (daily_publish.ps1 must be in repo root)
$DailyPublish = Join-Path $RepoRoot "daily_publish.ps1"
if (-not (Test-Path $DailyPublish)) {
  throw "Missing daily_publish.ps1 in repo root. Create it (e.g., copy daily_publish_with_hash.ps1 to daily_publish.ps1)."
}

Write-Host "Publishing to site..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File $DailyPublish -RunDir "$RunDir" -TopN $TopN -Tags "$Tags" -PythonExe "$PythonExe"

Write-Host ""
Write-Host "Done: radar + publish complete." -ForegroundColor Green
