"""
Synthetic **2NF-only** materialisation (2NF but not 3NF): denormalised wide
clusters built with the same join engine as ``to_1nf``.

See ``preprocess_data.to_2nf.specs`` for per-database cluster definitions.
"""

from preprocess_data.to_2nf.convert import (
    ClusterMaterialization,
    TwoNfPlan,
    build_plan,
    describe_plan,
    materialize_sqlite,
)
from preprocess_data.to_2nf.specs import JoinOn, TwoNfClusterSpec, TwoNfDbSpec, SPECS

__all__ = [
    "ClusterMaterialization",
    "JoinOn",
    "TwoNfClusterSpec",
    "TwoNfDbSpec",
    "TwoNfPlan",
    "SPECS",
    "build_plan",
    "describe_plan",
    "materialize_sqlite",
]
