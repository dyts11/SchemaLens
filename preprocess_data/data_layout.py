"""Resolve source/output paths for 1NF and 2NF materialisation (BIRD or Spider)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class MaterializePaths:
    """Paths used by ``to_1nf`` / ``to_2nf`` build scripts."""

    tables_json: Path
    source_sqlite: Path
    output_sqlite: Path
    layout: str  # "bird" | "spider"


@dataclass(frozen=True)
class DataLayout:
    """
    Runtime path resolver for the experiment (schema builder, evaluator, runner).

    BIRD (default):
        tables  -> {data_dir}/dev_tables.json
        db dir  -> {data_dir}/dev_databases/{db_id}/

    Spider (spider_dir set):
        tables  -> {spider_dir}/tables.json
        db dir  -> {spider_dir}/database/{db_id}/

    ``database_dir`` and ``tables_json`` may be overridden explicitly.
    """

    data_dir: Path
    database_dir: Path
    tables_json: Path
    layout: str  # "bird" | "spider"

    @classmethod
    def create(
        cls,
        data_dir,
        *,
        spider_dir=None,
        database_dir=None,
        tables_json=None,
    ) -> "DataLayout":
        data_dir = Path(data_dir)
        layout = "bird"

        if spider_dir is not None:
            spider_dir = Path(spider_dir)
            layout = "spider"
            if database_dir is None:
                database_dir = spider_dir / "database"
            if tables_json is None:
                tables_json = spider_dir / "tables.json"

        if database_dir is None:
            database_dir = data_dir / "dev_databases"
        else:
            database_dir = Path(database_dir)

        if tables_json is None:
            tables_json = data_dir / "dev_tables.json"
        else:
            tables_json = Path(tables_json)

        return cls(
            data_dir=data_dir,
            database_dir=database_dir,
            tables_json=tables_json,
            layout=layout,
        )

    def db_dir(self, db_id: str) -> Path:
        return self.database_dir / db_id

    def source_sqlite(self, db_id: str) -> Path:
        return self.db_dir(db_id) / f"{db_id}.sqlite"

    def one_nf_sqlite(self, db_id: str) -> Path:
        return self.db_dir(db_id) / f"{db_id}__1nf.sqlite"

    def two_nf_sqlite(self, db_id: str) -> Path:
        return self.db_dir(db_id) / f"{db_id}__2nf.sqlite"

    def description_dir(self, db_id: str) -> Path:
        return self.db_dir(db_id) / "database_description"


def resolve_materialize_paths(
    db_id: str,
    *,
    data_dir: Path,
    variant_suffix: str,
    spider_dir: Optional[Path] = None,
    database_dir: Optional[Path] = None,
    tables_json: Optional[Path] = None,
    output: Optional[Path] = None,
) -> MaterializePaths:
    """
    Resolve metadata, 3NF source, and denormalised output paths.

    BIRD (default):
        tables  -> {data_dir}/dev_tables.json
        source  -> {data_dir}/dev_databases/{db_id}/{db_id}.sqlite
        output  -> {data_dir}/dev_databases/{db_id}/{db_id}{variant_suffix}.sqlite

    Spider (--spider-dir):
        tables  -> {spider_dir}/tables.json
        source  -> {spider_dir}/database/{db_id}/{db_id}.sqlite
        output  -> {spider_dir}/database/{db_id}/{db_id}{variant_suffix}.sqlite

    Overrides:
        --database-dir  folder containing per-db subfolders (car_1/car_1.sqlite)
        --tables-json   schema metadata (dev_tables.json or tables.json)
        -o / --output   explicit output .sqlite path
    """
    data_dir = Path(data_dir)
    layout = "bird"

    if spider_dir is not None:
        spider_dir = Path(spider_dir)
        layout = "spider"
        if database_dir is None:
            database_dir = spider_dir / "database"
        if tables_json is None:
            tables_json = spider_dir / "tables.json"

    if database_dir is None:
        database_dir = data_dir / "dev_databases"
    else:
        database_dir = Path(database_dir)

    if tables_json is None:
        tables_json = data_dir / "dev_tables.json"
    else:
        tables_json = Path(tables_json)

    db_folder = database_dir / db_id
    source = db_folder / f"{db_id}.sqlite"
    if output is not None:
        out = Path(output)
    else:
        out = db_folder / f"{db_id}{variant_suffix}.sqlite"

    return MaterializePaths(
        tables_json=tables_json,
        source_sqlite=source,
        output_sqlite=out,
        layout=layout,
    )


def add_materialize_path_args(parser) -> None:
    """Register shared path flags on an argparse parser."""
    parser.add_argument(
        "--data-dir",
        default="dev_20240627",
        help="BIRD data root with dev_tables.json (default: dev_20240627)",
    )
    parser.add_argument(
        "--spider-dir",
        default=None,
        help="Spider data root (uses database/ and tables.json under this path)",
    )
    parser.add_argument(
        "--database-dir",
        default=None,
        help="Override folder of per-db SQLite dirs (default: dev_databases/ or spider_dir/database/)",
    )
    parser.add_argument(
        "--tables-json",
        default=None,
        help="Override schema metadata JSON (BIRD dev_tables.json or Spider tables.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output .sqlite path (default: beside source as {db_id}__1nf.sqlite or __2nf.sqlite)",
    )
