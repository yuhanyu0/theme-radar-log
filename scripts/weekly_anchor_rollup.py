#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly_anchor_rollup.py
=======================
Generate a weekly rollup file and a weekly root hash.

Inputs:
- logs/YYYY-MM-DD.md (each contains a line: **BUNDLE_ROOT_SHA256:** `<hash>`)

Outputs:
- logs/weekly_<YEAR>-W<WW>.md
- prints WEEKLY_ROOT_SHA256 to stdout

Weekly root = sha256(concat(bytes.fromhex(daily_hash)) in chronological order)

Usage:
  python scripts/weekly_anchor_rollup.py --year 2026 --week 5

For the current ISO week:
  python scripts/weekly_anchor_rollup.py --thisweek

Or for "last 7 days" ending today:
  python scripts/weekly_anchor_rollup.py --last7

Notes:
- This does not require git.
- You can commit the weekly file and (optionally) also record the weekly root on-chain.
"""

from __future__ import annotations
import argparse, hashlib, re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Tuple

HASH_RE = re.compile(r"BUNDLE_ROOT_SHA256:\s*`([0-9a-fA-F]{64})`")

def sha256_hex_bytes(hex_list: List[str]) -> str:
    H = hashlib.sha256()
    for h in hex_list:
        H.update(bytes.fromhex(h))
    return H.hexdigest()

def parse_md_for_hash(p: Path) -> str | None:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = HASH_RE.search(txt)
    return m.group(1).lower() if m else None

def iso_week_dates(year: int, week: int) -> List[date]:
    # ISO week: Monday is first day
    # Find Jan 4th which is always in week 1
    jan4 = date(year, 1, 4)
    start = jan4 - timedelta(days=jan4.isoweekday()-1)
    monday = start + timedelta(weeks=week-1)
    return [monday + timedelta(days=i) for i in range(7)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--last7", action="store_true", help="Roll up last 7 calendar days ending today")
    ap.add_argument("--thisweek", action="store_true", help="Roll up the current ISO week (auto year/week from today)")
    args = ap.parse_args()

    root = Path.cwd()
    logs = root / "logs"
    if not logs.exists():
        raise FileNotFoundError("Run from repo root (logs/ not found).")

    if args.thisweek:
        today = date.today()
        y, w, _ = today.isocalendar()
        days = iso_week_dates(y, w)
        label = f"{y}-W{w:02d}"
    elif args.last7:
        end = date.today()
        days = [end - timedelta(days=i) for i in range(6, -1, -1)]
        label = f"{end.isocalendar().year}-W{end.isocalendar().week:02d}_last7"
    else:
        if args.year is None or args.week is None:
            raise ValueError("Provide --year and --week, or use --last7.")
        days = iso_week_dates(args.year, args.week)
        label = f"{args.year}-W{args.week:02d}"

    entries: List[Tuple[str,str]] = []
    missing = []
    for d in days:
        fname = logs / f"{d.isoformat()}.md"
        if not fname.exists():
            missing.append(d.isoformat())
            continue
        h = parse_md_for_hash(fname)
        if not h:
            missing.append(d.isoformat())
            continue
        entries.append((d.isoformat(), h))

    if not entries:
        raise RuntimeError("No daily hashes found for the selected period.")

    # Weekly root over available entries in chronological order
    daily_hashes = [h for _, h in entries]
    weekly_root = sha256_hex_bytes(daily_hashes)

    out = logs / f"weekly_{label}.md"
    lines = []
    lines.append(f"# Weekly Anchor Rollup — {label}")
    lines.append("")
    lines.append("## Daily bundle roots")
    for d, h in entries:
        lines.append(f"- {d}: `{h}`")
    if missing:
        lines.append("")
        lines.append("## Missing / not anchored")
        for d in missing:
            lines.append(f"- {d}")
    lines.append("")
    lines.append("## WEEKLY_ROOT_SHA256")
    lines.append(f"`{weekly_root}`")
    lines.append("")
    lines.append("_Weekly root = sha256(concat(daily bundle root bytes), chronological order over available days.)_")
    out.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote:", out)
    print("WEEKLY_ROOT_SHA256:", weekly_root)

if __name__ == "__main__":
    main()
