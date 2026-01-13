# 検査ルール（最低限）

## 1) JSONL 構造
- 1行=1JSON
- 必須キー: id, domain, source, evidence_latin, concept_ja, qa, tags
- source 必須キー: work, file, locator

## 2) 値制約
- domain は {herbal, regimen, astronomy}
- qa は配列で長さ 3（最小実験では固定）
- qa[*] は {q,a,evidence_ref}

## 3) 中世枠の保持
- 近代の化学物質名・臨床用語（抗菌薬/ビタミン等）を禁止
- 量・投与量の断定は禁止（古典に依る場合でも「〜と伝える」止まり）
- 断言が強い語（必ず治る等）が出たら concept_ja で“誇張修辞”と明示

## 4) 省力運用
- locator.lines が空なら不合格（人手確認ポイント）
- tags が空なら不合格
