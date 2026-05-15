"""
schema_builder.py

Generates a schema representation string for a given (db_id, structural_level, semantic_level).
The string is injected into the LLM prompt; the underlying SQLite database is never modified.

Structural levels implemented:
  L1 - 1NF wide table: one flat TEMP-view table per database (fact-anchored join
       plan from to_1nf; intentional redundancy).  Evaluation installs the same
       CREATE TEMP VIEW DDL.
  L3 - 3NF baseline    : table name + column names only
  L4 - 3NF + metadata  : adds SQLite types, PRIMARY KEY, NOT NULL, plus a short
                         preamble explaining how to read the notation
  L5 - 3NF + relations : L4 + inline FK comments on columns + a dedicated
                         FOREIGN KEY RELATIONSHIPS section after all tables
  L6 - 3NF + join paths: L5 + a JOIN PATHS section with example INNER JOIN lines

Semantic levels implemented:
  S1 - Anonymous    : col_a, col_b, col_c … (position-based, per table)
  S2 - Abbreviated  : short developer abbreviations (cust_id, dept_nm …)
  S3 - Descriptive  : full English column names (curated for all 11 databases)
  S4 - Descriptive+ : S3 names + inline description comments from BIRD CSV files

Usage:
    from src.schema_builder import SchemaBuilder
    builder = SchemaBuilder("student_club", "dev_20240627")
    print(builder.build(structural_level=5, semantic_level=3))
"""

import csv
import json
import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

from src.column_aliases import get_name as _get_alias


