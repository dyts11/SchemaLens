#!/usr/bin/env python3
"""
Sample N wrong answers from qwen2.5-coder-14b-local L1S3 and classify failures.

Categories:
  (a) genuine model error
  (b) partial  faithful 1NF shape; multiset would match with DISTINCT/dedup repair
  (c) unrecoverable evaluation artefact  executes but 1NF multiset ? 3NF gold;
      simple DISTINCT repair does not restore gold

Output: docs/error_analysis/qwen14b_L1S3_wrong_answer_sample60.md
"""

from __future__ import annotations

import csv
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.evaluator import evaluate
from src.schema_builder import SchemaBuilder

DATA_DIR = _ROOT / "dev_20240627"
RESULTS_CSV = _ROOT / "results" / "full" / "qwen2.5-coder-14b-local__L1S3.csv"
OUT_MD = _ROOT / "docs" / "qwen14b_L1S3_wrong_answer_sample60.md"

SAMPLE_N = 60
SEED = 42

AGG_RE = re.compile(r"\b(COUNT|SUM|AVG|MIN|MAX)\b", re.I)
JOIN_RE = re.compile(r"\bJOIN\b", re.I)
COUNT_DISTINCT_RE = re.compile(r"\bCOUNT\s*\(\s*DISTINCT\b", re.I)
SELECT_DISTINCT_RE = re.compile(r"\bSELECT\s+DISTINCT\b", re.I)


def _agg_set(sql: str) -> frozenset:
    return frozenset(m.upper() for m in AGG_RE.findall(sql))


def _distinct_repairs(sql: str) -> List[str]:
    """Heuristic DISTINCT repairs tried before labelling (b) vs (c)."""
    sql = sql.strip()
    out: List[str] = [sql]
    has_group = bool(re.search(r"\bGROUP\s+BY\b", sql, re.I))

    if not SELECT_DISTINCT_RE.search(sql) and not has_group:
        r = re.sub(r"\bSELECT\b", "SELECT DISTINCT", sql, count=1, flags=re.I)
        if r not in out:
            out.append(r)

    if re.search(r"\bCOUNT\s*\(", sql, re.I) and not COUNT_DISTINCT_RE.search(sql):
        r = re.sub(
            r"\bCOUNT\s*\(\s*(\*|DISTINCT\b)",
            r"COUNT(DISTINCT ",
            sql,
            flags=re.I,
        )
        # Fix double DISTINCT if we hit COUNT(DISTINCT
        r = re.sub(r"COUNT\(DISTINCT\s+DISTINCT\b", "COUNT(DISTINCT", r, flags=re.I)
        if r not in out:
            out.append(r)
        # COUNT(expr) -> COUNT(DISTINCT expr) for non-*
        r2 = re.sub(
            r"\bCOUNT\s*\(\s*(?!\*|DISTINCT)",
            "COUNT(DISTINCT ",
            sql,
            flags=re.I,
        )
        r2 = re.sub(r"COUNT\(DISTINCT\s+DISTINCT\b", "COUNT(DISTINCT", r2, flags=re.I)
        if r2 not in out:
            out.append(r2)

    return out


def _db_paths(db_id: str) -> Tuple[Path, Path]:
    base = DATA_DIR / "dev_databases" / db_id
    return base / f"{db_id}.sqlite", SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id)


def _is_partial_distinct_missing(gold: str, pred: str) -> Tuple[bool, str]:
    """Pattern (b): wide 1NF scan/count without DISTINCT; gold uses JOIN on 3NF."""
    if not (JOIN_RE.search(gold) and "one_nf_0" in pred.lower() and not JOIN_RE.search(pred)):
        return False, ""

    if re.search(r"\bCOUNT\s*\(", pred, re.I) and not COUNT_DISTINCT_RE.search(pred):
        return (
            True,
            "COUNT without DISTINCT on `one_nf_0`; gold JOIN avoids join fan-out on 3NF",
        )

    if (
        not re.search(r"\bGROUP\s+BY\b", pred, re.I)
        and not SELECT_DISTINCT_RE.search(pred)
        and re.search(r"\bSELECT\b", pred, re.I)
        and not re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", pred, re.I)
    ):
        return (
            True,
            "Retrieval SELECT without DISTINCT on denormalised `one_nf_0` (duplicate rows)",
        )

    return False, ""


def _try_repairs_match_gold(
    gold_sql: str, pred_sql: str, db_id: str
) -> Tuple[bool, Optional[str]]:
    db_path, pred_db = _db_paths(db_id)
    for repaired in _distinct_repairs(pred_sql):
        res = evaluate(
            str(db_path),
            repaired,
            gold_sql,
            predicted_db_path=str(pred_db),
        )
        if res.correct:
            return True, repaired
    return False, None


