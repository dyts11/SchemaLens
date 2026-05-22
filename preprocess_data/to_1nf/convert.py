"""
Build 1NF wide tables from explicit per-database join plans.

Each database in ``specs.SPECS`` defines an anchor table and a FULL OUTER JOIN chain
on FK keys (composite ``ON`` where needed).

Public API
----------
  build_plan(db_id, data_dir, semantic_level) -> OneNfPlan
  materialize_sqlite(db_id, data_dir, source_sqlite, output_sqlite, semantic_level)
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple, Union

from preprocess_data.bird_meta import load_dev_entry, quote_ident, tables_cols
from preprocess_data.to_1nf.specs import SPECS, JoinOn, JoinStep, OneNfSpec
from src.column_aliases import get_name as _get_alias

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class OneNfPlan:
    db_id: str
    table_name: str
    select_sql: str
    display_columns: List[str]


def _idx_to_label(n: int) -> str:
    """0 → 'a', 25 → 'z', 26 → 'aa', …"""
    label = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        label = chr(ord("a") + r) + label
    return label


def _normalize_join_step(
    step: JoinStep,
) -> Tuple[str, str, Tuple[JoinOn, ...], str | None]:
    """Return (table, join_type, on_pairs, column_prefix)."""
    if len(step) == 2:
        tbl, on_pairs = step  # type: ignore[misc]
        return tbl, "FULL OUTER", on_pairs, None
    if len(step) == 3:
        tbl, join_type, on_pairs = step  # type: ignore[misc]
        return tbl, join_type, on_pairs, None
    if len(step) == 4:
        tbl, join_type, on_pairs, prefix = step  # type: ignore[misc]
        return tbl, join_type, on_pairs, prefix
    raise ValueError(f"invalid join step: {step!r}")


def _parsed_join_steps(
    anchor: str, join_steps: Sequence[JoinStep]
) -> List[Tuple[str, str, Tuple[JoinOn, ...], str | None, str]]:
    """(physical_table, join_type, on_pairs, column_prefix, sql_alias)."""
    out: List[Tuple[str, str, Tuple[JoinOn, ...], str | None, str]] = [
        (anchor, "", (), None, "a0")
    ]
    for i, step in enumerate(join_steps, start=1):
        tbl, join_type, on_pairs, prefix = _normalize_join_step(step)
        out.append((tbl, join_type, on_pairs, prefix, f"a{i}"))
    return out


def _table_has_column(tables_cols: dict[str, List[dict]], table: str, col: str) -> bool:
    return any(c["name"] == col for c in tables_cols.get(table, []))


# Same FK under different column names (2NF COALESCE groups).
_FK_COLUMN_EQUIV: Tuple[frozenset[str], ...] = (
    frozenset({"CDSCode", "cds"}),
    frozenset({"home_team_api_id", "team_api_id"}),
)


def _equiv_column_names(col: str) -> frozenset[str]:
    for group in _FK_COLUMN_EQUIV:
        if col in group:
            return group
    return frozenset({col})


def _left_key_expr(
    col: str,
    accumulated_aliases: Sequence[str],
    alias_to_table: dict[str, str],
    tables_cols: dict[str, List[dict]],
    *,
    fallback_alias: str,
    use_equiv: bool = False,
) -> str:
    """COALESCE FK column(s) across aliases already in the join chain."""
    names = _equiv_column_names(col) if use_equiv else frozenset({col})
    parts: List[str] = []
    for al in accumulated_aliases:
        tbl = alias_to_table[al]
        for cn in sorted(names):
            if _table_has_column(tables_cols, tbl, cn):
                parts.append(f"{al}.{quote_ident(cn)}")
    if not parts:
        return f"{fallback_alias}.{quote_ident(col)}"
    if len(parts) == 1:
        return parts[0]
    return f"COALESCE({', '.join(parts)})"


def _right_key_expr(
    col: str,
    alias: str,
    table: str,
    tables_cols: dict[str, List[dict]],
    *,
    use_equiv: bool = False,
) -> str:
    names = _equiv_column_names(col) if use_equiv else frozenset({col})
    parts: List[str] = []
    for cn in sorted(names):
        if _table_has_column(tables_cols, table, cn):
            parts.append(f"{alias}.{quote_ident(cn)}")
    if not parts:
        return f"{alias}.{quote_ident(col)}"
    if len(parts) == 1:
        return parts[0]
    return f"COALESCE({', '.join(parts)})"


def _join_clause(
    join_type: str,
    source_prefix: str,
    tbl: str,
    alias: str,
    on_pairs: Tuple[JoinOn, ...],
    *,
    accumulated_aliases: Sequence[str] | None = None,
    alias_to_table: dict[str, str] | None = None,
    tables_cols: dict[str, List[dict]] | None = None,
    coalesce_left_keys: bool = False,
) -> str:
    on_parts: List[str] = []
    for left_al, lc, right_al, rc in on_pairs:
        if coalesce_left_keys and accumulated_aliases and alias_to_table and tables_cols:
            left = _left_key_expr(
                lc,
                accumulated_aliases,
                alias_to_table,
                tables_cols,
                fallback_alias=left_al,
                use_equiv=coalesce_left_keys,
            )
        else:
            left = f"{left_al}.{quote_ident(lc)}"
        if coalesce_left_keys and tables_cols:
            right = _right_key_expr(
                rc, right_al, tbl, tables_cols, use_equiv=True
            )
        else:
            right = f"{right_al}.{quote_ident(rc)}"
        on_parts.append(f"{left} = {right}")
    return (
        f"{join_type} JOIN {source_prefix}.{quote_ident(tbl)} AS {alias} "
        f"ON {' AND '.join(on_parts)}"
    )


def _build_select_sql(
    db_id: str,
    spec: OneNfSpec,
    tables_cols: dict[str, List[dict]],
    sem: int,
    *,
    source_prefix: str = "main",
    coalesce_join_keys: bool = False,
) -> Tuple[str, List[str]]:
    parsed = _parsed_join_steps(spec.anchor_table, spec.join_steps)
    alias_to_table = {al: tbl for tbl, _, _, _, al in parsed}

    from_sql = f"{source_prefix}.{quote_ident(spec.anchor_table)} AS a0"
    join_sqls: List[str] = []
    accumulated: List[str] = ["a0"]
    for tbl, join_type, on_pairs, _prefix, al in parsed[1:]:
        join_sqls.append(
            _join_clause(
                join_type,
                source_prefix,
                tbl,
                al,
                on_pairs,
                accumulated_aliases=accumulated,
                alias_to_table=alias_to_table,
                tables_cols=tables_cols,
                coalesce_left_keys=coalesce_join_keys,
            )
        )
        accumulated.append(al)

    select_parts: List[str] = []
    display_cols: List[str] = []
    global_s1 = 0
    for tbl, _jt, _on, col_prefix, al in parsed:
        for colinfo in tables_cols.get(tbl, []):
            cname = colinfo["name"]
            if sem == 1:
                out_alias = f"col_{_idx_to_label(global_s1)}"
                global_s1 += 1
            else:
                mapped = _get_alias(db_id, cname, sem)
                stem = (col_prefix or tbl).replace(" ", "_").replace("-", "_")
                out_alias = f"{stem}__{mapped}"
            qc = quote_ident(cname)
            if _SAFE_IDENT.match(out_alias):
                select_parts.append(f"{al}.{qc} AS {out_alias}")
            else:
                select_parts.append(f"{al}.{qc} AS {quote_ident(out_alias)}")
            display_cols.append(out_alias)

    body = (
        "SELECT\n    "
        + ",\n    ".join(select_parts)
        + f"\nFROM {from_sql}\n"
        + "\n".join(join_sqls)
    )
    return body, display_cols


def build_plan(
    db_id: str,
    data_dir: Union[str, Path],
    semantic_level: int = 3,
    *,
    table_name: str = "one_nf_0",
) -> OneNfPlan:
    if db_id not in SPECS:
        supported = ", ".join(sorted(SPECS))
        raise ValueError(f"No 1NF join spec for db_id={db_id!r}. Supported: {supported}")
    entry = load_dev_entry(db_id, Path(data_dir))
    select_sql, display_cols = _build_select_sql(
        db_id,
        SPECS[db_id],
        tables_cols(entry),
        semantic_level,
        source_prefix="main",
        coalesce_join_keys=True,
    )
    return OneNfPlan(
        db_id=db_id,
        table_name=table_name,
        select_sql=select_sql,
        display_columns=display_cols,
    )


def materialize_sqlite(
    db_id: str,
    data_dir: Union[str, Path],
    source_sqlite: Union[str, Path],
    output_sqlite: Union[str, Path],
    semantic_level: int = 3,
    *,
    attach_alias: str = "orig",
    table_name: str = "one_nf_0",
) -> Path:
    """
    Create a new SQLite file with one materialised 1NF wide table.

    Returns:
        Path to ``output_sqlite``.
    """
    data_dir = Path(data_dir)
    source_sqlite = Path(source_sqlite).resolve()
    output_sqlite = Path(output_sqlite).resolve()
    if not source_sqlite.is_file():
        raise FileNotFoundError(f"Source database not found: {source_sqlite}")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", attach_alias):
        raise ValueError(f"attach_alias must be a simple SQL identifier, got {attach_alias!r}")

    entry = load_dev_entry(db_id, data_dir)
    select_sql, _ = _build_select_sql(
        db_id,
        SPECS[db_id],
        tables_cols(entry),
        semantic_level,
        source_prefix=attach_alias,
        coalesce_join_keys=True,
    )
    ident = quote_ident(table_name)
    create_stmt = f"DROP TABLE IF EXISTS {ident};\nCREATE TABLE {ident} AS\n{select_sql};"

    output_sqlite.parent.mkdir(parents=True, exist_ok=True)
    if output_sqlite.exists():
        output_sqlite.unlink()

    conn = sqlite3.connect(str(output_sqlite))
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        conn.execute(f"ATTACH DATABASE ? AS {attach_alias}", (str(source_sqlite),))
        conn.executescript(create_stmt)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _one_nf_build_meta (k TEXT PRIMARY KEY, v TEXT)"
        )
        conn.execute("INSERT INTO _one_nf_build_meta VALUES ('source_db_id', ?)", (db_id,))
        conn.execute(
            "INSERT INTO _one_nf_build_meta VALUES ('semantic_level', ?)",
            (str(semantic_level),),
        )
        conn.execute(
            "INSERT INTO _one_nf_build_meta VALUES ('anchor_table', ?)",
            (SPECS[db_id].anchor_table,),
        )
        conn.commit()
    finally:
        conn.close()
    return output_sqlite
