"""
Convert BIRD SQLite databases to first normal form (1NF): one wide scalar table
per database, built from an explicit fact-anchored join plan.

See ``preprocess_data.to_1nf.convert`` for the API and join specs in ``.specs``.
"""

from preprocess_data.to_1nf.convert import (
    OneNfPlan,
    build_plan,
    materialize_sqlite,
)
from preprocess_data.to_1nf.specs import OneNfSpec, SPECS

__all__ = [
    "OneNfPlan",
    "OneNfSpec",
    "SPECS",
    "build_plan",
    "materialize_sqlite",
]
