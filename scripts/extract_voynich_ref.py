#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract a clean EVA corpus from IVTFF.
"""
import re, argparse
from pathlib import Path

def iter_lines(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            if not ln or ln.startswith("#"):
                continue
            if ln.startswith("<f") and ">" in ln:
                after = ln.split(">", 1)[1]
                txt = re.sub(r"[^a-z\.\s]", " ", after.lower())
                txt = re.sub(r"\s+", " ", txt).strip()
                if txt:
                    yield txt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ivtff", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max_lines", type=int, default=20000)
    args = ap.parse_args()

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with outp.open("w", encoding="utf-8") as w:
        for line in iter_lines(args.ivtff):
            w.write(line + "\n")
            n += 1
            if n >= args.max_lines:
                break
    print(f"wrote {n} lines to {outp}")

if __name__ == "__main__":
    main()
