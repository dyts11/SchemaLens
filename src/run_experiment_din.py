"""
run_experiment_din.py

Schema-effect experiment using a DIN-SQL style three-stage pipeline.

Per question, three LLM calls are made:
  1. Schema Linking  — which tables and columns are needed?
  2. Classification  — EASY, NON-NESTED, or NESTED?
  3. SQL Generation  — produce SQL given the linked schema and complexity.

Few-shot examples for each stage come from the same fixed per-DB examples used
in run_experiment.py (one per difficulty level per DB), automatically annotated
with schema links and complexity derived from their gold SQL — no manual
labelling required.

Output:
    results/  — CSVs with a '__din' suffix, e.g.
                results/gemini-2.5-flash__L3S3__din.csv

Extra columns vs the main experiment:
    schema_links     — stage 1 output (linked tables/columns)
    complexity_class — stage 2 output (EASY / NON-NESTED / NESTED)

Usage:
    python src/run_experiment_din.py
    python src/run_experiment_din.py --condition L3S3 --models gemini-2.5-flash
"""

import argparse
import csv
import fcntl
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
except ImportError:
    pass

from src.schema_builder import SchemaBuilder
from src.llm_runner import call_llm
from src.few_shot import (
    select_fixed_examples_by_difficulty,
    load_few_shot_json,
    get_sql_for_struct_level,
    adapt_sql_to_semantic_level,
)
from src.din_sql import (
    annotate_example,
    build_schema_linking_prompt,
    build_classification_prompt,
    build_sql_generation_prompt,
    parse_schema_links_output,
    parse_complexity_output,
)
from src.evaluator import (
    evaluate,
    build_col_rename_map,
    build_l1_col_rename_map,
    build_l2_col_rename_map,
)
from preprocess_data.data_layout import DataLayout
from preprocess_data.questions.question_classifier import load_question_types

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = "dev_20240627"
ARCWISE_QUESTIONS_PATH = os.path.join(DATA_DIR, "arcwise_plat_sql.json")
DEV_JSON_PATH = os.path.join(DATA_DIR, "dev.json")
RESULTS_DIR = "results/din"
QUESTIONS_DIR = "preprocess_data/questions"

SPIDER_DIR: Optional[str] = None
SPIDER_QUESTIONS_PATH = os.path.join(
    DATA_DIR, "spider_data", "experiment_questions_car1_tvshow.json"
)

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

MODEL_DELAY = {
    "gemini-2.0-flash":   3,
    "gemini-2.5-flash":   1,
    "gemini-3.5-flash":   1,
    "llama-3.3-70b-or":   1,
    "llama-3.1-8b-or":    1,
    "qwen2.5-coder-32b":  2,
    "llama-3.1-8b":       1,
    "llama-3.3-70b":      1,
    "qwen2.5-coder-0.5b-local": 0,
    "qwen2.5-coder-1.5b-local": 0,
    "qwen2.5-coder-3b-local":   0,
    "qwen2.5-coder-7b-local":   0,
    "qwen2.5-coder-14b-local":  0,
    "qwen2.5-coder-32b-local":  0,
    "phi-4-local":              0,
    "olmo-2-13b-local":         0,
}
DELAY_BETWEEN_CALLS = 3

ARCWISE_EXCLUDED_DB_IDS = frozenset({"card_games", "codebase_community"})
STRATIFIED_DB_SAMPLE: Optional[List[Tuple[str, int]]] = None
MAX_QUESTIONS: Optional[int] = None

# ---------------------------------------------------------------------------
# CSV schema (extends main experiment with two intermediate-output columns)
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "question_id", "db_id", "difficulty", "question_type",
    "structural_level", "semantic_level", "model",
    "gold_sql", "predicted_sql", "outcome", "correct", "error_msg",
    "schema_links", "complexity_class",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def results_file(
    model: str,
    struct_level: int,
    sem_level: int,
    results_dir: str = RESULTS_DIR,
) -> str:
    safe_model = model.replace("/", "-")
    return f"{results_dir}/{safe_model}__L{struct_level}S{sem_level}__din.csv"


def _parse_condition(value: str) -> Tuple[int, int]:
    m = re.fullmatch(r"[Ll](\d+)[Ss](\d+)", value)
    if not m:
        raise argparse.ArgumentTypeError(f"Invalid condition {value!r}; expected format L3S3")
    return int(m.group(1)), int(m.group(2))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the schema-effect experiment with DIN-SQL three-stage pipeline."
    )
    p.add_argument("--spider-dir", default=None)
    p.add_argument("--results-dir", default=None)
    p.add_argument(
        "--condition", action="append", dest="conditions",
        type=_parse_condition, metavar="LnSm",
    )
    p.add_argument("--models", nargs="+", default=None)
    return p.parse_args(argv)


