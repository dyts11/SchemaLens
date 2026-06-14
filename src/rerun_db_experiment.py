#!/usr/bin/env python3
"""
Purge and rerun experiment results for one database.

Use after rebuilding a materialised schema (e.g. 1NF SQLite) for a single db_id.
By default only L1 conditions are rerun (predicted SQL uses `{db_id}__1nf.sqlite`).

Usage (from schema_effect/):

    # Preview deletions for european_football_2 L1 results
    python -m src.rerun_db_experiment european_football_2 --dry-run

    # Delete stale rows and rerun L1 x S1-S3 for all models with existing CSVs
    python -m src.rerun_db_experiment european_football_2

    # Limit models or structural levels
    python -m src.rerun_db_experiment european_football_2 \\
        --models qwen2.5-coder-14b-local gemini-2.5-flash \\
        --structural-levels 1
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=True)
except ImportError:
    pass

from run_experiment import (  # noqa: E402
    CSV_COLUMNS,
    DATA_DIR,
    DELAY_BETWEEN_CALLS,
    MODEL_DELAY,
    append_row,
    build_col_rename_map,
    build_l1_col_rename_map,
    build_l2_col_rename_map,
    load_experiment_questions,
    results_file,
)
from src.evaluator import evaluate
from src.llm_runner import call_llm
from src.prompt_builder import build_prompt
from src.schema_builder import L1_DB_IDS, L2_DB_IDS, SchemaBuilder


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Delete results for one db_id and rerun those questions."
    )
    p.add_argument(
        "db_id",
        help="BIRD database id (e.g. european_football_2)",
    )
    p.add_argument(
        "--results-dir",
        default="results",
        help="Directory with {model}__L{l}S{s}.csv files (default: results)",
    )
    p.add_argument(
        "--structural-levels",
        default="1",
        help="Comma-separated structural levels to purge/rerun (default: 1)",
    )
    p.add_argument(
        "--semantic-levels",
        default="1,2,3",
        help="Comma-separated semantic levels to purge/rerun (default: 1,2,3)",
    )
    p.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Models to rerun (default: every model with a matching results CSV)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned deletions/reruns without writing or calling LLMs",
    )
    p.add_argument(
        "--delete-only",
        action="store_true",
        help="Remove stale rows only; do not rerun",
    )
    return p.parse_args(argv)


def _parse_int_list(spec: str, name: str) -> List[int]:
    out: List[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    if not out:
        raise ValueError(f"{name} must list at least one integer")
    return out


def _conditions(
    structural_levels: Iterable[int],
    semantic_levels: Iterable[int],
) -> List[Tuple[int, int]]:
    return [(sl, sem) for sl in structural_levels for sem in semantic_levels]


def _discover_models(results_dir: Path, conditions: List[Tuple[int, int]]) -> List[str]:
    wanted = {f"__L{sl}S{sem}.csv" for sl, sem in conditions}
    models: Set[str] = set()
    for path in results_dir.glob("*.csv"):
        name = path.name
        for suffix in wanted:
            if name.endswith(suffix):
                model = name[: -len(suffix)]
                if model:
                    models.add(model)
                break
    return sorted(models)


def _target_csv_paths(
    results_dir: Path,
    models: Sequence[str],
    conditions: List[Tuple[int, int]],
) -> List[Path]:
    paths: List[Path] = []
    for model in models:
        for sl, sem in conditions:
            paths.append(results_dir / Path(results_file(model, sl, sem)).name)
    return paths


def purge_db_rows(
    csv_path: Path,
    db_id: str,
    *,
    dry_run: bool,
) -> Tuple[int, int]:
    """Remove rows with matching db_id. Returns (rows_before, rows_removed)."""
    if not csv_path.is_file():
        return 0, 0

    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return 0, 0
        rows = list(reader)

    before = len(rows)
    kept = [r for r in rows if r.get("db_id") != db_id]
    removed = before - len(kept)
    if removed and not dry_run:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(kept)
    return before, removed


def _validate_db_prerequisites(db_id: str, conditions: List[Tuple[int, int]]) -> None:
    struct_levels = {sl for sl, _ in conditions}
    missing: List[str] = []

    p3 = _ROOT / DATA_DIR / "dev_databases" / db_id / f"{db_id}.sqlite"
    if not p3.is_file():
        missing.append(f"3NF: {p3}")

    if 1 in struct_levels:
        if db_id not in L1_DB_IDS:
            missing.append(f"L1: no 1NF spec for {db_id!r}")
        elif not SchemaBuilder.has_one_nf_database(DATA_DIR, db_id):
            missing.append(
                f"L1: missing {SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id)}"
            )

    if 2 in struct_levels:
        if db_id not in L2_DB_IDS:
            missing.append(f"L2: no 2NF spec for {db_id!r}")
        elif not SchemaBuilder.has_two_nf_database(DATA_DIR, db_id):
            missing.append(
                f"L2: missing {SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id)}"
            )

    if missing:
        raise FileNotFoundError(
            "Missing prerequisites:\n" + "\n".join(f"  - {m}" for m in missing)
        )


def rerun(
    db_id: str,
    *,
    results_dir: Path,
    conditions: List[Tuple[int, int]],
    models: Sequence[str],
    questions: List[dict],
    dry_run: bool,
) -> None:
    builder = SchemaBuilder(db_id, DATA_DIR)
    sem_levels = sorted({sem for _, sem in conditions})

    rename_maps = {
        sem: build_col_rename_map(db_id, DATA_DIR, sem) for sem in sem_levels
    }
    l1_rename_maps = {
        sem: build_l1_col_rename_map(db_id, DATA_DIR, sem) for sem in sem_levels
    }
    l2_rename_maps = {
        sem: build_l2_col_rename_map(db_id, DATA_DIR, sem) for sem in sem_levels
    }

    db_path = str(_ROOT / DATA_DIR / "dev_databases" / db_id / f"{db_id}.sqlite")
    total = len(conditions) * len(models) * len(questions)
    done = 0

    print(
        f"\nRerunning {len(questions)} questions x {len(conditions)} conditions "
        f"x {len(models)} models = {total} LLM calls"
    )

    for struct_level, sem_level in conditions:
        condition_label = f"L{struct_level}S{sem_level}"
        for model in models:
            csv_path = results_dir / Path(results_file(model, struct_level, sem_level)).name
            print(f"\n{'=' * 60}")
            print(f"  {condition_label} | {model}")
            print(f"  Output: {csv_path}")

            if dry_run:
                print(f"  [dry-run] would run {len(questions)} questions")
                done += len(questions)
                continue

            pred_conn = None
            try:
                for q in questions:
                    schema = builder.build(struct_level, sem_level)
                    prompt = build_prompt(
                        schema, q["question"], structural_level=struct_level
                    )
                    predicted_sql = call_llm(model, prompt)

                    if struct_level in (1, 2):
                        from src.evaluator import _build_pred_connection

                        if struct_level == 1:
                            mat_path = str(
                                SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id)
                            )
                            mat_rename = l1_rename_maps.get(sem_level)
                        else:
                            mat_path = str(
                                SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id)
                            )
                            mat_rename = l2_rename_maps.get(sem_level)

                        if pred_conn is None:
                            pred_conn = _build_pred_connection(
                                mat_path, mat_rename or {}
                            )
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            col_rename_map=mat_rename,
                            predicted_db_path=mat_path,
                            pred_reuse_connection=pred_conn,
                            verbose=False,
                        )
                    else:
                        col_rename_map = rename_maps.get(sem_level)
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            col_rename_map=col_rename_map,
                            verbose=False,
                        )

                    append_row(
                        str(csv_path),
                        {
                            "question_id": q["question_id"],
                            "db_id": db_id,
                            "difficulty": q["difficulty"],
                            "question_type": q["question_type"],
                            "structural_level": struct_level,
                            "semantic_level": sem_level,
                            "model": model,
                            "gold_sql": q["SQL"],
                            "predicted_sql": predicted_sql,
                            "outcome": result.outcome,
                            "correct": result.correct,
                            "error_msg": result.error_msg or "",
                        },
                    )
                    done += 1
                    acc_note = "ok" if result.correct else result.outcome
                    print(
                        f"  [{done}/{total}] Q{q['question_id']} {acc_note}",
                        flush=True,
                    )
                    time.sleep(MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS))
            finally:
                if pred_conn is not None:
                    try:
                        pred_conn.close()
                    except Exception:
                        pass


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    db_id = args.db_id
    results_dir = (_ROOT / args.results_dir).resolve()
    struct_levels = _parse_int_list(args.structural_levels, "--structural-levels")
    sem_levels = _parse_int_list(args.semantic_levels, "--semantic-levels")
    conditions = _conditions(struct_levels, sem_levels)

    all_questions = load_experiment_questions()
    questions = [q for q in all_questions if q["db_id"] == db_id]
    if not questions:
        raise SystemExit(f"No questions found for db_id={db_id!r} in arcwise_plat_sql.json")

    models = args.models or _discover_models(results_dir, conditions)
    if not models:
        raise SystemExit(
            f"No results CSVs found under {results_dir} for conditions {conditions}"
        )

    csv_paths = _target_csv_paths(results_dir, models, conditions)

    print(f"Database     : {db_id}")
    print(f"Questions    : {len(questions)}")
    print(f"Conditions   : {', '.join(f'L{sl}S{sem}' for sl, sem in conditions)}")
    print(f"Models       : {', '.join(models)}")
    print(f"Results dir  : {results_dir}")
    if args.dry_run:
        print("Mode         : dry-run")
    if args.delete_only:
        print("Mode         : delete-only")

    total_removed = 0
    print("\nPurging stale rows:")
    for path in csv_paths:
        before, removed = purge_db_rows(path, db_id, dry_run=args.dry_run)
        if removed or path.is_file():
            action = "would remove" if args.dry_run else "removed"
            print(f"  {path.name}: {action} {removed} / {before} rows")
        total_removed += removed
    print(f"Total rows {'to remove' if args.dry_run else 'removed'}: {total_removed}")

    if args.delete_only:
        return

    if not args.dry_run:
        _validate_db_prerequisites(db_id, conditions)

    rerun(
        db_id,
        results_dir=results_dir,
        conditions=conditions,
        models=models,
        questions=questions,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        print("\nDone.")


if __name__ == "__main__":
    main()
