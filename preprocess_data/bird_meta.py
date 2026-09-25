"""Shared helpers for reading BIRD ``dev_tables.json`` metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List


def load_dev_entry(
    db_id: str,
    data_dir: Path,
    *,
    tables_path: Path | None = None,
) -> dict:
    path = tables_path if tables_path is not None else data_dir / "dev_tables.json"
    with open(path, encoding="utf-8") as f:
        all_entries = json.load(f)
    try:
        return next(t for t in all_entries if t["db_id"] == db_id)
    except StopIteration as exc:
        raise KeyError(f"db_id={db_id!r} not found in {path}") from exc


def tables_cols(entry: dict) -> dict[str, List[dict]]:
    out: dict[str, List[dict]] = {t: [] for t in entry["table_names_original"]}
    for table_idx, col_name in entry["column_names_original"]:
        if table_idx == -1:
            continue
        out[entry["table_names_original"][table_idx]].append({"name": col_name})
    return out


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'
