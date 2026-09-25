#!/usr/bin/env python3
"""
run_experiment_s1r.py

Separate experiment runner for S1R (randomized table + column aliases).

Runs L1-L6 with frozen mappings from column_aliases_s1r.py. Does not modify
the main run_experiment.py pipeline.

Usage (from schema_effect/):

    python src/run_experiment_s1r.py --model qwen2.5-coder-14b-local
    python src/run_experiment_s1r.py --model gemini-2.5-flash --structural-levels 3 4 5 6
    python src/run_experiment_s1r.py --model qwen2.5-coder-14b-local --spider-dir \\
        dev_20240627/spider_data --results-dir results/spider_s1r

Output:
    results/s1r/{model}__L{struct}S1R.csv  (or results/spider_s1r/ in Spider mode)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=True)
except ImportError:
    pass

from preprocess_data.data_layout import DataLayout
from run_experiment import (
    ARCWISE_EXCLUDED_DB_IDS,
    ARCWISE_QUESTIONS_PATH,
    DATA_DIR,
    DELAY_BETWEEN_CALLS,
    MODEL_DELAY,
    SPIDER_QUESTIONS_PATH,
    append_row,
    load_completed_with_correct,
    load_experiment_questions,
    load_spider_questions,
    print_progress,
    select_questions,
    validate_run_prerequisites,
)
from src.evaluator import evaluate
from src.evaluator_s1r import (
    S1R_SEMANTIC_LEVEL,
    build_l1_s1r_rename_map,
    build_l2_s1r_rename_map,
    build_s1r_l3_view_spec,
    build_s1r_pred_connection_l3,
    build_s1r_pred_connection_materialised,
)
from src.llm_runner import call_llm
from src.prompt_builder import build_prompt
from src.schema_builder import L1_DB_IDS, L2_DB_IDS, SchemaBuilder
from src.schema_builder_s1r import SchemaBuilderS1R

RESULTS_DIR_S1R = "results/s1r"
DEFAULT_STRUCTURAL_LEVELS = (1, 2, 3, 4, 5, 6)


def results_file_s1r(
    model: str,
    struct_level: int,
    results_dir: str,
) -> str:
    safe_model = model.replace("/", "-")
    return f"{results_dir}/{safe_model}__L{struct_level}S1R.csv"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run S1R (randomized alias) experiments for one model, L1-L6."
    )
    p.add_argument(
        "--model",
        required=True,
        help="Model id (same names as run_experiment.py MODELS)",
    )
    p.add_argument(
        "--structural-levels",
        nargs="+",
        type=int,
        default=list(DEFAULT_STRUCTURAL_LEVELS),
        metavar="L",
        help="Structural levels to run (default: 1 2 3 4 5 6)",
    )
    p.add_argument(
        "--spider-dir",
        default=None,
        help="Spider data root; enables Spider question set when set.",
    )
    p.add_argument(
        "--results-dir",
        default=None,
        help="Output directory (default: results_s1r or results/spider_s1r)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only; do not call LLM or write CSVs",
    )
    return p.parse_args()


def run_s1r(
    model: str,
    *,
    structural_levels: List[int],
    spider_dir: Optional[str] = None,
    results_dir: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    layout = DataLayout.create(DATA_DIR, spider_dir=spider_dir)
    spider_mode = layout.layout == "spider"
    active_results_dir = results_dir or (
        "results/spider_s1r" if spider_mode else RESULTS_DIR_S1R
    )
    conditions = [(sl, S1R_SEMANTIC_LEVEL) for sl in sorted(set(structural_levels))]
    tables_path = str(layout.tables_json)

    if spider_mode:
        all_questions = load_spider_questions()
        print(f"[Spider S1R] Loaded {len(all_questions)} questions from {SPIDER_QUESTIONS_PATH}")
    else:
        all_questions = load_experiment_questions()
        print(
            f"[BIRD S1R] Loaded {len(all_questions)} questions from {ARCWISE_QUESTIONS_PATH}"
        )

    questions = select_questions(
        all_questions,
        stratified_slices=None,
        max_prefix=None,
        exclude_db_ids=None if spider_mode else ARCWISE_EXCLUDED_DB_IDS,
    )
    print(f"Questions selected: {len(questions)}")
    print(f"Model: {model}")
    print(f"Conditions: {', '.join(f'L{sl}S1R' for sl, _ in conditions)}")
    print(f"Results: {active_results_dir}/")
    print(f"Semantic level code in CSV: {S1R_SEMANTIC_LEVEL} (S1R track)")

    if dry_run:
        for struct_level, _ in conditions:
            print(f"  would write {results_file_s1r(model, struct_level, active_results_dir)}")
        return

    validate_run_prerequisites(questions, conditions, layout)
    os.makedirs(active_results_dir, exist_ok=True)

    db_ids = list({q["db_id"] for q in questions})
    builders = {db_id: SchemaBuilderS1R(db_id, DATA_DIR, layout) for db_id in db_ids}

    l3_view_specs = {
        db_id: build_s1r_l3_view_spec(db_id, DATA_DIR, tables_path) for db_id in db_ids
    }
    l1_rename_maps = {
        db_id: build_l1_s1r_rename_map(db_id, DATA_DIR, tables_path)
        for db_id in db_ids
        if db_id in L1_DB_IDS
    }
    l2_rename_maps = {
        db_id: build_l2_s1r_rename_map(db_id, DATA_DIR, tables_path)
        for db_id in db_ids
        if db_id in L2_DB_IDS
    }

    total_runs = len(conditions) * len(questions)
    overall_done = 0
    overall_correct = 0

    for struct_level, sem_level in conditions:
        condition_label = f"L{struct_level}S1R"

        csv_path = results_file_s1r(model, struct_level, active_results_dir)
        completed, correct = load_completed_with_correct(csv_path)
        done = len(completed)
        remaining = len(questions) - done

        print(f"\n{'=' * 60}")
        print(f"  Condition : {condition_label}")
        print(f"  Model     : {model}")
        print(f"  Output    : {csv_path}")
        print(f"  Completed : {done}  |  Remaining: {remaining}")
        print(f"{'=' * 60}")

        pred_conn_by_key: Dict[Tuple[str, int], object] = {}
        try:
            for q in questions:
                if q["question_id"] in completed:
                    continue

                disk_completed, disk_correct = load_completed_with_correct(csv_path)
                if q["question_id"] in disk_completed:
                    completed = disk_completed
                    correct = disk_correct
                    done = len(completed)
                    continue

                db_id = q["db_id"]
                db_path = str(layout.source_sqlite(db_id))
                schema = builders[db_id].build(struct_level)
                prompt = build_prompt(schema, q["question"], structural_level=struct_level)
                predicted_sql = call_llm(model, prompt)

                if struct_level in (1, 2):
                    if struct_level == 1:
                        mat_path = str(
                            SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id, layout)
                        )
                        mat_rename = l1_rename_maps.get(db_id)
                    else:
                        mat_path = str(
                            SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id, layout)
                        )
                        mat_rename = l2_rename_maps.get(db_id)

                    conn_key = (db_id, struct_level)
                    if conn_key not in pred_conn_by_key:
                        pred_conn_by_key[conn_key] = (
                            build_s1r_pred_connection_materialised(
                                mat_path, mat_rename or {}
                            )
                        )
                    result = evaluate(
                        db_path,
                        predicted_sql,
                        q["SQL"],
                        col_rename_map=mat_rename,
                        predicted_db_path=mat_path,
                        pred_reuse_connection=pred_conn_by_key[conn_key],
                        verbose=False,
                    )
                else:
                    view_spec = l3_view_specs[db_id]
                    conn_key = (db_id, struct_level)
                    if conn_key not in pred_conn_by_key:
                        pred_conn_by_key[conn_key] = build_s1r_pred_connection_l3(
                            db_path, view_spec
                        )
                    # col_rename_map unused when pred_reuse_connection is set;
                    # views already expose S1R names on the original DB path.
                    result = evaluate(
                        db_path,
                        predicted_sql,
                        q["SQL"],
                        col_rename_map=None,
                        predicted_db_path=db_path,
                        pred_reuse_connection=pred_conn_by_key[conn_key],
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

                print_progress(done, len(questions), correct, condition_label, model)
                time.sleep(MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS))
        finally:
            for conn in pred_conn_by_key.values():
                try:
                    conn.close()
                except Exception:
                    pass
            pred_conn_by_key.clear()

        print()
        final_acc = correct / done if done > 0 else 0.0
        print(f"  Done. Accuracy: {correct}/{done} = {final_acc:.1%}")
        print(f"  Saved to: {csv_path}")

    print(f"\n{'=' * 60}")
    print("S1R experiment complete.")
    print(f"Results saved to: {active_results_dir}/")
    if overall_done > 0:
        print(
            f"Overall accuracy: {overall_correct}/{overall_done} "
            f"= {overall_correct / overall_done:.1%}"
        )


def main() -> None:
    args = _parse_args()
    run_s1r(
        args.model,
        structural_levels=args.structural_levels,
        spider_dir=args.spider_dir,
        results_dir=args.results_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
