#!/usr/bin/env python3
"""Write docs/table_primary_keys_nine_db.md from SQLite PRAGMA table_info."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DATA = _ROOT / "dev_20240627" / "dev_databases"
OUT = _ROOT / "docs" / "table_primary_keys_nine_db.md"

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


def table_pks(path: Path) -> dict[str, list[str]]:
    conn = sqlite3.connect(path)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        if not r[0].startswith("_")
    ]
    out: dict[str, list[str]] = {}
    for t in tables:
        info = conn.execute(f"PRAGMA table_info({t!r})").fetchall()
        pk_cols = sorted(
            [(row[5], row[1]) for row in info if row[5]],
            key=lambda x: x[0],
        )
        out[t] = [c for _, c in pk_cols]
    conn.close()
    return out


def _fmt_pk(cols: list[str]) -> str:
    if not cols:
        return "(none declared in SQLite)"
    if len(cols) == 1:
        return f"`{cols[0]}`"
    return ", ".join(f"`{c}`" for c in cols)


def main() -> None:
    lines = [
        "# Primary keys by table (nine databases, 3NF SQLite)\n\n",
        "Source: `dev_20240627/dev_databases/{db_id}/{db_id}.sqlite`, "
        "via `PRAGMA table_info` (`pk` column > 0). "
        "Composite keys are listed in SQLite declaration order.\n\n",
    ]

    for db in DBS:
        pks = table_pks(DATA / db / f"{db}.sqlite")
        lines.append(f"## `{db}`\n\n")
        lines.append("| Table | Primary key(s) |\n")
        lines.append("|-------|----------------|\n")
        for table, cols in sorted(pks.items()):
            lines.append(f"| `{table}` | {_fmt_pk(cols)} |\n")
        lines.append("\n")

    lines.append("---\n\nRegenerate: `python3 analysis/list_table_primary_keys.py`\n")
    OUT.write_text("".join(lines), encoding="utf-8")
    n_tables = sum(len(table_pks(DATA / db / f"{db}.sqlite")) for db in DBS)
    print(f"Wrote {OUT} ({n_tables} tables)")


if __name__ == "__main__":
    main()
