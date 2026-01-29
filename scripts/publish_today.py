#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_today.py
================
Creates/updates:
- logs/YYYY-MM-DD.md
- logs/index.json
- assets/diagnostic/YYYY-MM-DD_W63.png (optional copy)
- assets/diagnostic/YYYY-MM-DD_W252.png (optional copy)

Input:
--run_dir  outputs/theme_radar_full_YYYYMMDD_HHMMSS  (or any v3 output folder)

What it extracts:
- leaders_W63.csv latest row
- challengers_W63.csv latest k=2 and k=3 rows
- migration_W63.csv latest: top risers/fallers (topn)
- metrics_timeseries.csv latest W=63 risk line: s1,theta_v1,v_fr,score
- diagnostic_W63.png and diagnostic_W252.png if present

Usage:
python scripts/publish_today.py --run_dir outputs/theme_radar_full_YYYYMMDD_HHMMSS --topn 10 --tags "daily,full"
"""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
import pandas as pd

def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    return pd.read_csv(path, parse_dates=["date"])

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run_dir", type=str, required=True)
    p.add_argument("--topn", type=int, default=10)
    p.add_argument("--tags", type=str, default="", help="Comma-separated tags, e.g. daily,full")
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    repo = run_dir.resolve()
    # assume scripts/ is inside repo root; run_dir is relative to repo root
    # We find repo root by walking up until logs/ exists.
    root = Path.cwd()
    if not (root / "logs").exists():
        # try parent of run_dir if user ran inside outputs/
        root = run_dir.parent.parent if (run_dir.parent.parent / "logs").exists() else Path.cwd()

    leaders = read_csv(run_dir / "leaders_W63.csv").sort_values("date")
    latest_date = leaders["date"].iloc[-1]
    dstr = str(latest_date.date())

    chall = read_csv(run_dir / "challengers_W63.csv").sort_values(["date","k"])
    ch2 = chall[(chall["date"]==latest_date) & (chall["k"]==2)].tail(1)
    ch3 = chall[(chall["date"]==latest_date) & (chall["k"]==3)].tail(1)

    mig = read_csv(run_dir / "migration_W63.csv").sort_values("date")
    mig_last = mig[mig["date"]==latest_date]
    if len(mig_last)==0:
        mig_last = mig.tail(1)
    slopes = mig_last.drop(columns=["date"]).iloc[0].sort_values(ascending=False)
    top_risers = slopes.head(args.topn)
    top_fallers = slopes.tail(args.topn)

    metrics = pd.read_csv(run_dir / "metrics_timeseries.csv", parse_dates=["date"]).sort_values(["date","W"])
    m63 = metrics[metrics["W"]==63].tail(1).iloc[0]

    # Copy diagnostics if exist
    diag_dir = root / "assets" / "diagnostic"
    diag_dir.mkdir(parents=True, exist_ok=True)
    for W in (63, 252):
        src = run_dir / f"diagnostic_W{W}.png"
        if src.exists():
            shutil.copyfile(src, diag_dir / f"{dstr}_W{W}.png")

    # Build markdown
    md = []
    md.append(f"# Theme Radar Daily Brief — {dstr}")
    md.append("")
    if (diag_dir / f"{dstr}_W63.png").exists():
        md.append(f"![diagnostic W63](../assets/diagnostic/{dstr}_W63.png)")
        md.append("")
    md.append("## Leaders (v1) — W=63")
    last_leader = leaders.tail(1).iloc[0]
    md.append(f"- **{last_leader['leader1']}** ({last_leader['leader1_share']})")
    md.append(f"- {last_leader['leader2']} ({last_leader['leader2_share']})")
    md.append(f"- {last_leader['leader3']} ({last_leader['leader3_share']})")
    md.append("")
    md.append("## Challengers — W=63")
    if len(ch2):
        r = ch2.iloc[0]
        md.append(f"**v2:** {r['ch1']} ({r['ch1_share']}), {r['ch2']} ({r['ch2_share']}), {r['ch3']} ({r['ch3_share']})")
    if len(ch3):
        r = ch3.iloc[0]
        md.append(f"**v3:** {r['ch1']} ({r['ch1_share']}), {r['ch2']} ({r['ch2_share']}), {r['ch3']} ({r['ch3_share']})")
    md.append("")
    md.append("## Migration (20D slope) — W=63")
    md.append("**Top risers:**")
    for k,v in top_risers.items():
        md.append(f"- {k}: {v}")
    md.append("")
    md.append("**Top fallers:**")
    for k,v in top_fallers.items():
        md.append(f"- {k}: {v}")
    md.append("")
    md.append("## Risk line (W=63)")
    md.append(f"- s1: {m63['s1']}")
    md.append(f"- theta_v1: {m63['theta_v1']}")
    md.append(f"- v_FR: {m63['v_fr']}")
    md.append(f"- single_axis_score: {m63['single_axis_score']}")
    md.append("")

    log_path = root / "logs" / f"{dstr}.md"
    log_path.write_text("\n".join(md), encoding="utf-8")

    # Update index.json
    idx_path = root / "logs" / "index.json"
    idx = {"items": []}
    if idx_path.exists():
        idx = json.loads(idx_path.read_text(encoding="utf-8") or '{"items":[]}')
    items = idx.get("items", [])

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    # Build record
    rec = {
        "date": dstr,
        "leader1": str(last_leader["leader1"]),
        "leader1_share": float(last_leader["leader1_share"]),
        "leader2": str(last_leader["leader2"]),
        "leader2_share": float(last_leader["leader2_share"]),
        "leader3": str(last_leader["leader3"]),
        "leader3_share": float(last_leader["leader3_share"]),
        "ch2_1": str(ch2.iloc[0]["ch1"]) if len(ch2) else "",
        "ch2_1_share": float(ch2.iloc[0]["ch1_share"]) if len(ch2) else None,
        "ch2_2": str(ch2.iloc[0]["ch2"]) if len(ch2) else "",
        "ch2_2_share": float(ch2.iloc[0]["ch2_share"]) if len(ch2) else None,
        "ch2_3": str(ch2.iloc[0]["ch3"]) if len(ch2) else "",
        "ch2_3_share": float(ch2.iloc[0]["ch3_share"]) if len(ch2) else None,
        "ch3_1": str(ch3.iloc[0]["ch1"]) if len(ch3) else "",
        "ch3_1_share": float(ch3.iloc[0]["ch1_share"]) if len(ch3) else None,
        "ch3_2": str(ch3.iloc[0]["ch2"]) if len(ch3) else "",
        "ch3_2_share": float(ch3.iloc[0]["ch2_share"]) if len(ch3) else None,
        "ch3_3": str(ch3.iloc[0]["ch3"]) if len(ch3) else "",
        "ch3_3_share": float(ch3.iloc[0]["ch3_share"]) if len(ch3) else None,
        "s1": float(m63["s1"]),
        "theta_v1": float(m63["theta_v1"]),
        "v_fr": float(m63["v_fr"]),
        "single_axis_score": float(m63["single_axis_score"]),
        "tags": tags
    }

    # replace or insert
    items = [x for x in items if x.get("date") != dstr]
    items.append(rec)
    items.sort(key=lambda x: x["date"])
    idx["items"] = items
    idx_path.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Wrote:", log_path)
    print("Updated:", idx_path)
    print("Copied diagnostics to:", diag_dir)

if __name__ == "__main__":
    main()
