"""
Build the WAMEX held-out subset (Acuity release, PascalSun/acuity) in Spider-mode layout.

Outputs under ``dev_20240627/wamex_data/``:
  database/wamex/wamex.sqlite        hub + 4 satellites, declared PK/FK
  tables.json                        Spider-format schema entry
  experiment_questions_wamex.json    ~150 stratified questions (experiment format)

Usage:
  python -m preprocess_data.wamex.build_wamex_subset \
      --source /path/to/wamex.sqlite --qa /path/to/benchmarks/wamex/wamex/qa_pairs.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sqlite3
from collections import Counter, defaultdict

DB_ID = "wamex"
OUT_DIR = os.path.join("dev_20240627", "wamex_data")

HUB = "wamex_reports"
SATELLITES = ("drilling_summaries", "abstracts", "storages", "geo_chemistry")
ALL_SATELLITES = SATELLITES + ("survey_reports", "documents", "digital_files", "historic_titles")

# abstracts.abstract is never filtered on by any released question; truncated to
# keep the 1NF wide table small (identical text is served at every level).
ABSTRACT_MAX_CHARS = 200

# Stratified sample sizes per tier (E/M/H); multi-join classes are kept in full.
SINGLE_TABLE_PER_TIER = 18
ONE_HOP_PER_TIER = 18
SEED = 42

DDL = {
    HUB: """CREATE TABLE wamex_reports (
    anumber INTEGER PRIMARY KEY,
    reporttitle TEXT,
    reportdate TEXT,
    authorids TEXT,
    authornames TEXT,
    operatorids TEXT,
    operators TEXT,
    projectname TEXT,
    targetcommoditiesids TEXT,
    targetcommoditiesnames TEXT,
    keywords TEXT,
    confidentiality TEXT
)""",
    "drilling_summaries": """CREATE TABLE drilling_summaries (
    id INTEGER PRIMARY KEY,
    anumber INTEGER NOT NULL,
    holetype TEXT,
    numberofholes INTEGER,
    totaldrilled INTEGER,
    FOREIGN KEY (anumber) REFERENCES wamex_reports(anumber)
)""",
    "abstracts": """CREATE TABLE abstracts (
    id INTEGER PRIMARY KEY,
    anumber INTEGER NOT NULL,
    abstract TEXT,
    FOREIGN KEY (anumber) REFERENCES wamex_reports(anumber)
)""",
    "storages": """CREATE TABLE storages (
    id INTEGER PRIMARY KEY,
    anumber INTEGER NOT NULL,
    volume REAL,
    storage TEXT,
    number TEXT,
    description TEXT,
    FOREIGN KEY (anumber) REFERENCES wamex_reports(anumber)
)""",
    "geo_chemistry": """CREATE TABLE geo_chemistry (
    id INTEGER PRIMARY KEY,
    anumber INTEGER NOT NULL,
    sampletype TEXT,
    numberofsamples INTEGER,
    FOREIGN KEY (anumber) REFERENCES wamex_reports(anumber)
)""",
}


def _columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    return [(r[1], r[2]) for r in conn.execute(f'PRAGMA table_info("{table}")')]


def build_database(source: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        os.remove(dest)
    conn = sqlite3.connect(dest)
    conn.execute("ATTACH DATABASE ? AS src", (source,))
    for table in (HUB,) + SATELLITES:
        conn.execute(DDL[table])
        cols = [c for c, _ in _columns(conn, table)]
        select = ", ".join(
            f"substr(abstract, 1, {ABSTRACT_MAX_CHARS})" if (table, c) == ("abstracts", "abstract") else c
            for c in cols
        )
        # Satellite rows whose anumber is absent from the hub are dropped (FK integrity).
        where = "" if table == HUB else f" WHERE anumber IN (SELECT anumber FROM src.{HUB})"
        conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) SELECT {select} FROM src.{table}{where}")
        if table != HUB:
            conn.execute(f"CREATE INDEX idx_{table}_anumber ON {table}(anumber)")
    conn.commit()
    conn.execute("DETACH DATABASE src")
    conn.execute("VACUUM")
    conn.close()


def _distinct_gold(sql: str) -> str:
    """
    Released gold SQL is a plain JOIN, so fan-out repeats report numbers; the
    released answer (``answer_row_ids``) is a key set. DISTINCT makes the gold
    result equal that set under multiset comparison.
    """
    sql = " ".join(sql.split())
    if not sql.startswith("SELECT wamex_reports.anumber FROM "):
        raise ValueError(f"unexpected gold SQL shape: {sql[:80]}")
    return sql.replace("SELECT ", "SELECT DISTINCT ", 1)


def select_questions(qa_path: str) -> list[dict]:
    with open(qa_path, encoding="utf-8") as f:
        pairs = json.load(f)["qa_pairs"]

    by_class: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in pairs:
        used = {s for s in ALL_SATELLITES if re.search(rf"\b{s}\b", p["sql"])}
        if not used <= set(SATELLITES):
            continue
        pattern, tier = p["strategy"][:-1], p["strategy"][-1]
        by_class[(pattern, tier)].append(p)

    rng = random.Random(SEED)
    chosen: list[dict] = []
    for (pattern, tier), items in sorted(by_class.items()):
        cap = {"0": SINGLE_TABLE_PER_TIER, "1p": ONE_HOP_PER_TIER}.get(pattern)
        if cap is not None and len(items) > cap:
            items = rng.sample(items, cap)
        chosen.extend(items)

    tier_name = {"E": "simple", "M": "moderate", "H": "challenging"}
    questions = []
    for qid, p in enumerate(chosen):
        questions.append(
            {
                "question_id": qid,
                "db_id": DB_ID,
                "question": p["question"],
                "SQL": _distinct_gold(p["sql"]),
                "evidence": None,
                "difficulty": tier_name[p["strategy"][-1]],
                "question_type": p["strategy"][:-1],
                "acuity_uid": p["uid"],
                "acuity_strategy": p["strategy"],
                "canonical_question": p["canonical_question"],
                "answer_row_ids": p["answer_row_ids"],
            }
        )
    return questions


def verify_gold(db_path: str, questions: list[dict]) -> None:
    conn = sqlite3.connect(db_path)
    bad = []
    for q in questions:
        got = [r[0] for r in conn.execute(q["SQL"])]
        # multiset check: no duplicate rows, and exactly the released key set
        if len(got) != len(set(got)) or set(got) != set(q["answer_row_ids"]):
            bad.append((q["question_id"], len(got), len(q["answer_row_ids"])))
    conn.close()
    if bad:
        raise RuntimeError(f"gold SQL disagrees with released answer_row_ids: {bad}")


def build_tables_json(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    tables = (HUB,) + SATELLITES
    column_names = [[-1, "*"]]
    column_types = ["text"]
    primary_keys, fk_src = [], []
    for ti, table in enumerate(tables):
        for name, ctype in _columns(conn, table):
            column_names.append([ti, name])
            column_types.append("text" if ctype.upper() == "TEXT" else "number")
            idx = len(column_names) - 1
            if (table == HUB and name == "anumber") or (table != HUB and name == "id"):
                primary_keys.append(idx)
            elif name == "anumber":
                fk_src.append(idx)
    conn.close()
    hub_pk = primary_keys[0]
    return [
        {
            "db_id": DB_ID,
            "table_names_original": list(tables),
            "table_names": [t.replace("_", " ") for t in tables],
            "column_names_original": column_names,
            "column_names": [[t, c.replace("_", " ")] for t, c in column_names],
            "column_types": column_types,
            "primary_keys": primary_keys,
            "foreign_keys": [[src, hub_pk] for src in fk_src],
        }
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="decompressed wamex.sqlite from the wamex-db-v1 release")
    ap.add_argument("--qa", required=True, help="benchmarks/wamex/wamex/qa_pairs.json from the Acuity repo")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()

    db_path = os.path.join(args.out_dir, "database", DB_ID, f"{DB_ID}.sqlite")
    build_database(args.source, db_path)
    questions = select_questions(args.qa)
    verify_gold(db_path, questions)

    with open(os.path.join(args.out_dir, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(build_tables_json(db_path), f, indent=2)
    with open(os.path.join(args.out_dir, f"experiment_questions_{DB_ID}.json"), "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    counts = Counter(q["question_type"] for q in questions)
    print(f"{db_path}: {os.path.getsize(db_path) / 1e6:.1f} MB")
    print(f"{len(questions)} questions: {dict(sorted(counts.items()))}")
    print(f"single-table share: {counts['0'] / len(questions):.1%}; gold SQL verified against answer_row_ids")


if __name__ == "__main__":
    main()
