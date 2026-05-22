"""
Per-database **synthetic 2NF-only** plans derived from the 3NF BIRD schema.

Design goals (see ``.cursor/skills/nf-specs/SKILL.md``)
------------------------------------------------------
1. Wide tables are **2NF but not 3NF** (transitive dependencies kept on the anchor).
2. **No row loss** — chained FULL OUTER JOINs; orphan rows appear with NULL on the
   missing side (dimensions joined from a fact hub need not get their own cluster).
3. **Minimize NULLs** — join order by shared-key count, then match ratio (Step 3).

Each **cluster** is one materialised wide table:

  anchor  = hub table for that cluster
  joins   = FULL OUTER chain; 2NF build uses ``COALESCE`` on left join keys
            (``to_2nf.convert`` → ``coalesce_join_keys=True``).

When two columns differ by name but are the same key (e.g. ``CDSCode`` / ``cds``), keep
both in the ``JoinOn`` tuple — COALESCE only merges the **same** column name.

Do **not** merge **sibling facts** (e.g. ``trans`` + ``loan`` + ``order`` on ``account``):
many children → one parent in one chain does not preserve one row per child PK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from preprocess_data.to_1nf.specs import FOJ, JoinOn, JoinStep

__all__ = ["JoinOn", "JoinStep", "FOJ", "TwoNfClusterSpec", "TwoNfDbSpec", "SPECS"]


def join_step_table(step: JoinStep) -> str:
    """Physical source table for a join step (2-, 3-, or 4-tuple)."""
    return step[0]


@dataclass(frozen=True)
class TwoNfClusterSpec:
    output_table: str
    anchor_table: str
    join_steps: Tuple[JoinStep, ...]


@dataclass(frozen=True)
class TwoNfDbSpec:
    clusters: Tuple[TwoNfClusterSpec, ...]


# ---------------------------------------------------------------------------
# formula_1 — driverStandings only on two_nf_results (FOJ); qualifying own PK
# ---------------------------------------------------------------------------
_FORMULA_1 = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_results",
            "results",
            (
                (
                    "driverStandings",
                    (
                        ("a0", "raceId", "a1", "raceId"),
                        ("a0", "driverId", "a1", "driverId"),
                    ),
                ),
                ("races", (("a0", "raceId", "a2", "raceId"),)),
                ("drivers", (("a0", "driverId", "a3", "driverId"),)),
                ("constructors", (("a0", "constructorId", "a4", "constructorId"),)),
                ("status", (("a0", "statusId", "a5", "statusId"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_races",
            "races",
            (
                ("seasons", (("a0", "year", "a1", "year"),)),
                ("circuits", (("a0", "circuitId", "a2", "circuitId"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_qualifying",
            "qualifying",
            (
                ("constructors", (("a0", "constructorId", "a1", "constructorId"),)),
                ("drivers", (("a0", "driverId", "a2", "driverId"),)),
                ("races", (("a0", "raceId", "a3", "raceId"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_lap_times",
            "lapTimes",
            (
                ("drivers", (("a0", "driverId", "a1", "driverId"),)),
                ("races", (("a0", "raceId", "a2", "raceId"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_pit_stops",
            "pitStops",
            (
                ("drivers", (("a0", "driverId", "a1", "driverId"),)),
                ("races", (("a0", "raceId", "a2", "raceId"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_constructors",
            "constructors",
            (
                ("constructorResults", (("a0", "constructorId", "a1", "constructorId"),)),
                (
                    "constructorStandings",
                    (
                        ("a0", "constructorId", "a2", "constructorId"),
                        ("a1", "raceId", "a2", "raceId"),
                    ),
                ),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# debit_card_specializing — transactions hub; orphan dims via FOJ (no solo clusters)
# yearmonth stays separate (not joined into transactions)
# ---------------------------------------------------------------------------
_DEBIT_CARD = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_yearmonth",
            "yearmonth",
            (("customers", (("a0", "CustomerID", "a1", "CustomerID"),)),),
        ),
        TwoNfClusterSpec(
            "two_nf_transactions",
            "transactions_1k",
            (
                ("customers", (("a0", "CustomerID", "a1", "CustomerID"),)),
                ("products", (("a0", "ProductID", "a2", "ProductID"),)),
                ("gasstations", (("a0", "GasStationID", "a3", "GasStationID"),)),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# california_schools — schools hub; frpm + satscores via FOJ (no satscores cluster)
# ---------------------------------------------------------------------------
_CALIFORNIA_SCHOOLS = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_schools",
            "schools",
            (
                ("satscores", (("a0", "CDSCode", "a1", "cds"),)),
                ("frpm", (("a0", "CDSCode", "a2", "CDSCode"),)),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# financial — sibling facts stay separate; card merged into disp
# ---------------------------------------------------------------------------
_FINANCIAL = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_trans",
            "trans",
            (
                ("account", (("a0", "account_id", "a1", "account_id"),)),
                ("district", (("a1", "district_id", "a2", "district_id"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_loan",
            "loan",
            (
                ("account", (("a0", "account_id", "a1", "account_id"),)),
                ("district", (("a1", "district_id", "a2", "district_id"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_order",
            "order",
            (
                ("account", (("a0", "account_id", "a1", "account_id"),)),
                ("district", (("a1", "district_id", "a2", "district_id"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_disp",
            "disp",
            (
                ("card", (("a0", "disp_id", "a1", "disp_id"),)),
                ("client", (("a0", "client_id", "a2", "client_id"),)),
                ("district", (("a2", "district_id", "a3", "district_id"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_account",
            "account",
            (("district", (("a0", "district_id", "a1", "district_id"),)),),
        ),
    ),
)

# ---------------------------------------------------------------------------
# student_club — event hub (+ attendance, member); member hub; expense separate
# ---------------------------------------------------------------------------
_STUDENT_CLUB = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_member",
            "member",
            (
                ("zip_code", (("a0", "zip", "a1", "zip_code"),)),
                ("major", (("a0", "link_to_major", "a2", "major_id"),)),
                ("income", (("a0", "member_id", "a3", "link_to_member"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_event",
            "event",
            (
                ("budget", (("a0", "event_id", "a1", "link_to_event"),)),
                ("attendance", (("a0", "event_id", "a2", "link_to_event"),)),
                ("member", (("a2", "link_to_member", "a3", "member_id"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_expense",
            "expense",
            (
                ("member", (("a0", "link_to_member", "a1", "member_id"),)),
                ("budget", (("a0", "link_to_budget", "a2", "budget_id"),)),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# thrombosis_prediction — Patient + Examination | Patient + Laboratory (2 clusters)
# ---------------------------------------------------------------------------
_THROMBOSIS_PREDICTION = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_patient_examination",
            "Patient",
            (("Examination", (("a0", "ID", "a1", "ID"),)),),
        ),
        TwoNfClusterSpec(
            "two_nf_patient_laboratory",
            "Patient",
            (("Laboratory", (("a0", "ID", "a1", "ID"),)),),
        ),
    ),
)

# ---------------------------------------------------------------------------
# toxicology — single connected hub (bond → atom ×2 → molecule); FOJ keeps atom-only rows
# ---------------------------------------------------------------------------
_TOXICOLOGY = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_connected",
            "connected",
            (
                FOJ("bond", ("a0", "bond_id", "a1", "bond_id")),
                FOJ("atom", ("a0", "atom_id", "a2", "atom_id"), prefix="atom_1"),
                FOJ("atom", ("a0", "atom_id2", "a3", "atom_id"), prefix="atom_2"),
                FOJ("molecule", ("a1", "molecule_id", "a4", "molecule_id")),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# superhero — superhero hub; colour ×3 (skin/hair/eye); junction clusters separate
# ---------------------------------------------------------------------------
_SUPERHERO = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_superhero",
            "superhero",
            (
                FOJ("gender", ("a0", "gender_id", "a1", "id")),
                FOJ("alignment", ("a0", "alignment_id", "a2", "id")),
                FOJ("publisher", ("a0", "publisher_id", "a3", "id")),
                FOJ("race", ("a0", "race_id", "a4", "id")),
                FOJ("colour", ("a0", "skin_colour_id", "a5", "id"), prefix="colour_skin"),
                FOJ("colour", ("a0", "hair_colour_id", "a6", "id"), prefix="colour_hair"),
                FOJ("colour", ("a0", "eye_colour_id", "a7", "id"), prefix="colour_eye"),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_hero_attribute",
            "hero_attribute",
            (
                ("attribute", (("a0", "attribute_id", "a1", "id"),)),
                ("superhero", (("a0", "hero_id", "a2", "id"),)),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_hero_power",
            "hero_power",
            (
                ("superpower", (("a0", "power_id", "a1", "id"),)),
                ("superhero", (("a0", "hero_id", "a2", "id"),)),
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# european_football_2 — Match hub (no TA/PA); team/player attrs on own clusters
# ---------------------------------------------------------------------------
_EUROPEAN_FOOTBALL_2 = TwoNfDbSpec(
    clusters=(
        TwoNfClusterSpec(
            "two_nf_match",
            "Match",
            (
                FOJ("Country", ("a0", "country_id", "a1", "id")),
                FOJ("League", ("a0", "league_id", "a2", "id")),
                FOJ("Team", ("a0", "home_team_api_id", "a3", "team_api_id"), prefix="team_home"),
                FOJ("Team", ("a0", "away_team_api_id", "a4", "team_api_id"), prefix="team_away"),
                FOJ("Player", ("a0", "home_player_1", "a5", "player_api_id")),
            ),
        ),
        TwoNfClusterSpec(
            "two_nf_team",
            "Team",
            (("Team_Attributes", (("a0", "team_api_id", "a1", "team_api_id"),)),),
        ),
        TwoNfClusterSpec(
            "two_nf_player",
            "Player",
            (
                ("Player_Attributes", (("a0", "player_api_id", "a1", "player_api_id"),)),
            ),
        ),
    ),
)


SPECS: dict[str, TwoNfDbSpec] = {
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
