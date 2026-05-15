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
    question_id, db_id, difficulty,
    structural_level, semantic_level, model,
    predicted_sql, outcome, correct, error_msg
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

# Load API keys from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # dotenv not installed — keys must be set as environment variables

from src.schema_builder import SchemaBuilder
from src.prompt_builder import build_prompt
from src.llm_runner import call_llm
from src.evaluator import evaluate, build_col_rename_map, open_l1_eval_connection
from to_1nf.convert import view_ddls

# ---------------------------------------------------------------------------
# Configuration — edit this section to change what gets run
# ---------------------------------------------------------------------------

DATA_DIR = "dev_20240627"
RESULTS_DIR = "results"


def results_file(model: str, struct_level: int, sem_level: int) -> str:
    """Return the CSV path for a specific (model, condition) combination.
    Example: results/llama-3.3-70b-or__L3S3.csv
    """
    safe_model = model.replace("/", "-")
    return f"{RESULTS_DIR}/{safe_model}__L{struct_level}S{sem_level}.csv"

# Conditions to run: list of (structural_level, semantic_level) tuples
CONDITIONS = [
    (1, 3),   # L3 · S3
]

# Models to run
MODELS = [
    "llama-3.3-70b-or",       # Llama 3.3 70B via OpenRouter (working, free)
    #"gemini-2.5-flash",
]

# Per-model delay in seconds between API calls to respect rate limits.
MODEL_DELAY = {
    "gemini-2.0-flash":   3,
    "gemini-2.5-flash":   1,
    "llama-3.3-70b-or":   1,
    "llama-3.1-8b-or":    1,
    "qwen2.5-coder-32b":  2,
    "llama-3.1-8b":       1,
    "llama-3.3-70b":      1,
}
DELAY_BETWEEN_CALLS = 3  # fallback if model not in MODEL_DELAY

# Question selection
# ------------------
# Set STRATIFIED_DB_SAMPLE to a non-empty list of (db_id, n) to take the first n
# questions for each database in dev.json file order (deterministic; same ids
# every run). Set to None to instead take the first MAX_QUESTIONS rows from
# dev.json as a single prefix (original behaviour).
#
# Example: 4 × 25 = 100 questions from four databases.
STRATIFIED_DB_SAMPLE = [
    ("formula_1", 25),
    ("financial", 25),
    ("card_games", 25),
    ("student_club", 25),  # fourth DB — replace if you want a different one (≥25 qs in dev)
]

# Used only when STRATIFIED_DB_SAMPLE is None.
# Set to None to run all 1534 questions.
MAX_QUESTIONS = 100


def select_questions(
    all_questions: List[dict],
    *,
    stratified_slices: Optional[List[Tuple[str, int]]],
    max_prefix: Optional[int],
) -> List[dict]:
    """
    Return the question list for this run.

    If stratified_slices is a non-empty list of (db_id, n), take the first n
    questions for each db_id in the order they appear in all_questions (dev.json
    order). Otherwise take all_questions[:max_prefix] (or all if max_prefix is None).
    """
    if stratified_slices:
        by_db: dict[str, List[dict]] = {}
        for q in all_questions:
            db = q["db_id"]
            by_db.setdefault(db, []).append(q)

        picked: List[dict] = []
        for db_id, n in stratified_slices:
            bucket = by_db.get(db_id, [])
            if len(bucket) < n:
                raise ValueError(
                    f"Stratified sample: database {db_id!r} has only {len(bucket)} "
                    f"questions in dev.json but {n} were requested."
                )
            picked.extend(bucket[:n])
        return picked

    if max_prefix is not None:
        return all_questions[:max_prefix]
    return list(all_questions)

# ---------------------------------------------------------------------------
# CSV schema
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "question_id",
    "db_id",
    "difficulty",
    "structural_level",
    "semantic_level",
    "model",
    "gold_sql",
    "predicted_sql",
    "outcome",
    "correct",
    "error_msg",
]