def load_completed_with_correct(csv_path: str) -> Tuple[set, int]:
    completed, n_correct = set(), 0
    if not os.path.exists(csv_path):
        return completed, n_correct
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            completed.add(int(row["question_id"]))
            if row.get("correct", "").strip().lower() == "true":
                n_correct += 1
    return completed, n_correct


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


def print_progress(done: int, total: int, correct: int, condition: str, model: str) -> None:
    acc = correct / done if done > 0 else 0.0
    print(
        f"  [{condition} | {model}] {done}/{total} ({done/total*100:.1f}%) — "
        f"accuracy so far: {acc:.1%}",
        end="\r", flush=True,
    )


def load_experiment_questions(
    arcwise_path: str = ARCWISE_QUESTIONS_PATH,
    dev_json_path: str = DEV_JSON_PATH,
    questions_dir: str = QUESTIONS_DIR,
) -> List[dict]:
    with open(arcwise_path, encoding="utf-8") as f:
        arcwise = json.load(f)
    with open(dev_json_path, encoding="utf-8") as f:
        dev_by_id = {int(q["question_id"]): q for q in json.load(f)}
    types_by_id = load_question_types(questions_dir)

    questions: List[dict] = []
    for rec in arcwise:
        qid = int(rec["question_id"])
        dev_rec = dev_by_id.get(qid)
        if dev_rec is None:
            raise KeyError(f"question_id {qid} not found in {dev_json_path}")
        type_rec = types_by_id.get(qid)
        if type_rec is None:
            raise KeyError(f"question_id {qid} missing from question_types.json")
        questions.append({
            "question_id": qid,
            "db_id": rec["db_id"],
            "question": rec["question"],
            "SQL": rec["SQL"],
            "evidence": rec.get("evidence", ""),
            "difficulty": dev_rec["difficulty"],
            "question_type": type_rec["question_type"],
        })
    return questions


