#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight EVA-ish generator (no ML fine-tuning).
- Builds a char-bigram Markov model from IVTFF EVA corpus (LSI_ivtff_0d.txt).
- Generates "voynich-like" tokens conditioned on card-derived seeds.
- Produces two streams (A/B) by simple, explicit biasing rules.
"""
from __future__ import annotations
import re, json, math, random
from collections import Counter, defaultdict
from pathlib import Path

KEEP_RE = re.compile(r"[a-z]+", re.I)

def _iter_ivtff_text_lines(ivtff_path: str):
    """
    Extract main EVA text lines from IVTFF.
    Lines look like:
      <f116v.1,@Lx;U>    oror.sheey!!!!!!
    We keep only the chunk after '>' and strip non letters/dots/spaces.
    """
    with open(ivtff_path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln or ln.startswith("#"):
                continue
            if ln.startswith("<f") and ">" in ln:
                try:
                    after = ln.split(">", 1)[1]
                except Exception:
                    continue
                # remove locator spacing, keep letters/dots/spaces
                txt = re.sub(r"[^a-z\.\s]", " ", after.lower())
                txt = re.sub(r"\s+", " ", txt).strip()
                if txt:
                    yield txt

def build_bigram_model(ivtff_path: str, max_lines: int = 20000):
    """
    Bigram model over characters including boundary tokens '^' and '$'.
    """
    trans = defaultdict(Counter)
    starters = Counter()
    n = 0
    for line in _iter_ivtff_text_lines(ivtff_path):
        n += 1
        # split by spaces and dots into "words"
        parts = re.split(r"[.\s]+", line)
        for w in parts:
            if not w:
                continue
            w = re.sub(r"[^a-z]", "", w)
            if len(w) < 2:
                continue
            starters[w[:2]] += 1
            s = "^" + w + "$"
            for a, b in zip(s, s[1:]):
                trans[a][b] += 1
        if n >= max_lines:
            break

    # normalize to probabilities
    model = {}
    for a, cnt in trans.items():
        total = sum(cnt.values())
        model[a] = {b: c/total for b, c in cnt.items()}
    # starter distribution
    st_total = sum(starters.values()) or 1
    starters_prob = {k: v/st_total for k, v in starters.items()}
    return {"bigram": model, "starters": starters_prob}

def _weighted_choice(rng: random.Random, prob_dict: dict[str, float]) -> str:
    r = rng.random()
    acc = 0.0
    last = None
    for k, p in prob_dict.items():
        acc += p
        last = k
        if r <= acc:
            return k
    return last if last is not None else next(iter(prob_dict))

def _apply_stream_bias(stream: str, prev_char: str, probs: dict[str, float]) -> dict[str, float]:
    """
    Minimal A/B divergence without needing Currier labels.
    A: slightly favors 'q' and 'o' (q- prefix feel)
    B: slightly favors 'ch','sh' feel => favors 'c','h','s' sequences by biasing next char.
    """
    if not probs:
        return probs
    out = dict(probs)
    if stream.upper() == "A":
        # favor q/o a bit
        for ch in ("q", "o"):
            if ch in out:
                out[ch] *= 1.25
    elif stream.upper() == "B":
        for ch in ("c", "h", "s", "e", "y"):
            if ch in out:
                out[ch] *= 1.20
    # renormalize
    s = sum(out.values())
    if s <= 0:
        return probs
    for k in list(out.keys()):
        out[k] /= s
    return out

def generate_word(model: dict, seed: int, stream: str = "A",
                  target_len: int = 6, start_hint: str | None = None) -> str:
    rng = random.Random(seed)
    bigram = model["bigram"]
    starters = model["starters"]

    # decide start 2 chars
    if start_hint and len(start_hint) >= 2 and start_hint[:2].islower():
        start2 = start_hint[:2]
    else:
        start2 = _weighted_choice(rng, starters)

    w = start2
    prev = start2[-1]
    # continue until length or '$'
    while len(w) < max(3, target_len):
        probs = bigram.get(prev, None)
        if not probs:
            break
        probs2 = _apply_stream_bias(stream, prev, probs)
        nxt = _weighted_choice(rng, probs2)
        if nxt == "$":
            break
        if nxt == "^":
            continue
        w += nxt
        prev = nxt
    return w

def card_seed_string(card: dict) -> str:
    """
    Stable seed string from card content. Changing sources changes seeds.
    """
    parts = []
    parts.append(card.get("id",""))
    parts.append(card.get("domain",""))
    parts.append(card.get("concept_ja","")[:50])
    parts.append(card.get("evidence_latin","")[:120])
    src = card.get("source", {})
    parts.append(src.get("work",""))
    parts.append(src.get("locator",""))
    s = "|".join(parts).lower()
    s = re.sub(r"\s+", " ", s)
    return s

def seed_to_int(s: str) -> int:
    # deterministic hash without Python's randomized hash
    h = 2166136261
    for b in s.encode("utf-8", errors="ignore"):
        h ^= b
        h = (h * 16777619) & 0xffffffff
    return h

def generate_line_from_card(model: dict, card: dict, stream: str = "A",
                            words: int = 8) -> str:
    seed_s = card_seed_string(card)
    h = seed_to_int(seed_s)
    rng = random.Random(h)

    # use Latin letters (if any) as a start hint source
    latin = re.sub(r"[^a-z]", "", card.get("evidence_latin","").lower())
    hint = latin[:2] if len(latin) >= 2 else None

    # word length distribution influenced by seed
    base_len = 4 + (h % 5)  # 4..8
    toks = []
    for i in range(words):
        tl = max(3, int(rng.gauss(base_len, 1.2)))
        wi = generate_word(model, seed=h + i*9973, stream=stream, target_len=tl, start_hint=hint)
        # add occasional '.' like EVA
        toks.append(wi)
        if rng.random() < 0.12:
            toks[-1] += "."
    return " ".join(toks)

def save_model(model: dict, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False)

def load_model(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
