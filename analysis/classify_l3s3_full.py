#!/usr/bin/env python3
"""
Full-population automated classifier for qwen2.5-coder-14b-local L3.S3, under the
7-category taxonomy in docs/error_analysis/error_taxonomy.md.

Unlike analysis/classify_l1s3_qwen14b_sample.py (heuristic, L1-specific, samples 60),
this classifies all 284 L3.S3 failures using:

  - the real S3 column-rename map (build_col_rename_map) to know exactly which
    column names the model actually saw per table, so "does this identifier exist
    anywhere in the schema" is a real schema lookup, not a guess;
  - regex-based structural extraction of tables / GROUP BY / HAVING / subqueries /
    set operations from gold and predicted SQL, compared against each other.

This is a rule-based classifier, not an LLM classifier: it reliably detects wrong-TABLE
issues (table-set comparison) and execution-error routing (Invalid SQL vs JOIN vs
Schema linking, via the real schema), but it UNDER-counts same-table wrong-COLUMN
choices (e.g. ranking by the wrong existing column on a table it got right) into
"Other", because distinguishing "wrong column semantically" from "wrong literal/logic"
without a real SQL semantic parse is unreliable by regex alone. See the "Known
limitations" section of the generated report.

Output: docs/error_analysis/qwen14b_L3S3_full_error_analysis.md
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.evaluator import build_col_rename_map

DATA_DIR = _ROOT / "dev_20240627"
TABLES_PATH = DATA_DIR / "dev_tables.json"
RESULTS_CSV = _ROOT / "results" / "full" / "qwen2.5-coder-14b-local__L3S3.csv"
OUT_MD = _ROOT / "docs" / "qwen14b_L3S3_full_error_analysis.md"

# Manual labels for the n=60 sample from docs/error_analysis/qwen14b_L3S3_error_taxonomy.md,
# used only to report agreement between the automated classifier and the
# human-annotated sample (§5.2 validation procedure, calibration step).
MANUAL_LABELS: Dict[str, str] = {}
for qid in ("1039", "1068", "1078", "954", "1003", "1361", "1381", "1409", "1411", "717", "268"):
    MANUAL_LABELS[qid] = "correct"
for qid in ("32", "1528", "125", "194", "868", "959"):
    MANUAL_LABELS[qid] = "join"
for qid in ("48", "79", "1147", "149", "152", "846", "865", "950", "990", "1403", "1422", "1164", "1187", "206"):
    MANUAL_LABELS[qid] = "schema_linking"
for qid in ("1498",):
    MANUAL_LABELS[qid] = "groupby"
# Q1092/Q212 are tie-preserving HAVING patterns (`HAVING x = (SELECT MAX(...))`);
# per error_taxonomy.md's resolved rule, HAVING mismatches are Nesting, not GROUP BY.
for qid in ("1092", "212"):
    MANUAL_LABELS[qid] = "nesting"
for qid in ("41",):
    MANUAL_LABELS[qid] = "nesting"
for qid in (
    "1476", "1493", "1505", "1506", "1529", "1036", "1037", "1105", "1136", "95",
    "118", "967", "981", "1394", "723", "724", "782", "791", "1150", "1209",
    "1225", "1229", "1265", "1275", "219",
):
    MANUAL_LABELS[qid] = "other"

CATEGORY_ORDER = [
    "invalid_sql",
    "schema_linking",
    "join",
    "fanout",
    "groupby",
    "nesting",
    "other",
]
CATEGORY_LABEL = {
    "invalid_sql": "Invalid SQL",
    "schema_linking": "Schema linking",
    "join": "JOIN errors",
    "fanout": "Fan-out",
    "groupby": "GROUP BY errors",
    "nesting": "Nesting problem",
    "other": "Other",
    "correct": "Correct",
}

FROM_JOIN_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+`?\"?\[?(\w+)\]?\"?`?", re.IGNORECASE
)
TABLE_ALIAS_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+`?\"?\[?(\w+)\]?\"?`?\s*(?:AS\s+)?(`?\"?(\w+)`?\"?)?",
    re.IGNORECASE,
)
CTE_NAME_RE = re.compile(r"\bWITH\s+(\w+)\s+AS\s*\(", re.IGNORECASE)
SELECT_LIST_RE = re.compile(r"\bSELECT\b\s+(?:DISTINCT\s+)?(.*?)\bFROM\b", re.IGNORECASE | re.DOTALL)
QUALIFIED_COL_RE = re.compile(r"\b(\w+)\.(\w+)\b")
NO_SUCH_COLUMN_RE = re.compile(r"no such column:\s*([\w.]+)", re.IGNORECASE)
NO_SUCH_TABLE_RE = re.compile(r"no such table:\s*([\w.]+)", re.IGNORECASE)
GROUP_BY_RE = re.compile(r"\bGROUP\s+BY\b", re.IGNORECASE)
HAVING_RE = re.compile(r"\bHAVING\b", re.IGNORECASE)
SETOP_RE = re.compile(r"\b(UNION|INTERSECT|EXCEPT)\b", re.IGNORECASE)
WINDOW_RE = re.compile(r"\bOVER\s*\(", re.IGNORECASE)

_RESERVED_ALIAS_WORDS = {
    "where", "group", "order", "having", "limit", "on", "inner", "left", "right",
    "outer", "join", "union", "intersect", "except", "and", "or", "as", "select",
    "from", "set", "cross", "natural", "using",
}


def _cte_names(sql: str) -> Set[str]:
    return {m.group(1).lower() for m in CTE_NAME_RE.finditer(sql)}


def _tables_in(sql: str) -> Set[str]:
    ctes = _cte_names(sql)
    return {m.group(1).lower() for m in FROM_JOIN_RE.finditer(sql)} - ctes


def _table_aliases(sql: str) -> Dict[str, str]:
    """Map both bare table names and their aliases (lowercased) to the real table name."""
    ctes = _cte_names(sql)
    aliases: Dict[str, str] = {}
    for m in TABLE_ALIAS_RE.finditer(sql):
        table = m.group(1).lower()
        if table in ctes:
            continue
        aliases[table] = table
        alias = m.group(3)
        if alias and alias.lower() not in _RESERVED_ALIAS_WORDS and alias.lower() != table:
            aliases[alias.lower()] = table
    return aliases


def _select_list_tables(sql: str) -> Set[str]:
    """Tables referenced via qualified `alias.column` in the outer SELECT list."""
    m = SELECT_LIST_RE.search(sql)
    if not m:
        return set()
    select_list = m.group(1)
    aliases = _table_aliases(sql)
    tables = set()
    for qm in QUALIFIED_COL_RE.finditer(select_list):
        prefix = qm.group(1).lower()
        if prefix in aliases:
            tables.add(aliases[prefix])
    return tables


class DbSchema:
    """Per-database schema as actually exposed to the model at S3 (post-rename)."""

    def __init__(self, db_id: str, tables_entry: dict):
        self.db_id = db_id
        self.table_names: Set[str] = {t.lower() for t in tables_entry["table_names_original"]}

        rename_map = build_col_rename_map(db_id, str(DATA_DIR), semantic_level=3, tables_path=str(TABLES_PATH))
        table_cols: Dict[str, Set[str]] = defaultdict(set)

        if rename_map is not None:
            for table, pairs in rename_map.items():
                for _orig, mapped in pairs:
                    table_cols[table.lower()].add(mapped.lower())
        else:
            # No renaming anywhere in this db: exposed names == original names.
            table_names = tables_entry["table_names_original"]
            for table_idx, col_name in tables_entry["column_names_original"]:
                if table_idx == -1:
                    continue
                table_cols[table_names[table_idx].lower()].add(col_name.lower())

        self.table_cols = table_cols  # table -> set(exposed column names)
        col_owners: Dict[str, Set[str]] = defaultdict(set)
        for table, cols in table_cols.items():
            for c in cols:
                col_owners[c].add(table)
        self.col_owners = col_owners  # exposed column name -> set(tables that have it)

    def table_exists(self, name: str) -> bool:
        return name.lower() in self.table_names

    def column_owners(self, name: str) -> Set[str]:
        # Strip a table/alias qualifier if present (e.g. "frpm.school_ownership_code").
        bare = name.split(".")[-1].strip("`\"[]")
        return self.col_owners.get(bare.lower(), set())


def _load_schemas(db_ids: Set[str]) -> Dict[str, DbSchema]:
    all_entries = json.load(TABLES_PATH.open(encoding="utf-8"))
    by_id = {e["db_id"]: e for e in all_entries}
    return {db_id: DbSchema(db_id, by_id[db_id]) for db_id in db_ids if db_id in by_id}


def classify(row: dict, schema: DbSchema) -> Tuple[str, str, str]:
    """Return (category, subtype, reason)."""
    gold_sql = row.get("gold_sql") or ""
    pred_sql = row.get("predicted_sql") or ""
    outcome = row.get("outcome", "")
    error_msg = row.get("error_msg") or ""

    if outcome == "error":
        col_m = NO_SUCH_COLUMN_RE.search(error_msg)
        tbl_m = NO_SUCH_TABLE_RE.search(error_msg)

        if tbl_m:
            name = tbl_m.group(1)
            if not schema.table_exists(name):
                return "invalid_sql", "wrong_table", f"`{name}` is not a real table in this schema"
            # Real table name but still errored (rare: case/quoting edge case) -> fall through.

        if col_m:
            name = col_m.group(1)
            owners = schema.column_owners(name)
            if not owners:
                return "invalid_sql", "wrong_column", f"`{name}` does not exist anywhere in this schema"
            gold_tables = _tables_in(gold_sql)
            if owners & gold_tables:
                return (
                    "join",
                    "wrong_table",
                    f"`{name}` exists on {sorted(owners)}, which gold joins but prediction doesn't",
                )
            return (
                "schema_linking",
                "wrong_column",
                f"`{name}` exists on {sorted(owners)} (not referenced by gold either) — wrong column, no join needed",
            )

        # Execution error without a recognisable "no such X" message (syntax, type, etc.)
        return "invalid_sql", "other_execution_error", (error_msg[:200] or "execution failed")

    # wrong_answer: structural comparison. CTE names are excluded from _tables_in,
    # so a query using a CTE alias as its outer FROM target doesn't look like a
    # missing/extra real table.
    gold_tables, pred_tables = _tables_in(gold_sql), _tables_in(pred_sql)
    if gold_tables != pred_tables:
        missing = gold_tables - pred_tables
        extra = pred_tables - gold_tables
        if missing and extra:
            # Real substitution (at least one table swapped for another), regardless
            # of whether the counts happen to match — this is a table-choice mistake,
            # not a join-plan mistake.
            return (
                "schema_linking",
                "wrong_table",
                f"table substitution: gold uses {sorted(missing)}, prediction uses {sorted(extra)} instead",
            )
        if extra and not missing:
            # Purely additive: does the prediction's own SELECT list actually pull
            # its answer from the extra table? If so this is a wrong-table choice
            # that happens to require an extra join, not a join-plan mistake.
            select_tables = _select_list_tables(pred_sql)
            if select_tables & extra:
                return (
                    "schema_linking",
                    "wrong_table",
                    f"prediction selects from {sorted(select_tables & extra)}, "
                    f"a table gold never uses — wrong table for the answer itself",
                )
            return "join", "extra_table", f"prediction adds {sorted(extra)} not in gold — changes join grain"
        return "join", "missing_table", f"prediction omits {sorted(missing)} that gold joins"

    gold_gb, pred_gb = bool(GROUP_BY_RE.search(gold_sql)), bool(GROUP_BY_RE.search(pred_sql))
    if gold_gb != pred_gb:
        return (
            "groupby",
            "missing_or_extra_groupby",
            f"gold GROUP BY={gold_gb}, prediction GROUP BY={pred_gb}",
        )

    # HAVING is a post-aggregation filter, not the GROUP BY clause itself, so a
    # HAVING mismatch is Nesting — not GROUP BY — regardless of whether it
    # contains a literal subquery (per error_taxonomy.md's resolved rule).
    gold_hv, pred_hv = bool(HAVING_RE.search(gold_sql)), bool(HAVING_RE.search(pred_sql))
    if gold_hv != pred_hv:
        return "nesting", "having_mismatch", f"gold HAVING={gold_hv}, prediction HAVING={pred_hv}"

    gold_so, pred_so = bool(SETOP_RE.search(gold_sql)), bool(SETOP_RE.search(pred_sql))
    gold_win, pred_win = bool(WINDOW_RE.search(gold_sql)), bool(WINDOW_RE.search(pred_sql))
    gold_cte, pred_cte = bool(_cte_names(gold_sql)), bool(_cte_names(pred_sql))
    if gold_so != pred_so:
        return "nesting", "set_op_mismatch", f"gold set-op={gold_so}, prediction set-op={pred_so}"
    if gold_win != pred_win:
        return "nesting", "window_fn_mismatch", f"gold window fn={gold_win}, prediction window fn={pred_win}"
    if gold_cte != pred_cte:
        return "nesting", "cte_mismatch", f"gold CTE={gold_cte}, prediction CTE={pred_cte}"

    # NOTE: a raw "number of SELECT keywords differs" check was tried here and
    # removed — it fires on ordinary `WHERE x IN (SELECT ...)` filtering subqueries
    # that both gold and prediction use idiomatically, which is not a nesting
    # *problem*, just a stylistic difference. Genuine nesting failures are caught
    # above via CTE/window/set-op presence; anything else falls through to Other.
    return "other", "value_or_logic", "same tables/join/group-by/nesting shape — literal, formula, or logic mismatch"


def main() -> int:
    rows = list(csv.DictReader(RESULTS_CSV.open(encoding="utf-8")))
    failures = [r for r in rows if r.get("outcome") != "correct"]
    db_ids = {r["db_id"] for r in failures}
    schemas = _load_schemas(db_ids)

    results = []
    for row in failures:
        db_id = row["db_id"]
        schema = schemas.get(db_id)
        if schema is None:
            cat, sub, reason = "other", "unknown_db", "schema not found"
        else:
            cat, sub, reason = classify(row, schema)
        results.append((row, cat, sub, reason))

    counts = Counter(cat for _, cat, _, _ in results)
    subtype_counts: Dict[str, Counter] = defaultdict(Counter)
    for _, cat, sub, _ in results:
        subtype_counts[cat][sub] += 1

    by_db_cat: Dict[str, Counter] = defaultdict(Counter)
    for row, cat, _, _ in results:
        by_db_cat[row["db_id"]][cat] += 1

    # Agreement check against the n=60 manual sample.
    agree, disagree, checked = 0, 0, 0
    disagreements: List[Tuple[str, str, str]] = []
    manual_pred_rows = {r["question_id"]: r for r in rows}
    for qid, manual_cat in MANUAL_LABELS.items():
        if manual_cat == "correct":
            continue
        row = manual_pred_rows.get(qid)
        if row is None or row.get("outcome") == "correct":
            continue
        schema = schemas.get(row["db_id"])
        if schema is None:
            continue
        auto_cat, _, _ = classify(row, schema)
        checked += 1
        if auto_cat == manual_cat:
            agree += 1
        else:
            disagree += 1
            disagreements.append((qid, manual_cat, auto_cat))

    total_failures = len(failures)
    lines: List[str] = []
    lines.append("# Qwen2.5-Coder-14B · L3·S3 full error analysis (n=284, automated)\n\n")
    lines.append(
        f"**Source:** `results/full/qwen2.5-coder-14b-local__L3S3.csv` · "
        f"**Population:** {total_failures} failures / 397 questions (113 correct)\n\n"
    )
    lines.append(
        "**Method:** rule-based classifier (`analysis/classify_l3s3_full.py`) applying the "
        "7-category priority order from `docs/error_analysis/error_taxonomy.md` to **every** failure, not a "
        "sample. Schema existence checks use the real S3 column-rename map "
        "(`build_col_rename_map`), so \"does this identifier exist\" reflects exactly what the "
        "model saw. This is a mechanical classifier, not an LLM classifier — see **Known "
        "limitations** before treating category boundaries as precise.\n\n"
    )

    lines.append("## Summary (all 284 failures)\n\n")
    lines.append("| Category | Count | % of failures |\n")
    lines.append("|----------|------:|----------------:|\n")
    for cat in CATEGORY_ORDER:
        c = counts.get(cat, 0)
        pct = 100.0 * c / total_failures if total_failures else 0.0
        note = " *(N/A at L3 — no materialised denormalised surface)*" if cat == "fanout" else ""
        lines.append(f"| {CATEGORY_LABEL[cat]} | {c} | {pct:.1f}%{note} |\n")
    lines.append(f"| **Total** | {total_failures} | 100.0% |\n\n")

    lines.append("## Subtype breakdown\n\n")
    for cat in CATEGORY_ORDER:
        if not subtype_counts.get(cat):
            continue
        lines.append(f"### {CATEGORY_LABEL[cat]}\n\n")
        lines.append("| Subtype | Count |\n|---------|------:|\n")
        for sub, c in subtype_counts[cat].most_common():
            lines.append(f"| {sub} | {c} |\n")
        lines.append("\n")

    lines.append("## By database\n\n")
    all_dbs = sorted(by_db_cat.keys())
    db_cat_cols = [c for c in CATEGORY_ORDER if c != "fanout"]
    header = "| Database | " + " | ".join(CATEGORY_LABEL[c] for c in db_cat_cols) + " | Total |\n"
    lines.append(header)
    lines.append("|" + "---|" * (len(db_cat_cols) + 2) + "\n")
    for db in all_dbs:
        row_counts = by_db_cat[db]
        total_db = sum(row_counts.values())
        cells = " | ".join(str(row_counts.get(c, 0)) for c in CATEGORY_ORDER if c != "fanout")
        lines.append(f"| {db} | {cells} | {total_db} |\n")
    lines.append("\n")

    lines.append("## Agreement with the n=60 manual sample\n\n")
    lines.append(
        f"Checked {checked} non-correct questions from the manually-labelled sample "
        f"(`docs/error_analysis/qwen14b_L3S3_error_taxonomy.md`) against this automated classifier: "
        f"**{agree}/{checked} agree ({100.0*agree/checked:.1f}%)**.\n\n"
    )
    if disagreements:
        lines.append("| QID | Manual label | Automated label |\n|-----|--------------|-------------------|\n")
        for qid, manual_cat, auto_cat in disagreements:
            lines.append(f"| Q{qid} | {CATEGORY_LABEL[manual_cat]} | {CATEGORY_LABEL[auto_cat]} |\n")
        lines.append("\n")

    lines.append("## Calibration history\n\n")
    lines.append(
        "This classifier went through one calibration pass against the n=60 manual sample: "
        "agreement went from **75.5% (37/49)** to **83.7% (41/49)** after two fixes, both kept "
        "in the current code:\n\n"
    )
    lines.append(
        "1. **CTE names are excluded from the table-set comparison** (`_tables_in` subtracts "
        "`WITH x AS (...)` names), and CTE-presence mismatch was added as its own Nesting "
        "signal alongside set-operator and window-function mismatch. Before this fix, a CTE "
        "name like `ranked` in `WITH ranked AS (...) SELECT ... FROM ranked` looked like a "
        "missing real table, misrouting the failure to JOIN.\n"
    )
    lines.append(
        "2. **The raw \"subquery count differs\" signal for Nesting was removed.** It fired on "
        "ordinary `WHERE x IN (SELECT ...)` filtering subqueries that both gold and prediction "
        "use idiomatically — not a nesting *problem* by any reasonable reading. Nesting is now "
        "detected only via CTE/window-function/set-operator presence mismatches, which are "
        "real structural signals. This dropped Nesting from 28 (9.9%) to 4 (1.4%) — the manual "
        "sample's rate is 2.0% (1/49), so the two now agree.\n"
    )
    lines.append(
        "3. **Extra/missing-table cases now check whether the prediction's own SELECT list "
        "pulls its answer from the extra table** (via alias resolution). If it does, that's "
        "reclassified from JOIN to Schema linking — an extra join whose whole purpose was "
        "sourcing the (wrong) answer column is a table-choice mistake, not a join-plan mistake. "
        "This fixed 2 of the original 4 same-pattern disagreements (Q1422, Q1187) and, combined "
        "with also treating differing-size *substitutions* (both a missing and an extra table, "
        "not just equal-size swaps) as Schema linking, fixed Q206 too. Schema linking rose from "
        "16 (5.6%) to 23 (8.1%); JOIN fell from 84 (29.6%) to 72 (25.4%).\n\n"
    )
    lines.append("## Remaining disagreements (8/49) — read before trusting a specific count\n\n")
    lines.append(
        "- **Q1147, Q152, Q865, Q1164** (manual: Schema linking; auto: Other) — all four are "
        "**same-table wrong-column choices** (e.g. ranking by `strength` instead of "
        "`overall_rating`, both on the same joined table). Table sets match exactly, so there is "
        "no structural signal left to catch these — they fall to Other by construction. This is "
        "the single largest remaining gap: **Schema linking's true rate is still higher than "
        "this doc's 8.1%**, and Other's true rate is correspondingly lower than 56.3%.\n"
    )
    lines.append(
        "- **Q1403** (manual: Schema linking; auto: JOIN, extra_table) — the extra joined table "
        "(`expense`) doesn't feed the SELECT list directly (the model recomputed overspend via "
        "`SUM(expense.cost) - budget.amount` instead of using the existing `budget.remaining` "
        "column), so the alias-resolution check doesn't catch it. Recognising \"a column already "
        "exists for exactly this purpose and was ignored\" needs semantic knowledge this "
        "classifier doesn't have.\n"
    )
    lines.append(
        "- **Q41, Q95** (manual: Nesting / Other; auto: GROUP BY) — on inspection these are "
        "**arguably relabels, not classifier errors**: gold in both cases has no top-level "
        "`GROUP BY` (Q41 uses a window function instead; Q95 has an unrelated grouping "
        "artefact one level up) while the prediction adds one that gold doesn't have. Per "
        "`error_taxonomy.md`'s own priority order (GROUP BY checked before Nesting/Other), a "
        "genuine `GROUP BY`-presence mismatch outranks the manual labels chosen for these two "
        "during the original by-hand pass — the manual doc, not the classifier, is the looser "
        "of the two here.\n"
    )
    lines.append(
        "- **Q219** (manual: Other; auto: JOIN, missing_table) — gold joins `atom` and the "
        "prediction drops it entirely, which is a genuine structural omission; the manual pass "
        "weighted the (also-present) invented literal values as the more salient cause. Both "
        "readings are defensible; this is a real judgment call, not a bug.\n\n"
    )
    lines.append("## Known limitations\n\n")
    lines.append(
        "- **Same-table wrong-column choices fall into \"Other\", not \"Schema linking\"** — "
        "see Q1147/Q152/Q865/Q1164 above. This is the dominant remaining gap and is not fixable "
        "without a real semantic parse of which column the question actually refers to.\n"
    )
    lines.append(
        "- **An extra join is only reclassified to Schema linking if the SELECT list directly "
        "references it** via a resolvable alias — extra joins that only feed a `WHERE`/`ORDER "
        "BY`/aggregate expression (like Q1403) still default to JOIN.\n"
    )
    lines.append(
        "- **JOIN key mismatches within an unchanged table set are not detected** (e.g. joining "
        "on the wrong FK column when both tables were already correct, without changing which "
        "tables are used) — these fall into GROUP BY/Nesting/Other depending on what else "
        "differs.\n"
    )
    lines.append(
        "- **Alias resolution is regex-based, not a real SQL parser** — it can mis-attribute "
        "aliases in unusual formatting (no `AS`, nested parens, multiple statements) though this "
        "wasn't observed to matter in the n=60 spot-check.\n"
    )
    lines.append(
        "- Treat this doc as the **full-population, mechanical complement** to the "
        "`qwen14b_L3S3_error_taxonomy.md` manual n=60: use the manual doc's category boundaries "
        "as ground truth on close calls, and this doc's per-database breakdown as the "
        "large-sample view, keeping the Schema-linking-vs-Other undercount above in mind.\n"
    )

    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print("Counts:", dict(counts))
    print(f"Agreement: {agree}/{checked} ({100.0*agree/checked:.1f}%)" if checked else "no agreement check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