def classify_row(row: dict) -> Tuple[str, str]:
    """Return (category letter, reason)."""
    gold = (row.get("gold_sql") or "").strip()
    pred = (row.get("predicted_sql") or "").strip()
    outcome = row.get("outcome", "")
    db_id = row.get("db_id", "")

    if outcome == "error":
        msg = (row.get("error_msg") or "Predicted SQL failed to execute").strip()
        return "c", f"Execution failure (unrecoverable at evaluation): {msg[:400]}"

    if not pred:
        return "c", "Empty prediction  cannot execute"

    fixed, repaired = _try_repairs_match_gold(gold, pred, db_id)
    if fixed:
        snippet = repaired[:200] + ("" if len(repaired) > 200 else "")
        return "b", f"Multiset matches gold after DISTINCT repair. Example fix: {snippet}"

    gold_aggs = _agg_set(gold)
    pred_aggs = _agg_set(pred)
    gold_join = bool(JOIN_RE.search(gold))
    pred_wide = "one_nf_0" in pred.lower() and not JOIN_RE.search(pred)
    pred_has_distinct = bool(re.search(r"\bDISTINCT\b", pred, re.I))

    # Wrong aggregate family
    if gold_aggs and pred_aggs and gold_aggs != pred_aggs:
        return (
            "a",
            f"Different aggregate / metric: gold uses {sorted(gold_aggs)}; "
            f"predicted uses {sorted(pred_aggs)}",
        )

    # Obvious generation: gold subquery / GROUP BY HAVING pattern missing in pred
    if re.search(r"\bHAVING\b", gold, re.I) and not re.search(r"\bHAVING\b", pred, re.I):
        return "a", "Gold uses HAVING / per-entity subquery; prediction omits or simplifies it"

    if re.search(r"\b/\s*12\b", gold) and not re.search(r"\b/\s*12\b", pred):
        return "a", "Gold divides by 12 (monthly average); prediction omits scaling"

    partial, partial_reason = _is_partial_distinct_missing(gold, pred)
    if partial:
        return "b", partial_reason

    # Fan-out family on 1NF (needs more than DISTINCT keyword)
    if gold_join and pred_wide and pred_aggs:
        if "AVG" in gold_aggs and "AVG" in pred_aggs:
            return (
                "c",
                "AVG over duplicated 1NF rows (and/or missing /12): dedup subquery needed; "
                "adding DISTINCT on the averaged column alone does not match 3NF gold",
            )

        if "SUM" in gold_aggs and "SUM" in pred_aggs:
            return (
                "c",
                "SUM on fan-out 1NF rows: requires deduplicating subquery on fact keys; "
                "simple DISTINCT in SUM is insufficient",
            )

        if "COUNT" in pred_aggs and COUNT_DISTINCT_RE.search(pred):
            return (
                "c",
                "COUNT(DISTINCT) present but multiset still differs  wrong entity key, "
                "filters, or residual 1NF vs 3NF semantics",
            )

        return (
            "c",
            "Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent "
            "deduplication  evaluation asymmetry not fixed by tried DISTINCT patches",
        )

    if not pred_wide and gold_join:
        return "a", "Prediction does not use one_nf_0 wide table as expected for L1"

    return (
        "a",
        "Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair "
        "does not restore gold multiset",
    )


def _escape_md(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def main() -> int:
    rows = list(csv.DictReader(RESULTS_CSV.open(encoding="utf-8")))
    wrong = [
        r
        for r in rows
        if r.get("outcome") != "correct"
        and str(r.get("correct", "")).lower() not in ("true", "1", "yes")
    ]

    classifications: dict[str, Tuple[str, str]] = {}
    for i, row in enumerate(wrong, 1):
        qid = row.get("question_id", str(i))
        classifications[qid] = classify_row(row)
        if i % 25 == 0 or i == len(wrong):
            print(f"Classified {i}/{len(wrong)} failures...", flush=True)

    rng = random.Random(SEED)
    sample = rng.sample(wrong, min(SAMPLE_N, len(wrong)))

    labels: List[str] = []
    records = []
    for row in sample:
        cat, reason = classifications[row["question_id"]]
        labels.append(cat)
        records.append((row, cat, reason))

    # Display order: group by database name, then question_id (sample set unchanged).
    def _sort_key(rec):
        row = rec[0]
        try:
            qid = int(row.get("question_id", 0))
        except (TypeError, ValueError):
            qid = 0
        return (row.get("db_id", ""), qid)

    records.sort(key=_sort_key)

    total = len(labels)
    counts = Counter(labels)
    pct = {k: 100.0 * v / total for k, v in counts.items()}

    pop_labels = [classifications[r["question_id"]][0] for r in wrong]
    pop_counts = Counter(pop_labels)
    pop_pct = {k: 100.0 * v / len(pop_labels) for k, v in pop_counts.items()}

    lines: List[str] = []
    lines.append("# Qwen2.5-Coder-14B  L1S3 wrong-answer sample (n=60)\n\n")
    lines.append(
        "**Source:** `results/full/qwen2.5-coder-14b-local__L1S3.csv`  "
        f"**Population:** {len(wrong)} failures / 397 questions  "
        f"**Sample:** seed={SEED}, n={total}\n\n"
    )
    lines.append("**Setup:** Gold SQL on 3NF SQLite; predicted SQL on `{db_id}__1nf.sqlite` "
                 "(`one_nf_0`). Multiset execution comparison (`evaluator.py`).\n\n")
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
        "| **(c)** | Unrecoverable evaluation artefact | SQL executes but multiset ? gold; "
        "execution errors; or fan-out needs dedup **subquery** (SUM/AVG), not keyword DISTINCT alone |\n"
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
    lines.append(f"\n### Full failure population (n={len(pop_labels)}, same classifier)\n\n")
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
    lines.append(
        f"\n*Sample seed={SEED}. Classification: execute DISTINCT repairs where applicable, "
        "then SQL-shape rules (`analysis/classify_l1s3_qwen14b_sample.py`). "
        "(b) = faithful wide-table SQL missing deduplication; "
        "(c) = SUM/AVG fan-out, execution errors, or DISTINCT present but still mismatched.*\n\n"
    )
    lines.append("---\n\n## Sampled failures\n\n")

    for i, (row, cat, reason) in enumerate(records, 1):
        qid = row.get("question_id", "?")
        db = row.get("db_id", "?")
        diff = row.get("difficulty", "?")
        qtype = row.get("question_type", "?")
        outcome = row.get("outcome", "?")
        lines.append(f"### {i}. Q{qid} ({db}, {diff}, {qtype})  **({cat})**\n\n")
        lines.append(f"**Outcome:** `{outcome}`  **Category ({cat}):** {reason}\n\n")
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
