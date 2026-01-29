<# 
daily_publish.ps1 (v2)
======================
One-command daily publish for Theme Radar Log site, with hash anchored in commit message.

What it does:
1) publish_today.py -> creates logs/YYYY-MM-DD.md, updates logs/index.json, copies diagnostics
2) anchor_hash.py   -> computes BUNDLE_ROOT_SHA256 for that date
3) git add/commit/push with commit message: "log: YYYY-MM-DD | sha256:<BUNDLE_ROOT_SHA256>"

Usage:
  powershell -ExecutionPolicy Bypass -File C:\Users\80686\Desktop\theme_radar_log_site_template\daily_publish.ps1 `
    -RunDir "C:\Users\80686\outputs\theme_radar_full_YYYYMMDD_HHMMSS" `
    -TopN 10 `
    -Tags "daily,full"

#>

param(
  [Parameter(Mandatory=$true)]
  [string]$RunDir,

  [int]$TopN = 10,

  [string]$Tags = "daily,full",

  # Pin a specific python executable if you like:
  [string]$PythonExe = "C:/Python313/python.exe"
)

$ErrorActionPreference = "Stop"

# Repo root = folder where this .ps1 lives
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "RepoRoot: $RepoRoot"
Write-Host "RunDir:   $RunDir"
Write-Host "TopN:     $TopN"
Write-Host "Tags:     $Tags"

# 1) Publish today's markdown + update index + copy diagnostics
& $PythonExe "scripts/publish_today.py" --run_dir "$RunDir" --topn $TopN --tags "$Tags"
Write-Host "publish_today.py done."

# Stage all changes
git add .

# If no changes, exit cleanly
$Status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($Status)) {
  Write-Host "No changes to commit. Done."
  exit 0
}

# Identify date from newest log filename
$LatestLog = Get-ChildItem -Path (Join-Path $RepoRoot "logs") -Filter "*.md" | Sort-Object LastWriteTime | Select-Object -Last 1
$DateStr = [System.IO.Path]::GetFileNameWithoutExtension($LatestLog.Name)

# 2) Compute bundle root hash for integrity anchoring
# anchor_hash.py prints a line: "BUNDLE_ROOT_SHA256: <hash>"
$AnchorOut = & $PythonExe "scripts/anchor_hash.py" --date "$DateStr"
$HashLine = $AnchorOut | Where-Object { $_ -match "^BUNDLE_ROOT_SHA256:" } | Select-Object -Last 1
if (-not $HashLine) {
  Write-Host "[warn] Could not find BUNDLE_ROOT_SHA256 in anchor_hash output. Committing without hash."
  $Msg = "log: $DateStr"
} else {
  $Hash = ($HashLine -split ":",2)[1].Trim()
  $Msg = "log: $DateStr | sha256:$Hash"
}

# 3) Commit & push
git commit -m "$Msg"
git push

Write-Host "Committed & pushed: $Msg"
