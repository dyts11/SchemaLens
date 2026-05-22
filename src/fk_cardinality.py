"""
FK cardinality labels for L5/L6 schema prompts.

Default is ``many-to-one`` (child → parent). BIRD rarely has a true 1:1 FK;
a column that is both PK and FK is usually a *forwarded* or *delegated* PK
(weak entity / extension table), not a join-safe one-to-one.

Only edges listed in ``TRUE_ONE_TO_ONE`` are labelled ``one-to-one``.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

# (child_table, child_col_original, parent_table, parent_col_original)
FkEdge = Tuple[str, str, str, str]

# Verified or domain-clear 1:1 extension rows (child row identifies parent row uniquely).
TRUE_ONE_TO_ONE: Dict[str, FrozenSet[FkEdge]] = {
    "california_schools": frozenset(
        {
            ("frpm", "CDSCode", "schools", "CDSCode"),
            ("satscores", "cds", "schools", "CDSCode"),
        }
    ),
}


def fk_cardinality_label(
    db_id: str,
    child_table: str,
    child_col: str,
    parent_table: str,
    parent_col: str,
) -> str:
    """
    Cardinality from the child (FK holder) toward the parent row.

    Almost all BIRD foreign keys are many-to-one. One-to-one is only returned
    when the edge is explicitly listed for ``db_id`` in ``TRUE_ONE_TO_ONE``.
    """
    edge: FkEdge = (child_table, child_col, parent_table, parent_col)
    if edge in TRUE_ONE_TO_ONE.get(db_id, frozenset()):
        return "one-to-one"
    return "many-to-one"
