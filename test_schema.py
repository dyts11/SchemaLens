"""
test_schema.py

Print the schema string produced by SchemaBuilder for any combination of
database, structural level, and semantic level.

Usage (from the schema_effect/ directory):

    # Single condition
    python3 test_schema.py --db california_schools --sl 4 --sem 3

    # All structural levels for one database / semantic level
    python3 test_schema.py --db california_schools --sem 3 --all-sl

    # Compare two specific conditions side-by-side (diff mode)
    python3 test_schema.py --db california_schools --sem 3 --diff 3 4

Available databases:
    california_schools, card_games, codebase_community,
    debit_card_specializing, european_football_2, financial,
    formula_1, student_club, superhero, thrombosis_prediction, toxicology
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.schema_builder import SchemaBuilder

DATA_DIR = "dev_20240627"

LEVEL_LABELS = {
    1: "L1 · 1NF wide table (fact-anchored join; see to_1nf/specs.py)",
    2: "L2 · 2NF (partial deps removed)",
    3: "L3 · 3NF baseline (names only)",
    4: "L4 · 3NF + types / PK / NOT NULL",
    5: "L5 · 3NF + FK + cardinality",
    6: "L6 · 3NF + explicit JOIN paths",
}

SEM_LABELS = {
    1: "S1 · anonymous (col_a, col_b…)",
    2: "S2 · abbreviated",
    3: "S3 · descriptive (original names)",
    4: "S4 · descriptive + descriptions",
}

DIVIDER = "=" * 70


def print_schema(db: str, sl: int, sem: int) -> str:
    builder = SchemaBuilder(db, DATA_DIR)
    schema = builder.build(structural_level=sl, semantic_level=sem)
    header = (
        f"\n{DIVIDER}\n"
        f"  DB : {db}\n"
        f"  SL : {LEVEL_LABELS.get(sl, f'L{sl}')}\n"
        f"  SEM: {SEM_LABELS.get(sem, f'S{sem}')}\n"
        f"{DIVIDER}\n"
    )
    print(header + schema + f"\n{DIVIDER}")
    return schema


def diff_schemas(db: str, sem: int, sl_a: int, sl_b: int):
    """Print both schemas then highlight lines that differ."""
    import difflib

    builder = SchemaBuilder(db, DATA_DIR)
    a = builder.build(sl_a, sem).splitlines()
    b = builder.build(sl_b, sem).splitlines()

    label_a = f"L{sl_a}·S{sem}"
    label_b = f"L{sl_b}·S{sem}"

    print(f"\n{DIVIDER}")
    print(f"  DIFF  {label_a}  →  {label_b}   (db={db})")
    print(f"{DIVIDER}")

    diff = list(difflib.unified_diff(a, b, fromfile=label_a, tofile=label_b, lineterm=""))
    if diff:
        for line in diff:
            if line.startswith("+"):
                print(f"\033[32m{line}\033[0m")   # green
            elif line.startswith("-"):
                print(f"\033[31m{line}\033[0m")   # red
            else:
                print(line)
    else:
        print("  (schemas are identical)")
    print(DIVIDER)


def main():
    parser = argparse.ArgumentParser(
        description="Print the schema string for a given DB / structural / semantic level."
    )
    parser.add_argument("--db", default="california_schools",
                        help="Database name (default: california_schools)")
    parser.add_argument("--sl", type=int, default=3,
                        help="Structural level 1 or 3-6 (default: 3)")
    parser.add_argument("--sem", type=int, default=3,
                        help="Semantic level 1-4 (default: 3)")
    parser.add_argument("--all-sl", action="store_true",
                        help="Print all structural levels (L3–L6) for the given db/sem")
    parser.add_argument("--diff", nargs=2, type=int, metavar=("SL_A", "SL_B"),
                        help="Show unified diff between two structural levels, e.g. --diff 3 4")

    args = parser.parse_args()

    if args.diff:
        diff_schemas(args.db, args.sem, args.diff[0], args.diff[1])
    elif args.all_sl:
        for sl in (3, 4, 5, 6):
            try:
                print_schema(args.db, sl, args.sem)
            except NotImplementedError as e:
                print(f"\n[L{sl}·S{args.sem}] Not yet implemented: {e}")
    else:
        try:
            print_schema(args.db, args.sl, args.sem)
        except NotImplementedError as e:
            print(f"\n[L{args.sl}·S{args.sem}] Not yet implemented: {e}")


if __name__ == "__main__":
    main()
