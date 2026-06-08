# Theme Radar Log (Static Site)

This repo hosts a simple static website that lists your daily Theme Radar briefs.

## Workflow
1) Run your radar script (e.g., macro_theme_radar_v3_full.py) to generate a run folder:
   outputs/theme_radar_full_YYYYMMDD_HHMMSS/

2) Generate a daily markdown log + update the site index:
   python scripts/publish_today.py --run_dir outputs/theme_radar_full_YYYYMMDD_HHMMSS

3) Commit & push. GitHub Pages (via Actions) deploys automatically.

## Daily GitHub Actions publish
This repo includes `.github/workflows/daily-radar-log.yml`, which runs every day
around 12:15 PM America/New_York, commits the generated daily log, pushes it to
`main`, and deploys GitHub Pages.

Before enabling it:
1) Commit the radar generator at `scripts/macro_theme_radar_v3_full.py`, or edit
   `RADAR_SCRIPT` in the workflow to point at the correct in-repo path.
2) Add any Python packages required by the radar generator to `requirements.txt`.
   `pandas` is already listed because `scripts/publish_today.py` uses it.
3) In GitHub repo settings, ensure Actions can write to the repository:
   Settings -> Actions -> General -> Workflow permissions -> Read and write.

## Optional: On-chain anchoring
Use scripts/anchor_hash.py to compute a SHA256 fingerprint for a day's log bundle
(markdown + diagnostic images). You can record the hash anywhere (commit message,
a public gist, or a blockchain transaction) to prove integrity later.
