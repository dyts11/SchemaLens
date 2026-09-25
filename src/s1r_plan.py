"""
Build L1/L2 display-column lists for the S1R experiment track.

Physical materialised SQLite files store S3-style names; prompts use
``{table_alias}__{column_alias}`` from column_aliases_s1r.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from preprocess_data.bird_meta import load_dev_entry, tables_cols
from preprocess_data.to_1nf.convert import _parsed_join_steps
from preprocess_data.to_1nf.specs import SPECS as ONE_NF_SPECS
from preprocess_data.to_2nf.convert import _cluster_to_one_nf_spec
from preprocess_data.to_2nf.specs import SPECS as TWO_NF_SPECS
from src.column_aliases_s1r import get_column_name_s1r, get_table_name_s1r


def _s1r_wide_column_name(db_id: str, table: str, column: str) -> str:
    t_alias = get_table_name_s1r(db_id, table)
    c_alias = get_column_name_s1r(db_id, table, column)
    return f"{t_alias}__{c_alias}"


def build_l1_s1r_display_columns(
    db_id: str,
    data_dir: Union[str, Path],
    *,
    tables_path: Union[str, Path, None] = None,
) -> List[str]:
    """Ordered S1R display columns for the L1 wide table (matches 1NF join plan)."""
    if db_id not in ONE_NF_SPECS:
        raise ValueError(f"No 1NF spec for db_id={db_id!r}")

    entry = load_dev_entry(
        db_id, Path(data_dir), tables_path=Path(tables_path) if tables_path else None
    )
    cols_by_table = tables_cols(entry)
    parsed = _parsed_join_steps(
        ONE_NF_SPECS[db_id].anchor_table, ONE_NF_SPECS[db_id].join_steps
    )

    display_cols: List[str] = []
    for tbl, _jt, _on, _prefix, _al in parsed:
        for colinfo in cols_by_table.get(tbl, []):
            display_cols.append(_s1r_wide_column_name(db_id, tbl, colinfo["name"]))
    return display_cols


def build_l2_s1r_display_columns_by_cluster(
    db_id: str,
    data_dir: Union[str, Path],
    *,
    tables_path: Union[str, Path, None] = None,
) -> List[List[str]]:
    """Per-cluster S1R display columns (same order as 2NF materialisation plan)."""
    if db_id not in TWO_NF_SPECS:
        raise ValueError(f"No 2NF spec for db_id={db_id!r}")

    entry = load_dev_entry(
        db_id, Path(data_dir), tables_path=Path(tables_path) if tables_path else None
    )
    cols_by_table = tables_cols(entry)
    out: List[List[str]] = []

    for cluster in TWO_NF_SPECS[db_id].clusters:
        one = _cluster_to_one_nf_spec(cluster)
        parsed = _parsed_join_steps(one.anchor_table, one.join_steps)
        cluster_cols: List[str] = []
        for tbl, _jt, _on, _prefix, _al in parsed:
            for colinfo in cols_by_table.get(tbl, []):
                cluster_cols.append(
                    _s1r_wide_column_name(db_id, tbl, colinfo["name"])
                )
        out.append(cluster_cols)
    return out
