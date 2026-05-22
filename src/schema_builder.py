"""
schema_builder.py

Generates a schema representation string for a given (db_id, structural_level, semantic_level).
The string is injected into the LLM prompt; the underlying SQLite database is never modified.

Structural levels implemented:
  L1 - 1NF wide table: one denormalised table per database, read from the
       materialised ``{db_id}__1nf.sqlite`` file under dev_databases/ (see
       preprocess_data/to_1nf/build_sqlite.py).  Nine databases (see MATERIALISED_DB_IDS).
  L2 - 2NF synthetic clusters: multiple denormalised wide tables per database from
       ``{db_id}__2nf.sqlite`` (see preprocess_data/to_2nf/build_sqlite.py).  Same nine databases as L1.  S1–S4 use rename maps at eval time (physical S3 columns in file).
  L3 - 3NF baseline    : table name + column names only
  L4 - 3NF + metadata  : adds SQLite types, PRIMARY KEY, NOT NULL, plus a short
                         preamble explaining how to read the notation
  L5 - 3NF + relations : L4 + inline FK comments on columns + a dedicated
                         FOREIGN KEY RELATIONSHIPS section after all tables
  L6 - 3NF + join paths: L5 + a JOIN PATHS section with example INNER JOIN lines

Semantic levels implemented:
  S1 - Anonymous    : col_a, col_b, col_c … (position-based, per table)
  S2 - Abbreviated  : short developer abbreviations (cust_id, dept_nm …)
  S3 - Descriptive  : full English column names (curated per database)
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
from src.fk_cardinality import fk_cardinality_label

# Databases with materialised L1 / L2 SQLite files under dev_databases/.
MATERIALISED_DB_IDS = frozenset(
    {
        "california_schools",
        "debit_card_specializing",
        "european_football_2",
        "financial",
        "formula_1",
        "student_club",
        "superhero",
        "thrombosis_prediction",
        "toxicology",
    }
)
L1_DB_IDS = MATERIALISED_DB_IDS  # alias
L2_DB_IDS = MATERIALISED_DB_IDS
L1_TABLE_NAME = "one_nf_0"


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
            structural_level: Integer 1, 2, or 3-6 (L1/L2 materialised, or L3-L6).
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
            return self._format_one_nf_schema(semantic_level)
        if structural_level == 2:
            return self._format_two_nf_schema(semantic_level)
        if structural_level not in (3, 4, 5, 6):
            raise ValueError(
                f"structural_level must be 1, 2, 3, 4, 5, or 6 — got {structural_level}"
            )
        return self._format_schema(structural_level, semantic_level)

    @staticmethod
    def one_nf_sqlite_path(data_dir: Union[str, Path], db_id: str) -> Path:
        """Path to the materialised 1NF SQLite file (physical S3 column names)."""
        return Path(data_dir) / "dev_databases" / db_id / f"{db_id}__1nf.sqlite"

    @classmethod
    def has_one_nf_database(cls, data_dir: Union[str, Path], db_id: str) -> bool:
        return db_id in L1_DB_IDS and cls.one_nf_sqlite_path(data_dir, db_id).is_file()

    @staticmethod
    def two_nf_sqlite_path(data_dir: Union[str, Path], db_id: str) -> Path:
        """Path to the materialised 2NF SQLite file (physical S3 column names)."""
        return Path(data_dir) / "dev_databases" / db_id / f"{db_id}__2nf.sqlite"

    @classmethod
    def has_two_nf_database(cls, data_dir: Union[str, Path], db_id: str) -> bool:
        return db_id in L2_DB_IDS and cls.two_nf_sqlite_path(data_dir, db_id).is_file()

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

    def _format_one_nf_schema(self, semantic_level: int) -> str:
        """
        Build the L1 prompt schema for the requested semantic level.

        The materialised ``{db_id}__1nf.sqlite`` always stores physical S3-style
        column names; S1/S2/S4 display names are derived from the join plan (same
        logic as L3–L6).  Evaluation maps display names back via ``build_l1_col_rename_map``.
        """
        if self.db_id not in L1_DB_IDS:
            supported = ", ".join(sorted(L1_DB_IDS))
            raise ValueError(
                f"No 1NF database for db_id={self.db_id!r}. Supported: {supported}"
            )
        path = self.one_nf_sqlite_path(self.data_dir, self.db_id)
        if not path.is_file():
            raise FileNotFoundError(
                f"1NF database not found: {path}\n"
                f"Build it with: python3 -m preprocess_data.to_1nf.build_sqlite "
                f"--db {self.db_id}"
            )

        from preprocess_data.to_1nf.convert import build_plan

        display_columns = build_plan(
            self.db_id, self.data_dir, semantic_level=semantic_level
        ).display_columns

        lines = [
            "-- L1 · 1NF wide table (denormalised; intentional redundancy).",
            "-- All attributes appear in a single table — no joins required.",
            f"-- Query table: {L1_TABLE_NAME}",
            "",
            f"TABLE {L1_TABLE_NAME} (",
            "    " + ",\n    ".join(_quote_if_needed(c) for c in display_columns),
            ")",
        ]
        return "\n".join(lines)

    def _format_two_nf_schema(self, semantic_level: int) -> str:
        """
        Build the L2 prompt schema: one TABLE block per materialised cluster.

        ``{db_id}__2nf.sqlite`` stores physical S3-style names; display names for
        S1/S2/S4 come from ``build_plan`` (same approach as L1).  Evaluation uses
        ``build_l2_col_rename_map``.
        """
        if self.db_id not in L2_DB_IDS:
            supported = ", ".join(sorted(L2_DB_IDS))
            raise ValueError(
                f"No 2NF database for db_id={self.db_id!r}. Supported: {supported}"
            )
        path = self.two_nf_sqlite_path(self.data_dir, self.db_id)
        if not path.is_file():
            raise FileNotFoundError(
                f"2NF database not found: {path}\n"
                f"Build it with: python3 -m preprocess_data.to_2nf.build_sqlite "
                f"--db {self.db_id}"
            )

        from preprocess_data.to_2nf.convert import build_plan, _anchor_pk_labels
        from preprocess_data.to_2nf.specs import SPECS

        plan = build_plan(self.db_id, self.data_dir, semantic_level=semantic_level)
        spec = SPECS[self.db_id]
        anchor_pks = _anchor_pk_labels(self.db_id, self.data_dir)

        lines = [
            "-- L2 · 2NF synthetic clusters (denormalised hubs; not 3NF).",
            "-- Query the appropriate cluster table; JOIN across clusters when needed.",
            f"-- Database file: {self.db_id}__2nf.sqlite",
            "",
        ]
        for cluster, cl in zip(plan.clusters, spec.clusters):
            pk = anchor_pks.get(cl.anchor_table, "?")
            from preprocess_data.to_2nf.specs import join_step_table

            joined = [join_step_table(s) for s in cl.join_steps]
            lines.append(
                f"-- Cluster anchor: {cl.anchor_table} (row key: {pk})"
            )
            if joined:
                lines.append(f"--   joined entities: {', '.join(joined)}")
            lines.append(f"TABLE {cluster.output_table} (")
            lines.append(
                "    "
                + ",\n    ".join(_quote_if_needed(c) for c in cluster.display_columns)
            )
            lines.append(")")
            lines.append("")

        return "\n".join(lines).rstrip()

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
            cardinality = fk_cardinality_label(
                self.db_id, table_name, col["name"], to_table, to_col
            )
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
        body = [
            "SCHEMA NOTATION (this structural level)",
            "",
            "Each column lists its SQLite storage class / affinity (TEXT, INTEGER, REAL, …).",
            "PRIMARY KEY marks the column (or column set) that uniquely identifies a row.",
            "For composite keys, a single PRIMARY KEY (col1, col2, …) line appears at the bottom of the table.",
            "NOT NULL means the database does not allow NULL in that column for stored rows.",
        ]
        if structural_level >= 5:
            body.extend(
                [
                    "",
                    "Columns that are foreign keys carry an inline note: FK → parent_table.parent_column",
                    "with a cardinality hint (many-to-one vs one-to-one) from the child table's perspective.",
                    "FK columns that are also part of the primary key are still labelled many-to-one unless",
                    "the relationship is listed as a verified one-to-one extension (e.g. school detail tables).",
                ]
            )
        if structural_level >= 6:
            body.extend(
                [
                    "",
                    "After all tables: FOREIGN KEY RELATIONSHIPS recaps every link in one block.",
                    "JOIN PATHS lists example INNER JOIN … ON … lines you can adapt when writing queries.",
                ]
            )
        elif structural_level >= 5:
            body.append(
                "After all tables, FOREIGN KEY RELATIONSHIPS lists every parent/child link in one block."
            )
        return _block_comment(body)

    def _fk_cardinality(self, from_col_idx: int, to_col_idx: int) -> str:
        """Cardinality from the child (FK) row toward the parent."""
        col_lookup = self._meta["col_lookup"]
        if from_col_idx not in col_lookup or to_col_idx not in col_lookup:
            return "many-to-one"
        from_info = col_lookup[from_col_idx]
        to_info = col_lookup[to_col_idx]
        return fk_cardinality_label(
            self.db_id,
            from_info["table"],
            from_info["name"],
            to_info["table"],
            to_info["name"],
        )

    def _format_foreign_key_relationships(self, semantic_level: int) -> str:
        """
        L5/L6: dedicated block that highlights every FK edge between tables, using the same
        mapped column names as in the TABLE definitions.
        """
        col_lookup = self._meta["col_lookup"]
        raw = self._meta["foreign_keys_raw"]
        if not raw:
            return ""

        body = [
            "FOREIGN KEY RELATIONSHIPS",
            "Each line: child_table.child_column → parent_table.parent_column (cardinality from child side)",
            "",
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
            card = self._fk_cardinality(from_idx, to_idx)
            body.append(
                f"{from_info['table']}.{from_name} → {to_info['table']}.{to_name} ({card})"
            )
        return _block_comment(body)

    def _format_join_paths(self, semantic_level: int = 3) -> str:
        """
        Passive JOIN PATHS block for L6 (block comment, not executable SQL).
        """
        col_lookup = self._meta["col_lookup"]
        body = [
            "JOIN PATHS",
            "Example INNER JOIN patterns — adapt table and column names to your query.",
            "",
        ]

        for from_idx, to_idx in self._meta["foreign_keys_raw"]:
            if from_idx not in col_lookup or to_idx not in col_lookup:
                continue
            from_info = col_lookup[from_idx]
            to_info = col_lookup[to_idx]
            from_name = _quote_if_needed(_get_alias(self.db_id, from_info["name"], semantic_level))
            to_name = _quote_if_needed(_get_alias(self.db_id, to_info["name"], semantic_level))
            body.append(
                f"{from_info['table']} JOIN {to_info['table']}"
                f" ON {from_info['table']}.{from_name} = {to_info['table']}.{to_name}"
            )

        return _block_comment(body)


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


def _block_comment(lines: list[str]) -> str:
    """Format lines as a single /* … */ block (passive documentation, not SQL)."""
    if not lines:
        return "/* */"
    inner = "\n".join(lines)
    return f"/*\n{inner}\n*/"


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
