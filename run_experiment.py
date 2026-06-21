"""
run_experiment.py

Runs the schema-effect experiment for specified conditions and models.
Results are written row-by-row to a CSV file so progress is never lost.

Checkpointing: if the output CSV already exists, rows that have already been
completed are skipped — you can safely interrupt and resume at any time.

Usage:
    python run_experiment.py

Output:
    results/results.csv   — one row per (question, condition, model)

Columns in results.csv:
    question_id, db_id, difficulty, question_type,
    structural_level, semantic_level, model,
    gold_sql, predicted_sql, outcome, correct, error_msg

Questions are loaded from dev_20240627/arcwise_plat_sql.json; difficulty and
question_type are joined from dev.json and question_types.json by question_id.
"""

import csv
import json
import os
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
from src.evaluator import (
    evaluate,
    build_col_rename_map,
    build_l1_col_rename_map,
    build_l2_col_rename_map,
)
from preprocess_data.questions.question_classifier import load_question_types

# ---------------------------------------------------------------------------
# Configuration — edit this section to change what gets run
# ---------------------------------------------------------------------------

DATA_DIR = "dev_20240627"
ARCWISE_QUESTIONS_PATH = os.path.join(DATA_DIR, "arcwise_plat_sql.json")
DEV_JSON_PATH = os.path.join(DATA_DIR, "dev.json")
RESULTS_DIR = "results"
QUESTIONS_DIR = "preprocess_data/questions"

def results_file(model: str, struct_level: int, sem_level: int) -> str:
    """Return the CSV path for a specific (model, condition) combination.
    Example: results/llama-3.3-70b-or__L3S3.csv
    """
    safe_model = model.replace("/", "-")
    return f"{RESULTS_DIR}/{safe_model}__L{struct_level}S{sem_level}.csv"

# Conditions to run: list of (structural_level, semantic_level) tuples
CONDITIONS = [
    (struct, sem)
    for struct in range(1, 7)   # L1–L6
    for sem in range(1, 4)      # S1–S3
]

# Models to run
MODELS = [
    "gemini-3.5-flash",
]

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
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def validate_run_prerequisites(
    questions: List[dict],
    conditions: List[Tuple[int, int]],
) -> None:
    """
    Fail fast if required SQLite files or schema support are missing for this run.
    """
    from src.schema_builder import L1_DB_IDS, L2_DB_IDS

    db_ids = sorted({q["db_id"] for q in questions})
    struct_levels = {sl for sl, _ in conditions}
    missing: List[str] = []

    for db_id in db_ids:
        p3 = os.path.join(DATA_DIR, "dev_databases", db_id, f"{db_id}.sqlite")
        if not os.path.isfile(p3):
            missing.append(f"3NF: {p3}")

        if 1 in struct_levels:
            if db_id not in L1_DB_IDS:
                missing.append(
                    f"L1: no 1NF spec for {db_id!r} (supported: {sorted(L1_DB_IDS)})"
                )
            elif not SchemaBuilder.has_one_nf_database(DATA_DIR, db_id):
                missing.append(f"L1: {SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id)}")

        if 2 in struct_levels:
            if db_id not in L2_DB_IDS:
                missing.append(
                    f"L2: no 2NF spec for {db_id!r} (supported: {sorted(L2_DB_IDS)})"
                )
            elif not SchemaBuilder.has_two_nf_database(DATA_DIR, db_id):
                missing.append(f"L2: {SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id)}")

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


def run() -> None:
    all_questions = load_experiment_questions()
    print(
        f"Loaded {len(all_questions)} questions from {ARCWISE_QUESTIONS_PATH} "
        f"(difficulty from {DEV_JSON_PATH}, types from question_types.json)"
    )

    stratified = STRATIFIED_DB_SAMPLE if STRATIFIED_DB_SAMPLE else None
    questions = select_questions(
        all_questions,
        stratified_slices=stratified,
        max_prefix=MAX_QUESTIONS,
        exclude_db_ids=ARCWISE_EXCLUDED_DB_IDS,
    )
    if stratified:
        print("Question selection: stratified (first n per db in arcwise file order)")
        for db_id, n in stratified:
            print(f"  {db_id}: {n} questions")
    else:
        from collections import Counter

        by_db = Counter(q["db_id"] for q in questions)
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

    validate_run_prerequisites(questions, CONDITIONS)

    # Pre-build one SchemaBuilder per database (reused across conditions)
    db_ids = list({q["db_id"] for q in questions})
    print(f"Building schema metadata for {len(db_ids)} databases...")
    builders = {db_id: SchemaBuilder(db_id, DATA_DIR) for db_id in db_ids}

    # Pre-build column rename maps for every (db, semantic_level) combination
    # so the evaluator can run predicted SQL against correctly-named views.
    # Returns None when no renaming is needed (e.g. S3 with original names).
    sem_levels_needed = {sem for _, sem in CONDITIONS}
    from src.schema_builder import L1_DB_IDS, L2_DB_IDS

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

    total_runs = len(CONDITIONS) * len(MODELS) * len(questions)
    print(f"\nTotal runs planned : {total_runs}")
    print()

    overall_done = 0
    overall_correct = 0

    for struct_level, sem_level in CONDITIONS:
        condition_label = f"L{struct_level}·S{sem_level}"

        for model in MODELS:
            csv_path = results_file(model, struct_level, sem_level)

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
                    # Skip if already done (checkpoint)
                    if q["question_id"] in completed:
                        continue

                    db_id = q["db_id"]
                    db_path = os.path.join(
                        DATA_DIR, "dev_databases", db_id, f"{db_id}.sqlite"
                    )

                    # Build schema string for this condition
                    schema = builders[db_id].build(struct_level, sem_level)

                    # Build prompt
                    prompt = build_prompt(
                        schema, q["question"], structural_level=struct_level
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
                                SchemaBuilder.one_nf_sqlite_path(DATA_DIR, db_id)
                            )
                            if not SchemaBuilder.has_one_nf_database(DATA_DIR, db_id):
                                raise FileNotFoundError(
                                    f"Missing 1NF DB for {db_id}: {mat_path}\n"
                                    f"Build: python3 -m preprocess_data.to_1nf.build_sqlite "
                                    f"--db {db_id}"
                                )
                            mat_rename = l1_rename_maps.get((db_id, sem_level))
                        else:
                            mat_path = str(
                                SchemaBuilder.two_nf_sqlite_path(DATA_DIR, db_id)
                            )
                            if not SchemaBuilder.has_two_nf_database(DATA_DIR, db_id):
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
    print(f"Results saved to: {RESULTS_DIR}/")
    if overall_done > 0:
        print(f"Overall accuracy: {overall_correct}/{overall_done} = {overall_correct/overall_done:.1%}")


if __name__ == "__main__":
    run()
