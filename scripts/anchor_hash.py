#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor_hash.py
==============
Compute a SHA256 fingerprint for a day's log bundle:
- logs/YYYY-MM-DD.md
- assets/diagnostic/YYYY-MM-DD_W63.png (if exists)
- assets/diagnostic/YYYY-MM-DD_W252.png (if exists)

Usage:
python scripts/anchor_hash.py --date 2026-01-28

You can record the resulting SHA256 anywhere (commit message / gist / tx memo)
to prove integrity later.
"""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    root = Path.cwd()
    md = root / "logs" / f"{args.date}.md"
    w63 = root / "assets" / "diagnostic" / f"{args.date}_W63.png"
    w252 = root / "assets" / "diagnostic" / f"{args.date}_W252.png"

    parts = []
    for p in (md, w63, w252):
        if p.exists():
            parts.append((p.as_posix(), sha256_file(p)))

    if not parts:
        raise FileNotFoundError("No files found for that date. Run publish_today.py first.")

    print("BUNDLE:")
    for name, h in parts:
        print(f"- {name}: {h}")

    # bundle root hash = sha256(concat(filehashes))
    H = hashlib.sha256()
    for _, h in parts:
        H.update(bytes.fromhex(h))
    print("\nBUNDLE_ROOT_SHA256:", H.hexdigest())

if __name__ == "__main__":
    main()
