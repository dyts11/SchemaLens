#!/usr/bin/env python3
"""
Re-evaluate Spider L1/L2 result CSVs in place (no LLM calls).

Updates outcome, correct, and error_msg using current materialised __1nf / __2nf
databases and the same evaluation logic as run_experiment.py.

Usage (from schema_effect/):

    python -m src.reevaluate_spider_l1_l2
    python -m src.reevaluate_spider_l1_l2 --results-dir results/spider --dry-run
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from preprocess_data.data_layout import DataLayout
from run_experiment import CSV_COLUMNS, DATA_DIR
from src.evaluator import (
    _build_pred_connection,
    build_l1_col_rename_map,
    build_l2_col_rename_map,
    evaluate,
)
from src.schema_builder import L1_DB_IDS, L2_DB_IDS, SchemaBuilder

_L12_PATTERN = re.compile(r"__L([12])S([1-3])\.csv$", re.IGNORECASE)
DEFAULT_SPIDER_DIR = os.path.join(DATA_DIR, "spider_data")
DEFAULT_RESULTS_DIR = "results/spider"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Re-evaluate Spider L1/L2 CSVs in place.")
    p.add_argument(
        "--spider-dir",
        default=DEFAULT_SPIDER_DIR,
        help=f"Spider data root (default: {DEFAULT_SPIDER_DIR})",
    )
    p.add_argument(
        "--results-dir",
        default=DEFAULT_RESULTS_DIR,
        help=f"Folder of result CSVs (default: {DEFAULT_RESULTS_DIR})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only; do not write CSVs",
    )
    p.add_argument(
        "--backup",
        action="store_true",
        help="Write .csv.bak before updating each file",
    )
    return p.parse_args()


def _l12_csv_paths(results_dir: str) -> List[Path]:
    paths = sorted(Path(results_dir).glob("*__L*S*.csv"))
    out: List[Path] = []
    for p in paths:
        if _L12_PATTERN.search(p.name):
            out.append(p)
    return out


def _write_csv(csv_path: Path, rows: List[dict]) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = _parse_args()
    layout = DataLayout.create(DATA_DIR, spider_dir=args.spider_dir)
    tables_path = str(layout.tables_json)
    csv_paths = _l12_csv_paths(args.results_dir)

    if not csv_paths:
        print(f"No L1/L2 CSVs found in {args.results_dir}")
        return

    db_ids = ("car_1", "tvshow")
    sem_levels = (1, 2, 3)
    l1_rename_maps = {
        (db_id, sem): build_l1_col_rename_map(db_id, DATA_DIR, sem, tables_path)
        for db_id in db_ids
        if db_id in L1_DB_IDS
        for sem in sem_levels
    }
    l2_rename_maps = {
        (db_id, sem): build_l2_col_rename_map(db_id, DATA_DIR, sem, tables_path)
        for db_id in db_ids
        if db_id in L2_DB_IDS
        for sem in sem_levels
    }

    print(f"Spider dir   : {args.spider_dir}")
    print(f"Results dir  : {args.results_dir}")
    print(f"Files        : {len(csv_paths)} L1/L2 CSVs")
    if args.dry_run:
        print("Mode         : dry-run")
    print()

    total_rows = 0
    total_correct = 0
    total_err_before = 0
    total_err_after = 0

    for csv_path in csv_paths:
        if args.dry_run:
            with open(csv_path, newline="", encoding="utf-8") as f:
                n = sum(1 for _ in csv.DictReader(f))
            err = 0
            with open(csv_path, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("outcome") == "error":
                        err += 1
            print(f"  [dry-run] {csv_path.name}: {n} rows, {err} errors currently")
            continue

        # Load, re-evaluate, write (need rows in memory for write)
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        errors_before = sum(1 for r in rows if r.get("outcome") == "error")
        struct_level = int(rows[0]["structural_level"])
        sem_level = int(rows[0]["semantic_level"])

        pred_conn_by_db: Dict[Tuple[str, int], object] = {}
        correct_after = 0
        try:
            for row in rows:
                db_id = row["db_id"]
                db_path = str(layout.source_sqlite(db_id))
                if struct_level == 1:
                    mat_path = str(
                        SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id, layout)
                    )
                    mat_rename = l1_rename_maps.get((db_id, sem_level))
                else:
                    mat_path = str(
                        SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id, layout)
                    )
                    mat_rename = l2_rename_maps.get((db_id, sem_level))

                conn_key = (db_id, struct_level)
                if conn_key not in pred_conn_by_db:
                    pred_conn_by_db[conn_key] = _build_pred_connection(
                        mat_path, mat_rename or {}
                    )

                result = evaluate(
                    db_path,
                    row["predicted_sql"],
                    row["gold_sql"],
                    col_rename_map=mat_rename,
                    predicted_db_path=mat_path,
                    pred_reuse_connection=pred_conn_by_db[conn_key],
                    verbose=False,
                )
                row["outcome"] = result.outcome
                row["correct"] = str(result.correct)
                row["error_msg"] = result.error_msg or ""
                if result.correct:
                    correct_after += 1
        finally:
            for conn in pred_conn_by_db.values():
                try:
                    conn.close()
                except Exception:
                    pass

        errors_after = sum(1 for r in rows if r.get("outcome") == "error")

        if args.backup:
            shutil.copy2(csv_path, csv_path.with_suffix(csv_path.suffix + ".bak"))

        _write_csv(csv_path, rows)

        acc = correct_after / len(rows) if rows else 0.0
        print(
            f"  {csv_path.name}: {correct_after}/{len(rows)} correct ({acc:.1%}) "
            f"| errors {errors_before} -> {errors_after}"
        )

        total_rows += len(rows)
        total_correct += correct_after
        total_err_before += errors_before
        total_err_after += errors_after

    if not args.dry_run and total_rows:
        print()
        print(
            f"Done. {total_correct}/{total_rows} correct overall "
            f"({total_correct/total_rows:.1%})"
        )
        print(f"Errors: {total_err_before} -> {total_err_after}")


if __name__ == "__main__":
    main()
