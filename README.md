# Theme Radar Log (Static Site)

This repo hosts a simple static website that lists your daily Theme Radar briefs.

## Workflow
1) Run your radar script (e.g., macro_theme_radar_v3_full.py) to generate a run folder:
   outputs/theme_radar_full_YYYYMMDD_HHMMSS/

2) Generate a daily markdown log + update the site index:
   python scripts/publish_today.py --run_dir outputs/theme_radar_full_YYYYMMDD_HHMMSS

3) Commit & push. GitHub Pages (via Actions) deploys automatically.

## Optional: On-chain anchoring
Use scripts/anchor_hash.py to compute a SHA256 fingerprint for a day's log bundle
(markdown + diagnostic images). You can record the hash anywhere (commit message,
a public gist, or a blockchain transaction) to prove integrity later.
