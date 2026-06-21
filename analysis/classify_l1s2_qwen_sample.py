#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sample and classify qwen2.5-coder-14b-local L1-S2 wrong answers."""

from __future__ import annotations

import csv
import random
import sys
from collections import Counter
from pathlib import Path
from typing import List, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.classify_l1s3_gemini_sample import classify_row

RESULTS_CSV = _ROOT / "results" / "qwen2.5-coder-14b-local__L1S2.csv"
OUT_MD = _ROOT / "docs" / "qwen14b_L1S2_wrong_answer_sample50.md"

SAMPLE_N = 50
SEED = 42


def fine_bucket(row: dict, cat: str, reason: str) -> str:
    if row.get("outcome") == "error":
        msg = (row.get("error_msg") or "").lower()
        if msg.startswith("no such column:"):
            col = msg.split(":", 1)[1].strip()
            if "__" not in col:
                return "exec: bare column (no table__ prefix)"
            return "exec: wrong/hallucinated prefixed column"
        if msg.startswith("no such table:"):
            if "__" in msg.split(":", 1)[1].strip():
                return "exec: column used as table name"
            return "exec: 3NF table on 1NF db"
        return "exec: other"

    if cat == "b":
        return "logic: missing DISTINCT (repairable)"
    if "Different aggregate" in reason:
        return "logic: wrong aggregate/metric"
    if "HAVING" in reason:
        return "logic: missing HAVING/subquery"
    if "/12" in reason:
        return "logic: missing /12 scaling"
    if "SUM on fan-out" in reason:
        return "1NF asymmetry: SUM fan-out"
    if "AVG over" in reason:
        return "1NF asymmetry: AVG fan-out"
    if "COUNT(DISTINCT)" in reason:
        return "logic: COUNT DISTINCT but wrong key/filter"
    if "aggregates one_nf_0 without" in reason:
        return "1NF asymmetry: wide scan no dedup"
    return "logic: wrong filters/columns/order"