class SchemaBuilder:
    """
    Builds schema representation strings for a single database.

    Args:
        db_id   : Database identifier matching the folder name (e.g. 'student_club').
        data_dir: Path to the BIRD dev root directory that contains
                  dev_tables.json and the dev_databases/ subfolder.
    """

    def __init__(self, db_id: str, data_dir: Union[str, Path]):
        self.db_id = db_id
        self.data_dir = Path(data_dir)
        self._meta = self._load_metadata()
        self._pragma = self._load_pragma_info()
        self._descriptions = self._load_descriptions()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def build(self, structural_level: int, semantic_level: int) -> str:
        """
        Generate a schema representation string for the given condition.

        Args:
            structural_level: Integer 1 or 3-6 (L1 wide clusters, or L3-L6).
            semantic_level  : Integer 1-4 (S1 anonymous → S4 descriptive+).

        Returns:
            A multi-line string describing the schema, ready to be inserted
            into an LLM prompt.
        """
        if semantic_level not in (1, 2, 3, 4):
            raise ValueError(
                f"semantic_level must be 1, 2, 3, or 4 — got {semantic_level}"
            )
        if structural_level == 1:
            from to_1nf.convert import format_schema_prompt

            return format_schema_prompt(self.get_one_nf_plan(semantic_level))
        if structural_level not in (3, 4, 5, 6):
            raise ValueError(
                f"structural_level must be 1, 3, 4, 5, or 6 — got {structural_level}"
            )
        return self._format_schema(structural_level, semantic_level)

    def get_one_nf_plan(self, semantic_level: int):
        """
        Return (and cache) the OneNfPlan for this database at the given semantic level.
        Used by run_experiment to install TEMP VIEW DDL for predicted SQL.
        """
        from to_1nf.convert import OneNfPlan, build_plan

        if not hasattr(self, "_one_nf_plan_cache") or self._one_nf_plan_sem != semantic_level:
            self._one_nf_plan_cache: OneNfPlan = build_plan(
                self.db_id, self.data_dir, semantic_level
            )
            self._one_nf_plan_sem = semantic_level
        return self._one_nf_plan_cache

    def get_l1_plan(self, semantic_level: int):
        """Alias for :meth:`get_one_nf_plan` (legacy name)."""
        return self.get_one_nf_plan(semantic_level)

    # ------------------------------------------------------------------ #
    #  Data loading                                                        #
    # ------------------------------------------------------------------ #

    def _load_metadata(self) -> dict:
        """
        Parse dev_tables.json for this database and build convenient lookups:
          - tables_cols   : {table_name: [col_dict, ...]}
          - pk_cols       : set of column indices that are (part of) a PK
          - fk_map        : {from_col_idx: (to_table, to_col_name)}
          - composite_pks : {table_name: [col_name, ...]}  (only for composite PKs)
          - foreign_keys_raw: raw list of [from_idx, to_idx] pairs (used by L6)
          - col_lookup    : {col_idx: {table, name, type}}
        """
        tables_path = self.data_dir / "dev_tables.json"
        with open(tables_path, encoding="utf-8") as f:
            all_entries = json.load(f)
        entry = next(t for t in all_entries if t["db_id"] == self.db_id)

        # col_idx → {table, name, type}  (skip the special [-1, '*'] at index 0)
        col_lookup: dict = {}
        for idx, (table_idx, col_name) in enumerate(entry["column_names_original"]):
            if table_idx == -1:
                continue
            col_lookup[idx] = {
                "table": entry["table_names_original"][table_idx],
                "table_idx": table_idx,
                "name": col_name,
                "type": entry["column_types"][idx].upper(),
            }

        # Which column indices are primary keys?
        pk_cols: set = set()
        for pk in entry["primary_keys"]:
            if isinstance(pk, list):
                pk_cols.update(pk)
            else:
                pk_cols.add(pk)

        # FK map: from_col_idx → (to_table_name, to_col_name)
        fk_map: dict = {}
        for from_idx, to_idx in entry["foreign_keys"]:
            if to_idx in col_lookup:
                fk_map[from_idx] = (
                    col_lookup[to_idx]["table"],
                    col_lookup[to_idx]["name"],
                )

        # Composite PKs: table_name → [col_name, ...]
        composite_pks: dict = {}
        for pk in entry["primary_keys"]:
            if isinstance(pk, list):
                table = col_lookup[pk[0]]["table"]
                composite_pks[table] = [col_lookup[i]["name"] for i in pk]

        # Group columns by table, preserving original order
        tables_cols: dict = {t: [] for t in entry["table_names_original"]}
        for idx, info in col_lookup.items():
            tables_cols[info["table"]].append(
                {
                    "idx": idx,
                    "name": info["name"],
                    "type": info["type"],
                    "is_pk": idx in pk_cols,
                    "fk_to": fk_map.get(idx),  # (to_table, to_col) or None
                }
            )

        return {
            "table_names": entry["table_names_original"],
            "tables_cols": tables_cols,
            "pk_cols": pk_cols,
            "fk_map": fk_map,
            "composite_pks": composite_pks,
            "foreign_keys_raw": entry["foreign_keys"],
            "col_lookup": col_lookup,
        }

    def _load_pragma_info(self) -> dict[str, dict[str, dict]]:
        """
        Query SQLite PRAGMA table_info() to get NOT NULL flags that are not
        captured in dev_tables.json.

        Returns:
            {table_name: {col_name: {"notnull": bool}}}
        """
        db_path = (
            self.data_dir / "dev_databases" / self.db_id / f"{self.db_id}.sqlite"
        )
        pragma_data: dict = {}
        conn = sqlite3.connect(str(db_path))
        try:
            for table_name in self._meta["table_names"]:
                rows = conn.execute(
                    f"PRAGMA table_info('{table_name}')"
                ).fetchall()
                # PRAGMA columns: cid, name, type, notnull, dflt_value, pk
                pragma_data[table_name] = {
                    row[1]: {"notnull": bool(row[3])} for row in rows
                }
        finally:
            conn.close()
        return pragma_data

    def _load_descriptions(self) -> dict[str, dict[str, str]]:
        """
        Load column descriptions from the database_description/ CSV files.
        Used by semantic level S4 (descriptions injected as inline comments).

        Returns:
            {table_name: {original_column_name: full_description_string}}
        """
        desc_dir = (
            self.data_dir / "dev_databases" / self.db_id / "database_description"
        )
        descriptions: dict = {}

        for table_name in self._meta["table_names"]:
            # CSV filenames may differ in capitalisation from table names
            csv_path: Optional[Path] = None
            for fname in os.listdir(desc_dir):
                if fname.lower() == f"{table_name.lower()}.csv":
                    csv_path = desc_dir / fname
                    break

            if csv_path is None:
                descriptions[table_name] = {}
                continue

            col_descs: dict = {}
            with open(csv_path, encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    orig_col = row.get("original_column_name", "").strip()
                    col_desc = row.get("column_description", "").strip()
                    val_desc = row.get("value_description", "").strip()
                    # Merge column_description and value_description into one string
                    if col_desc and val_desc:
                        full_desc = f"{col_desc}. {val_desc}"
                    else:
                        full_desc = col_desc or val_desc
                    if orig_col:
                        col_descs[orig_col] = full_desc
            descriptions[table_name] = col_descs

        return descriptions

    # ------------------------------------------------------------------ #
    #  Schema formatting                                                   #
    # ------------------------------------------------------------------ #

    def _format_schema(self, structural_level: int, semantic_level: int) -> str:
        """Build the complete schema string for the given condition."""
        table_blocks = []

        for table_name in self._meta["table_names"]:
            cols = self._meta["tables_cols"][table_name]
            composite_pk = self._meta["composite_pks"].get(table_name)

            col_lines = []
            for col_idx_in_table, col in enumerate(cols):
                line = self._format_column(
                    col, table_name, structural_level, semantic_level,
                    composite_pk, col_idx_in_table,
                )
                col_lines.append(f"    {line}")

            # Table-level composite PK constraint (L4 and above only).
            # Use the mapped names so they match what the LLM sees in the columns.
            if structural_level >= 4 and composite_pk:
                mapped_pk = [
                    _get_alias(self.db_id, c, semantic_level)
                    for c in composite_pk
                ]
                pk_str = ", ".join(_quote_if_needed(c) for c in mapped_pk)
                col_lines.append(f"    PRIMARY KEY ({pk_str})")

            block = (
                f"TABLE {table_name} (\n"
                + ",\n".join(col_lines)
                + "\n)"
            )
            table_blocks.append(block)

        schema_str = "\n\n".join(table_blocks)

        # L4+ : short guide so the added metadata is self-explanatory in the prompt
        if structural_level >= 4:
            schema_str = self._structure_level_intro(structural_level) + "\n\n" + schema_str

        # L5+ : recap all FK edges in one place (in addition to inline column comments)
        if structural_level >= 5:
            fk_block = self._format_foreign_key_relationships(semantic_level)
            if fk_block:
                schema_str += "\n\n" + fk_block

        # L6 : executable join hints after the relationship recap
        if structural_level == 6:
            schema_str += "\n\n" + self._format_join_paths(semantic_level)

        return schema_str

    def _format_column(
        self,
        col: dict,
        table_name: str,
        structural_level: int,
        semantic_level: int,
        composite_pk: Optional[list],
        col_idx_in_table: int = 0,
    ) -> str:
        """
        Format one column into a single schema line.

        L3 example:  event_id
        L4 example:  event_id TEXT PRIMARY KEY
        L5 example:  link_to_event TEXT  -- FK → event.event_id (many-to-one)
        L6 example:  (same as L5; the JOIN section is added at the table level)
        S4 example:  event_id TEXT PRIMARY KEY  -- The unique identifier of the event
        """
        name = self._get_column_name(col, semantic_level, col_idx_in_table)
        parts = [name]

        if structural_level >= 4:
            parts.append(col["type"])

            # Single-column PK annotation (composite PKs get a table-level line)
            if col["is_pk"] and not composite_pk:
                parts.append("PRIMARY KEY")

            # NOT NULL for non-PK columns that are declared NOT NULL in SQLite
            pragma_col = self._pragma.get(table_name, {}).get(col["name"], {})
            if pragma_col.get("notnull") and not col["is_pk"]:
                parts.append("NOT NULL")

        line = " ".join(parts)

        # FK inline comment for L5 and L6
        if structural_level >= 5 and col["fk_to"]:
            to_table, to_col = col["fk_to"]
            mapped_to_col = _get_alias(self.db_id, to_col, semantic_level)
            is_sole_pk = col["is_pk"] and not composite_pk
            cardinality = "one-to-one" if is_sole_pk else "many-to-one"
            line += f"  -- FK → {to_table}.{_quote_if_needed(mapped_to_col)} ({cardinality})"

        # S4: append column description as an inline comment (only when no FK comment)
        if semantic_level == 4:
            desc = self._descriptions.get(table_name, {}).get(col["name"], "")
            # Truncate long descriptions so the prompt doesn't balloon
            if desc:
                short_desc = desc.split(".")[0].strip()[:120]
                if structural_level >= 5 and col["fk_to"]:
                    # Already has FK comment; append description after it
                    line += f" | {short_desc}"
                else:
                    line += f"  -- {short_desc}"

        return line

    def _get_column_name(
        self,
        col: dict,
        semantic_level: int,
        col_idx_in_table: int = 0,
    ) -> str:
        """
        Return the (possibly quoted) column name for the given semantic level.

        S1 - Anonymous  : col_a, col_b … (position within the table, 0-based → a, b …)
        S2 - Abbreviated: curated short name from column_aliases.py, else original
        S3 - Descriptive: curated full name from column_aliases.py, else original
        S4 - Descriptive: same as S3 (description suffix handled in _format_column)

        All names are backtick-quoted when they contain spaces or special characters.
        """
        if semantic_level == 1:
            # Generate col_a … col_z, col_aa, col_ab …
            label = _idx_to_label(col_idx_in_table)
            return f"col_{label}"

        mapped = _get_alias(self.db_id, col["name"], semantic_level)
        return _quote_if_needed(mapped)

    def _structure_level_intro(self, structural_level: int) -> str:
        """
        Human-readable preamble for L4+ so types / PK / NOT NULL are obvious in the prompt.
        """
        lines = [
            "-- SCHEMA NOTATION (this structural level):",
            "--   • Each column lists its SQLite storage class / affinity (TEXT, INTEGER, REAL, …).",
            "--   • PRIMARY KEY marks the column (or column set) that uniquely identifies a row.",
            "--     For composite keys, a single PRIMARY KEY (col1, col2, …) line appears at the bottom of the table.",
            "--   • NOT NULL means the database does not allow NULL in that column for stored rows.",
        ]
        if structural_level >= 5:
            lines.extend(
                [
                    "--   • Columns that are foreign keys carry an inline note: FK → parent_table.parent_column",
                    "--     with a cardinality hint (many-to-one vs one-to-one) from the child table's perspective.",
                ]
            )
        if structural_level >= 6:
            lines.append(
                "--   • After all tables: FOREIGN KEY RELATIONSHIPS recap every link, then JOIN PATHS shows"
            )
            lines.append(
                "--     example INNER JOIN … ON … lines you can adapt when writing queries."
            )
        elif structural_level >= 5:
            lines.append(
                "--   • After all tables, FOREIGN KEY RELATIONSHIPS lists every parent/child link in one place."
            )
        return "\n".join(lines)

    def _fk_cardinality(self, from_col_idx: int) -> str:
        """Cardinality from the child (FK) row toward the parent: one-to-one vs many-to-one."""
        col_lookup = self._meta["col_lookup"]
        if from_col_idx not in col_lookup:
            return "many-to-one"
        info = col_lookup[from_col_idx]
        table = info["table"]
        is_pk = from_col_idx in self._meta["pk_cols"]
        composite = self._meta["composite_pks"].get(table)
        if is_pk and not composite:
            return "one-to-one"
        return "many-to-one"

    def _format_foreign_key_relationships(self, semantic_level: int) -> str:
        """
        L5/L6: dedicated block that highlights every FK edge between tables, using the same
        mapped column names as in the TABLE definitions.
        """
        col_lookup = self._meta["col_lookup"]
        raw = self._meta["foreign_keys_raw"]
        if not raw:
            return ""

        lines = [
            "-- FOREIGN KEY RELATIONSHIPS:",
            "--   Each line: <child_table>.<child_column> → <parent_table>.<parent_column>  (cardinality from child side)",
        ]
        for from_idx, to_idx in raw:
            if from_idx not in col_lookup or to_idx not in col_lookup:
                continue
            from_info = col_lookup[from_idx]
            to_info = col_lookup[to_idx]
            from_name = _quote_if_needed(
                _get_alias(self.db_id, from_info["name"], semantic_level)
            )
            to_name = _quote_if_needed(
                _get_alias(self.db_id, to_info["name"], semantic_level)
            )
            card = self._fk_cardinality(from_idx)
            lines.append(
                f"--   {from_info['table']}.{from_name} → {to_info['table']}.{to_name}  ({card})"
            )
        return "\n".join(lines)

    def _format_join_paths(self, semantic_level: int = 3) -> str:
        """
        Generate the '-- JOIN PATHS:' block appended at L6.
        Lists one JOIN expression per FK relationship, using the mapped column names
        for the given semantic level.
        """
        col_lookup = self._meta["col_lookup"]
        lines = ["-- JOIN PATHS:"]

        for from_idx, to_idx in self._meta["foreign_keys_raw"]:
            if from_idx not in col_lookup or to_idx not in col_lookup:
                continue
            from_info = col_lookup[from_idx]
            to_info = col_lookup[to_idx]
            from_name = _quote_if_needed(_get_alias(self.db_id, from_info["name"], semantic_level))
            to_name   = _quote_if_needed(_get_alias(self.db_id, to_info["name"],   semantic_level))
            lines.append(
                f"--   {from_info['table']} JOIN {to_info['table']}"
                f" ON {from_info['table']}.{from_name}"
                f" = {to_info['table']}.{to_name}"
            )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

import re as _re

_SAFE_IDENTIFIER = _re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _idx_to_label(n: int) -> str:
    """
    Convert a 0-based column index to a spreadsheet-style letter label.
    0 → 'a', 25 → 'z', 26 → 'aa', 27 → 'ab', …
    """
    label = ""
    n += 1  # 1-based
    while n:
        n, r = divmod(n - 1, 26)
        label = chr(ord("a") + r) + label
    return label


def _quote_if_needed(name: str) -> str:
    """
    Wrap a column name in backticks if it contains spaces, special characters,
    or starts with a digit — making it an unambiguous SQLite quoted identifier.

    Examples:
        'customer_id'                      → 'customer_id'   (no change)
        'District Code'                    → '`District Code`'
        'Percent (%) Eligible Free (K-12)' → '`Percent (%) Eligible Free (K-12)`'
        '2013-14 CALPADS Status'           → '`2013-14 CALPADS Status`'
    """
    if _SAFE_IDENTIFIER.match(name):
        return name
    return f"`{name}`"
