#!/usr/bin/env python3
"""
Score held-out LLM classifier predictions against the 284 hand labels.
Usage: score_heldout.py <heldout_dir> [--out docs/error_analysis/classifier_heldout_validation.md]
"""
import csv, json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

CATS = ["Invalid SQL", "Schema linking", "JOIN errors", "Fan-out", "GROUP BY errors",
        "Nesting problem", "Predicate error", "Other"]
d = Path(sys.argv[1])
out_path = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None

truth = {r["question_id"]: r for r in csv.DictReader((d / "manual_labels.csv").open(encoding="utf-8"))}
folds = json.load((d / "folds.json").open())
pred = {}
for p in sorted(d.glob("pred_*.json")):
    for q, v in json.load(p.open()).items():
        pred[str(q)] = v
missing = sorted(set(truth) - set(pred), key=int)
bad = {q: v["category"] for q, v in pred.items() if v["category"] not in CATS}
n = len(truth); m = len(set(truth) & set(pred))
ids = sorted(set(truth) & set(pred), key=int)
t = [truth[q]["category"] for q in ids]; p = [pred[q]["category"] for q in ids]
acc = sum(a == b for a, b in zip(t, p)) / len(ids)

# Cohen's kappa
ct = Counter(t); cp = Counter(p)
pe = sum(ct[c] * cp[c] for c in CATS) / len(ids) ** 2
kappa = (acc - pe) / (1 - pe)

# confusion matrix
M = np.zeros((len(CATS), len(CATS)), int)
for a, b in zip(t, p):
    M[CATS.index(a), CATS.index(b)] += 1

# bootstrap CI for accuracy and kappa
rng = np.random.default_rng(42)
T = np.array([CATS.index(x) for x in t]); P = np.array([CATS.index(x) for x in p])
accs, kaps = [], []
for _ in range(5000):
    i = rng.integers(0, len(T), len(T))
    a = (T[i] == P[i]).mean()
    ct_ = np.bincount(T[i], minlength=8); cp_ = np.bincount(P[i], minlength=8)
    pe_ = (ct_ * cp_).sum() / len(i) ** 2
    accs.append(a); kaps.append((a - pe_) / (1 - pe_) if pe_ < 1 else 0)
acc_ci = np.percentile(accs, [2.5, 97.5]); kap_ci = np.percentile(kaps, [2.5, 97.5])

L = []
L.append("# Held-out validation of the LLM-assisted error classifier\n")
L.append(f"Scored {m}/{n} hand-labelled Qwen2.5-Coder-14B L3·S3 failures. "
         f"{len(folds and set(folds.values()))}-fold cross-validation: each fold was classified by a Claude "
         "subagent (Claude Code, model claude-fable-5-1, rules = docs/error_analysis/error_taxonomy.md + "
         ".claude/skills/error-classify/SKILL.md) that saw the hand labels of the OTHER folds as guidance "
         "and never saw the labels of the fold it classified.\n")
if missing: L.append(f"**Missing predictions:** {missing}\n")
if bad: L.append(f"**Invalid category strings:** {bad}\n")
L.append("## Overall agreement\n")
L.append("| metric | value | 95% bootstrap CI |\n|--|--:|--:|")
L.append(f"| accuracy (exact category match) | {100*acc:.1f}% | [{100*acc_ci[0]:.1f}%, {100*acc_ci[1]:.1f}%] |")
L.append(f"| Cohen's κ | {kappa:.3f} | [{kap_ci[0]:.3f}, {kap_ci[1]:.3f}] |\n")

# per fold
L.append("| fold | n | accuracy |\n|--|--:|--:|")
for k in sorted(set(folds.values())):
    qs = [q for q in ids if folds[q] == k]
    a = sum(truth[q]["category"] == pred[q]["category"] for q in qs) / len(qs)
    L.append(f"| {k} | {len(qs)} | {100*a:.1f}% |")
L.append("")

# per category P/R/F1
L.append("## Per-category precision / recall / F1 (human label = truth)\n")
L.append("| category | human n | classifier n | precision | recall | F1 |\n|--|--:|--:|--:|--:|--:|")
for i, c in enumerate(CATS):
    tp = M[i, i]; fn = M[i].sum() - tp; fp = M[:, i].sum() - tp
    pr = tp / (tp + fp) if tp + fp else float("nan"); rc = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * pr * rc / (pr + rc) if (pr + rc) and not np.isnan(pr + rc) else float("nan")
    if M[i].sum() == 0 and M[:, i].sum() == 0: continue
    L.append(f"| {c} | {M[i].sum()} | {M[:, i].sum()} | {pr:.2f} | {rc:.2f} | {f1:.2f} |")
L.append("")

# confusion matrix
L.append("## Confusion matrix (rows = human label, columns = classifier label)\n")
short = ["Invalid", "SchemaLink", "JOIN", "FanOut", "GROUPBY", "Nesting", "Predicate", "Other"]
L.append("| human \\ clf | " + " | ".join(short) + " | total |")
L.append("|--|" + "--:|" * (len(CATS) + 1))
for i, c in enumerate(CATS):
    if M[i].sum() == 0 and M[:, i].sum() == 0: continue
    L.append(f"| {short[i]} | " + " | ".join(f"**{M[i,j]}**" if i == j and M[i,j] else (str(M[i,j]) if M[i,j] else "·") for j in range(len(CATS))) + f" | {M[i].sum()} |")
L.append("| total | " + " | ".join(str(M[:, j].sum()) for j in range(len(CATS))) + f" | {M.sum()} |\n")

# category-rate sensitivity: human vs classifier marginals
L.append("## Category-rate sensitivity (what Tables 4–5 would look like under classifier vs human labels)\n")
L.append("| category | human % | classifier % | Δ (pp) |\n|--|--:|--:|--:|")
for i, c in enumerate(CATS):
    if M[i].sum() == 0 and M[:, i].sum() == 0: continue
    h = 100 * M[i].sum() / M.sum(); cl = 100 * M[:, i].sum() / M.sum()
    L.append(f"| {c} | {h:.1f} | {cl:.1f} | {cl-h:+.1f} |")
L.append("")

# disagreements
L.append("## Disagreements\n")
L.append("| qid | db | human | classifier | human reason | classifier reason |\n|--|--|--|--|--|--|")
for q in ids:
    if truth[q]["category"] != pred[q]["category"]:
        L.append(f"| {q} | {truth[q]['db_id']} | {truth[q]['category']} ({truth[q]['subtype']}) | "
                 f"{pred[q]['category']} ({pred[q].get('subtype','')}) | {truth[q]['reason'][:120]} | {pred[q].get('reason','')[:120]} |")
text = "\n".join(L)
print(text)
if out_path:
    out_path.write_text(text, encoding="utf-8"); print(f"[written] {out_path}", file=sys.stderr)
