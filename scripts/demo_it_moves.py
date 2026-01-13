#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end "it moves" demo:
1) Build Markov model from IVTFF
2) Generate EVA-ish lines from your cards (stream A and/or B)
3) Score similarity vs reference corpus
4) Swap "seed mode" to see score move (proxy for "changing training texts changes likeness")
"""
from __future__ import annotations
import json, argparse, os
from pathlib import Path

from eva_encode import build_bigram_model, save_model, load_model, generate_line_from_card

def read_cards(paths):
    cards=[]
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            for ln in f:
                ln=ln.strip()
                if not ln: 
                    continue
                cards.append(json.loads(ln))
    return cards

def write_gen(cards, model, out_path: str, stream: str, lines_per_card: int, words: int, seed_mode: str):
    """
    seed_mode:
      - normal: use card's evidence/source as seed (source-sensitive)
      - neutral: blank out evidence/source (source-insensitive baseline)
    """
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf-8") as w:
        for c in cards:
            cc = dict(c)
            if seed_mode == "neutral":
                cc["evidence_latin"] = ""
                cc["source"] = {"work":"", "file":"", "locator":""}
            for i in range(lines_per_card):
                line = generate_line_from_card(model, cc, stream=stream, words=words)
                w.write(line + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ivtff", required=True, help="LSI_ivtff_0d.txt")
    ap.add_argument("--ref_txt", required=True, help="reference corpus extracted from IVTFF")
    ap.add_argument("--cards_glob", default="cards/*.jsonl")
    ap.add_argument("--out_dir", default="runs/demo")
    ap.add_argument("--stream", default="A", choices=["A","B"])
    ap.add_argument("--lines_per_card", type=int, default=5)
    ap.add_argument("--words", type=int, default=8)
    ap.add_argument("--seed_mode", default="normal", choices=["normal","neutral"])
    args = ap.parse_args()

    # resolve cards
    root = Path(__file__).resolve().parents[1]
    card_paths = sorted((root / args.cards_glob).glob("*.jsonl")) if args.cards_glob.endswith("*.jsonl") else sorted((root / args.cards_glob).glob("*"))
    if not card_paths:
        # fallback: explicit dirs
        card_paths = list((root/"cards").glob("*.jsonl"))
    cards = read_cards(card_paths)

    out_dir = Path(root/args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir/"markov_model.json"
    if not model_path.exists():
        model = build_bigram_model(args.ivtff, max_lines=20000)
        save_model(model, str(model_path))
    else:
        model = load_model(str(model_path))

    gen_path = out_dir/f"gen_stream{args.stream}_{args.seed_mode}.txt"
    write_gen(cards, model, str(gen_path), args.stream, args.lines_per_card, args.words, args.seed_mode)

    # score
    import subprocess, sys
    scorer = Path(__file__).resolve().parent/"score_similarity.py"
    cmd = [sys.executable, str(scorer), "--ref", args.ref_txt, "--gen", str(gen_path)]
    print(" ".join(cmd))
    subprocess.run(cmd, check=False)

    print(f"\nGenerated: {gen_path}")
    print("Tip: run twice with --seed_mode normal vs neutral and compare the scores.")

if __name__ == "__main__":
    main()
