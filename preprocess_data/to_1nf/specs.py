"""Per-database 1NF join plans: anchor table + FULL OUTER JOIN chain on FK keys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Union

JoinOn = Tuple[str, str, str, str]
# (table, on_pairs) | (table, join_type, on_pairs) | (table, join_type, on_pairs, prefix)
JoinStep = Union[
    Tuple[str, Tuple[JoinOn, ...]],
    Tuple[str, str, Tuple[JoinOn, ...]],
    Tuple[str, str, Tuple[JoinOn, ...], str],
]


def FOJ(
    table: str,
    *on_pairs: JoinOn,
    prefix: str | None = None,
) -> JoinStep:
    """
    One join step: FULL OUTER on explicit (left_alias, col, right_alias, col) pairs.

    ``prefix`` — when the same physical ``table`` is joined more than once (e.g.
    ``colour`` for skin / hair / eye), set a unique prefix for output columns
    (``colour_skin__id``, ``colour_hair__colour``, …).
    """
    if prefix is not None:
        return (table, "FULL OUTER", on_pairs, prefix)
    return (table, "FULL OUTER", on_pairs)


@dataclass(frozen=True)
class OneNfSpec:
    """Wide table plan: anchor + ordered join steps (each step uses full FK keys)."""

    anchor_table: str
    join_steps: Tuple[JoinStep, ...] = ()


_FORMULA_1 = OneNfSpec(
    anchor_table="results",
    join_steps=(
        FOJ("races", ("a0", "raceId", "a1", "raceId")),
        FOJ("drivers", ("a0", "driverId", "a2", "driverId")),
        FOJ("constructors", ("a0", "constructorId", "a3", "constructorId")),
        FOJ("status", ("a0", "statusId", "a4", "statusId")),
        FOJ("circuits", ("a1", "circuitId", "a5", "circuitId")),
        FOJ("seasons", ("a1", "year", "a6", "year")),
        FOJ(
            "qualifying",
            ("a0", "raceId", "a7", "raceId"),
            ("a0", "driverId", "a7", "driverId"),
            ("a0", "constructorId", "a7", "constructorId"),
        ),
        FOJ(
            "lapTimes",
            ("a0", "raceId", "a8", "raceId"),
            ("a0", "driverId", "a8", "driverId"),
        ),
        FOJ(
            "pitStops",
            ("a0", "raceId", "a9", "raceId"),
            ("a0", "driverId", "a9", "driverId"),
        ),
        FOJ(
            "driverStandings",
            ("a0", "raceId", "a10", "raceId"),
            ("a0", "driverId", "a10", "driverId"),
        ),
        FOJ(
            "constructorResults",
            ("a0", "raceId", "a11", "raceId"),
            ("a0", "constructorId", "a11", "constructorId"),
        ),
        FOJ(
            "constructorStandings",
            ("a0", "raceId", "a12", "raceId"),
            ("a0", "constructorId", "a12", "constructorId"),
        ),
    ),
)

# Hub: customers; txn/product/gas hang off transactions; yearmonth on CustomerID only.
_DEBIT_CARD = OneNfSpec(
    anchor_table="customers",
    join_steps=(
        FOJ("transactions_1k", ("a0", "CustomerID", "a1", "CustomerID")),
        FOJ("yearmonth", ("a0", "CustomerID", "a2", "CustomerID")),
        FOJ("products", ("a1", "ProductID", "a3", "ProductID")),
        FOJ("gasstations", ("a1", "GasStationID", "a4", "GasStationID")),
    ),
)

_CALIFORNIA_SCHOOLS = OneNfSpec(
    anchor_table="schools",
    join_steps=(
        # frpm 100% school-key overlap vs satscores ~91%; join higher overlap first
        FOJ("frpm", ("a0", "CDSCode", "a1", "CDSCode")),
        FOJ("satscores", ("a0", "CDSCode", "a2", "cds")),
    ),
)

_FINANCIAL = OneNfSpec(
    anchor_table="trans",
    join_steps=(
        FOJ("account", ("a0", "account_id", "a1", "account_id")),
        FOJ("loan", ("a0", "account_id", "a2", "account_id")),
        FOJ("order", ("a0", "account_id", "a3", "account_id")),
        FOJ("disp", ("a1", "account_id", "a4", "account_id")),
        FOJ("client", ("a4", "client_id", "a5", "client_id")),
        FOJ("district", ("a1", "district_id", "a6", "district_id")),
        FOJ("card", ("a4", "disp_id", "a7", "disp_id")),
    ),
)

_SUPERHERO = OneNfSpec(
    anchor_table="superhero",
    join_steps=(
        FOJ("gender", ("a0", "gender_id", "a1", "id")),
        FOJ("alignment", ("a0", "alignment_id", "a2", "id")),
        FOJ("publisher", ("a0", "publisher_id", "a3", "id")),
        FOJ("race", ("a0", "race_id", "a4", "id")),
        FOJ("colour", ("a0", "skin_colour_id", "a5", "id"), prefix="colour_skin"),
        FOJ("colour", ("a0", "hair_colour_id", "a6", "id"), prefix="colour_hair"),
        FOJ("colour", ("a0", "eye_colour_id", "a7", "id"), prefix="colour_eye"),
        FOJ("hero_attribute", ("a0", "id", "a8", "hero_id")),
        FOJ("attribute", ("a8", "attribute_id", "a9", "id")),
        FOJ("hero_power", ("a0", "id", "a10", "hero_id")),
        FOJ("superpower", ("a10", "power_id", "a11", "id")),
    ),
)

# Team_Attributes / Player_Attributes: join on team_api_id / player_api_id only.
# Do not join on date — Match.date (fixture) ≠ attribute snapshot date.
_EUROPEAN_FOOTBALL_2 = OneNfSpec(
    anchor_table="Match",
    join_steps=(
        FOJ("Country", ("a0", "country_id", "a1", "id")),
        FOJ("League", ("a0", "league_id", "a2", "id")),
        FOJ("Team", ("a0", "home_team_api_id", "a3", "team_api_id"), prefix="team_home"),
        FOJ("Team", ("a0", "away_team_api_id", "a4", "team_api_id"), prefix="team_away"),
        FOJ("Team_Attributes", ("a0", "home_team_api_id", "a5", "team_api_id")),
        FOJ("Player", ("a0", "home_player_1", "a6", "player_api_id")),
        FOJ("Player_Attributes", ("a6", "player_api_id", "a7", "player_api_id")),
    ),
)

# member hub; expense bridges to budget / event; attendance on member
_STUDENT_CLUB = OneNfSpec(
    anchor_table="member",
    join_steps=(
        FOJ("income", ("a0", "member_id", "a1", "link_to_member")),
        FOJ("expense", ("a0", "member_id", "a2", "link_to_member")),
        FOJ("major", ("a0", "link_to_major", "a3", "major_id")),
        FOJ("budget", ("a2", "link_to_budget", "a4", "budget_id")),
        FOJ("event", ("a4", "link_to_event", "a5", "event_id")),
        FOJ(
            "attendance",
            ("a0", "member_id", "a6", "link_to_member"),
            ("a5", "event_id", "a6", "link_to_event"),
        ),
        FOJ("zip_code", ("a0", "zip", "a7", "zip_code")),
    ),
)

# Patient hub; Examination and Laboratory sibling facts (same ID key)
_THROMBOSIS_PREDICTION = OneNfSpec(
    anchor_table="Patient",
    join_steps=(
        FOJ("Laboratory", ("a0", "ID", "a1", "ID")),
        FOJ("Examination", ("a0", "ID", "a2", "ID")),
    ),
)

# connected hub; bond + atom ×2 (atom_id / atom_id2) + molecule
_TOXICOLOGY = OneNfSpec(
    anchor_table="connected",
    join_steps=(
        FOJ("bond", ("a0", "bond_id", "a1", "bond_id")),
        FOJ("atom", ("a0", "atom_id", "a2", "atom_id"), prefix="atom_1"),
        FOJ("atom", ("a0", "atom_id2", "a3", "atom_id"), prefix="atom_2"),
        FOJ("molecule", ("a1", "molecule_id", "a4", "molecule_id")),
    ),
)

SPECS: dict[str, OneNfSpec] = {
    "formula_1": _FORMULA_1,
    "debit_card_specializing": _DEBIT_CARD,
    "california_schools": _CALIFORNIA_SCHOOLS,
    "financial": _FINANCIAL,
    "superhero": _SUPERHERO,
    "european_football_2": _EUROPEAN_FOOTBALL_2,
    "student_club": _STUDENT_CLUB,
    "thrombosis_prediction": _THROMBOSIS_PREDICTION,
    "toxicology": _TOXICOLOGY,
}