def select_questions(
    all_questions: List[dict],
    *,
    stratified_slices: Optional[List[Tuple[str, int]]],
    max_prefix: Optional[int],
    exclude_db_ids: Optional[FrozenSet[str]] = None,
) -> List[dict]:
    if exclude_db_ids:
        all_questions = [q for q in all_questions if q["db_id"] not in exclude_db_ids]
    if stratified_slices:
        by_db: Dict[str, List[dict]] = {}
        for q in all_questions:
            by_db.setdefault(q["db_id"], []).append(q)
        picked: List[dict] = []
        for db_id, n in stratified_slices:
            bucket = by_db.get(db_id, [])
            if len(bucket) < n:
                raise ValueError(f"{db_id!r} has only {len(bucket)} questions, {n} requested")
            picked.extend(bucket[:n])
        return picked
    if max_prefix is not None:
        return all_questions[:max_prefix]
    return list(all_questions)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(
    *,
    spider_dir: Optional[str] = None,
    results_dir: Optional[str] = None,
    conditions: Optional[List[Tuple[int, int]]] = None,
    models: Optional[List[str]] = None,
) -> None:
    active_spider_dir = spider_dir if spider_dir is not None else SPIDER_DIR
    layout = DataLayout.create(DATA_DIR, spider_dir=active_spider_dir)
    active_results_dir = results_dir or RESULTS_DIR
    active_conditions = conditions if conditions is not None else CONDITIONS
    active_models = models if models is not None else MODELS
    tables_path = str(layout.tables_json)

    os.makedirs(active_results_dir, exist_ok=True)

    all_questions = load_experiment_questions()
    print(f"Loaded {len(all_questions)} questions from {ARCWISE_QUESTIONS_PATH}")

    # Reserved IDs — questions held out as few-shot examples, excluded from test set.
    _, reserved_ids = select_fixed_examples_by_difficulty(all_questions)
    print(f"Reserved {len(reserved_ids)} questions as fixed few-shot examples")

    # Load the manually curated few-shot JSON (correct SQL per structural level).
    few_shot_json = load_few_shot_json()

    questions = select_questions(
        all_questions,
        stratified_slices=STRATIFIED_DB_SAMPLE,
        max_prefix=MAX_QUESTIONS,
        exclude_db_ids=ARCWISE_EXCLUDED_DB_IDS,
    )
    before = len(questions)
    questions = [q for q in questions if q["question_id"] not in reserved_ids]
    print(f"Removed {before - len(questions)} reserved questions from test set")
    print(f"Total test questions: {len(questions)}")

    from run_experiment import validate_run_prerequisites
    validate_run_prerequisites(questions, active_conditions, layout)

    db_ids = list({q["db_id"] for q in questions})
    print(f"Building schema metadata for {len(db_ids)} databases…")
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
        for db_id in db_ids
        if db_id in L1_DB_IDS
        for sem in sem_levels_needed
    }
    l2_rename_maps = {
        (db_id, sem): build_l2_col_rename_map(db_id, DATA_DIR, sem, tables_path)
        for db_id in db_ids
        if db_id in L2_DB_IDS
        for sem in sem_levels_needed
    }

    total_runs = len(active_conditions) * len(active_models) * len(questions)
    print(f"\nTotal runs planned : {total_runs}  (3 LLM calls each)")
    print(f"Results directory  : {active_results_dir}/")
    print()

    overall_done = 0
    overall_correct = 0
    delay = MODEL_DELAY.get(active_models[0] if active_models else "", DELAY_BETWEEN_CALLS)

    for struct_level, sem_level in active_conditions:
        condition_label = f"L{struct_level}·S{sem_level}"

        # Pre-annotate fixed examples for this condition.
        # Pick the correct SQL variant per structural level, then adapt column names
        # for the current semantic level before deriving schema links and complexity.
        annotated_by_db: Dict[str, List[dict]] = {}
        for db_id, entries in few_shot_json.items():
            if struct_level == 1:
                sem_rename = l1_rename_maps.get((db_id, sem_level))
            elif struct_level == 2:
                sem_rename = l2_rename_maps.get((db_id, sem_level))
            else:
                sem_rename = rename_maps.get((db_id, sem_level))
            annotated_by_db[db_id] = [
                annotate_example(
                    e["question"],
                    adapt_sql_to_semantic_level(
                        get_sql_for_struct_level(e, struct_level), sem_rename
                    ),
                )
                for e in entries
            ]

        for model in active_models:
            delay = MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS)
            csv_path = results_file(model, struct_level, sem_level,
                                    results_dir=active_results_dir)
            completed, correct = load_completed_with_correct(csv_path)
            done = len(completed)

            print(f"\n{'='*60}")
            print(f"  Condition : {condition_label}")
            print(f"  Model     : {model}")
            print(f"  Output    : {csv_path}")
            print(f"  Completed : {done}  |  Remaining: {len(questions) - done}")
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
                    examples = annotated_by_db.get(db_id, [])

                    # ---- Stage 1: Schema Linking ----
                    p1 = build_schema_linking_prompt(schema, q["question"], examples)
                    raw_links = call_llm(model, p1)
                    time.sleep(delay)
                    schema_links = parse_schema_links_output(raw_links)

                    # ---- Stage 2: Classification ----
                    p2 = build_classification_prompt(q["question"], schema_links, examples)
                    raw_class = call_llm(model, p2)
                    time.sleep(delay)
                    complexity = parse_complexity_output(raw_class)

                    # ---- Stage 3: SQL Generation ----
                    p3 = build_sql_generation_prompt(
                        schema, q["question"], schema_links, complexity, examples,
                        structural_level=struct_level,
                    )
                    predicted_sql = call_llm(model, p3)
                    time.sleep(delay)

                    # ---- Evaluate ----
                    if struct_level in (1, 2):
                        from src.evaluator import _build_pred_connection

                        if struct_level == 1:
                            mat_path = str(SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id, layout))
                            if not SchemaBuilder.has_one_nf_database(DATA_DIR, db_id, layout):
                                raise FileNotFoundError(f"Missing 1NF DB for {db_id}")
                            mat_rename = l1_rename_maps.get((db_id, sem_level))
                        else:
                            mat_path = str(SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id, layout))
                            if not SchemaBuilder.has_two_nf_database(DATA_DIR, db_id, layout):
                                raise FileNotFoundError(f"Missing 2NF DB for {db_id}")
                            mat_rename = l2_rename_maps.get((db_id, sem_level))

                        conn_key = (db_id, struct_level)
                        if conn_key not in pred_conn_by_db:
                            pred_conn_by_db[conn_key] = _build_pred_connection(
                                mat_path, mat_rename or {}
                            )
                        result = evaluate(
                            db_path, predicted_sql, q["SQL"],
                            col_rename_map=mat_rename,
                            predicted_db_path=mat_path,
                            pred_reuse_connection=pred_conn_by_db[conn_key],
                            verbose=False,
                        )
                    else:
                        col_rename_map = rename_maps.get((db_id, sem_level))
                        result = evaluate(
                            db_path, predicted_sql, q["SQL"],
                            col_rename_map=col_rename_map,
                            verbose=False,
                        )

                    append_row(csv_path, {
                        "question_id":    q["question_id"],
                        "db_id":          db_id,
                        "difficulty":     q["difficulty"],
                        "question_type":  q["question_type"],
                        "structural_level": struct_level,
                        "semantic_level": sem_level,
                        "model":          model,
                        "gold_sql":       q["SQL"],
                        "predicted_sql":  predicted_sql,
                        "outcome":        result.outcome,
                        "correct":        result.correct,
                        "error_msg":      result.error_msg or "",
                        "schema_links":   schema_links,
                        "complexity_class": complexity,
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
        print(f"Overall accuracy: {overall_correct}/{overall_done} = {overall_correct/overall_done:.1%}")


if __name__ == "__main__":
    args = parse_args()
    run(
        spider_dir=args.spider_dir,
        results_dir=args.results_dir,
        conditions=args.conditions,
        models=args.models,
    )
