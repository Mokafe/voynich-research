#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight EVA-ish generator (no ML fine-tuning).
- Builds a char-bigram Markov model from IVTFF EVA corpus (LSI_ivtff_0d.txt).
- Generates "voynich-like" tokens conditioned on card-derived seeds.
- Produces two streams (A/B) by simple, explicit biasing rules.
"""
from __future__ import annotations

import re
import json
import random
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
        total = sum(cnt.values()) or 1
        model[a] = {b: c / total for b, c in cnt.items()}

    # starter distribution
    st_total = sum(starters.values()) or 1
    starters_prob = {k: v / st_total for k, v in starters.items()}
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


def generate_word(
    model: dict,
    seed: int,
    stream: str = "A",
    target_len: int = 6,
    start_hint: str | None = None,
) -> str:
    rng = random.Random(seed)
    bigram = model["bigram"]
    starters = model["starters"]

    # decide start 2 chars
    hint2 = None
    if start_hint and len(start_hint) >= 2:
        h2 = start_hint[:2].lower()
        # starters は dict[str,float] なので、存在チェックしてから採用
        if h2 in starters:
            hint2 = h2
    start2 = hint2 if hint2 else _weighted_choice(rng, starters)

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


def _as_str(x) -> str:
    """Join 用に安全に文字列化する（dict/listもOK）"""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, (int, float, bool)):
        return str(x)
    if isinstance(x, dict):
        return json.dumps(x, ensure_ascii=False, sort_keys=True)
    if isinstance(x, list):
        # list内も再帰的に文字列化
        ys = [_as_str(v) for v in x]
        ys = [y for y in ys if y]
        return "|".join(ys)
    return str(x)


def card_seed_string(card: dict) -> str:
    """
    Stable seed string from card content. Changing sources changes seeds.
    """
    parts = []
    parts.append(card.get("id", ""))
    parts.append(card.get("domain", ""))
    parts.append((card.get("concept_ja", "") or "")[:50])
    parts.append((card.get("evidence_latin", "") or "")[:120])

    src = card.get("source", {}) or {}
    parts.append(src.get("work", ""))
    # locator は dict の可能性があるので、そのまま入れてOK（_as_str で吸収）
    parts.append(src.get("locator", ""))

    # ★ここが重要：join 前に文字列化
    parts = [_as_str(p) for p in parts]
    parts = [p for p in parts if p]  # 空は捨てる

    s = "|".join(parts).lower()
    s = re.sub(r"\s+", " ", s)
    return s


def seed_to_int(s: str) -> int:
    # deterministic hash without Python's randomized hash
    h = 2166136261
    for b in s.encode("utf-8", errors="ignore"):
        h ^= b
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def generate_line_from_card(model: dict, card: dict, stream: str = "A", words: int = 8) -> str:
    seed_s = card_seed_string(card)
    h = seed_to_int(seed_s)
    rng = random.Random(h)

    # use Latin letters (if any) as a start hint source
    latin = re.sub(r"[^a-z]", "", (card.get("evidence_latin", "") or "").lower())
    hint = latin[:2] if len(latin) >= 2 else None

    # word length distribution influenced by seed
    base_len = 4 + (h % 5)  # 4..8
    toks = []
    for i in range(words):
        tl = max(3, int(rng.gauss(base_len, 1.2)))
        wi = generate_word(
            model,
            seed=h + i * 9973,
            stream=stream,
            target_len=tl,
            start_hint=hint,
        )
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
