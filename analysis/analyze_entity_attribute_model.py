#!/usr/bin/env python3
"""Entity / attribute analysis for nine 3NF BIRD databases."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

_ROOT = Path(__file__).resolve().parent.parent
DATA = _ROOT / "dev_20240627" / "dev_databases"
OUT = _ROOT / "docs" / "entity_attribute_analysis_nine_db.md"

DBS = [
    "california_schools",
    "debit_card_specializing",
    "european_football_2",
    "financial",
    "formula_1",
    "student_club",
    "superhero",
    "thrombosis_prediction",
    "toxicology",
]

ENTITY_MODEL: Dict[str, Dict[str, Tuple[str, str]]] = {
    "california_schools": {
        "schools": ("School (CDSCode)", "core"),
        "frpm": ("School (CDSCode)", "extension"),
        "satscores": ("School (CDSCode)", "extension"),
    },
    "debit_card_specializing": {
        "customers": ("Customer", "core"),
        "gasstations": ("Gas station", "core"),
        "products": ("Product", "core"),
        "transactions_1k": ("Transaction", "fact"),
        "yearmonth": ("Customer", "extension"),
    },
    "european_football_2": {
        "Country": ("Country", "lookup"),
        "League": ("League", "core"),
        "Team": ("Team", "core"),
        "Player": ("Player", "core"),
        "Match": ("Match (fixture)", "fact"),
        "Player_Attributes": ("Player", "extension"),
        "Team_Attributes": ("Team", "extension"),
    },
    "financial": {
        "district": ("District", "lookup"),
        "client": ("Client", "core"),
        "account": ("Account", "core"),
        "disp": ("Client-Account link", "bridge"),
        "card": ("Card", "dependent"),
        "loan": ("Loan", "dependent"),
        "order": ("Order", "dependent"),
        "trans": ("Bank transaction", "dependent"),
    },
    "formula_1": {
        "circuits": ("Circuit", "lookup"),
        "constructors": ("Constructor", "core"),
        "drivers": ("Driver", "core"),
        "seasons": ("Season", "lookup"),
        "status": ("Status", "lookup"),
        "races": ("Race", "core"),
        "results": ("Race result", "fact"),
        "qualifying": ("Qualifying", "fact"),
        "lapTimes": ("Lap time", "fact"),
        "pitStops": ("Pit stop", "fact"),
        "constructorResults": ("Constructor race result", "fact"),
        "constructorStandings": ("Constructor standing", "fact"),
        "driverStandings": ("Driver standing", "fact"),
    },
    "student_club": {
        "major": ("Major", "lookup"),
        "zip_code": ("ZIP code", "lookup"),
        "member": ("Member", "core"),
        "event": ("Event", "core"),
        "budget": ("Event budget", "dependent"),
        "expense": ("Expense", "dependent"),
        "income": ("Income", "dependent"),
        "attendance": ("Event-Member", "bridge"),
    },
    "superhero": {
        "superhero": ("Superhero", "core"),
        "publisher": ("Publisher", "lookup"),
        "race": ("Race", "lookup"),
        "gender": ("Gender", "lookup"),
        "alignment": ("Alignment", "lookup"),
        "colour": ("Colour", "lookup"),
        "attribute": ("Attribute type", "lookup"),
        "superpower": ("Superpower", "lookup"),
        "hero_attribute": ("Superhero-Attribute", "bridge"),
        "hero_power": ("Superhero-Power", "bridge"),
    },
    "thrombosis_prediction": {
        "Patient": ("Patient", "core"),
        "Examination": ("Patient", "extension"),
        "Laboratory": ("Patient", "extension"),
    },
    "toxicology": {
        "molecule": ("Molecule", "core"),
        "atom": ("Atom", "dependent"),
        "bond": ("Bond", "dependent"),
        "connected": ("Atom-Bond", "bridge"),
    },
}

BLURBS: Dict[str, str] = {
    "california_schools": (
        "**One school entity.** `schools` is the root; `frpm` and `satscores` are "
        "**vertical partitions** of school-related attributes. Their PKs (`CDSCode` / "
        "`cds`) are **foreign keys** to `schools.CDSCode`, not separate institutions."
    ),
    "debit_card_specializing": (
        "**Four conceptual entities:** Customer, Gas station, Product, Transaction. "
        "`yearmonth` is **monthly consumption per customer** (composite PK includes "
        "`CustomerID`); merge under Customer, not a fifth business object. "
        "`transactions_1k` has no declared FK but is an independent fact table."
    ),
    "european_football_2": (
        "**Country** (lookup), **League**, **Team**, **Player**, **Match** (fixture fact). "
        "`Player_Attributes` / `Team_Attributes` are **time-varying extensions**, not "
        "new players or teams. `Match` references many player slots via FKs."
    ),
    "financial": (
        "**District** (lookup), **Client**, **Account** as cores; **`disp`** links "
        "clients to accounts (bridge). Card, loan, order, and `trans` are **account- or "
        "client-scoped dependents**, not peers of Client."
    ),
    "formula_1": (
        "**Circuit, Season, Status** (lookups); **Constructor, Driver, Race** (cores); "
        "six **fact/standing** tables (results, qualifying, lapTimes, pitStops, "
        "constructor/driver standings). High table count, moderate distinct entity count."
    ),
    "student_club": (
        "**Major, ZIP** (lookups); **Member, Event** (cores). Budget/expense/income are "
        "**financial records** tied to events or members. **`attendance`** is an "
        "Event-Member bridge (composite PK = both FKs)."
    ),
    "superhero": (
        "Each `id` is **scoped to its own table** (`race.id` != `publisher.id`). "
        "**Superhero** is the only core noun; seven small **lookup** tables; "
        "`hero_attribute` / `hero_power` are **M:N bridges** with no PK."
    ),
    "thrombosis_prediction": (
        "**One patient entity.** `Laboratory` = lab panel per (`ID`, `Date`). "
        "`Examination` has **no PK** and allows multiple rows per patient (and NULL "
        "`ID`); treat as examination observations, not a separate Patient type."
    ),
    "toxicology": (
        "**Molecule** is the root; **Atom** and **Bond** belong to a molecule. "
        "`connected` links atoms to bonds (composite PK on atom pair). Chemically "
        "three object types, but **one hub entity** (Molecule) in the FK graph."
    ),
}


def schema(db_id: str) -> Dict[str, dict]:
    conn = sqlite3.connect(DATA / db_id / f"{db_id}.sqlite")
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        if not r[0].startswith("_")
    ]
    info = {}
    for t in tables:
        cols = conn.execute(f"PRAGMA table_info({t!r})").fetchall()
        pks = [c[1] for c in sorted([(r[5], r[1]) for r in cols if r[5]], key=lambda x: x[0])]
        fks = [
            (r[3], r[2], r[4] if r[4] else "?")
            for r in conn.execute(f"PRAGMA foreign_key_list({t!r})")
        ]
        info[t] = {
            "pks": pks,
            "fks": fks,
            "non_pk": [r[1] for r in cols if not r[5]],
        }
    conn.close()
    return info


def _fmt_fks(fks: List[Tuple[str, str, str]]) -> str:
    if not fks:
        return "none"
    seen, parts = set(), []
    for fr, ref_t, ref_c in fks:
        key = (fr, ref_t, ref_c)
        if key in seen:
            continue
        seen.add(key)
        parts.append(f"`{fr}` -> `{ref_t}.{ref_c}`")
    return "; ".join(parts)


def _fmt_pk(pks: List[str]) -> str:
    return "(none)" if not pks else ", ".join(f"`{p}`" for p in pks)


# Roles that denote a distinct identifiable thing (per user definition)
ENTITY_ROLES = frozenset({"core", "lookup", "fact", "dependent"})
NON_ENTITY_ROLES = frozenset({"extension", "bridge"})


def entity_summary(db_id: str, info: Dict[str, dict]) -> dict:
    model = ENTITY_MODEL[db_id]
    groups: Dict[str, dict] = {}
    for table, (entity, role) in model.items():
        g = groups.setdefault(
            entity,
            {"role": role, "tables": [], "attrs": 0, "is_entity": role in ENTITY_ROLES},
        )
        g["tables"].append(table)
        g["attrs"] += len(info[table]["non_pk"])

    entity_groups = {e: g for e, g in groups.items() if g["is_entity"]}
    bridge_tables = [t for t, (_, r) in model.items() if r == "bridge"]
    extension_tables = [t for t, (_, r) in model.items() if r == "extension"]

    ent_attrs = sum(g["attrs"] for g in entity_groups.values())
    n_ent = len(entity_groups)

    return {
        "groups": groups,
        "entity_groups": entity_groups,
        "n_entities": n_ent,
        "n_bridge_tables": len(bridge_tables),
        "n_extension_tables": len(extension_tables),
        "n_tables": len(info),
        "total_attrs": sum(len(v["non_pk"]) for v in info.values()),
        "entity_attrs": ent_attrs,
        "attrs_per_entity": ent_attrs / n_ent if n_ent else 0.0,
        "bridge_tables": bridge_tables,
        "extension_tables": extension_tables,
    }


def main() -> None:
    lines = [
        "# Entity and attribute analysis (nine 3NF databases)\n\n",
        "Entity = a **distinct, uniquely identifiable** real-world object, person, place, "
        "concept, or event. Uses PK/FK from SQLite (`dev_20240627/dev_databases/`).\n\n",
        "## What counts as an entity?\n\n",
        "| Role | Count as entity? | Rationale |\n",
        "|------|------------------|----------|\n",
        "| **core** | Yes | Primary noun (Client, School, Molecule, ...) |\n",
        "| **lookup** | Yes | Identifiable reference concept (District, Race, Season, ...) |\n",
        "| **fact** | Yes | Identifiable event/record (Match, Transaction, Race result, ...) |\n",
        "| **dependent** | **Yes** | Own surrogate PK + names a thing (Loan, Card, Atom, Expense, ...) |\n",
        "| **extension** | **No** | Same entity as parent; extra columns or observations (frpm, Laboratory, ...) |\n",
        "| **bridge** | **No** (default) | **Relationship** between entities (M:N link), not a third business object |\n\n",
        "### Bridge vs dependent (guidance)\n\n",
        "**Dependent** tables usually **are entities**: a `loan` row is a Loan, an `atom` row is an "
        "Atom, even though FK ties them to Account or Molecule. They have their own identity (PK) "
        "and are not just duplicate keys of the parent.\n\n",
        "**Bridge** tables usually **are not entities**: `disp` (client-account), `attendance` "
        "(event-member), `hero_power` (hero-power) primarily **link** two entities. Count them as "
        "**relationships**. Exception: if a bridge stores rich relationship-specific facts and you "
        "treat the link as a first-class object (e.g. enrollment with grade, contract with terms), "
        "you may reclassify as **fact** or **dependent**; none of the nine DB bridges here warrant "
        "that in the default reading.\n\n",
        "**Extension** never adds an entity count: `california_schools` stays **1 school**, "
        "`thrombosis_prediction` stays **1 patient**.\n\n",
        "**Counts:** **Entities** = distinct entity groups with role in "
        "{core, lookup, fact, dependent}. **Stored attrs** = all non-PK columns. "
        "**Entity attrs** = non-PK on entity groups only (includes extension cols merged into parent). "
        "**Attrs / entity** = entity attrs / entity count.\n\n",
        "PK reference: [`table_primary_keys_nine_db.md`](table_primary_keys_nine_db.md).\n\n",
        "## Summary\n\n",
        "| Database | Tables | **Entities** | Bridge tables | Extension tables | "
        "Entity attrs | Attrs / entity | All attrs |\n",
        "|----------|-------:|-------------:|--------------:|-----------------:|"
        "------------:|---------------:|----------:|\n",
    ]
    for db in DBS:
        s = entity_summary(db, schema(db))
        lines.append(
            f"| `{db}` | {s['n_tables']} | {s['n_entities']} | {s['n_bridge_tables']} | "
            f"{s['n_extension_tables']} | {s['entity_attrs']} | {s['attrs_per_entity']:.1f} | "
            f"{s['total_attrs']} |\n"
        )
    lines.append("\n---\n\n")
    for db in DBS:
        info = schema(db)
        s = entity_summary(db, info)
        lines.append(f"## `{db}`\n\n{BLURBS[db]}\n\n")
        lines.append("### Tables\n\n")
        lines.append("| Table | PK | Foreign keys | Role | Entity group | Non-PK attrs |\n")
        lines.append("|-------|-----|--------------|------|--------------|-------------:|\n")
        for t in sorted(info):
            ent, role = ENTITY_MODEL[db][t]
            lines.append(
                f"| `{t}` | {_fmt_pk(info[t]['pks'])} | {_fmt_fks(info[t]['fks'])} | "
                f"{role} | {ent} | {len(info[t]['non_pk'])} |\n"
            )
        lines.append("\n### Entity groups\n\n")
        lines.append("| Entity group | Role | Tables | Non-PK attrs |\n")
        lines.append("|--------------|------|--------|-------------:|\n")
        for ent, g in sorted(s["groups"].items()):
            tbls = ", ".join(f"`{x}`" for x in g["tables"])
            lines.append(f"| {ent} | {g['role']} | {tbls} | {g['attrs']} |\n")
        ent_list = ", ".join(f"**{e}** ({g['role']})" for e, g in sorted(s["entity_groups"].items()))
        lines.append(f"\n**Entities ({s['n_entities']}):** {ent_list}.\n")
        if s["bridge_tables"]:
            lines.append(
                f"**Bridges (not counted):** {', '.join(f'`{t}`' for t in s['bridge_tables'])}.\n"
            )
        if s["extension_tables"]:
            lines.append(
                f"**Extensions (merged into parent):** "
                f"{', '.join(f'`{t}`' for t in s['extension_tables'])}.\n"
            )
        lines.append(
            f"\n**Totals:** {s['n_entities']} entities, {s['entity_attrs']} entity attributes "
            f"({s['attrs_per_entity']:.1f} per entity), {s['total_attrs']} attributes in schema.\n\n"
            "---\n\n"
        )
    lines.append("Regenerate: `python3 analysis/analyze_entity_attribute_model.py`\n")
    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
