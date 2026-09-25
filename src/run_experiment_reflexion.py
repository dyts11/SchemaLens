"""
run_experiment_reflexion.py

Runs the schema-effect experiment with Reflexion-style self-correction.

For each question:
  1. Generate initial SQL (same as run_experiment.py).
  2. Evaluate; if incorrect, enter the Reflexion loop (up to MAX_ROUNDS):
       a. Reflection prompt  → call LLM → verbal reflection (not SQL)
       b. Correction prompt  → call LLM → corrected SQL
       c. Re-evaluate; break early if correct.
  3. Write final result to CSV with two extra columns:
       attempts        : total SQL generation attempts (1 = no correction used)
       initial_outcome : outcome of the very first attempt

Feedback per outcome:
  - "error"       : the SQLite error message (concrete signal)
  - "wrong_answer": "executed but returned incorrect results" (binary signal,
                    no gold leakage — mirrors Reflexion's reasoning-task design)

Output CSVs use the suffix __reflexionN (e.g. __reflexion2 for MAX_ROUNDS=2).

Usage:
    python src/run_experiment_reflexion.py
    python src/run_experiment_reflexion.py --condition L3S3 --models gemini-2.5-flash
    python src/run_experiment_reflexion.py --max-rounds 3
"""

import argparse
import csv
import fcntl
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root so we can import run_experiment helpers and src.* modules.
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
except ImportError:
    pass

from src.schema_builder import SchemaBuilder
from src.prompt_builder import build_prompt
from src.llm_runner import call_llm
from src.reflexion import get_feedback, build_reflection_prompt, build_correction_prompt
from src.few_shot import select_fixed_examples_by_difficulty, adapt_sql_to_semantic_level
from src.evaluator import (
    evaluate,
    build_col_rename_map,
    build_l1_col_rename_map,
    build_l2_col_rename_map,
    _build_pred_connection,
)
from preprocess_data.data_layout import DataLayout

# Shared helpers and constants from the main experiment entry point.
from run_experiment import (
    load_experiment_questions,
    load_spider_questions,
    select_questions,
    load_completed_with_correct,
    validate_run_prerequisites,
    print_progress,
    DATA_DIR,
    ARCWISE_EXCLUDED_DB_IDS,
    STRATIFIED_DB_SAMPLE,
    MAX_QUESTIONS,
    MODEL_DELAY,
    DELAY_BETWEEN_CALLS,
    SPIDER_QUESTIONS_PATH,
)

# ---------------------------------------------------------------------------
# Configuration — edit this section to change what gets run
# ---------------------------------------------------------------------------

RESULTS_DIR = "results/reflexion"

SPIDER_DIR: Optional[str] = None

CONDITIONS = [
    (1, 1), (1, 2), (1, 3),
    (2, 1), (2, 2), (2, 3),
    (3, 1), (3, 2), (3, 3),
    (4, 1), (4, 2), (4, 3),
    (5, 1), (5, 2), (5, 3),
    (6, 1), (6, 2), (6, 3),
]

MODELS = [
    "gemini-2.5-flash",
]

# Number of Reflexion rounds per question (each round = one reflect + one correct call).
MAX_ROUNDS: int = 2

FEW_SHOT_N: int = 0

# ---------------------------------------------------------------------------
# CSV schema
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "question_id",
    "db_id",
    "difficulty",
    "question_type",
    "structural_level",
    "semantic_level",
    "model",
    "gold_sql",
    "predicted_sql",
    "outcome",
    "correct",
    "error_msg",
    "attempts",
    "initial_outcome",
]


def results_file(
    model: str,
    struct_level: int,
    sem_level: int,
    results_dir: str,
    max_rounds: int,
    few_shot_n: int = 0,
) -> str:
    safe_model = model.replace("/", "-")
    fs_suffix = f"__fs{few_shot_n}" if few_shot_n > 0 else ""
    return (
        f"{results_dir}/{safe_model}__L{struct_level}S{sem_level}"
        f"{fs_suffix}__reflexion{max_rounds}.csv"
    )


