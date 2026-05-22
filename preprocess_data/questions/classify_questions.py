#!/usr/bin/env python3
"""
Classify all BIRD dev questions as retrieval vs aggregate from gold SQL.

Usage (from schema_effect/):

    python3 preprocess_data/questions/classify_questions.py
    python3 preprocess_data/questions/classify_questions.py --data-dir dev_20240627

Writes:
    preprocess_data/questions/question_types.json
    preprocess_data/questions/question_types.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from preprocess_data.questions.question_classifier import (
    QUESTIONS_DIR,
    classify_dev_questions,
    save_question_types,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Classify dev.json questions by gold SQL.")
    p.add_argument(
        "--data-dir",
        default="dev_20240627",
        help="Directory containing dev.json (default: dev_20240627)",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Where to write question_types.* (default: preprocess_data/questions/)",
    )
    args = p.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = _ROOT / data_dir
    dev_path = data_dir / "dev.json"
    if not dev_path.is_file():
        raise SystemExit(f"Not found: {dev_path}")

    out_dir = Path(args.output_dir) if args.output_dir else QUESTIONS_DIR

    with open(dev_path, encoding="utf-8") as f:
        questions = json.load(f)

    records = classify_dev_questions(questions)
    json_path, csv_path = save_question_types(records, out_dir)

    n_agg = sum(1 for r in records if r["question_type"] == "aggregate")
    n_ret = len(records) - n_agg
    print(f"Classified {len(records)} questions from {dev_path}")
    print(f"  retrieval : {n_ret}")
    print(f"  aggregate : {n_agg}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
