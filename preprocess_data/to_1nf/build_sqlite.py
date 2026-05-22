#!/usr/bin/env python3
"""
Materialise a 1NF wide SQLite table from a BIRD source database.

Usage (from schema_effect/):

    python3 -m preprocess_data.to_1nf.build_sqlite --db formula_1
    python3 -m preprocess_data.to_1nf.build_sqlite --db formula_1 --sem 3 -o /tmp/formula_1__1nf.sqlite

Default output:
    {data_dir}/dev_databases/{db_id}/{db_id}__1nf.sqlite
    (physical S3 column names; S1/S2 use TEMP VIEW renaming at eval time, like L3)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from preprocess_data.to_1nf.convert import materialize_sqlite


def main() -> None:
    p = argparse.ArgumentParser(description="Materialise 1NF wide table into a new SQLite file.")
    p.add_argument(
        "--db",
        required=True,
        help="BIRD dev db_id (see preprocess_data.to_1nf.specs.SPECS)",
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
        help="Semantic level for column aliases (default: 3)",
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output .sqlite path (default: dev_databases/{db}/{db}__1nf.sqlite)",
    )
    args = p.parse_args()

    data_dir = Path(args.data_dir)
    source = data_dir / "dev_databases" / args.db / f"{args.db}.sqlite"
    if args.output:
        out = Path(args.output)
    else:
        out = data_dir / "dev_databases" / args.db / f"{args.db}__1nf.sqlite"

    print(f"Source : {source.resolve()}")
    print(f"Output : {out.resolve()}")
    print(f"db_id={args.db!r}  semantic_level={args.sem}")
    print("Building…")

    materialize_sqlite(args.db, data_dir, source, out, semantic_level=args.sem)
    print("Done.")


if __name__ == "__main__":
    main()