def append_row(csv_path: str, row: dict) -> None:
    parent = os.path.dirname(csv_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_condition(value: str) -> Tuple[int, int]:
    m = re.fullmatch(r"[Ll](\d+)[Ss](\d+)", value)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid condition {value!r}; expected format L3S3"
        )
    return int(m.group(1)), int(m.group(2))


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Run schema-effect experiment with Reflexion self-correction."
    )
    p.add_argument("--spider-dir", default=None)
    p.add_argument("--results-dir", default=None)
    p.add_argument(
        "--condition",
        action="append",
        dest="conditions",
        type=_parse_condition,
        metavar="LnSm",
        help="Condition to run, e.g. L3S3 (repeatable; default: all 18).",
    )
    p.add_argument("--models", nargs="+", default=None)
    p.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        metavar="N",
        help="Reflexion rounds per question (default: MAX_ROUNDS).",
    )
    p.add_argument(
        "--few-shot",
        type=int,
        default=None,
        metavar="N",
        help="Number of per-database few-shot examples (default: FEW_SHOT_N).",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Evaluation helper
# ---------------------------------------------------------------------------

def _do_evaluate(
    predicted_sql: str,
    db_path: str,
    gold_sql: str,
    struct_level: int,
    sem_level: int,
    db_id: str,
    rename_maps: dict,
    l1_rename_maps: dict,
    l2_rename_maps: dict,
    pred_conn_by_db: dict,
    layout,
):
    """
    Route evaluate() to the correct database file and rename map.

    For L1/L2, predicted SQL runs on the materialised wide-table database;
    gold SQL runs on the original 3NF database. Connections are cached in
    pred_conn_by_db so they are reused across the Reflexion rounds and across
    questions of the same (db_id, struct_level) within one condition run.
    """
    if struct_level in (1, 2):
        if struct_level == 1:
            mat_path = str(SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id, layout))
            mat_rename = l1_rename_maps.get((db_id, sem_level))
        else:
            mat_path = str(SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id, layout))
            mat_rename = l2_rename_maps.get((db_id, sem_level))

        conn_key = (db_id, struct_level)
        if conn_key not in pred_conn_by_db:
            pred_conn_by_db[conn_key] = _build_pred_connection(mat_path, mat_rename or {})

        return evaluate(
            db_path,
            predicted_sql,
            gold_sql,
            col_rename_map=mat_rename,
            predicted_db_path=mat_path,
            pred_reuse_connection=pred_conn_by_db[conn_key],
        )
    else:
        return evaluate(
            db_path,
            predicted_sql,
            gold_sql,
            col_rename_map=rename_maps.get((db_id, sem_level)),
        )


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(
    *,
    spider_dir: Optional[str] = None,
    results_dir: Optional[str] = None,
    conditions: Optional[List[Tuple[int, int]]] = None,
    models: Optional[List[str]] = None,
    max_rounds: Optional[int] = None,
    few_shot_n: Optional[int] = None,
) -> None:
    active_spider_dir = spider_dir if spider_dir is not None else SPIDER_DIR
    layout = DataLayout.create(DATA_DIR, spider_dir=active_spider_dir)
    spider_mode = layout.layout == "spider"
    active_results_dir = (
        results_dir if results_dir is not None
        else ("results/spider" if spider_mode else RESULTS_DIR)
    )
    active_conditions = conditions if conditions is not None else CONDITIONS
    active_models = models if models is not None else MODELS
    active_max_rounds = max_rounds if max_rounds is not None else MAX_ROUNDS
    active_few_shot_n = few_shot_n if few_shot_n is not None else FEW_SHOT_N
    tables_path = str(layout.tables_json)

    os.makedirs(active_results_dir, exist_ok=True)

    if spider_mode:
        all_questions = load_spider_questions()
        print(f"[Spider mode] Loaded {len(all_questions)} questions from {SPIDER_QUESTIONS_PATH}")
    else:
        all_questions = load_experiment_questions()
        print(f"Loaded {len(all_questions)} questions")

    db_few_shot_examples: Dict[str, list] = {}
    reserved_for_few_shot: set = set()
    if active_few_shot_n > 0 and not spider_mode:
        db_few_shot_examples, reserved_for_few_shot = select_fixed_examples_by_difficulty(
            all_questions
        )
        print(
            f"Few-shot: {active_few_shot_n}-shot — reserved "
            f"{len(reserved_for_few_shot)} questions as fixed examples"
        )

    questions = select_questions(
        all_questions,
        stratified_slices=STRATIFIED_DB_SAMPLE,
        max_prefix=MAX_QUESTIONS,
        exclude_db_ids=None if spider_mode else ARCWISE_EXCLUDED_DB_IDS,
    )

    if reserved_for_few_shot:
        before = len(questions)
        questions = [q for q in questions if q["question_id"] not in reserved_for_few_shot]
        print(f"  Removed {before - len(questions)} reserved questions from test set")

    print(f"Total questions  : {len(questions)}")
    print(f"Reflexion rounds : {active_max_rounds}")

    validate_run_prerequisites(questions, active_conditions, layout)

    db_ids = list({q["db_id"] for q in questions})
    builders = {db_id: SchemaBuilder(db_id, DATA_DIR, layout) for db_id in db_ids}

    sem_levels_needed = {sem for _, sem in active_conditions}
    from src.schema_builder import L1_DB_IDS, L2_DB_IDS

    rename_maps = {
        (db_id, sem): build_col_rename_map(db_id, DATA_DIR, sem, tables_path)
        for db_id in db_ids
        for sem in sem_levels_needed
    }
    l1_rename_maps = {
        (db_id, sem): build_l1_col_rename_map(db_id, DATA_DIR, sem, tables_path)
        for db_id in db_ids if db_id in L1_DB_IDS
        for sem in sem_levels_needed
    }
    l2_rename_maps = {
        (db_id, sem): build_l2_col_rename_map(db_id, DATA_DIR, sem, tables_path)
        for db_id in db_ids if db_id in L2_DB_IDS
        for sem in sem_levels_needed
    }

    total_runs = len(active_conditions) * len(active_models) * len(questions)
    print(f"Total runs planned : {total_runs}")
    print(f"Results directory  : {active_results_dir}/\n")

    overall_done = 0
    overall_correct = 0

    for struct_level, sem_level in active_conditions:
        condition_label = f"L{struct_level}·S{sem_level}"

        for model in active_models:
            csv_path = results_file(
                model, struct_level, sem_level,
                results_dir=active_results_dir,
                max_rounds=active_max_rounds,
                few_shot_n=active_few_shot_n,
            )
            completed, correct = load_completed_with_correct(csv_path)
            done = len(completed)
            remaining = len(questions) - done

            print(f"\n{'='*60}")
            print(f"  Condition : {condition_label}")
            print(f"  Model     : {model}")
            print(f"  Output    : {csv_path}")
            print(f"  Completed : {done}  |  Remaining: {remaining}")
            print(f"{'='*60}")

            pred_conn_by_db = {}
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
                    schema = builders[db_id].build(struct_level, sem_level)

                    few_shot_examples = None
                    if active_few_shot_n > 0 and db_few_shot_examples:
                        raw = db_few_shot_examples.get(db_id, [])
                        if struct_level not in (1, 2):
                            l3_rename = rename_maps.get((db_id, sem_level))
                            few_shot_examples = [
                                (qt, adapt_sql_to_semantic_level(sql, l3_rename))
                                for qt, sql in raw
                            ]
                        else:
                            few_shot_examples = raw

                    prompt = build_prompt(
                        schema,
                        q["question"],
                        structural_level=struct_level,
                        few_shot_examples=few_shot_examples,
                    )

                    # --- Initial generation ---
                    predicted_sql = call_llm(model, prompt)
                    time.sleep(MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS))

                    result = _do_evaluate(
                        predicted_sql, db_path, q["SQL"],
                        struct_level, sem_level, db_id,
                        rename_maps, l1_rename_maps, l2_rename_maps,
                        pred_conn_by_db, layout,
                    )

                    attempts = 1
                    initial_outcome = result.outcome

                    # --- Reflexion loop ---
                    for _ in range(active_max_rounds):
                        if result.correct:
                            break

                        feedback = get_feedback(result.outcome, result.error_msg)

                        # Step 1: reflect — model explains what went wrong (returns text, not SQL)
                        reflection_prompt = build_reflection_prompt(prompt, predicted_sql, feedback)
                        reflection = call_llm(model, reflection_prompt)
                        time.sleep(MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS))

                        # Step 2: correct — model writes fixed SQL given its reflection
                        correction_prompt = build_correction_prompt(
                            prompt, predicted_sql, feedback, reflection
                        )
                        predicted_sql = call_llm(model, correction_prompt)
                        time.sleep(MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS))

                        result = _do_evaluate(
                            predicted_sql, db_path, q["SQL"],
                            struct_level, sem_level, db_id,
                            rename_maps, l1_rename_maps, l2_rename_maps,
                            pred_conn_by_db, layout,
                        )
                        attempts += 1

                    # --- Write result ---
                    append_row(csv_path, {
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
                        "attempts": attempts,
                        "initial_outcome": initial_outcome,
                    })
                    completed.add(q["question_id"])

                    done += 1
                    overall_done += 1
                    if result.correct:
                        correct += 1
                        overall_correct += 1

                    print_progress(done, len(questions), correct, condition_label, model)

            finally:
                for _c in pred_conn_by_db.values():
                    try:
                        _c.close()
                    except Exception:
                        pass
                pred_conn_by_db.clear()

            print()
            final_acc = correct / done if done > 0 else 0.0
            print(f"  Done. Accuracy: {correct}/{done} = {final_acc:.1%}")
            print(f"  Saved to: {csv_path}")

    print(f"\n{'='*60}")
    print("Experiment complete.")
    if overall_done > 0:
        print(
            f"Overall accuracy: {overall_correct}/{overall_done} = "
            f"{overall_correct/overall_done:.1%}"
        )


if __name__ == "__main__":
    args = parse_args()
    run(
        spider_dir=args.spider_dir,
        results_dir=args.results_dir,
        conditions=args.conditions,
        models=args.models,
        max_rounds=args.max_rounds,
        few_shot_n=args.few_shot,
    )
