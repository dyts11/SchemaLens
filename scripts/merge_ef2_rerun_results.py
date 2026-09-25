#!/usr/bin/env python3
"""Copy full experiment result CSVs and replace european_football_2 L1 rows with rerun data."""

from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
ORIGINAL_DIR = RESULTS_DIR / "original"
RERUN_DIR = RESULTS_DIR / "rerun"
OUTPUT_DIR = RESULTS_DIR / "full"

RERUN_PATTERN = re.compile(r"european_football_2__(.+)__(L1S[123])\.csv$")
EF2_DB_ID = "european_football_2"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"No header found in {path}")
        return list(reader.fieldnames), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def merge_file(rerun_path: Path) -> dict[str, int]:
    match = RERUN_PATTERN.match(rerun_path.name)
    if not match:
        raise ValueError(f"Unexpected rerun filename: {rerun_path.name}")

    model, condition = match.group(1), match.group(2)
    orig_path = ORIGINAL_DIR / f"{model}__{condition}.csv"
    if not orig_path.exists():
        raise FileNotFoundError(f"Missing original results file: {orig_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / orig_path.name

    shutil.copy2(orig_path, out_path)

    orig_fieldnames, orig_rows = read_csv(orig_path)
    rerun_fieldnames, rerun_rows = read_csv(rerun_path)
    if orig_fieldnames != rerun_fieldnames:
        raise ValueError(
            f"Header mismatch for {orig_path.name}: "
            f"orig={orig_fieldnames}, rerun={rerun_fieldnames}"
        )

    rerun_by_qid = {row["question_id"]: row for row in rerun_rows}
    if len(rerun_by_qid) != len(rerun_rows):
        raise ValueError(f"Duplicate question_id values in {rerun_path}")

    replaced = 0
    missing_in_rerun: list[str] = []
    merged_rows: list[dict[str, str]] = []

    for row in orig_rows:
        if row["db_id"] != EF2_DB_ID:
            merged_rows.append(row)
            continue
        qid = row["question_id"]
        if qid not in rerun_by_qid:
            missing_in_rerun.append(qid)
            merged_rows.append(row)
            continue
        merged_rows.append(rerun_by_qid[qid])
        replaced += 1

    if missing_in_rerun:
        raise ValueError(
            f"{orig_path.name}: {len(missing_in_rerun)} european_football_2 rows "
            f"not found in rerun ({missing_in_rerun[:5]}...)"
        )

    orig_ef_count = sum(1 for row in orig_rows if row["db_id"] == EF2_DB_ID)
    if replaced != orig_ef_count:
        raise ValueError(
            f"{orig_path.name}: expected to replace {orig_ef_count} rows, replaced {replaced}"
        )
    if replaced != len(rerun_rows):
        raise ValueError(
            f"{orig_path.name}: rerun has {len(rerun_rows)} rows but replaced {replaced}"
        )

    write_csv(out_path, orig_fieldnames, merged_rows)
    return {
        "replaced": replaced,
        "total": len(orig_rows),
        "output": str(out_path),
    }


def main() -> None:
    rerun_files = sorted(RERUN_DIR.glob("european_football_2__*.csv"))
    if not rerun_files:
        raise SystemExit(f"No rerun files found in {RERUN_DIR}")

    print(f"Writing merged copies to {OUTPUT_DIR}")
    total_replaced = 0
    for rerun_path in rerun_files:
        stats = merge_file(rerun_path)
        total_replaced += stats["replaced"]
        print(
            f"  {rerun_path.name} -> {Path(stats['output']).name}: "
            f"replaced {stats['replaced']}/{stats['total']} rows"
        )

    print(f"Done. Updated {len(rerun_files)} files, {total_replaced} european_football_2 rows replaced.")


if __name__ == "__main__":
    main()
