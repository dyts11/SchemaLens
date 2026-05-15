"""
Convert BIRD SQLite databases to first normal form (1NF): one wide scalar table
per database, built from an explicit fact-anchored join plan.

See ``to_1nf.convert`` for the API and per-database join specs in ``to_1nf.specs``.
"""

from to_1nf.convert import (
    OneNfPlan,
    build_plan,
    format_schema_prompt,
    materialize_sqlite,
    view_ddls,
)
from to_1nf.specs import OneNfSpec, SPECS

__all__ = [
    "OneNfPlan",
    "OneNfSpec",
    "build_plan",
    "format_schema_prompt",
    "materialize_sqlite",
    "view_ddls",
]
