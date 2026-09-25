#!/usr/bin/env python3
"""
Build k-fold held-out files for validating the LLM-assisted error classifier.

Parses the 284 hand labels in docs/error_analysis/qwen14b_L3S3_manual_error_details.md, splits
question ids into k stratified-by-database folds (fixed seed), and writes per fold:
  guidance_{k}.md : labelled examples from the OTHER folds (category, subtype, reason, SQL)
  blind_{k}.md    : the held-out items with NO labels (db, outcome, error_msg, gold, predicted)
plus manual_labels.csv with the parsed truth.
"""
import csv, json, random, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "docs/error_analysis/qwen14b_L3S3_manual_error_details.md"
CSV = ROOT / "results/full/qwen2.5-coder-14b-local__L3S3.csv"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "analysis/heldout"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 4
OUT.mkdir(parents=True, exist_ok=True)

HDR = re.compile(r"^### Q(\d+) \(([^,]+), ([^)]+)\) — \*\*(.+?)\*\*(?: \((.*?)\))?\s*$")
labels = {}
cur = None
for line in MD.read_text(encoding="utf-8").splitlines():
    m = HDR.match(line)
    if m:
        cur = m.group(1)
        labels[cur] = {"question_id": cur, "difficulty": m.group(2), "question_type": m.group(3),
                       "category": m.group(4).strip(), "subtype": (m.group(5) or "").strip(), "reason": ""}
        continue
    if cur and line.startswith("**Outcome:**"):
        r = re.search(r"\*\*Reason:\*\* (.*)$", line)
        labels[cur]["reason"] = r.group(1).strip() if r else ""
rows = {r["question_id"]: r for r in csv.DictReader(CSV.open(encoding="utf-8"))}
fails = [q for q, r in rows.items() if r["outcome"] != "correct"]
assert set(fails) == set(labels), (len(fails), len(labels), set(fails) ^ set(labels))
for q in labels:
    labels[q]["db_id"] = rows[q]["db_id"]

with (OUT / "manual_labels.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["question_id", "db_id", "difficulty", "question_type", "category", "subtype", "reason"])
    w.writeheader()
    for q in sorted(labels, key=int):
        w.writerow(labels[q])

rng = random.Random(20260918)
fold_of = {}
by_db = defaultdict(list)
for q in labels:
    by_db[labels[q]["db_id"]].append(q)
for db, qs in sorted(by_db.items()):
    qs = sorted(qs, key=int)
    rng.shuffle(qs)
    for i, q in enumerate(qs):
        fold_of[q] = i % K
json.dump(fold_of, (OUT / "folds.json").open("w"), indent=0)

def item(q, with_label):
    r = rows[q]; l = labels[q]
    s = [f"### Q{q} · db={r['db_id']} · outcome={r['outcome']}"]
    if with_label:
        s.append(f"**LABEL:** {l['category']} ({l['subtype']}) — {l['reason']}")
    if r["error_msg"].strip():
        s.append(f"error_msg: `{r['error_msg'].strip()[:300]}`")
    s.append("Gold SQL:\n```sql\n" + r["gold_sql"].strip() + "\n```")
    s.append("Predicted SQL:\n```sql\n" + r["predicted_sql"].strip() + "\n```")
    return "\n".join(s) + "\n"

for k in range(K):
    held = sorted([q for q in labels if fold_of[q] == k], key=int)
    rest = sorted([q for q in labels if fold_of[q] != k], key=int)
    (OUT / f"guidance_{k}.md").write_text(
        f"# Guidance: {len(rest)} hand-labelled L3·S3 failures (Qwen2.5-Coder-14B)\n\n"
        "Each item shows the human label (category, subtype, one-line reason) plus gold and predicted SQL.\n\n"
        + "\n".join(item(q, True) for q in rest), encoding="utf-8")
    (OUT / f"blind_{k}.md").write_text(
        f"# Blind set fold {k}: {len(held)} L3·S3 failures to classify\n\n"
        + "\n".join(item(q, False) for q in held), encoding="utf-8")
    print(f"fold {k}: held-out {len(held)}, guidance {len(rest)}")
from collections import Counter
print(Counter(l["category"] for l in labels.values()))
