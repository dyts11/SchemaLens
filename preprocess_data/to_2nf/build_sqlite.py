#!/usr/bin/env python3
"""
Materialise a **synthetic 2NF-only** SQLite database from a BIRD source.

Each database gets one or more **denormalised wide clusters** (same column
naming as ``to_1nf``) where transitive dependencies are kept on the anchor key
(2NF but not 3NF). No separate 3NF lookup copies.

Usage (from schema_effect/):

    # Review plan without writing a file
    python3 -m preprocess_data.to_2nf.build_sqlite --db formula_1 --dry-run

    # Build (after you approve the plan)
    python3 -m preprocess_data.to_2nf.build_sqlite --db formula_1 --sem 3

    python3 -m preprocess_data.to_2nf.build_sqlite --db formula_1 -o /tmp/formula_1__2nf.sqlite

Default output:
    {data_dir}/dev_databases/{db_id}/{db_id}__2nf.sqlite

Supported databases (see preprocess_data.to_2nf.specs.SPECS):
    Nine db_ids (same set as preprocess_data.to_1nf.specs.SPECS).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json

from preprocess_data.to_2nf.convert import build_plan, describe_plan, materialize_sqlite
from preprocess_data.to_2nf.specs import SPECS


def _load_table_count(dev_tables_path: Path, db_id: str) -> list:
    with open(dev_tables_path, encoding="utf-8") as f:
        for e in json.load(f):
            if e["db_id"] == db_id:
                return e["table_names_original"]
    return []


def main() -> None:
    p = argparse.ArgumentParser(
        description="Materialise synthetic 2NF-only (denormalised) clusters into a new SQLite file."
    )
    p.add_argument(
        "--db",
        default=None,
        help="BIRD dev db_id (see preprocess_data.to_2nf.specs.SPECS)",
    )
    p.add_argument(
        "--data-dir",
        default="dev_20240627",
        help="Root with dev_tables.json and dev_databases/ (default: dev_20240627)",
    )
    p.add_argument(
        "--sem",
        type=int,
        default=3,
        choices=(1, 2, 3, 4),
        help="Semantic level for physical column aliases (default: 3, same as to_1nf)",
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output .sqlite path (default: dev_databases/{db}/{db}__2nf.sqlite)",
    )
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

    if args.list_dbs:
        for db_id in sorted(SPECS):
            spec = SPECS[db_id]
            names = ", ".join(c.output_table for c in spec.clusters)
            n_3nf = len(
                _load_table_count(data_dir / "dev_tables.json", db_id)
            )
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

    source = data_dir / "dev_databases" / args.db / f"{args.db}.sqlite"
    out = (
        Path(args.output)
        if args.output
        else data_dir / "dev_databases" / args.db / f"{args.db}__2nf.sqlite"
    )

    plan = build_plan(args.db, data_dir, args.sem, source_prefix="orig")

    print(f"Source : {source.resolve()}")
    print(f"Output : {out.resolve()}")
    print(f"db_id={args.db!r}  semantic_level=S{args.sem}")
    print()
    print(describe_plan(plan, data_dir))

    if args.dry_run:
        print("(dry-run — no file written)")
        return

    if not source.is_file():
        sys.exit(f"Source database not found: {source}")

    print("Building…")
    materialize_sqlite(args.db, data_dir, source, out, semantic_level=args.sem)
    print("Done.")


if __name__ == "__main__":
    main()
