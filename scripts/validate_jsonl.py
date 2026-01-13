#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys

ALLOWED_DOMAIN = {"herbal","regimen","astronomy"}

def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)

def validate_obj(o, line_no):
    for k in ["id","domain","source","evidence_latin","concept_ja","qa","tags"]:
        if k not in o:
            fail(f"line {line_no}: missing key {k}")
    if o["domain"] not in ALLOWED_DOMAIN:
        fail(f"line {line_no}: bad domain {o['domain']}")
    src = o["source"]
    for k in ["work","file","locator"]:
        if k not in src:
            fail(f"line {line_no}: source missing {k}")
    if not isinstance(o["qa"], list) or len(o["qa"]) != 5:
        fail(f"line {line_no}: qa must be list of length 5")
    for i, qa in enumerate(o["qa"]):
        for k in ["q","a","evidence_ref"]:
            if k not in qa:
                fail(f"line {line_no}: qa[{i}] missing {k}")
    if not isinstance(o["tags"], list) or len(o["tags"]) == 0:
        fail(f"line {line_no}: tags must be non-empty")
    loc = src["locator"]
    if isinstance(loc, dict) and not loc.get("lines"):
        fail(f"line {line_no}: locator.lines is empty")

def main(path):
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            validate_obj(o, ln)
    print("OK:", path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_jsonl.py cards/file.jsonl")
        sys.exit(2)
    main(sys.argv[1])