def main() -> int:
    rows = list(csv.DictReader(RESULTS_CSV.open(encoding="utf-8")))
    wrong = [
        r
        for r in rows
        if r.get("outcome") != "correct"
        and str(r.get("correct", "")).lower() not in ("true", "1", "yes")
    ]
    correct_n = sum(
        1
        for r in rows
        if str(r.get("correct", "")).lower() in ("true", "1", "yes")
    )

    rng = random.Random(SEED)
    sample = rng.sample(wrong, min(SAMPLE_N, len(wrong)))

    records: List[Tuple[dict, str, str, str]] = []
    labels: List[str] = []
    fine_labels: List[str] = []
    for row in sample:
        cat, reason = classify_row(row)
        fine = fine_bucket(row, cat, reason)
        labels.append(cat)
        fine_labels.append(fine)
        records.append((row, cat, reason, fine))

    counts = Counter(labels)
    total = len(labels)
    pct = {k: 100.0 * v / total for k, v in counts.items()}

    pop_labels: List[str] = []
    pop_fine: List[str] = []
    for r in wrong:
        cat, reason = classify_row(r)
        pop_labels.append(cat)
        pop_fine.append(fine_bucket(r, cat, reason))
    pop_counts = Counter(pop_labels)
    pop_pct = {k: 100.0 * v / len(pop_labels) for k, v in pop_counts.items()}
    pop_fine_counts = Counter(pop_fine)

    sample_fine_counts = Counter(fine_labels)
    sample_outcomes = Counter(r[0].get("outcome", "?") for r in records)

    lines: List[str] = []
    lines.append(
        "# Qwen 2.5 Coder 14B (local) \u00b7 L1\u00b7S2 wrong-answer sample (n=50)\n\n"
    )
    lines.append(
        "**Source:** `results/qwen2.5-coder-14b-local__L1S2.csv` \u00b7 "
        f"**Accuracy:** {correct_n}/{len(rows)} ({100.0 * correct_n / len(rows):.1f}%) \u00b7 "
        f"**Population:** {len(wrong)} failures / 397 questions \u00b7 "
        f"**Sample:** seed={SEED}, n={total}\n\n"
    )
    lines.append(
        "**Setup:** L1 = single wide table `one_nf_0`; S2 = abbreviated column names "
        "(`table__abbrev` in prompt). Gold SQL on 3NF SQLite; predicted SQL on "
        "`{db_id}__1nf.sqlite`. Multiset execution comparison (`evaluator.py`); "
        "S2 display names mapped at eval time via `build_l1_col_rename_map`.\n\n"
    )

    lines.append("## Category definitions\n\n")
    lines.append("| Code | Label | Meaning |\n")
    lines.append("|------|--------|--------|\n")
    lines.append(
        "| **(a)** | Genuine model error | Wrong metric, filter, column, `HAVING`, "
        "missing `/12`, `MAX` vs `SUM`, etc. |\n"
    )
    lines.append(
        "| **(b)** | Partial (missing DISTINCT) | 1NF translation largely faithful; "
        "automated DISTINCT repair **or** clear `COUNT`/scan fan-out without DISTINCT "
        "would align with gold |\n"
    )
    lines.append(
        "| **(c)** | Unrecoverable evaluation artefact | SQL executes but multiset \u2260 gold; "
        "execution errors; or fan-out needs dedup **subquery** (SUM/AVG), not keyword "
        "DISTINCT alone |\n"
    )

    lines.append("\n## Summary (sample)\n\n")
    lines.append("| Category | Count | % of sample |\n")
    lines.append("|----------|------:|------------:|\n")
    for code, name in [
        ("a", "Genuine model error"),
        ("b", "Partial (DISTINCT missing)"),
        ("c", "Unrecoverable eval artefact"),
    ]:
        lines.append(f"| **({code})** {name} | {counts.get(code, 0)} | {pct.get(code, 0):.1f}% |\n")
    lines.append(f"| **Total** | {total} | 100.0% |\n")

    lines.append(
        f"\n**Outcomes in sample:** "
        f"`wrong_answer` {sample_outcomes.get('wrong_answer', 0)}, "
        f"`error` {sample_outcomes.get('error', 0)}\n\n"
    )

    lines.append("### Fine-grained failure types (sample)\n\n")
    lines.append("| Failure type | Count | % |\n")
    lines.append("|--------------|------:|--:|\n")
    for label, n in sample_fine_counts.most_common():
        lines.append(f"| {label} | {n} | {100.0 * n / total:.1f}% |\n")

    lines.append(f"\n### Full failure population (n={len(wrong)}, same classifier)\n\n")
    lines.append("| Category | Count | % |\n")
    lines.append("|----------|------:|--:|\n")
    for code, name in [
        ("a", "Genuine model error"),
        ("b", "Partial (DISTINCT missing)"),
        ("c", "Unrecoverable eval artefact"),
    ]:
        lines.append(
            f"| **({code})** {name} | {pop_counts.get(code, 0)} | {pop_pct.get(code, 0):.1f}% |\n"
        )
    lines.append(f"| **Total** | {len(pop_labels)} | 100.0% |\n")

    lines.append("\n### Fine-grained failure types (full population)\n\n")
    lines.append("| Failure type | Count | % |\n")
    lines.append("|--------------|------:|--:|\n")
    for label, n in pop_fine_counts.most_common():
        lines.append(f"| {label} | {n} | {100.0 * n / len(wrong):.1f}% |\n")

    exec_n = sum(1 for r in wrong if r.get("outcome") == "error")
    lines.append(
        f"\n### S2 execution-error patterns (full population, n={exec_n})\n\n"
    )
    lines.append(
        "At L1\u00b7S2 the prompt shows abbreviated `table__abbrev` names; the 1NF SQLite file "
        "stores S3-style physical names. The evaluator renames display \u2192 physical, but only "
        "when the model uses the **exact** prefixed name from the schema.\n\n"
    )
    lines.append("| Pattern | Count | % of exec errors |\n")
    lines.append("|---------|------:|-----------------:|\n")
    exec_fine = Counter(
        fine_bucket(r, *classify_row(r))
        for r in wrong
        if r.get("outcome") == "error"
    )
    for label in [
        "exec: bare column (no table__ prefix)",
        "exec: wrong/hallucinated prefixed column",
        "exec: column used as table name",
        "exec: 3NF table on 1NF db",
        "exec: other",
    ]:
        n = exec_fine.get(label, 0)
        if n:
            lines.append(f"| {label} | {n} | {100.0 * n / exec_n:.1f}% |\n")

    lines.append(
        f"\n*Sample seed={SEED}. Classification reuses DISTINCT repair + SQL-shape rules "
        "from `analysis/classify_l1s3_gemini_sample.py` (`classify_row`). "
        "Regenerate: `python analysis/classify_l1s2_qwen_sample.py`.*\n\n"
    )
    lines.append("---\n\n## Sampled failures\n\n")

    for i, (row, cat, reason, fine) in enumerate(records, 1):
        qid = row.get("question_id", "?")
        db = row.get("db_id", "?")
        diff = row.get("difficulty", "?")
        qtype = row.get("question_type", "?")
        outcome = row.get("outcome", "?")
        err = (row.get("error_msg") or "").strip()
        lines.append(f"### {i}. Q{qid} ({db}, {diff}, {qtype}) \u2014 **({cat})**\n\n")
        lines.append(f"**Outcome:** `{outcome}`")
        if err:
            lines.append(f" \u00b7 **Error:** `{err}`")
        lines.append(f" \u00b7 **Fine type:** {fine}\n\n")
        lines.append(f"**Category ({cat}):** {reason}\n\n")
        lines.append("**Gold SQL:**\n\n```sql\n")
        lines.append(row.get("gold_sql", "").strip())
        lines.append("\n```\n\n**Predicted SQL:**\n\n```sql\n")
        lines.append(row.get("predicted_sql", "").strip())
        lines.append("\n```\n\n")

    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Counts: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
