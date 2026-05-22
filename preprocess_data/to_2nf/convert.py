"""
Build **synthetic 2NF-only** SQLite databases: denormalised wide clusters
(2NF with transitive dependencies kept — not 3NF), plus optional narrow support
tables copied from the source.

Uses the same SELECT/JOIN/column-alias logic as ``preprocess_data.to_1nf``.

Public API
----------
  build_plan(db_id, data_dir, semantic_level) -> TwoNfPlan
  describe_plan(plan) -> str
  materialize_sqlite(db_id, data_dir, source_sqlite, output_sqlite, semantic_level)
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from preprocess_data.bird_meta import load_dev_entry, quote_ident, tables_cols
from preprocess_data.to_1nf.convert import _build_select_sql
from preprocess_data.to_1nf.specs import OneNfSpec
from preprocess_data.to_2nf.specs import SPECS, TwoNfClusterSpec, TwoNfDbSpec, join_step_table

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class ClusterMaterialization:
    output_table: str
    select_sql: str
    display_columns: List[str]


@dataclass
class TwoNfPlan:
    db_id: str
    semantic_level: int
    clusters: List[ClusterMaterialization]


def _cluster_to_one_nf_spec(c: TwoNfClusterSpec) -> OneNfSpec:
    return OneNfSpec(anchor_table=c.anchor_table, join_steps=c.join_steps)


def build_plan(
    db_id: str,
    data_dir: Union[str, Path],
    semantic_level: int = 3,
    *,
    source_prefix: str = "main",
) -> TwoNfPlan:
    if db_id not in SPECS:
        supported = ", ".join(sorted(SPECS))
        raise ValueError(f"No 2NF spec for db_id={db_id!r}. Supported: {supported}")
    if semantic_level not in (1, 2, 3, 4):
        raise ValueError(f"semantic_level must be 1–4, got {semantic_level}")

    spec: TwoNfDbSpec = SPECS[db_id]
    entry = load_dev_entry(db_id, Path(data_dir))
    cols_by_table = tables_cols(entry)

    clusters: List[ClusterMaterialization] = []
    for c in spec.clusters:
        if not _SAFE_IDENT.match(c.output_table):
            raise ValueError(f"unsafe output_table name: {c.output_table!r}")
        one = _cluster_to_one_nf_spec(c)
        select_sql, display_cols = _build_select_sql(
            db_id,
            one,
            cols_by_table,
            semantic_level,
            source_prefix=source_prefix,
            coalesce_join_keys=True,
        )
        clusters.append(
            ClusterMaterialization(
                output_table=c.output_table,
                select_sql=select_sql,
                display_columns=display_cols,
            )
        )

    return TwoNfPlan(
        db_id=db_id,
        semantic_level=semantic_level,
        clusters=clusters,
    )


def _anchor_pk_labels(db_id: str, data_dir: Path) -> dict[str, str]:
    entry = load_dev_entry(db_id, data_dir)
    col_lookup = {}
    for idx, (ti, cn) in enumerate(entry["column_names_original"]):
        if ti == -1:
            continue
        col_lookup[idx] = {"table": entry["table_names_original"][ti], "name": cn}
    by_table: dict[str, str] = {}
    for pk in entry["primary_keys"]:
        if isinstance(pk, list):
            t = col_lookup[pk[0]]["table"]
            by_table[t] = "(" + ", ".join(col_lookup[i]["name"] for i in pk) + ")"
        else:
            t = col_lookup[pk]["table"]
            by_table[t] = col_lookup[pk]["name"]
    return by_table


def describe_plan(plan: TwoNfPlan, data_dir: Union[str, Path] = "dev_20240627") -> str:
    pks = _anchor_pk_labels(plan.db_id, Path(data_dir))
    spec = SPECS[plan.db_id]
    lines = [
        f"db_id={plan.db_id!r}  semantic_level=S{plan.semantic_level}",
        "Synthetic 2NF-only: FULL OUTER clusters, COALESCE on left FK keys.",
        "",
        f"Wide clusters ({len(plan.clusters)}):",
    ]
    for c, cl in zip(plan.clusters, spec.clusters):
        joined = [join_step_table(s) for s in cl.join_steps]
        pk = pks.get(cl.anchor_table, "?")
        lines.append(
            f"  • {c.output_table}  anchor={cl.anchor_table}  PK={pk}  "
            f"({len(c.display_columns)} cols)"
        )
        if joined:
            lines.append(f"      joins: {', '.join(joined)}")
    lines.append("")
    lines.append("Example DDL (first cluster):")
    first = plan.clusters[0]
    ident = quote_ident(first.output_table)
    lines.append(f"CREATE TABLE {ident} AS\n{first.select_sql};")
    return "\n".join(lines)


def materialize_sqlite(
    db_id: str,
    data_dir: Union[str, Path],
    source_sqlite: Union[str, Path],
    output_sqlite: Union[str, Path],
    semantic_level: int = 3,
    *,
    attach_alias: str = "orig",
) -> Path:
    """
    Create ``output_sqlite`` with all wide 2NF clusters.

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

    plan = build_plan(db_id, data_dir, semantic_level, source_prefix=attach_alias)
    spec = SPECS[db_id]

    probe = sqlite3.connect(str(source_sqlite))
    try:
        existing = {
            row[0]
            for row in probe.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        probe.close()

    ddl_parts: List[str] = []
    built_clusters: List[str] = []
    for c, cl in zip(plan.clusters, spec.clusters):
        if cl.anchor_table not in existing:
            print(
                f"[to_2nf] Skipping cluster {c.output_table!r}: "
                f"anchor {cl.anchor_table!r} not in source {source_sqlite.name}"
            )
            continue
        ident = quote_ident(c.output_table)
        ddl_parts.append(f"DROP TABLE IF EXISTS {ident};")
        ddl_parts.append(f"CREATE TABLE {ident} AS\n{c.select_sql};")
        built_clusters.append(c.output_table)

    output_sqlite.parent.mkdir(parents=True, exist_ok=True)
    if output_sqlite.exists():
        output_sqlite.unlink()

    conn = sqlite3.connect(str(output_sqlite))
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        conn.execute(f"ATTACH DATABASE ? AS {attach_alias}", (str(source_sqlite),))
        conn.executescript("\n".join(ddl_parts))

        conn.execute(
            "CREATE TABLE IF NOT EXISTS _two_nf_build_meta (k TEXT PRIMARY KEY, v TEXT)"
        )
        conn.execute("DELETE FROM _two_nf_build_meta")
        conn.execute(
            "INSERT INTO _two_nf_build_meta VALUES ('source_db_id', ?)", (db_id,)
        )
        conn.execute(
            "INSERT INTO _two_nf_build_meta VALUES ('semantic_level', ?)",
            (str(semantic_level),),
        )
        conn.execute(
            "INSERT INTO _two_nf_build_meta VALUES ('normal_form', ?)",
            ("synthetic_2nf_not_3nf",),
        )
        conn.execute(
            "INSERT INTO _two_nf_build_meta VALUES ('cluster_tables', ?)",
            (",".join(built_clusters),),
        )
        conn.commit()
    finally:
        conn.close()

    return output_sqlite
