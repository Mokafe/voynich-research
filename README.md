# voynich_mini_experiment

3資料（Macer / Regimen / Sacrobosco）から **各5カード**（計15カード）の最小 JSONL 学習セット。

## 最小チェック
python scripts/validate_jsonl.py cards/macer_5cards.jsonl
python scripts/validate_jsonl.py cards/regimen_5cards.jsonl
python scripts/validate_jsonl.py cards/sacrobosco_5cards.jsonl

## 省力運用の肝
- 人手は locator(lines) の確認と、矛盾統合だけに寄せる
- prompts/ のテンプレで自動下書き → rules/ で落とす

## Quick "it moves" demo (no fine-tuning)

This mini-project already contains 15 cards (5×3 sources).  
To get a *working mental image fast*, do this:

1) Extract a clean Voynich reference corpus from IVTFF:

```bash
python scripts/extract_voynich_ref.py --ivtff /path/to/LSI_ivtff_0d.txt --out runs/voynich_ref.txt --max_lines 20000
```

2) Run the end-to-end demo (generates EVA-ish text from cards + scores similarity):

```bash
python scripts/demo_it_moves.py --ivtff /path/to/LSI_ivtff_0d.txt --ref_txt runs/voynich_ref.txt --stream A --seed_mode normal
python scripts/demo_it_moves.py --ivtff /path/to/LSI_ivtff_0d.txt --ref_txt runs/voynich_ref.txt --stream A --seed_mode neutral
```

- `seed_mode=normal` uses each card's Latin evidence/source as a seed (source-sensitive)
- `seed_mode=neutral` blanks those fields (source-insensitive baseline)

If your upstream material changes, the **normal** run will move more than the neutral run.
This is a proxy for: "changing training texts changes Voynich-likeness".

Notes:
- This is NOT a cryptanalytic claim. It's a cheap distributional likeness metric.
- Two streams A/B are implemented as explicit probability biases (no Currier labels needed).

---

## Run on Colab (1-click)

Open:

https://colab.research.google.com/github/Mokafe/voynich-research/blob/main/notebooks/00_colab_demo.ipynb

## Reference data

The demo downloads the IVTFF (EVA) transcription file `LSI_ivtff_0d.txt` from voynich.nu.
