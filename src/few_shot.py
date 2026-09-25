"""
few_shot.py

Fixed per-database few-shot examples for the schema-effect experiment.

Example source:
  dev_20240627/few_shot_examples.json  — one entry per DB per difficulty level.
  Each entry stores three SQL variants:
    sql_l3  — original 3NF SQL (gold SQL, usually correct as-is)
    sql_l2  — manually adjusted for the 2NF (two_nf_*) schema
    sql_l1  — manually adjusted for the 1NF flat (one_nf_0) schema
  L4-L6 use sql_l3 (same 3NF table structure).

  Edit dev_20240627/few_shot_examples.json to fix the sql_l1 / sql_l2 entries.
  sql_l3 is the gold SQL and should not normally need editing.

Semantic adaptation (S1/S2):
  SQL stored in the JSON uses S3 (original / descriptive) column names.
  At runtime we apply the appropriate rename map for the current semantic level:
    L1  → build_l1_col_rename_map  (physical L1 col names → S1/S2 display names)
    L2  → build_l2_col_rename_map  (physical L2 col names → S1/S2 display names)
    L3+ → build_col_rename_map     (original 3NF names    → S1/S2 display names)
  S1 names are fixed-positional (col_a, col_b, …), not random (that is S1R).

Reserved questions:
  The three questions per DB are also removed from the evaluation set so no
  question serves as both example and test item.
"""

import json
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

BIRD_DIFFICULTIES = ("simple", "moderate", "challenging")
_FEW_SHOT_JSON = "dev_20240627/few_shot_examples.json"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_few_shot_json(
    path: str = _FEW_SHOT_JSON,
) -> Dict[str, List[dict]]:
    """
    Load the curated few-shot examples file.
    Returns {db_id: [{"difficulty", "question", "sql_l1", "sql_l2", "sql_l3"}, ...]}.
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_sql_for_struct_level(example: dict, struct_level: int) -> str:
    """Return the SQL variant that matches the structural level."""
    if struct_level == 1:
        return example["sql_l1"]
    if struct_level == 2:
        return example["sql_l2"]
    # L3–L6 all use the original 3NF SQL
    return example["sql_l3"]


# ---------------------------------------------------------------------------
# Reserved-question selection (unchanged)
# ---------------------------------------------------------------------------

def select_fixed_examples_by_difficulty(
    questions: List[dict],
    difficulties: Tuple[str, ...] = BIRD_DIFFICULTIES,
) -> Tuple[Dict[str, List[Tuple[str, str]]], Set[int]]:
    """
    Pick one question per difficulty level per db_id as fixed few-shot examples.

    Returns:
        db_examples:  {db_id: [(question_text, gold_sql), ...]}
        reserved_ids: question_ids to remove from the evaluation set.
    """
    by_db_by_diff: Dict[str, Dict[str, List[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for q in questions:
        diff = q.get("difficulty") or "unknown"
        by_db_by_diff[q["db_id"]][diff].append(q)

    db_examples: Dict[str, List[Tuple[str, str]]] = {}
    reserved_ids: Set[int] = set()

    for db_id, by_diff in by_db_by_diff.items():
        examples: List[Tuple[str, str]] = []
        for diff in difficulties:
            candidates = by_diff.get(diff, [])
            if candidates:
                rec = candidates[0]
                examples.append((rec["question"], rec["SQL"]))
                reserved_ids.add(int(rec["question_id"]))
        db_examples[db_id] = examples

    return db_examples, reserved_ids


# ---------------------------------------------------------------------------
# Semantic adaptation (S1/S2/S3)
# ---------------------------------------------------------------------------

def adapt_sql_to_semantic_level(
    sql: str,
    col_rename_map: Optional[Dict[str, List[Tuple[str, str]]]],
) -> str:
    """
    Replace column names in example SQL with the display names for the current
    semantic level.  Uses word-boundary regex to avoid partial matches.
    Pass col_rename_map=None when no renaming is needed (S3 with original names).
    """
    if not col_rename_map:
        return sql
    for _table, pairs in col_rename_map.items():
        for orig, mapped in pairs:
            if orig == mapped or not orig:
                continue
            sql = re.sub(
                r"\b" + re.escape(orig) + r"\b",
                mapped,
                sql,
                flags=re.IGNORECASE,
            )
    return sql
