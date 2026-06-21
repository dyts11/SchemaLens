#!/usr/bin/env python3
"""
Rerun experiment results for one database after rebuilding its schema SQLite.

Loads every question for ``db_id`` from the arcwise question set, then runs
the requested structural x semantic levels for each model. Results are written
to separate CSV files under ``results/rerun/`` - the main ``results/`` CSVs
are never read or modified.

Usage (from schema_effect/):

    # Edit MODELS below, then:
    python -m src.rerun_db_experiment european_football_2

    # Or override models on the command line:
    python -m src.rerun_db_experiment european_football_2 \\
        --models qwen2.5-coder-14b-local gemini-2.5-flash \\
        --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=True)
except ImportError:
    pass

from run_experiment import (  # noqa: E402
    DATA_DIR,
    DELAY_BETWEEN_CALLS,
    MODEL_DELAY,
    append_row,
    build_col_rename_map,
    build_l1_col_rename_map,
    build_l2_col_rename_map,
    load_experiment_questions,
)
from src.evaluator import evaluate
from src.llm_runner import call_llm
from src.prompt_builder import build_prompt
from src.schema_builder import L1_DB_IDS, L2_DB_IDS, SchemaBuilder

# ---------------------------------------------------------------------------
# Configuration - edit this section to change what gets run
# ---------------------------------------------------------------------------

MODELS = [
    "qwen2.5-coder-0.5b-local",
    "qwen2.5-coder-1.5b-local",
    "qwen2.5-coder-3b-local",
    "qwen2.5-coder-7b-local",
    "qwen2.5-coder-14b-local",
    "qwen2.5-coder-32b-local",
    "phi-4-local",
    "olmo-2-13b-local",
]

# L1 predicted SQL runs on ``{db_id}__1nf.sqlite``.
DEFAULT_STRUCTURAL_LEVELS = (1,)
DEFAULT_SEMANTIC_LEVELS = (1, 2, 3)

DEFAULT_RESULTS_DIR = "results/rerun"


def rerun_results_path(
    results_dir: Path,
    db_id: str,
    model: str,
    struct_level: int,
    sem_level: int,
) -> Path:
    """Path for a per-db rerun CSV (separate from main experiment results)."""
    safe_model = model.replace("/", "-")
    return results_dir / f"{db_id}__{safe_model}__L{struct_level}S{sem_level}.csv"


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Rerun experiment results for all questions of one db_id."
    )
    p.add_argument(
        "db_id",
        help="BIRD database id (e.g. european_football_2)",
    )
    p.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Override MODELS in this file (one or more model ids)",
    )
    p.add_argument(
        "--results-dir",
        default=DEFAULT_RESULTS_DIR,
        help=f"Output directory for rerun CSVs (default: {DEFAULT_RESULTS_DIR})",
    )
    p.add_argument(
        "--structural-levels",
        default=",".join(str(x) for x in DEFAULT_STRUCTURAL_LEVELS),
        help="Comma-separated structural levels (default: 1)",
    )
    p.add_argument(
        "--semantic-levels",
        default=",".join(str(x) for x in DEFAULT_SEMANTIC_LEVELS),
        help="Comma-separated semantic levels (default: 1,2,3)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned runs without calling LLMs or writing CSVs",
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


def load_questions_for_db(db_id: str) -> List[dict]:
    """All arcwise questions for ``db_id``, in arcwise file order."""
    questions = [q for q in load_experiment_questions() if q["db_id"] == db_id]
    if not questions:
        raise SystemExit(f"No questions found for db_id={db_id!r} in arcwise_plat_sql.json")
    return questions


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


def run_experiments(
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
        f"\nRunning {len(questions)} questions x {len(conditions)} conditions "
        f"x {len(models)} models = {total} LLM calls"
    )

    results_dir.mkdir(parents=True, exist_ok=True)

    for struct_level, sem_level in conditions:
        condition_label = f"L{struct_level}S{sem_level}"
        for model in models:
            csv_path = rerun_results_path(
                results_dir, db_id, model, struct_level, sem_level
            )
            print(f"\n{'=' * 60}")
            print(f"  {condition_label} | {model}")
            print(f"  Output: {csv_path}")

            if dry_run:
                print(f"  [dry-run] would run {len(questions)} questions")
                done += len(questions)
                continue

            if csv_path.is_file():
                csv_path.unlink()

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

    questions = load_questions_for_db(db_id)
    question_ids = {int(q["question_id"]) for q in questions}

    models = args.models if args.models is not None else MODELS
    if not models:
        raise SystemExit(
            "No models to run: set MODELS in src/rerun_db_experiment.py "
            "or pass --models on the command line."
        )

    print(f"Database     : {db_id}")
    print(f"Questions    : {len(questions)} "
          f"(ids {min(question_ids)}-{max(question_ids)})")
    print(f"Conditions   : {', '.join(f'L{sl}S{sem}' for sl, sem in conditions)}")
    print(f"Models       : {', '.join(models)}")
    print(f"Results dir  : {results_dir}")
    if args.dry_run:
        print("Mode         : dry-run")

    if not args.dry_run:
        _validate_db_prerequisites(db_id, conditions)

    run_experiments(
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
