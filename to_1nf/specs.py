"""Per-database 1NF join plans (anchor table + ordered LEFT JOIN steps)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

JoinOn = Tuple[str, str, str, str]


@dataclass(frozen=True)
class OneNfSpec:
    """Explicit wide join: anchor table plus ordered LEFT JOIN steps."""

    anchor_table: str
    join_steps: Tuple[Tuple[str, Tuple[JoinOn, ...]], ...]


_FORMULA_1 = OneNfSpec(
    anchor_table="results",
    join_steps=(
        ("races", (("a0", "raceId", "a1", "raceId"),)),
        ("drivers", (("a0", "driverId", "a2", "driverId"),)),
        ("constructors", (("a0", "constructorId", "a3", "constructorId"),)),
        ("status", (("a0", "statusId", "a4", "statusId"),)),
        ("circuits", (("a1", "circuitId", "a5", "circuitId"),)),
        ("seasons", (("a1", "year", "a6", "year"),)),
        (
            "qualifying",
            (
                ("a0", "raceId", "a7", "raceId"),
                ("a0", "driverId", "a7", "driverId"),
                ("a0", "constructorId", "a7", "constructorId"),
            ),
        ),
        (
            "driverStandings",
            (
                ("a0", "raceId", "a8", "raceId"),
                ("a0", "driverId", "a8", "driverId"),
            ),
        ),
        (
            "constructorResults",
            (
                ("a0", "raceId", "a9", "raceId"),
                ("a0", "constructorId", "a9", "constructorId"),
            ),
        ),
        (
            "constructorStandings",
            (
                ("a0", "raceId", "a10", "raceId"),
                ("a0", "constructorId", "a10", "constructorId"),
            ),
        ),
        (
            "lapTimes",
            (
                ("a0", "raceId", "a11", "raceId"),
                ("a0", "driverId", "a11", "driverId"),
            ),
        ),
        (
            "pitStops",
            (
                ("a0", "raceId", "a12", "raceId"),
                ("a0", "driverId", "a12", "driverId"),
            ),
        ),
    ),
)

SPECS: dict[str, OneNfSpec] = {
    "formula_1": _FORMULA_1,
}
