#!/usr/bin/env python3
"""
Materialise a **synthetic 2NF-only** SQLite database from a BIRD or Spider source.

Usage (from schema_effect/):

    # BIRD (default)
    python3 -m preprocess_data.to_2nf.build_sqlite --db formula_1 --dry-run
    python3 -m preprocess_data.to_2nf.build_sqlite --db formula_1 --sem 3

    # Spider dev databases
    python3 -m preprocess_data.to_2nf.build_sqlite --db tvshow --dry-run \\
        --spider-dir dev_20240627/spider_data

Default output:
    BIRD  : {data_dir}/dev_databases/{db_id}/{db_id}__2nf.sqlite
    Spider: {spider_dir}/database/{db_id}/{db_id}__2nf.sqlite
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from preprocess_data.data_layout import add_materialize_path_args, resolve_materialize_paths
from preprocess_data.to_2nf.convert import build_plan, describe_plan, materialize_sqlite
from preprocess_data.to_2nf.specs import SPECS


def _load_table_count(tables_json: Path, db_id: str) -> list:
    with open(tables_json, encoding="utf-8") as f:
        for e in json.load(f):
            if e["db_id"] == db_id:
                return e["table_names_original"]
    return []


def main() -> None:
    p = argparse.ArgumentParser(
        description="Materialise synthetic 2NF-only clusters (BIRD or Spider source)."
    )
    p.add_argument(
        "--db",
        default=None,
        help="db_id (see preprocess_data.to_2nf.specs.SPECS)",
    )
    p.add_argument(
        "--sem",
        type=int,
        default=3,
        choices=(1, 2, 3, 4),
        help="Semantic level for physical column aliases (default: 3)",
    )
    add_materialize_path_args(p)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the materialisation plan and exit without creating a file",
    )
    p.add_argument(
        "--list-dbs",
        action="store_true",
        help="List supported db_id values and exit",
    )
    args = p.parse_args()

    data_dir = Path(args.data_dir)
    tables_json_default = (
        Path(args.tables_json)
        if args.tables_json
        else (
            Path(args.spider_dir) / "tables.json"
            if args.spider_dir
            else data_dir / "dev_tables.json"
        )
    )

    if args.list_dbs:
        for db_id in sorted(SPECS):
            spec = SPECS[db_id]
            names = ", ".join(c.output_table for c in spec.clusters)
            n_3nf = len(_load_table_count(tables_json_default, db_id))
            print(
                f"{db_id}: 3NF_tables={n_3nf}  2NF_clusters={len(spec.clusters)}"
            )
            print(f"    {names}")
        return

    if not args.db:
        p.error("--db is required unless --list-dbs is set")

    if args.db not in SPECS:
        supported = ", ".join(sorted(SPECS))
        sys.exit(f"Unknown --db {args.db!r}. Supported: {supported}")

    paths = resolve_materialize_paths(
        args.db,
        data_dir=data_dir,
        variant_suffix="__2nf",
        spider_dir=Path(args.spider_dir) if args.spider_dir else None,
        database_dir=Path(args.database_dir) if args.database_dir else None,
        tables_json=Path(args.tables_json) if args.tables_json else None,
        output=Path(args.output) if args.output else None,
    )

    plan = build_plan(
        args.db,
        data_dir,
        args.sem,
        source_prefix="orig",
        tables_path=paths.tables_json,
    )

    print(f"Layout : {paths.layout}")
    print(f"Tables : {paths.tables_json.resolve()}")
    print(f"Source : {paths.source_sqlite.resolve()}")
    print(f"Output : {paths.output_sqlite.resolve()}")
    print(f"db_id={args.db!r}  semantic_level=S{args.sem}")
    print()
    print(describe_plan(plan, data_dir, tables_path=paths.tables_json))

    if args.dry_run:
        print("(dry-run — no file written)")
        return

    if not paths.source_sqlite.is_file():
        sys.exit(f"Source database not found: {paths.source_sqlite}")

    print("Building…")
    materialize_sqlite(
        args.db,
        data_dir,
        paths.source_sqlite,
        paths.output_sqlite,
        semantic_level=args.sem,
        tables_path=paths.tables_json,
    )
    print("Done.")


if __name__ == "__main__":
    main()
