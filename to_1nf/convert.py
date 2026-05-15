"""
Build 1NF wide tables from explicit per-database join plans.

Each database with a spec in ``to_1nf.specs.SPECS`` defines:

  • Anchor = main fact table (e.g. ``results`` for formula_1).
  • Dimensions joined on full FK keys before high-cardinality children.
  • Composite keys where needed (e.g. lapTimes on raceId + driverId).

Public API
----------
  build_plan(db_id, data_dir, semantic_level) -> OneNfPlan
  view_ddls(plan) -> list[str]
  format_schema_prompt(plan) -> str
  materialize_sqlite(db_id, data_dir, source_sqlite, output_sqlite, semantic_level)
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple, Union

from src.column_aliases import get_name as _get_alias
from to_1nf.specs import SPECS, JoinOn, OneNfSpec

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


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _load_dev_entry(db_id: str, data_dir: Path) -> dict:
    tables_path = data_dir / "dev_tables.json"
    with open(tables_path, encoding="utf-8") as f:
        all_entries = json.load(f)
    return next(t for t in all_entries if t["db_id"] == db_id)


def _tables_cols(entry: dict) -> dict[str, List[dict]]:
    out: dict[str, List[dict]] = {t: [] for t in entry["table_names_original"]}
    for table_idx, col_name in entry["column_names_original"]:
        if table_idx == -1:
            continue
        out[entry["table_names_original"][table_idx]].append({"name": col_name})
    return out


def _alias_for_table(
    anchor: str, join_steps: Sequence[Tuple[str, Tuple[JoinOn, ...]]]
) -> dict[str, str]:
    aliases = {anchor: "a0"}
    for i, (tbl, _) in enumerate(join_steps, start=1):
        aliases[tbl] = f"a{i}"
    return aliases


def _build_select_sql(
    db_id: str,
    spec: OneNfSpec,
    tables_cols: dict[str, List[dict]],
    sem: int,
    *,
    source_prefix: str = "main",
) -> Tuple[str, List[str]]:
    alias_by_table = _alias_for_table(spec.anchor_table, spec.join_steps)
    join_order = [spec.anchor_table] + [t for t, _ in spec.join_steps]

    from_sql = f"{source_prefix}.{_quote_ident(spec.anchor_table)} AS a0"
    join_sqls: List[str] = []
    for tbl, on_pairs in spec.join_steps:
        al = alias_by_table[tbl]
        on_parts = [
            f"{left_al}.{_quote_ident(lc)} = {al}.{_quote_ident(rc)}"
            for left_al, lc, _right_al, rc in on_pairs
        ]
        join_sqls.append(
            f"LEFT JOIN {source_prefix}.{_quote_ident(tbl)} AS {al} "
            f"ON {' AND '.join(on_parts)}"
        )

    select_parts: List[str] = []
    display_cols: List[str] = []
    global_s1 = 0
    for tbl in join_order:
        al = alias_by_table[tbl]
        for colinfo in tables_cols.get(tbl, []):
            cname = colinfo["name"]
            if sem == 1:
                out_alias = f"col_{_idx_to_label(global_s1)}"
                global_s1 += 1
            else:
                mapped = _get_alias(db_id, cname, sem)
                stem = tbl.replace(" ", "_").replace("-", "_")
                out_alias = f"{stem}__{mapped}"
            qc = _quote_ident(cname)
            if _SAFE_IDENT.match(out_alias):
                select_parts.append(f"{al}.{qc} AS {out_alias}")
            else:
                select_parts.append(f"{al}.{qc} AS {_quote_ident(out_alias)}")
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
    entry = _load_dev_entry(db_id, Path(data_dir))
    select_sql, display_cols = _build_select_sql(
        db_id, SPECS[db_id], _tables_cols(entry), semantic_level, source_prefix="main"
    )
    return OneNfPlan(
        db_id=db_id,
        table_name=table_name,
        select_sql=select_sql,
        display_columns=display_cols,
    )


def view_ddls(plan: OneNfPlan) -> List[str]:
    """CREATE TEMP VIEW statements for execution-backed L1 evaluation."""
    ident = _quote_ident(plan.table_name)
    return [f"CREATE TEMP VIEW {ident} AS\n{plan.select_sql};"]


def format_schema_prompt(plan: OneNfPlan) -> str:
    from src.schema_builder import _quote_if_needed

    lines = [
        "-- L1 · 1NF wide table (fact-anchored join; composite FK keys where needed).",
        "-- Each cell is scalar; redundancy is intentional.",
        f"-- Query table: {plan.table_name}",
        "",
        f"TABLE {plan.table_name} (",
        "    " + ",\n    ".join(_quote_if_needed(c) for c in plan.display_columns),
        ")",
    ]
    return "\n".join(lines)


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

    entry = _load_dev_entry(db_id, data_dir)
    select_sql, _ = _build_select_sql(
        db_id,
        SPECS[db_id],
        _tables_cols(entry),
        semantic_level,
        source_prefix=attach_alias,
    )
    ident = _quote_ident(table_name)
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
