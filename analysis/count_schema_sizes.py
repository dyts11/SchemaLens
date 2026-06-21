#!/usr/bin/env python3
"""Write docs/schema_size_1nf_2nf_3nf.md from materialised SQLite files."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DATA = _ROOT / "dev_20240627" / "dev_databases"
OUT = _ROOT / "docs" / "schema_size_1nf_2nf_3nf.md"

DBS = [
    "california_schools",
    "debit_card_specializing",
    "european_football_2",
    "financial",
    "formula_1",
    "student_club",
    "superhero",
    "thrombosis_prediction",
    "toxicology",
]


def count_schema(path: Path) -> tuple[int, int]:
    conn = sqlite3.connect(path)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        if not r[0].startswith("_")
    ]
    cols = sum(
        len(conn.execute(f"PRAGMA table_info({t!r})").fetchall()) for t in tables
    )
    conn.close()
    return len(tables), cols


def _section(title: str, key: str, rows: dict) -> list[str]:
    lines = [f"### {title}\n\n", "| Database | Tables | Total cols |\n", "|----------|-------:|-----------:|\n"]
    for db in DBS:
        t, c = rows[db][key]
        lines.append(f"| `{db}` | {t} | {c} |\n")
    return lines


def main() -> None:
    rows = {
        db: {
            "3NF": count_schema(DATA / db / f"{db}.sqlite"),
            "1NF": count_schema(DATA / db / f"{db}__1nf.sqlite"),
            "2NF": count_schema(DATA / db / f"{db}__2nf.sqlite"),
        }
        for db in DBS
    }

    lines = [
        "# Schema size: 1NF, 2NF, and 3NF (nine materialised databases)\n\n",
        "Physical SQLite under `dev_20240627/dev_databases/{db_id}/`:\n\n",
        "| Normal form | File |\n",
        "|-------------|------|\n",
        "| **3NF** | `{db_id}.sqlite` |\n",
        "| **1NF** | `{db_id}__1nf.sqlite` (`one_nf_0`) |\n",
        "| **2NF** | `{db_id}__2nf.sqlite` (`two_nf_*`) |\n\n",
        "Build metadata tables (`_one_nf_build_meta`, `_two_nf_build_meta`) are excluded. "
        "**Total cols** = sum of columns over counted tables.\n\n",
        "---\n\n",
        "## Combined\n\n",
        "| Database | 3NF tables | 3NF cols | 1NF tables | 1NF cols | "
        "2NF tables | 2NF cols |\n",
        "|----------|----------:|---------:|----------:|---------:|"
        "----------:|---------:|\n",
    ]
    sums = {k: [0, 0] for k in ("3NF", "1NF", "2NF")}
    for db in DBS:
        r = rows[db]
        for k in sums:
            sums[k][0] += r[k][0]
            sums[k][1] += r[k][1]
        lines.append(
            f"| `{db}` | {r['3NF'][0]} | {r['3NF'][1]} | {r['1NF'][0]} | {r['1NF'][1]} | "
            f"{r['2NF'][0]} | {r['2NF'][1]} |\n"
        )
    lines.append(
        f"| **Total** | **{sums['3NF'][0]}** | **{sums['3NF'][1]}** | "
        f"**{sums['1NF'][0]}** | **{sums['1NF'][1]}** | "
        f"**{sums['2NF'][0]}** | **{sums['2NF'][1]}** |\n"
    )
    lines.append("\n---\n\n## By normal form\n\n")
    lines += _section("3NF", "3NF", rows)
    lines.append("\n")
    lines += _section("1NF", "1NF", rows)
    lines.append("\n")
    lines += _section("2NF", "2NF", rows)
    lines.append(
        "\n---\n\nRegenerate: `python3 analysis/count_schema_sizes.py`\n"
    )
    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