def load_completed(csv_path: str) -> set:
    """
    Read an existing results CSV and return the set of completed question_ids
    so we can skip them on resume. Each file covers one (model, condition) pair.
    """
    completed, _ = load_completed_with_correct(csv_path)
    return completed


def load_completed_with_correct(csv_path: str) -> Tuple[set, int]:
    """
    Same as load_completed, but also returns how many completed rows were correct
    (for accurate progress / final summary when resuming a partial run).
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
    # Load questions
    questions_path = os.path.join(DATA_DIR, "dev.json")
    with open(questions_path, encoding="utf-8") as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions from {questions_path}")

    stratified = STRATIFIED_DB_SAMPLE if STRATIFIED_DB_SAMPLE else None
    questions = select_questions(
        questions,
        stratified_slices=stratified,
        max_prefix=MAX_QUESTIONS,
    )
    if stratified:
        print("Question selection: stratified (first n per db in dev.json order)")
        for db_id, n in stratified:
            print(f"  {db_id}: {n} questions")
        print(f"Total selected: {len(questions)}")
    elif MAX_QUESTIONS is not None:
        print(f"TEST MODE — first {MAX_QUESTIONS} questions from dev.json (prefix)")
    else:
        print("Running on full dev set (all questions)")

    # Pre-build one SchemaBuilder per database (reused across conditions)
    db_ids = list({q["db_id"] for q in questions})
    print(f"Building schema metadata for {len(db_ids)} databases...")
    builders = {db_id: SchemaBuilder(db_id, DATA_DIR) for db_id in db_ids}

    # Pre-build column rename maps for every (db, semantic_level) combination
    # so the evaluator can run predicted SQL against correctly-named views.
    # Returns None when no renaming is needed (e.g. S3 with original names).
    sem_levels_needed = {sem for _, sem in CONDITIONS}
    rename_maps = {
        (db_id, sem): build_col_rename_map(db_id, DATA_DIR, sem)
        for db_id in db_ids
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

            l1_conn_by_db = {}
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
                    prompt = build_prompt(schema, q["question"])

                    # Heartbeat: progress only updates after the LLM returns
                    print(
                        f"  → LLM {model}  q_id={q['question_id']}  db={db_id}  "
                        f"prompt_len={len(prompt)}",
                        flush=True,
                    )

                    # Call LLM
                    predicted_sql = call_llm(model, prompt)
                    print(
                        f"  ⇠ LLM returned ({len(predicted_sql)} chars)",
                        flush=True,
                    )

                    if struct_level == 1:
                        if db_id not in l1_conn_by_db:
                            print(
                                f"  [L1] Installing wide TEMP VIEWs for {db_id} "
                                f"(one-time per DB; large joins can take minutes)…",
                                flush=True,
                            )
                            ddls = view_ddls(
                                builders[db_id].get_one_nf_plan(sem_level)
                            )
                            l1_conn_by_db[db_id] = open_l1_eval_connection(
                                db_path, ddls
                            )
                            print(f"  [L1] Ready for {db_id}.", flush=True)
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            None,
                            None,
                            l1_conn_by_db[db_id],
                            verbose=True,
                        )
                    else:
                        col_rename_map = rename_maps.get((db_id, sem_level))
                        result = evaluate(
                            db_path,
                            predicted_sql,
                            q["SQL"],
                            col_rename_map,
                            None,
                            None,
                            verbose=False,
                        )

                    # Write result immediately (so nothing is lost on crash)
                    row = {
                        "question_id": q["question_id"],
                        "db_id": db_id,
                        "difficulty": q["difficulty"],
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

                    # Rate-limit pause (per-model)
                    delay = MODEL_DELAY.get(model, DELAY_BETWEEN_CALLS)
                    time.sleep(delay)
            finally:
                for _c in l1_conn_by_db.values():
                    try:
                        _c.close()
                    except Exception:
                        pass
                l1_conn_by_db.clear()

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
