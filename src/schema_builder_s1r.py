"""
Schema strings for the S1R (randomized table + column alias) experiment track.

Uses frozen mappings from column_aliases_s1r.py. Does not modify SchemaBuilder.
"""

from __future__ import annotations

from typing import Optional

from preprocess_data.to_2nf.convert import _anchor_pk_labels
from preprocess_data.to_2nf.specs import SPECS as TWO_NF_SPECS
from src.column_aliases_s1r import get_column_name_s1r, get_table_name_s1r
from src.fk_cardinality import fk_cardinality_label
from src.schema_builder import (
    L1_DB_IDS,
    L1_TABLE_NAME,
    L2_DB_IDS,
    SchemaBuilder,
    _block_comment,
    _quote_if_needed,
)
from src.s1r_plan import (
    build_l1_s1r_display_columns,
    build_l2_s1r_display_columns_by_cluster,
)


class SchemaBuilderS1R(SchemaBuilder):
    """Build prompt schemas using S1R randomized table/column aliases."""

    def build(self, structural_level: int) -> str:
        """Generate schema for structural level L1-L6 at S1R."""
        if structural_level == 1:
            return self._format_one_nf_schema_s1r()
        if structural_level == 2:
            return self._format_two_nf_schema_s1r()
        if structural_level not in (3, 4, 5, 6):
            raise ValueError(
                f"structural_level must be 1-6 for S1R - got {structural_level}"
            )
        return self._format_schema_s1r(structural_level)

    def _format_one_nf_schema_s1r(self) -> str:
        if self.db_id not in L1_DB_IDS:
            supported = ", ".join(sorted(L1_DB_IDS))
            raise ValueError(
                f"No 1NF database for db_id={self.db_id!r}. Supported: {supported}"
            )
        path = self.one_nf_sqlite_path(self.data_dir, self.db_id, self.layout)
        if not path.is_file():
            raise FileNotFoundError(
                f"1NF database not found: {path}\n"
                f"Build: python3 -m preprocess_data.to_1nf.build_sqlite --db {self.db_id}"
            )

        display_columns = build_l1_s1r_display_columns(
            self.db_id,
            self.data_dir,
            tables_path=self.layout.tables_json,
        )
        lines = [
            "-- L1 - 1NF wide table (denormalised; intentional redundancy).",
            "-- All attributes appear in a single table - no joins required.",
            f"-- Query table: {L1_TABLE_NAME}",
            "",
            f"TABLE {L1_TABLE_NAME} (",
            "    " + ",\n    ".join(_quote_if_needed(c) for c in display_columns),
            ")",
        ]
        return "\n".join(lines)

    def _format_two_nf_schema_s1r(self) -> str:
        if self.db_id not in L2_DB_IDS:
            supported = ", ".join(sorted(L2_DB_IDS))
            raise ValueError(
                f"No 2NF database for db_id={self.db_id!r}. Supported: {supported}"
            )
        path = self.two_nf_sqlite_path(self.data_dir, self.db_id, self.layout)
        if not path.is_file():
            raise FileNotFoundError(
                f"2NF database not found: {path}\n"
                f"Build: python3 -m preprocess_data.to_2nf.build_sqlite --db {self.db_id}"
            )

        from preprocess_data.to_2nf.convert import build_plan
        from preprocess_data.to_2nf.specs import join_step_table

        plan = build_plan(
            self.db_id,
            self.data_dir,
            semantic_level=3,
            tables_path=self.layout.tables_json,
        )
        s1r_cols_by_cluster = build_l2_s1r_display_columns_by_cluster(
            self.db_id,
            self.data_dir,
            tables_path=self.layout.tables_json,
        )
        spec = TWO_NF_SPECS[self.db_id]
        anchor_pks = _anchor_pk_labels(
            self.db_id, self.data_dir, tables_path=self.layout.tables_json
        )

        lines = [
            "-- L2 - 2NF synthetic clusters (denormalised hubs; not 3NF).",
            "-- Query the appropriate cluster table; JOIN across clusters when needed.",
            f"-- Database file: {self.db_id}__2nf.sqlite",
            "",
        ]
        for cluster, cl, s1r_cols in zip(plan.clusters, spec.clusters, s1r_cols_by_cluster):
            pk = anchor_pks.get(cl.anchor_table, "?")
            joined = [join_step_table(s) for s in cl.join_steps]
            lines.append(f"-- Cluster anchor: {cl.anchor_table} (row key: {pk})")
            if joined:
                lines.append(f"--   joined entities: {', '.join(joined)}")
            lines.append(f"TABLE {cluster.output_table} (")
            lines.append(
                "    " + ",\n    ".join(_quote_if_needed(c) for c in s1r_cols)
            )
            lines.append(")")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _format_schema_s1r(self, structural_level: int) -> str:
        table_blocks = []
        for table_name in self._meta["table_names"]:
            s1r_table = get_table_name_s1r(self.db_id, table_name)
            cols = self._meta["tables_cols"][table_name]
            composite_pk = self._meta["composite_pks"].get(table_name)

            col_lines = []
            for col in cols:
                line = self._format_column_s1r(
                    col, table_name, structural_level, composite_pk
                )
                col_lines.append(f"    {line}")

            if structural_level >= 4 and composite_pk:
                mapped_pk = [
                    _quote_if_needed(
                        get_column_name_s1r(self.db_id, table_name, c)
                    )
                    for c in composite_pk
                ]
                pk_str = ", ".join(mapped_pk)
                col_lines.append(f"    PRIMARY KEY ({pk_str})")

            block = f"TABLE {s1r_table} (\n" + ",\n".join(col_lines) + "\n)"
            table_blocks.append(block)

        schema_str = "\n\n".join(table_blocks)
        if structural_level >= 4:
            schema_str = self._structure_level_intro(structural_level) + "\n\n" + schema_str
        if structural_level >= 5:
            fk_block = self._format_foreign_key_relationships_s1r()
            if fk_block:
                schema_str += "\n\n" + fk_block
        if structural_level == 6:
            schema_str += "\n\n" + self._format_join_paths_s1r()
        return schema_str

    def _format_column_s1r(
        self,
        col: dict,
        table_name: str,
        structural_level: int,
        composite_pk: Optional[list],
    ) -> str:
        name = _quote_if_needed(
            get_column_name_s1r(self.db_id, table_name, col["name"])
        )
        parts = [name]

        if structural_level >= 4:
            parts.append(col["type"])
            if col["is_pk"] and not composite_pk:
                parts.append("PRIMARY KEY")
            pragma_col = self._pragma.get(table_name, {}).get(col["name"], {})
            if pragma_col.get("notnull") and not col["is_pk"]:
                parts.append("NOT NULL")

        line = " ".join(parts)

        if structural_level >= 5 and col["fk_to"]:
            to_table, to_col = col["fk_to"]
            s1r_to_table = get_table_name_s1r(self.db_id, to_table)
            s1r_to_col = _quote_if_needed(
                get_column_name_s1r(self.db_id, to_table, to_col)
            )
            cardinality = fk_cardinality_label(
                self.db_id, table_name, col["name"], to_table, to_col
            )
            line += f"  -- FK -> {s1r_to_table}.{s1r_to_col} ({cardinality})"

        return line

    def _format_foreign_key_relationships_s1r(self) -> str:
        col_lookup = self._meta["col_lookup"]
        raw = self._meta["foreign_keys_raw"]
        if not raw:
            return ""

        body = [
            "FOREIGN KEY RELATIONSHIPS",
            "Each line: child_table.child_column -> parent_table.parent_column "
            "(cardinality from child side)",
            "",
        ]
        for from_idx, to_idx in raw:
            if from_idx not in col_lookup or to_idx not in col_lookup:
                continue
            from_info = col_lookup[from_idx]
            to_info = col_lookup[to_idx]
            from_table = get_table_name_s1r(self.db_id, from_info["table"])
            to_table = get_table_name_s1r(self.db_id, to_info["table"])
            from_name = _quote_if_needed(
                get_column_name_s1r(
                    self.db_id, from_info["table"], from_info["name"]
                )
            )
            to_name = _quote_if_needed(
                get_column_name_s1r(self.db_id, to_info["table"], to_info["name"])
            )
            card = self._fk_cardinality(from_idx, to_idx)
            body.append(
                f"{from_table}.{from_name} -> {to_table}.{to_name} ({card})"
            )
        return _block_comment(body)

    def _format_join_paths_s1r(self) -> str:
        col_lookup = self._meta["col_lookup"]
        body = [
            "JOIN PATHS",
            "Example INNER JOIN patterns - adapt table and column names to your query.",
            "",
        ]
        for from_idx, to_idx in self._meta["foreign_keys_raw"]:
            if from_idx not in col_lookup or to_idx not in col_lookup:
                continue
            from_info = col_lookup[from_idx]
            to_info = col_lookup[to_idx]
            from_table = get_table_name_s1r(self.db_id, from_info["table"])
            to_table = get_table_name_s1r(self.db_id, to_info["table"])
            from_name = _quote_if_needed(
                get_column_name_s1r(
                    self.db_id, from_info["table"], from_info["name"]
                )
            )
            to_name = _quote_if_needed(
                get_column_name_s1r(self.db_id, to_info["table"], to_info["name"])
            )
            body.append(
                f"{from_table} JOIN {to_table}"
                f" ON {from_table}.{from_name} = {to_table}.{to_name}"
            )
        return _block_comment(body)
