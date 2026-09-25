"""
run_experiment_dense.py

Schema-effect experiment with dense retrieval few-shot example selection.

For each test question the k most similar questions (by cosine similarity of
sentence embeddings) are retrieved from a separate example pool (dev.json)
and injected into the prompt — replacing the fixed per-database examples used
in run_experiment.py.

Retrieval is restricted to the same db_id so examples always use the same
schema.  Test-set question_ids are excluded from the pool to prevent leakage.

Pool embeddings are cached to disk (dev_20240627/embeddings_cache/) so the
sentence-transformers model only runs once per pool file.

Usage:
    python src/run_experiment_dense.py
    python src/run_experiment_dense.py --condition L3S3 --models gemini-2.5-flash --k 3

Output:
    results/  — one CSV per (model, condition) with a '__dense_fsK' suffix
    e.g. results/gemini-2.5-flash__L3S3__dense_fs3.csv

Columns match run_experiment.py exactly.
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
from src.prompt_builder import build_prompt
from src.llm_runner import call_llm
from src.dense_retrieval import load_pool, build_retriever
from src.few_shot import adapt_sql_to_semantic_level
from src.evaluator import evaluate, build_col_rename_map
from preprocess_data.data_layout import DataLayout
from preprocess_data.questions.question_classifier import load_question_types

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = "dev_20240627"
ARCWISE_QUESTIONS_PATH = os.path.join(DATA_DIR, "arcwise_plat_sql.json")
DEV_JSON_PATH = os.path.join(DATA_DIR, "dev.json")
POOL_JSON_PATH = os.path.join(DATA_DIR, "dev.json")   # example pool
EMBEDDINGS_CACHE_DIR = os.path.join(DATA_DIR, "embeddings_cache")
RESULTS_DIR = "results/dense"
QUESTIONS_DIR = "preprocess_data/questions"

SPIDER_DIR: Optional[str] = None
SPIDER_QUESTIONS_PATH = os.path.join(
    DATA_DIR, "spider_data", "experiment_questions_car1_tvshow.json"
)

CONDITIONS = [
    (3, 1), (3, 2), (3, 3),
    (4, 1), (4, 2), (4, 3),
    (5, 1), (5, 2), (5, 3),
    (6, 1), (6, 2), (6, 3),
]

MODELS = [
    "gemini-2.5-flash",
]

# Number of examples to retrieve per question (k).
DENSE_K: int = 3

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
# Helpers shared with run_experiment.py
# ---------------------------------------------------------------------------

def get_data_layout() -> DataLayout:
    return DataLayout.create(DATA_DIR, spider_dir=SPIDER_DIR)


def results_file(
    model: str,
    struct_level: int,
    sem_level: int,
    k: int,
    results_dir: str = RESULTS_DIR,
) -> str:
    safe_model = model.replace("/", "-")
    return f"{results_dir}/{safe_model}__L{struct_level}S{sem_level}__dense_fs{k}.csv"


def _parse_condition(value: str) -> Tuple[int, int]:
    m = re.fullmatch(r"[Ll](\d+)[Ss](\d+)", value)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid condition {value!r}; expected format L3S3"
        )
    return int(m.group(1)), int(m.group(2))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the schema-effect experiment with dense retrieval few-shot."
    )
    p.add_argument("--spider-dir", default=None)
    p.add_argument("--results-dir", default=None)
    p.add_argument(
        "--condition",
        action="append",
        dest="conditions",
        type=_parse_condition,
        metavar="LnSm",
    )
    p.add_argument("--models", nargs="+", default=None)
    p.add_argument(
        "--k",
        type=int,
        default=None,
        metavar="K",
        help="Number of retrieved examples per question (default: DENSE_K).",
    )
    p.add_argument(
        "--pool",
        default=None,
        metavar="PATH",
        help="Path to the example pool JSON (default: POOL_JSON_PATH).",
    )
    return p.parse_args(argv)


CSV_COLUMNS = [
    "question_id", "db_id", "difficulty", "question_type",
    "structural_level", "semantic_level", "model",
    "gold_sql", "predicted_sql", "outcome", "correct", "error_msg",
]


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
    pct = done / total * 100
    print(
        f"  [{condition} | {model}] {done}/{total} ({pct:.1f}%) — "
        f"accuracy so far: {acc:.1%}",
        end="\r",
        flush=True,
    )


def load_experiment_questions(
    arcwise_path: str = ARCWISE_QUESTIONS_PATH,
    dev_json_path: str = DEV_JSON_PATH,
    questions_dir: str = QUESTIONS_DIR,
) -> List[dict]:
    with open(arcwise_path, encoding="utf-8") as f:
        arcwise = json.load(f)
    with open(dev_json_path, encoding="utf-8") as f:
        dev_by_id: Dict[int, dict] = {int(q["question_id"]): q for q in json.load(f)}
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
    k: Optional[int] = None,
    pool_path: Optional[str] = None,
) -> None:
    active_spider_dir = spider_dir if spider_dir is not None else SPIDER_DIR
    layout = DataLayout.create(DATA_DIR, spider_dir=active_spider_dir)
    active_results_dir = results_dir or RESULTS_DIR
    active_conditions = conditions if conditions is not None else CONDITIONS
    active_models = models if models is not None else MODELS
    active_k = k if k is not None else DENSE_K
    active_pool_path = pool_path if pool_path is not None else POOL_JSON_PATH
    tables_path = str(layout.tables_json)

    os.makedirs(active_results_dir, exist_ok=True)

    # Load test questions
    all_questions = load_experiment_questions()
    print(f"Loaded {len(all_questions)} test questions from {ARCWISE_QUESTIONS_PATH}")

    # Collect test question_ids to exclude from the retrieval pool
    test_ids = {int(q["question_id"]) for q in all_questions}

    questions = select_questions(
        all_questions,
        stratified_slices=STRATIFIED_DB_SAMPLE,
        max_prefix=MAX_QUESTIONS,
        exclude_db_ids=ARCWISE_EXCLUDED_DB_IDS,
    )

    from collections import Counter
    by_db = Counter(q["db_id"] for q in questions)
    print(f"Question selection: {len(questions)} questions across {len(by_db)} databases")
    for db_id in sorted(by_db):
        print(f"  {db_id}: {by_db[db_id]} questions")

    # Build dense retriever from pool, excluding all test question_ids
    print(f"\nLoading example pool from {active_pool_path}…")
    pool = load_pool(active_pool_path)
    print(f"  Pool size: {len(pool)} questions")
    print(f"  Excluding {len(test_ids)} test question_ids from pool")

    retriever = build_retriever(
        pool,
        exclude_ids=test_ids,
        cache_dir=EMBEDDINGS_CACHE_DIR,
    )

    # Validate prerequisites
    from run_experiment import validate_run_prerequisites
    validate_run_prerequisites(questions, active_conditions, layout)

    db_ids = list({q["db_id"] for q in questions})
    print(f"\nBuilding schema metadata for {len(db_ids)} databases…")
    builders = {db_id: SchemaBuilder(db_id, DATA_DIR, layout) for db_id in db_ids}

    sem_levels_needed = {sem for _, sem in active_conditions}
    rename_maps = {
        (db_id, sem): build_col_rename_map(db_id, DATA_DIR, sem, tables_path)
        for db_id in db_ids
        for sem in sem_levels_needed
    }

    total_runs = len(active_conditions) * len(active_models) * len(questions)
    print(f"\nTotal runs planned : {total_runs}")
    print(f"Dense k            : {active_k}")
    print(f"Results directory  : {active_results_dir}/")
    print()

    overall_done = 0
    overall_correct = 0

    for struct_level, sem_level in active_conditions:
        condition_label = f"L{struct_level}·S{sem_level}"

        for model in active_models:
            csv_path = results_file(
                model, struct_level, sem_level, active_k,
                results_dir=active_results_dir,
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

                    # Dense retrieval: top-k from same DB, excluding this question
                    raw_examples = retriever.retrieve(
                        q["question"],
                        db_id,
                        k=active_k,
                        exclude_question_id=q["question_id"],
                    )

                    # Adapt retrieved SQL column names to the current semantic level.
                    col_rename = rename_maps.get((db_id, sem_level))
                    few_shot_examples = [
                        (qt, adapt_sql_to_semantic_level(sql, col_rename))
                        for qt, sql in raw_examples
                    ] if raw_examples else None

                    prompt = build_prompt(
                        schema, q["question"],
                        structural_level=struct_level,
                        few_shot_examples=few_shot_examples,
                    )

                    predicted_sql = call_llm(model, prompt)

                    col_rename_map = rename_maps.get((db_id, sem_level))
                    result = evaluate(
                        db_path, predicted_sql, q["SQL"],
                        col_rename_map=col_rename_map,
                        verbose=False,
                    )

                    row = {
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
                    }
                    append_row(csv_path, row)
                    completed.add(q["question_id"])

                    done += 1
                    overall_done += 1
                    if result.correct:
                        correct += 1
                        overall_correct += 1

                    print_progress(done, len(questions), correct, condition_label, model)
                    time.sleep(MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS))

            finally:
                pass

            print()
            final_acc = correct / done if done > 0 else 0.0
            print(f"  Done. Accuracy: {correct}/{done} = {final_acc:.1%}")
            print(f"  Saved to: {csv_path}")

    print(f"\n{'='*60}")
    print("Experiment complete.")
    print(f"Results saved to: {active_results_dir}/")
    if overall_done > 0:
        print(f"Overall accuracy: {overall_correct}/{overall_done} = {overall_correct/overall_done:.1%}")


if __name__ == "__main__":
    args = parse_args()
    run(
        spider_dir=args.spider_dir,
        results_dir=args.results_dir,
        conditions=args.conditions,
        models=args.models,
        k=args.k,
        pool_path=args.pool,
    )
