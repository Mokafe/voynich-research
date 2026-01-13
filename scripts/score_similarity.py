#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Similarity metrics between two corpora.
- Char unigram / bigram Jensen–Shannon similarity (1 - JS divergence)
- Cosine similarity of char 3-gram counts
This is a proxy "Voynich-likeness" score that moves when distributions move.
"""
from __future__ import annotations
import math, argparse, re
from collections import Counter

def _normalize(c: Counter) -> dict[str, float]:
    total = sum(c.values()) or 1
    return {k: v/total for k,v in c.items()}

def _js_div(p: dict[str,float], q: dict[str,float]) -> float:
    # Jensen-Shannon divergence base 2
    keys = set(p) | set(q)
    m = {k: 0.5*(p.get(k,0.0)+q.get(k,0.0)) for k in keys}
    def kl(a,b):
        s=0.0
        for k,v in a.items():
            if v<=0: 
                continue
            bv = b.get(k,0.0)
            if bv<=0:
                continue
            s += v * math.log(v/bv, 2)
        return s
    return 0.5*kl(p,m)+0.5*kl(q,m)

def _char_ngrams(text: str, n: int) -> Counter:
    text = re.sub(r"[^a-z\. ]", " ", text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    c = Counter()
    if len(text) < n:
        return c
    for i in range(len(text)-n+1):
        g = text[i:i+n]
        c[g] += 1
    return c

def _cosine(c1: Counter, c2: Counter) -> float:
    keys = set(c1) | set(c2)
    dot = sum(c1.get(k,0)*c2.get(k,0) for k in keys)
    n1 = math.sqrt(sum(v*v for v in c1.values())) or 1.0
    n2 = math.sqrt(sum(v*v for v in c2.values())) or 1.0
    return dot/(n1*n2)

def score(a_text: str, b_text: str):
    u1 = _normalize(_char_ngrams(a_text, 1))
    u2 = _normalize(_char_ngrams(b_text, 1))
    b1 = _normalize(_char_ngrams(a_text, 2))
    b2 = _normalize(_char_ngrams(b_text, 2))

    js_u = _js_div(u1,u2)
    js_b = _js_div(b1,b2)

    sim_unigram = 1.0 - js_u
    sim_bigram  = 1.0 - js_b
    cos3 = _cosine(_char_ngrams(a_text,3), _char_ngrams(b_text,3))
    return {"js_sim_unigram": sim_unigram, "js_sim_bigram": sim_bigram, "cosine_3gram": cos3}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="reference corpus txt")
    ap.add_argument("--gen", required=True, help="generated corpus txt")
    args = ap.parse_args()

    ref = open(args.ref, "r", encoding="utf-8", errors="ignore").read()
    gen = open(args.gen, "r", encoding="utf-8", errors="ignore").read()
    s = score(ref, gen)
    for k,v in s.items():
        print(f"{k}\t{v:.6f}")

if __name__ == "__main__":
    main()
