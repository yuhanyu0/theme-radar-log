<# 
weekly_publish.ps1
==================
One-command weekly rollup + commit + push for Theme Radar Log site.

What it does:
1) Runs weekly_anchor_rollup.py --thisweek
2) Finds the newest logs/weekly_*.md file to determine YYYY-WWW
3) git add/commit/push with message: "weekly anchor: YYYY-WWW"

Usage:
  powershell -ExecutionPolicy Bypass -File C:\Users\80686\Desktop\theme_radar_log_site_template\weekly_publish.ps1

Optional:
  -PythonExe "C:/Python313/python.exe"
#>

param(
  [string]$PythonExe = "C:/Python313/python.exe"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "RepoRoot: $RepoRoot"

# 1) Generate weekly rollup for current ISO week
& $PythonExe "scripts/weekly_anchor_rollup.py" --thisweek

# 2) Determine week label from newest weekly file
$LatestWeekly = Get-ChildItem -Path (Join-Path $RepoRoot "logs") -Filter "weekly_*.md" | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $LatestWeekly) {
  throw "No weekly_*.md found under logs/. Did weekly_anchor_rollup.py run successfully?"
}
$WeekLabel = $LatestWeekly.BaseName.Replace("weekly_", "")

# 3) Commit & push if changes exist
git add .

$Status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($Status)) {
  Write-Host "No changes to commit. Done."
  exit 0
}

$Msg = "weekly anchor: $WeekLabel"
git commit -m "$Msg"
git push

Write-Host "Committed & pushed: $Msg"
