#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_today_with_interpretation_v5.py
=======================================

Adds to index.json:
watchlist, hedge_note, regime,
vfr_pct / theta_pct / s1_pct / score_pct (percentiles within W=63 history),
bundle_root_sha256.

This is intended as a drop-in replacement for scripts/publish_today.py.

Run from repo root:
  python scripts/publish_today.py --run_dir <RUN_DIR> --topn 10 --tags "daily,full"
"""

from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    return pd.read_csv(path, parse_dates=["date"])


def percentile_of_last(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 5:
        return float("nan")
    last = s.iloc[-1]
    return float((s <= last).mean())


def classify_regime(vfr_p: float, s1_p: float, score_p: float) -> str:
    if pd.notna(vfr_p) and vfr_p >= 0.90:
        return "structure_rewrite"
    if pd.notna(s1_p) and pd.notna(score_p) and s1_p >= 0.90 and score_p >= 0.90:
        return "single_axis_squeeze"
    return "theme_migration"


def compute_bundle_root_sha256(root: Path, dstr: str) -> str | None:
    import hashlib

    def sha256_file(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    md = root / "logs" / f"{dstr}.md"
    w63 = root / "assets" / "diagnostic" / f"{dstr}_W63.png"
    w252 = root / "assets" / "diagnostic" / f"{dstr}_W252.png"

    parts = []
    for p in (md, w63, w252):
        if p.exists():
            parts.append(sha256_file(p))
    if not parts:
        return None

    H = hashlib.sha256()
    for h in parts:
        H.update(bytes.fromhex(h))
    return H.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run_dir", type=str, required=True)
    p.add_argument("--topn", type=int, default=10)
    p.add_argument("--tags", type=str, default="", help="Comma-separated tags")
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    root = Path.cwd()

    # W=63 extraction
    leaders63 = read_csv(run_dir / "leaders_W63.csv").sort_values("date")
    latest_date = leaders63["date"].iloc[-1]
    dstr = str(latest_date.date())
    L63 = leaders63.tail(1).iloc[0]

    chall63 = read_csv(run_dir / "challengers_W63.csv").sort_values(["date", "k"])
    ch2_63 = chall63[(chall63["date"] == latest_date) & (chall63["k"] == 2)].tail(1)
    ch3_63 = chall63[(chall63["date"] == latest_date) & (chall63["k"] == 3)].tail(1)

    mig63 = read_csv(run_dir / "migration_W63.csv").sort_values("date")
    mig_last = mig63[mig63["date"] == latest_date]
    if len(mig_last) == 0:
        mig_last = mig63.tail(1)
    slopes = mig_last.drop(columns=["date"]).iloc[0].sort_values(ascending=False)
    top_risers = slopes.head(args.topn)
    top_fallers = slopes.tail(args.topn)

    metrics = pd.read_csv(run_dir / "metrics_timeseries.csv", parse_dates=["date"]).sort_values(["date", "W"])
    m63 = metrics[metrics["W"] == 63].copy()
    if len(m63) == 0:
        raise RuntimeError("No W=63 rows in metrics_timeseries.csv")
    last63 = m63.tail(1).iloc[0]

    vfr_pct = percentile_of_last(m63["v_fr"])
    s1_pct = percentile_of_last(m63["s1"])
    score_pct = percentile_of_last(m63["single_axis_score"])
    theta_pct = percentile_of_last(m63["theta_v1"])

    regime = classify_regime(vfr_pct, s1_pct, score_pct)

    # Copy diagnostics if exist
    diag_dir = root / "assets" / "diagnostic"
    diag_dir.mkdir(parents=True, exist_ok=True)
    for W in (63, 252):
        src = run_dir / f"diagnostic_W{W}.png"
        if src.exists():
            shutil.copyfile(src, diag_dir / f"{dstr}_W{W}.png")

    # Actionable one-liners
    v2_top1 = str(ch2_63.iloc[0]["ch1"]) if len(ch2_63) else ""
    watch_risers = [k.replace("axis_", "") for k in top_risers.index[:5]]
    watchlist = f"Tomorrow watchlist: {', '.join(watch_risers)}" + (f" + v2_top1={v2_top1}" if v2_top1 else "")

    hedge_note = "Hedge note: normal correlation stability."
    if pd.notna(vfr_pct) and vfr_pct >= 0.90 and pd.notna(theta_pct) and theta_pct >= 0.75:
        hedge_note = "Hedge note: v_FR high + theta high → correlation structure unstable; diversify hedges / reduce reliance on static correlations."
    elif pd.notna(vfr_pct) and vfr_pct >= 0.90:
        hedge_note = "Hedge note: v_FR high → structure is re-writing; treat correlation assumptions as fragile."

    # Markdown build
    md = []
    md.append(f"# Theme Radar Daily Brief — {dstr}")
    md.append("")
    if (diag_dir / f"{dstr}_W63.png").exists():
        md.append(f"![diagnostic W63](../assets/diagnostic/{dstr}_W63.png)")
        md.append("")
    md.append("## Leaders (v1) — W=63")
    md.append(f"- **{L63['leader1']}** ({L63['leader1_share']})")
    md.append(f"- {L63['leader2']} ({L63['leader2_share']})")
    md.append(f"- {L63['leader3']} ({L63['leader3_share']})")
    md.append("")
    md.append("## Challengers — W=63")
    if len(ch2_63):
        r = ch2_63.iloc[0]
        md.append(f"**v2:** {r['ch1']} ({r['ch1_share']}), {r['ch2']} ({r['ch2_share']}), {r['ch3']} ({r['ch3_share']})")
    if len(ch3_63):
        r = ch3_63.iloc[0]
        md.append(f"**v3:** {r['ch1']} ({r['ch1_share']}), {r['ch2']} ({r['ch2_share']}), {r['ch3']} ({r['ch3_share']})")
    md.append("")
    md.append("## Migration (20D slope) — W=63")
    md.append("**Top risers:**")
    for k, v in top_risers.items():
        md.append(f"- {k}: {v}")
    md.append("")
    md.append("**Top fallers:**")
    for k, v in top_fallers.items():
        md.append(f"- {k}: {v}")
    md.append("")
    md.append("## Risk line (W=63)")
    md.append(f"- s1: {last63['s1']}")
    md.append(f"- theta_v1: {last63['theta_v1']}")
    md.append(f"- v_FR: {last63['v_fr']}")
    md.append(f"- single_axis_score: {last63['single_axis_score']}")
    md.append("")
    md.append("## Interpretation")
    md.append(f"**Regime:** `{regime}`")
    md.append("")
    md.append(f"- Action: {watchlist}")
    md.append(f"- Action: {hedge_note}")
    md.append("")
    md.append(f"- Percentiles (W=63 history): vfr_pct={vfr_pct:.2f}, theta_pct={theta_pct:.2f}, s1_pct={s1_pct:.2f}, score_pct={score_pct:.2f}.")
    md.append("")

    log_path = root / "logs" / f"{dstr}.md"
    log_path.write_text("\n".join(md), encoding="utf-8")

    bundle = compute_bundle_root_sha256(root, dstr)
    if bundle:
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n---\n")
            f.write(f"**BUNDLE_ROOT_SHA256:** `{bundle}`\n")

    # index.json update
    idx_path = root / "logs" / "index.json"
    idx = {"items": []}
    if idx_path.exists():
        idx = json.loads(idx_path.read_text(encoding="utf-8") or '{"items":[]}')
    items = idx.get("items", [])

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if regime not in tags:
        tags.append(regime)

    rec = {
        "date": dstr,
        "leader1": str(L63["leader1"]), "leader1_share": float(L63["leader1_share"]),
        "leader2": str(L63["leader2"]), "leader2_share": float(L63["leader2_share"]),
        "leader3": str(L63["leader3"]), "leader3_share": float(L63["leader3_share"]),
        "ch2_1": str(ch2_63.iloc[0]["ch1"]) if len(ch2_63) else "",
        "ch2_1_share": float(ch2_63.iloc[0]["ch1_share"]) if len(ch2_63) else None,
        "ch2_2": str(ch2_63.iloc[0]["ch2"]) if len(ch2_63) else "",
        "ch2_2_share": float(ch2_63.iloc[0]["ch2_share"]) if len(ch2_63) else None,
        "ch2_3": str(ch2_63.iloc[0]["ch3"]) if len(ch2_63) else "",
        "ch2_3_share": float(ch2_63.iloc[0]["ch3_share"]) if len(ch2_63) else None,
        "ch3_1": str(ch3_63.iloc[0]["ch1"]) if len(ch3_63) else "",
        "ch3_1_share": float(ch3_63.iloc[0]["ch1_share"]) if len(ch3_63) else None,
        "ch3_2": str(ch3_63.iloc[0]["ch2"]) if len(ch3_63) else "",
        "ch3_2_share": float(ch3_63.iloc[0]["ch2_share"]) if len(ch3_63) else None,
        "ch3_3": str(ch3_63.iloc[0]["ch3"]) if len(ch3_63) else "",
        "ch3_3_share": float(ch3_63.iloc[0]["ch3_share"]) if len(ch3_63) else None,
        "s1": float(last63["s1"]),
        "theta_v1": float(last63["theta_v1"]),
        "v_fr": float(last63["v_fr"]),
        "single_axis_score": float(last63["single_axis_score"]),
        "watchlist": watchlist,
        "hedge_note": hedge_note,
        "regime": regime,
        "vfr_pct": float(vfr_pct) if pd.notna(vfr_pct) else None,
        "theta_pct": float(theta_pct) if pd.notna(theta_pct) else None,
        "s1_pct": float(s1_pct) if pd.notna(s1_pct) else None,
        "score_pct": float(score_pct) if pd.notna(score_pct) else None,
        "bundle_root_sha256": bundle,
        "tags": tags
    }

    items = [x for x in items if x.get("date") != dstr]
    items.append(rec)
    items.sort(key=lambda x: x["date"])
    idx["items"] = items
    idx_path.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Wrote:", log_path)
    print("Updated:", idx_path)
    print("Copied diagnostics to:", diag_dir)
    if bundle:
        print("BUNDLE_ROOT_SHA256:", bundle)


if __name__ == "__main__":
    main()
