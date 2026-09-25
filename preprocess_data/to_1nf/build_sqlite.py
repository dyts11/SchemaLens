#!/usr/bin/env python3
"""
Materialise a 1NF wide SQLite table from a BIRD or Spider source database.

Usage (from schema_effect/):

    # BIRD (default)
    python3 -m preprocess_data.to_1nf.build_sqlite --db formula_1

    # Spider dev databases
    python3 -m preprocess_data.to_1nf.build_sqlite --db car_1 \\
        --spider-dir dev_20240627/spider_data

Default output:
    BIRD  : {data_dir}/dev_databases/{db_id}/{db_id}__1nf.sqlite
    Spider: {spider_dir}/database/{db_id}/{db_id}__1nf.sqlite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from preprocess_data.data_layout import add_materialize_path_args, resolve_materialize_paths
from preprocess_data.to_1nf.convert import materialize_sqlite


def main() -> None:
    p = argparse.ArgumentParser(
        description="Materialise 1NF wide table into a new SQLite file (BIRD or Spider)."
    )
    p.add_argument(
        "--db",
        required=True,
        help="db_id (see preprocess_data.to_1nf.specs.SPECS)",
    )
    p.add_argument(
        "--sem",
        type=int,
        default=3,
        choices=(1, 2, 3, 4),
        help="Semantic level for column aliases (default: 3)",
    )
    add_materialize_path_args(p)
    args = p.parse_args()

    paths = resolve_materialize_paths(
        args.db,
        data_dir=Path(args.data_dir),
        variant_suffix="__1nf",
        spider_dir=Path(args.spider_dir) if args.spider_dir else None,
        database_dir=Path(args.database_dir) if args.database_dir else None,
        tables_json=Path(args.tables_json) if args.tables_json else None,
        output=Path(args.output) if args.output else None,
    )

    print(f"Layout : {paths.layout}")
    print(f"Tables : {paths.tables_json.resolve()}")
    print(f"Source : {paths.source_sqlite.resolve()}")
    print(f"Output : {paths.output_sqlite.resolve()}")
    print(f"db_id={args.db!r}  semantic_level={args.sem}")
    print("Building…")

    materialize_sqlite(
        args.db,
        Path(args.data_dir),
        paths.source_sqlite,
        paths.output_sqlite,
        semantic_level=args.sem,
        tables_path=paths.tables_json,
    )
    print("Done.")


if __name__ == "__main__":
    main()
