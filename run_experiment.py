"""
run_experiment.py

Runs the schema-effect experiment for specified conditions and models.
Results are written row-by-row to a CSV file so progress is never lost.

Checkpointing: if the output CSV already exists, rows that have already been
completed are skipped — you can safely interrupt and resume at any time.

Usage:
    python run_experiment.py
    python run_experiment.py --spider-dir dev_20240627/spider_data \\
        --condition L3S3 --models gemini-2.5-flash

Output:
    results/ or results/spider/   — one CSV per (model, condition)

Columns in results.csv:
    question_id, db_id, difficulty, question_type,
    structural_level, semantic_level, model,
    gold_sql, predicted_sql, outcome, correct, error_msg

Questions are loaded from dev_20240627/arcwise_plat_sql.json; difficulty and
question_type are joined from dev.json and question_types.json by question_id.
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

sys.path.insert(0, str(Path(__file__).parent))

# Load schema_effect/.env; overrides any API keys exported in the shell.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=True)
except ImportError:
    pass  # dotenv not installed — keys must be set as environment variables

from src.schema_builder import SchemaBuilder
from src.prompt_builder import build_prompt
from src.llm_runner import call_llm
from src.few_shot import (
    select_fixed_examples_by_difficulty,
    load_few_shot_json,
    get_sql_for_struct_level,
    adapt_sql_to_semantic_level,
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
# Configuration — edit this section to change what gets run
# ---------------------------------------------------------------------------

DATA_DIR = "dev_20240627"
ARCWISE_QUESTIONS_PATH = os.path.join(DATA_DIR, "arcwise_plat_sql.json")
DEV_JSON_PATH = os.path.join(DATA_DIR, "dev.json")
RESULTS_DIR = "results"
QUESTIONS_DIR = "preprocess_data/questions"

# ---------------------------------------------------------------------------
# Spider mode
# ---------------------------------------------------------------------------
# Set SPIDER_DIR to a Spider data root (containing database/ and tables.json)
# to run the experiment on Spider databases instead of the BIRD arcwise set.
# When set, questions are loaded from SPIDER_QUESTIONS_PATH (already converted
# to the experiment format: question_id, db_id, question, SQL, evidence,
# difficulty, question_type). Set SPIDER_DIR = None for the default BIRD run.
SPIDER_DIR: Optional[str] = None
SPIDER_QUESTIONS_PATH = os.path.join(
    DATA_DIR, "spider_data", "experiment_questions_car1_tvshow.json"
)


def get_data_layout() -> DataLayout:
    """Resolve the active data layout (BIRD by default, Spider when SPIDER_DIR is set)."""
    return DataLayout.create(DATA_DIR, spider_dir=SPIDER_DIR)

def results_file(
    model: str,
    struct_level: int,
    sem_level: int,
    results_dir: Optional[str] = None,
    few_shot_n: int = 0,
    cot: bool = False,
    evidence: bool = False,
) -> str:
    """Return the CSV path for a specific (model, condition) combination.
    Examples:
      results/llama-3.3-70b-or__L3S3.csv              (zero-shot)
      results/llama-3.3-70b-or__L3S3__fs3.csv         (3-shot)
      results/llama-3.3-70b-or__L3S3__cot__ev.csv     (cot + evidence)
    """
    safe_model = model.replace("/", "-")
    out_dir = results_dir or RESULTS_DIR
    fs_suffix = f"__fs{few_shot_n}" if few_shot_n > 0 else ""
    cot_suffix = "__cot" if cot else ""
    ev_suffix = "__ev" if evidence else ""
    return f"{out_dir}/{safe_model}__L{struct_level}S{sem_level}{fs_suffix}{cot_suffix}{ev_suffix}.csv"


def _parse_condition(value: str) -> Tuple[int, int]:
    m = re.fullmatch(r"[Ll](\d+)[Ss](\d+)", value)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid condition {value!r}; expected format L3S3"
        )
    return int(m.group(1)), int(m.group(2))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the schema-effect experiment.")
    p.add_argument(
        "--spider-dir",
        default=None,
        help="Spider data root (database/ + tables.json). Enables Spider mode.",
    )
    p.add_argument(
        "--questions",
        default=None,
        help="Spider-mode question file in experiment format "
             "(default: SPIDER_QUESTIONS_PATH), e.g. "
             "dev_20240627/wamex_data/experiment_questions_wamex.json.",
    )
    p.add_argument(
        "--results-dir",
        default=None,
        help="Output directory (default: results/spider in Spider mode, else results).",
    )
    p.add_argument(
        "--condition",
        action="append",
        dest="conditions",
        type=_parse_condition,
        metavar="LnSm",
        help="Condition to run, e.g. L3S3 (repeatable; default: all 18).",
    )
    p.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Models to run (default: MODELS in config).",
    )
    p.add_argument(
        "--few-shot",
        type=int,
        default=None,
        metavar="N",
        help="Number of per-database few-shot examples (0 = zero-shot, default: FEW_SHOT_N).",
    )
    p.add_argument(
        "--cot",
        action="store_true",
        default=False,
        help="Prepend a step-by-step query writing guide to every prompt.",
    )
    p.add_argument(
        "--evidence",
        action="store_true",
        default=False,
        help="Include the question's evidence field as a '### Evidence:' block in the prompt.",
    )
    return p.parse_args(argv)

# Conditions to run: list of (structural_level, semantic_level) tuples
# Remaining Spider (gemini-2.5 L3S1–S3 done). Reset to all 18 for full runs:
#   [(s, m) for s in range(1, 7) for m in range(1, 4)]
CONDITIONS = [
    (1, 1), (1, 2), (1, 3),
    (2, 1), (2, 2), (2, 3),
    (4, 1), (4, 2), (4, 3),
    (5, 1), (5, 2), (5, 3),
    (6, 1), (6, 2), (6, 3),
]

# Models to run
MODELS = [
    "gemini-2.5-flash",
]

# Few-shot configuration
# Set to 0 for zero-shot (default). Set to n > 0 to include n per-database
# examples drawn from arcwise_plat_sql.json (excluding the test question).
# Results are written to separate CSVs with an '__fsN' suffix.
# Note: for L1/L2 conditions the examples use original 3NF SQL, which does not
# align with the denormalised schema — their examples show task format only.
FEW_SHOT_N: int = 0

# Per-model delay in seconds between API calls to respect rate limits.
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
DELAY_BETWEEN_CALLS = 3  # fallback if model not in MODEL_DELAY

# Question selection (from arcwise_plat_sql.json)
# ---------------------------------------------------------------------------
# Full arcwise run (9 DBs): set STRATIFIED_DB_SAMPLE = None and keep exclusions below.
# Pilot (100 qs): set STRATIFIED_DB_SAMPLE to a list of (db_id, n) — exclusions still apply.
ARCWISE_EXCLUDED_DB_IDS = frozenset({"card_games", "codebase_community"})

STRATIFIED_DB_SAMPLE: Optional[List[Tuple[str, int]]] = None

# Used only when STRATIFIED_DB_SAMPLE is None. None = all questions after filters.
MAX_QUESTIONS: Optional[int] = None


def select_questions(
    all_questions: List[dict],
    *,
    stratified_slices: Optional[List[Tuple[str, int]]],
    max_prefix: Optional[int],
    exclude_db_ids: Optional[FrozenSet[str]] = None,
) -> List[dict]:
    """
    Subset questions for this run.

    If exclude_db_ids is set, drop questions for those db_id values first.
    If stratified_slices is set, take the first n questions per db_id in the
    order they appear in arcwise_plat_sql.json. Otherwise take a prefix of
    all_questions (or all if max_prefix is None).
    """
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
                raise ValueError(
                    f"Stratified sample: database {db_id!r} has only {len(bucket)} "
                    f"questions in arcwise_plat_sql.json but {n} were requested."
                )
            picked.extend(bucket[:n])
        return picked

    if max_prefix is not None:
        return all_questions[:max_prefix]
    return list(all_questions)


def load_experiment_questions(
    arcwise_path: str = ARCWISE_QUESTIONS_PATH,
    dev_json_path: str = DEV_JSON_PATH,
    questions_dir: str = QUESTIONS_DIR,
) -> List[dict]:
    """
    Load the experiment question set from arcwise_plat_sql.json and attach
    difficulty (dev.json) and question_type (question_types.json) by question_id.
    """
    with open(arcwise_path, encoding="utf-8") as f:
        arcwise = json.load(f)

    with open(dev_json_path, encoding="utf-8") as f:
        dev_by_id: Dict[int, dict] = {
            int(q["question_id"]): q for q in json.load(f)
        }

    types_by_id = load_question_types(questions_dir)

    questions: List[dict] = []
    for rec in arcwise:
        qid = int(rec["question_id"])
        dev_rec = dev_by_id.get(qid)
        if dev_rec is None:
            raise KeyError(
                f"question_id {qid} in {arcwise_path} not found in {dev_json_path}"
            )
        type_rec = types_by_id.get(qid)
        if type_rec is None:
            raise KeyError(
                f"question_id {qid} missing from question_types.json "
                f"(run classify_questions.py)"
            )
        questions.append(
            {
                "question_id": qid,
                "db_id": rec["db_id"],
                "question": rec["question"],
                "SQL": rec["SQL"],
                "evidence": rec.get("evidence", ""),
                "difficulty": dev_rec["difficulty"],
                "question_type": type_rec["question_type"],
            }
        )
    return questions


def load_spider_questions(path: str = SPIDER_QUESTIONS_PATH) -> List[dict]:
    """
    Load pre-converted Spider questions (already in experiment format:
    question_id, db_id, question, SQL, evidence, difficulty, question_type).
    """
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    questions: List[dict] = []
    for rec in records:
        missing = [k for k in ("question_id", "db_id", "question", "SQL") if k not in rec]
        if missing:
            raise KeyError(
                f"Spider question record missing keys {missing} in {path}: {rec!r}"
            )
        questions.append(
            {
                "question_id": int(rec["question_id"]),
                "db_id": rec["db_id"],
                "question": rec["question"],
                "SQL": rec["SQL"],
                "evidence": rec.get("evidence"),
                "difficulty": rec.get("difficulty"),
                "question_type": rec.get("question_type", "unknown"),
            }
        )
    return questions


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
]


def load_completed_with_correct(csv_path: str) -> Tuple[set, int]:
    """
    Read an existing results CSV: completed question_ids and count of correct rows
    (for resume skipping and accurate progress / final summary).
    """
    completed = set()
    n_correct = 0
    if not os.path.exists(csv_path):
        return completed, n_correct
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            completed.add(int(row["question_id"]))
            if row.get("correct", "").strip().lower() == "true":
                n_correct += 1
    return completed, n_correct


def append_row(csv_path: str, row: dict) -> None:
    """Append one result row to the CSV (writes header if file is new)."""
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


def validate_run_prerequisites(
    questions: List[dict],
    conditions: List[Tuple[int, int]],
    layout: Optional[DataLayout] = None,
) -> None:
    """
    Fail fast if required SQLite files or schema support are missing for this run.
    """
    from src.schema_builder import L1_DB_IDS, L2_DB_IDS

    if layout is None:
        layout = DataLayout.create(DATA_DIR)

    db_ids = sorted({q["db_id"] for q in questions})
    struct_levels = {sl for sl, _ in conditions}
    missing: List[str] = []

    for db_id in db_ids:
        p3 = layout.source_sqlite(db_id)
        if not p3.is_file():
            missing.append(f"3NF: {p3}")

        if 1 in struct_levels:
            if db_id not in L1_DB_IDS:
                missing.append(
                    f"L1: no 1NF spec for {db_id!r} (supported: {sorted(L1_DB_IDS)})"
                )
            elif not SchemaBuilder.has_one_nf_database(DATA_DIR, db_id, layout):
                missing.append(f"L1: {layout.one_nf_sqlite(db_id)}")

        if 2 in struct_levels:
            if db_id not in L2_DB_IDS:
                missing.append(
                    f"L2: no 2NF spec for {db_id!r} (supported: {sorted(L2_DB_IDS)})"
                )
            elif not SchemaBuilder.has_two_nf_database(DATA_DIR, db_id, layout):
                missing.append(f"L2: {layout.two_nf_sqlite(db_id)}")

    if missing:
        raise FileNotFoundError(
            "Missing databases or unsupported db_id for selected CONDITIONS:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


def print_progress(done: int, total: int, correct: int, condition: str, model: str) -> None:
    acc = correct / done if done > 0 else 0.0
    pct = done / total * 100
    print(
        f"  [{condition} | {model}] {done}/{total} ({pct:.1f}%) — "
        f"accuracy so far: {acc:.1%}",
        end="\r",
        flush=True,
    )


def run(
    *,
    spider_dir: Optional[str] = None,
    questions_path: Optional[str] = None,
    results_dir: Optional[str] = None,
    conditions: Optional[List[Tuple[int, int]]] = None,
    models: Optional[List[str]] = None,
    few_shot_n: Optional[int] = None,
    cot: bool = False,
    evidence: bool = False,
) -> None:
    active_spider_dir = spider_dir if spider_dir is not None else SPIDER_DIR
    layout = DataLayout.create(DATA_DIR, spider_dir=active_spider_dir)
    spider_mode = layout.layout == "spider"
    active_results_dir = (
        results_dir
        if results_dir is not None
        else ("results/spider" if spider_mode else RESULTS_DIR)
    )
    active_conditions = conditions if conditions is not None else CONDITIONS
    active_models = models if models is not None else MODELS
    active_few_shot_n = few_shot_n if few_shot_n is not None else FEW_SHOT_N
    active_cot = cot
    active_evidence = evidence
    tables_path = str(layout.tables_json)

    os.makedirs(active_results_dir, exist_ok=True)

    if spider_mode:
        active_questions_path = questions_path or SPIDER_QUESTIONS_PATH
        all_questions = load_spider_questions(active_questions_path)
        print(
            f"[Spider mode] Loaded {len(all_questions)} questions from "
            f"{active_questions_path}"
        )
        print(f"  data layout : {layout.layout}")
        print(f"  database dir: {layout.database_dir}")
        print(f"  tables json : {layout.tables_json}")
    else:
        all_questions = load_experiment_questions()
        print(
            f"Loaded {len(all_questions)} questions from {ARCWISE_QUESTIONS_PATH} "
            f"(difficulty from {DEV_JSON_PATH}, types from question_types.json)"
        )

    # Select fixed few-shot examples from BIRD questions before any filtering.
    # One question per difficulty level (simple/moderate/challenging) per DB.
    # These reserved questions are excluded from the evaluation set.
    reserved_for_few_shot: set = set()
    few_shot_json: dict = {}
    if active_few_shot_n > 0 and not spider_mode:
        _, reserved_for_few_shot = select_fixed_examples_by_difficulty(all_questions)
        few_shot_json = load_few_shot_json()
        print(f"Few-shot: {active_few_shot_n}-shot — reserved "
              f"{len(reserved_for_few_shot)} questions as fixed examples (1 per difficulty per DB)")
        for db_id in sorted(few_shot_json):
            print(f"  {db_id}: {len(few_shot_json[db_id])} example(s)")

    stratified = STRATIFIED_DB_SAMPLE if STRATIFIED_DB_SAMPLE else None
    questions = select_questions(
        all_questions,
        stratified_slices=stratified,
        max_prefix=MAX_QUESTIONS,
        exclude_db_ids=None if spider_mode else ARCWISE_EXCLUDED_DB_IDS,
    )

    # Remove reserved few-shot questions from the evaluation set
    if reserved_for_few_shot:
        before = len(questions)
        questions = [q for q in questions if q["question_id"] not in reserved_for_few_shot]
        print(f"  Removed {before - len(questions)} reserved example questions from test set")

    if stratified:
        print("Question selection: stratified (first n per db in arcwise file order)")
        for db_id, n in stratified:
            print(f"  {db_id}: {n} questions")
    else:
        from collections import Counter

        by_db = Counter(q["db_id"] for q in questions)
        if spider_mode:
            print(f"Question selection: all Spider questions in {len(by_db)} databases")
        else:
            print(
                "Question selection: all arcwise questions in 9 databases "
                f"(excluding {', '.join(sorted(ARCWISE_EXCLUDED_DB_IDS))})"
            )
        for db_id in sorted(by_db):
            print(f"  {db_id}: {by_db[db_id]} questions")
    if MAX_QUESTIONS is not None:
        print(f"  (then truncated to first {MAX_QUESTIONS} in file order)")
    print(f"Total selected: {len(questions)}")

    n_agg = sum(1 for q in questions if q["question_type"] == "aggregate")
    print(f"  {n_agg} aggregate, {len(questions) - n_agg} retrieval")

    validate_run_prerequisites(questions, active_conditions, layout)

    # Pre-build one SchemaBuilder per database (reused across conditions)
    db_ids = list({q["db_id"] for q in questions})
    print(f"Building schema metadata for {len(db_ids)} databases...")
    builders = {db_id: SchemaBuilder(db_id, DATA_DIR, layout) for db_id in db_ids}

    # Pre-build column rename maps for every (db, semantic_level) combination
    # so the evaluator can run predicted SQL against correctly-named views.
    # Returns None when no renaming is needed (e.g. S3 with original names).
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
    print(f"\nTotal runs planned : {total_runs}")
    print(f"Results directory  : {active_results_dir}/")
    print()

    overall_done = 0
    overall_correct = 0

    for struct_level, sem_level in active_conditions:
        condition_label = f"L{struct_level}·S{sem_level}"

        for model in active_models:
            csv_path = results_file(
                model, struct_level, sem_level,
                results_dir=active_results_dir,
                few_shot_n=active_few_shot_n,
                cot=active_cot,
                evidence=active_evidence,
            )

            # Load completed question_ids for this specific file
            completed, correct = load_completed_with_correct(csv_path)
            remaining = len(questions) - len(completed)

            done = len(completed)
            print(f"\n{'='*60}")
            print(f"  Condition : {condition_label}")
            print(f"  Model     : {model}")
            print(f"  Output    : {csv_path}")
            print(f"  Completed : {done}  |  Remaining: {remaining}")
            print(f"{'='*60}")

            pred_conn_by_db = {}
            try:
                for q in questions:
                    # Skip if already done (checkpoint); re-read disk in case of resume.
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

                    # Build schema string for this condition
                    schema = builders[db_id].build(struct_level, sem_level)

                    # Build few-shot examples for this question (fixed per DB).
                    # Load examples from JSON, pick the sql_l1/l2/l3 variant for
                    # this structural level, then apply semantic column renaming.
                    few_shot_examples = None
                    if active_few_shot_n > 0 and few_shot_json:
                        db_entries = few_shot_json.get(db_id, [])
                        if struct_level == 1:
                            sem_rename = l1_rename_maps.get((db_id, sem_level))
                        elif struct_level == 2:
                            sem_rename = l2_rename_maps.get((db_id, sem_level))
                        else:
                            sem_rename = rename_maps.get((db_id, sem_level))
                        few_shot_examples = [
                            (
                                e["question"],
                                adapt_sql_to_semantic_level(
                                    get_sql_for_struct_level(e, struct_level),
                                    sem_rename,
                                ),
                            )
                            for e in db_entries
                        ]

                    # Build prompt
                    prompt = build_prompt(
                        schema, q["question"],
                        structural_level=struct_level,
                        semantic_level=sem_level,
                        few_shot_examples=few_shot_examples,
                        include_cot=active_cot,
                        evidence=q.get("evidence") if active_evidence else None,
                    )

                    #print(
                    #    f"\n  → question_id={q['question_id']} ({db_id}) "
                    #    f"[{condition_label}] calling LLM…",
                    #    flush=True,
                    #)
                    t_llm = time.time()
                    predicted_sql = call_llm(model, prompt)
                    #print(
                    #    f"  ← LLM returned in {time.time() - t_llm:.1f}s "
                    #    f"(pred len={len(predicted_sql or '')})",
                    #    flush=True,
                    #)

                    if struct_level in (1, 2):
                        from src.evaluator import _build_pred_connection

                        if struct_level == 1:
                            mat_path = str(
                                SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id, layout)
                            )
                            if not SchemaBuilder.has_one_nf_database(
                                DATA_DIR, db_id, layout
                            ):
                                raise FileNotFoundError(
                                    f"Missing 1NF DB for {db_id}: {mat_path}\n"
                                    f"Build: python3 -m preprocess_data.to_1nf.build_sqlite "
                                    f"--db {db_id}"
                                )
                            mat_rename = l1_rename_maps.get((db_id, sem_level))
                        else:
                            mat_path = str(
                                SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id, layout)
                            )
                            if not SchemaBuilder.has_two_nf_database(
                                DATA_DIR, db_id, layout
                            ):
                                raise FileNotFoundError(
                                    f"Missing 2NF DB for {db_id}: {mat_path}\n"
                                    f"Build: python3 -m preprocess_data.to_2nf.build_sqlite "
                                    f"--db {db_id}"
                                )
                            mat_rename = l2_rename_maps.get((db_id, sem_level))

                        conn_key = (db_id, struct_level)
                        if conn_key not in pred_conn_by_db:
                            pred_conn_by_db[conn_key] = _build_pred_connection(
                                mat_path, mat_rename or {}
                            )
                        #print("  → evaluating SQL…", flush=True)
                        t_eval = time.time()
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            col_rename_map=mat_rename,
                            predicted_db_path=mat_path,
                            pred_reuse_connection=pred_conn_by_db[conn_key],
                            verbose=False,
                        )
                        #print(
                        #    f"  ← eval done in {time.time() - t_eval:.1f}s "
                        #    f"({result.outcome})",
                        #    flush=True,
                        #)
                    else:
                        col_rename_map = rename_maps.get((db_id, sem_level))
                        #print("  → evaluating SQL…", flush=True)
                        t_eval = time.time()
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            col_rename_map=col_rename_map,
                            verbose=False,
                        )
                        #print(
                        #    f"  ← eval done in {time.time() - t_eval:.1f}s "
                        #    f"({result.outcome})",
                        #    flush=True,
                        #)

                    # Write result immediately (so nothing is lost on crash)
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
                for _c in pred_conn_by_db.values():
                    try:
                        _c.close()
                    except Exception:
                        pass
                pred_conn_by_db.clear()

            # Final line for this condition+model
            print()  # newline after \r progress
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
        questions_path=args.questions,
        results_dir=args.results_dir,
        conditions=args.conditions,
        models=args.models,
        few_shot_n=args.few_shot,
        cot=args.cot,
        evidence=args.evidence,
    )
