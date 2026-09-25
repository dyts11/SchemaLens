"""
Evaluation helpers for the S1R (randomized table + column alias) experiment track.

L3-L6: temp views use S1R table names over physical tables.
L1/L2: materialised DB stores S3 physical columns; map to S1R display names.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from preprocess_data.to_2nf.convert import build_plan as build_2nf_plan
from preprocess_data.to_1nf.convert import build_plan as build_1nf_plan
from src.column_aliases_s1r import get_column_name_s1r, get_table_name_s1r
from src.schema_builder import L1_TABLE_NAME
from src.s1r_plan import (
    build_l1_s1r_display_columns,
    build_l2_s1r_display_columns_by_cluster,
)


# Stored in result CSVs to distinguish from baseline S1 (semantic_level=1).
S1R_SEMANTIC_LEVEL = 1

# view_name -> (physical_table, [(physical_col, display_col), ...])
S1RViewSpec = Dict[str, Tuple[str, List[Tuple[str, str]]]]


def build_s1r_l3_view_spec(
    db_id: str,
    data_dir: str,
    tables_path: Optional[str] = None,
) -> S1RViewSpec:
    """
    Build view spec for L3-L6: S1R table names shadowing original physical tables.
    """
    tables_path = (
        Path(tables_path) if tables_path else Path(data_dir) / "dev_tables.json"
    )
    with open(tables_path, encoding="utf-8") as f:
        all_entries = json.load(f)
    entry = next(t for t in all_entries if t["db_id"] == db_id)

    table_names = entry["table_names_original"]
    cols_by_table: Dict[str, List[str]] = {t: [] for t in table_names}
    for table_idx, col_name in entry["column_names_original"]:
        if table_idx == -1:
            continue
        cols_by_table[table_names[table_idx]].append(col_name)

    spec: S1RViewSpec = {}
    for orig_table, orig_cols in cols_by_table.items():
        s1r_table = get_table_name_s1r(db_id, orig_table)
        pairs = [
            (
                orig,
                get_column_name_s1r(db_id, orig_table, orig),
            )
            for orig in orig_cols
        ]
        spec[s1r_table] = (orig_table, pairs)
    return spec


def build_l1_s1r_rename_map(
    db_id: str,
    data_dir: str,
    tables_path: Optional[str] = None,
) -> Optional[Dict[str, List[Tuple[str, str]]]]:
    """Physical S3 columns in ``one_nf_0`` ? S1R display names."""
    tp = Path(tables_path) if tables_path else None
    phys = build_1nf_plan(
        db_id, data_dir, semantic_level=3, tables_path=tp
    ).display_columns
    disp = build_l1_s1r_display_columns(db_id, data_dir, tables_path=tp)
    if phys == disp:
        return None
    return {L1_TABLE_NAME: list(zip(phys, disp))}


def build_l2_s1r_rename_map(
    db_id: str,
    data_dir: str,
    tables_path: Optional[str] = None,
) -> Optional[Dict[str, List[Tuple[str, str]]]]:
    """Physical S3 columns per 2NF cluster ? S1R display names."""
    from preprocess_data.to_2nf.specs import SPECS

    if db_id not in SPECS:
        return None

    tp = Path(tables_path) if tables_path else None
    plan_phys = build_2nf_plan(db_id, data_dir, semantic_level=3, tables_path=tp)
    s1r_by_cluster = build_l2_s1r_display_columns_by_cluster(
        db_id, data_dir, tables_path=tp
    )

    rename_map: Dict[str, List[Tuple[str, str]]] = {}
    any_changed = False
    for cluster_phys, s1r_cols in zip(plan_phys.clusters, s1r_by_cluster):
        phys_cols = cluster_phys.display_columns
        if phys_cols != s1r_cols:
            rename_map[cluster_phys.output_table] = list(zip(phys_cols, s1r_cols))
            any_changed = True
    return rename_map if any_changed else None


def build_s1r_pred_connection_l3(
    db_path: str,
    view_spec: S1RViewSpec,
) -> sqlite3.Connection:
    """
    Open DB and install TEMP VIEWs named with S1R table aliases.

    Each view selects from the physical table (main schema) with S1R column aliases.
    """
    conn = sqlite3.connect(db_path)
    conn.text_factory = str
    for s1r_table, (phys_table, pairs) in view_spec.items():
        select_parts = [
            f'main."{phys_table}"."{orig_col}" AS `{mapped_col}`'
            for orig_col, mapped_col in pairs
        ]
        view_sql = (
            f'CREATE TEMP VIEW "{s1r_table}" AS '
            f'SELECT {", ".join(select_parts)} '
            f'FROM main."{phys_table}"'
        )
        try:
            conn.execute(view_sql)
        except sqlite3.OperationalError as e:
            print(
                f"[evaluator_s1r] Warning: could not create TEMP VIEW "
                f"'{s1r_table}' -> '{phys_table}': {e}"
            )
    return conn


def build_s1r_pred_connection_materialised(
    db_path: str,
    col_rename_map: Dict[str, List[Tuple[str, str]]],
) -> sqlite3.Connection:
    """L1/L2: same-table views with column renames only (reuse baseline logic)."""
    from src.evaluator import _build_pred_connection

    return _build_pred_connection(db_path, col_rename_map)
