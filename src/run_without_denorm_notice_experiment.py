#!/usr/bin/env python3
"""
L1/L2 experiment without the Schema Denormalization Notice (main 397-question set).

Same question selection as run_experiment.py (9 DBs, excluding card_games and
codebase_community). Writes one CSV per condition under results/without_denorm_notice/.

Usage (from schema_effect/):

    python -m src.run_without_denorm_notice_experiment
    python -m src.run_without_denorm_notice_experiment --dry-run
    python -m src.run_without_denorm_notice_experiment --models qwen2.5-coder-14b-local
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=True)
except ImportError:
    pass

from run_experiment import (  # noqa: E402
    ARCWISE_EXCLUDED_DB_IDS,
    DATA_DIR,
    DELAY_BETWEEN_CALLS,
    MODEL_DELAY,
    append_row,
    load_completed_with_correct,
    load_experiment_questions,
    print_progress,
    select_questions,
    validate_run_prerequisites,
)
from src.evaluator import (  # noqa: E402
    build_col_rename_map,
    build_l1_col_rename_map,
    build_l2_col_rename_map,
    evaluate,
)
from src.llm_runner import call_llm  # noqa: E402
from src.prompt_builder import build_prompt  # noqa: E402
from src.schema_builder import L1_DB_IDS, L2_DB_IDS, SchemaBuilder  # noqa: E402

RESULTS_DIR = "results/without_denorm_notice"

DEFAULT_MODELS = ("qwen2.5-coder-14b-local",)
DEFAULT_CONDITIONS: Tuple[Tuple[int, int], ...] = (
    (1, 1),
    (1, 2),
    (1, 3),
    (2, 1),
    (2, 2),
    (2, 3),
)


def results_file(model: str, struct_level: int, sem_level: int) -> str:
    safe_model = model.replace("/", "-")
    return f"{RESULTS_DIR}/{safe_model}__L{struct_level}S{sem_level}.csv"


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="L1/L2 experiment without denormalization notice (397 questions)."
    )
    p.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help=f"Model id(s) to run (default: {DEFAULT_MODELS[0]})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without calling LLMs or writing CSVs",
    )
    return p.parse_args(argv)


def _load_main_experiment_questions() -> List[dict]:
    all_questions = load_experiment_questions()
    return select_questions(
        all_questions,
        stratified_slices=None,
        max_prefix=None,
        exclude_db_ids=ARCWISE_EXCLUDED_DB_IDS,
    )


def run(models: Sequence[str], *, dry_run: bool) -> None:
    questions = _load_main_experiment_questions()
    conditions = list(DEFAULT_CONDITIONS)

    from collections import Counter

    by_db = Counter(q["db_id"] for q in questions)
    print(f"Questions: {len(questions)} (main experiment set, 9 DBs)")
    for db_id in sorted(by_db):
        print(f"  {db_id}: {by_db[db_id]}")
    print(f"Conditions: {', '.join(f'L{sl}S{sem}' for sl, sem in conditions)}")
    print(f"Models: {', '.join(models)}")
    print(f"Output: {RESULTS_DIR}/")
    print("Prompt: L1/L2 without denormalization notice")
    if dry_run:
        print("Mode: dry-run")

    if not dry_run:
        validate_run_prerequisites(questions, conditions)
        os.makedirs(RESULTS_DIR, exist_ok=True)

    db_ids = list({q["db_id"] for q in questions})
    builders = {db_id: SchemaBuilder(db_id, DATA_DIR) for db_id in db_ids}
    sem_levels_needed = {sem for _, sem in conditions}

    rename_maps = {
        (db_id, sem): build_col_rename_map(db_id, DATA_DIR, sem)
        for db_id in db_ids
        for sem in sem_levels_needed
    }
    l1_rename_maps = {
        (db_id, sem): build_l1_col_rename_map(db_id, DATA_DIR, sem)
        for db_id in db_ids
        if db_id in L1_DB_IDS
        for sem in sem_levels_needed
    }
    l2_rename_maps = {
        (db_id, sem): build_l2_col_rename_map(db_id, DATA_DIR, sem)
        for db_id in db_ids
        if db_id in L2_DB_IDS
        for sem in sem_levels_needed
    }

    total_runs = len(conditions) * len(models) * len(questions)
    print(f"\nTotal LLM calls planned: {total_runs}")
    if dry_run:
        for struct_level, sem_level in conditions:
            for model in models:
                print(f"  would write {results_file(model, struct_level, sem_level)}")
        return

    overall_done = 0
    overall_correct = 0

    for struct_level, sem_level in conditions:
        condition_label = f"L{struct_level}S{sem_level}"
        for model in models:
            csv_path = results_file(model, struct_level, sem_level)
            completed, correct = load_completed_with_correct(csv_path)
            done = len(completed)

            print(f"\n{'=' * 60}")
            print(f"  Condition : {condition_label}")
            print(f"  Model     : {model}")
            print(f"  Output    : {csv_path}")
            print(f"  Completed : {done}  |  Remaining: {len(questions) - done}")
            print(f"{'=' * 60}")

            pred_conn_by_db = {}
            try:
                for q in questions:
                    if q["question_id"] in completed:
                        continue

                    db_id = q["db_id"]
                    db_path = os.path.join(
                        DATA_DIR, "dev_databases", db_id, f"{db_id}.sqlite"
                    )
                    schema = builders[db_id].build(struct_level, sem_level)
                    prompt = build_prompt(
                        schema,
                        q["question"],
                        structural_level=struct_level,
                        include_denorm_notice=False,
                    )
                    predicted_sql = call_llm(model, prompt)

                    if struct_level == 1:
                        from src.evaluator import _build_pred_connection

                        mat_path = str(
                            SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id)
                        )
                        mat_rename = l1_rename_maps.get((db_id, sem_level))
                        conn_key = (db_id, struct_level)
                        if conn_key not in pred_conn_by_db:
                            pred_conn_by_db[conn_key] = _build_pred_connection(
                                mat_path, mat_rename or {}
                            )
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            col_rename_map=mat_rename,
                            predicted_db_path=mat_path,
                            pred_reuse_connection=pred_conn_by_db[conn_key],
                            verbose=False,
                        )
                    else:
                        from src.evaluator import _build_pred_connection

                        mat_path = str(
                            SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id)
                        )
                        mat_rename = l2_rename_maps.get((db_id, sem_level))
                        conn_key = (db_id, struct_level)
                        if conn_key not in pred_conn_by_db:
                            pred_conn_by_db[conn_key] = _build_pred_connection(
                                mat_path, mat_rename or {}
                            )
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            col_rename_map=mat_rename,
                            predicted_db_path=mat_path,
                            pred_reuse_connection=pred_conn_by_db[conn_key],
                            verbose=False,
                        )

                    append_row(
                        csv_path,
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
                    completed.add(q["question_id"])
                    done += 1
                    overall_done += 1
                    if result.correct:
                        correct += 1
                        overall_correct += 1

                    print_progress(
                        done, len(questions), correct, condition_label, model
                    )
                    time.sleep(MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS))
            finally:
                for conn in pred_conn_by_db.values():
                    try:
                        conn.close()
                    except Exception:
                        pass

            print()
            final_acc = correct / done if done > 0 else 0.0
            print(f"  Done. Accuracy: {correct}/{done} = {final_acc:.1%}")
            print(f"  Saved to: {csv_path}")

    print(f"\n{'=' * 60}")
    print("Experiment complete.")
    print(f"Results saved to: {RESULTS_DIR}/")
    if overall_done > 0:
        print(
            f"Overall accuracy: {overall_correct}/{overall_done} "
            f"= {overall_correct / overall_done:.1%}"
        )


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    run(args.models, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
