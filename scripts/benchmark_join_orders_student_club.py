#!/usr/bin/env python3
"""
Quick join-order benchmark on student_club (1NF FOJ + COALESCE).

Compares:
  - current   Method B spec order (checklist)
  - old       Legacy greedy (zip_code first)
  - overlap   Method A greedy overlap + sparse defer
  - simpli    Simpli-Squared style: FK 1:N children by ascending row count
  - workload  BIRD dev questions: join most-mentioned tables first
"""

from __future__ import annotations

import json
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preprocess_data.to_1nf.convert import _build_select_sql
from preprocess_data.to_1nf.specs import FOJ, OneNfSpec, SPECS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dev_20240627"
DB_ID = "student_club"
ANCHOR = "member"

# Undirected FK edges for auto JoinOn when reordering
_EDGES = [
    ("member", "member_id", "income", "link_to_member"),
    ("member", "member_id", "expense", "link_to_member"),
    ("member", "link_to_major", "major", "major_id"),
    ("expense", "link_to_budget", "budget", "budget_id"),
    ("budget", "link_to_event", "event", "event_id"),
    ("member", "member_id", "attendance", "link_to_member"),
    ("event", "event_id", "attendance", "link_to_event"),
    ("member", "zip", "zip_code", "zip_code"),
]

ORDERS = {
    "current": ["income", "expense", "major", "budget", "event", "attendance", "zip_code"],
    "old": ["zip_code", "major", "income", "expense", "budget", "event", "attendance"],
}


def _load_entry():
    with open(DATA / "dev_tables.json", encoding="utf-8") as f:
        return next(e for e in json.load(f) if e["db_id"] == DB_ID)


def _row_counts(db_path: Path) -> dict[str, int]:
    con = sqlite3.connect(db_path)
    out = {}
    for (t,) in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        out[t] = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    con.close()
    return out


def _build_spec_from_order_v2(order: list[str]) -> OneNfSpec:
    chain = [ANCHOR]
    join_steps = []
    alias = {ANCHOR: "a0"}

    for i, tbl in enumerate(order, start=1):
        al_new = f"a{i}"
        on_pairs = []
        for t1, c1, t2, c2 in _EDGES:
            if {t1, t2} - {tbl} - set(chain):
                continue
            if tbl not in (t1, t2):
                continue
            other = t2 if t1 == tbl else t1
            if other not in chain:
                continue
            a_other = alias[other]
            if t1 == tbl:
                on_pairs.append((a_other, c2 if other == t2 else c1, al_new, c1 if t1 == tbl else c2))
            else:
                on_pairs.append((a_other, c1 if other == t1 else c2, al_new, c2 if t2 == tbl else c1))
        # fix orientation: left = chain, right = new
        cleaned = []
        for t1, c1, t2, c2 in _EDGES:
            if tbl not in (t1, t2):
                continue
            other = t2 if t1 == tbl else t1
            if other not in chain:
                continue
            cleaned.append((alias[other], c2 if other == t2 else c1, al_new, c1 if t1 == tbl else c2))
        seen = set()
        uniq = []
        for p in cleaned:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        if not uniq:
            raise ValueError(f"Cannot join {tbl}; chain={chain}")
        join_steps.append(FOJ(tbl, *uniq))
        alias[tbl] = al_new
        chain.append(tbl)

    return OneNfSpec(anchor_table=ANCHOR, join_steps=tuple(join_steps))


def _greedy_overlap_order(db_path: Path, rows: dict[str, int]) -> list[str]:
    remaining = set(rows) - {ANCHOR}
    chain = [ANCHOR]
    fks = defaultdict(list)
    for t1, c1, t2, c2 in _EDGES:
        fks[t2].append((t1, c2, c1))
        fks[t1].append((t2, c1, c2))
    order = []

    def ov(child, cf, parent, pf):
        con = sqlite3.connect(db_path)
        n = con.execute(
            f'''SELECT COUNT(*) FROM "{child}" c WHERE c."{cf}" IS NOT NULL
            AND EXISTS (SELECT 1 FROM "{parent}" p WHERE p."{pf}"=c."{cf}")'''
        ).fetchone()[0]
        tot = con.execute(f'SELECT COUNT(*) FROM "{child}"').fetchone()[0]
        con.close()
        return n / tot if tot else 0.0

    while remaining:
        best, best_score = None, (-1, -1.0)
        for t in remaining:
            links = []
            for par, fc, pc in fks.get(t, []):
                if par in chain:
                    links.append((t, fc, par, pc))
            for c in chain:
                for par, fc, pc in fks.get(c, []):
                    if par == t:
                        links.append((c, fc, t, pc))
            nkeys = len(links)
            o = max((ov(ch, fc, pa, pc) for ch, fc, pa, pc in links), default=0.0)
            sparse = rows[t] > 10 * rows[ANCHOR] and o < 0.01
            score = (0 if sparse else 1, nkeys, o)
            if score > best_score:
                best_score, best = score, t
        order.append(best)
        chain.append(best)
        remaining.remove(best)
    return order


def _simpli_squared_order(rows: dict[str, int]) -> list[str]:
    """FK children of anchor: ascending row count (1:N small tables before huge dimensions)."""
    children = set()
    for t1, _, t2, _ in _EDGES:
        if t1 == ANCHOR:
            children.add(t2)
        elif t2 == ANCHOR:
            children.add(t1)
    # topological-ish: non-anchor tables by size, defer zip_code
    rest = [t for t in rows if t != ANCHOR]
    return sorted(rest, key=lambda t: (t == "zip_code", rows[t]))


def _workload_order() -> list[str]:
    with open(DATA / "dev.json", encoding="utf-8") as f:
        questions = [q for q in json.load(f) if q.get("db_id") == DB_ID]
    counts: Counter[str] = Counter()
    for q in questions:
        sql = (q.get("SQL") or q.get("sql") or "").lower()
        for t in (
            "income", "expense", "major", "budget", "event", "attendance", "zip_code", "member"
        ):
            if re.search(rf"\b{re.escape(t)}\b", sql):
                counts[t] += 1
    tables = [t for t in counts if t != ANCHOR]
    return sorted(tables, key=lambda t: (-counts[t], t))


def _eel_legal(order: list[str]) -> bool:
    """EEL-style: T joins only if every ON neighbor is already in the chain."""
    chain = {ANCHOR}
    for tbl in order:
        needed = set()
        for t1, c1, t2, c2 in _EDGES:
            if tbl not in (t1, t2):
                continue
            other = t2 if t1 == tbl else t1
            if other != ANCHOR:
                needed.add(other)
        if not needed <= chain:
            return False
        chain.add(tbl)
    return True


def _topo_sort(proposed: list[str]) -> list[str]:
    """Stable topological sort respecting join dependencies (budget←expense←event, etc.)."""
    tables = set(proposed)
    preds: dict[str, set[str]] = defaultdict(set)
    for t1, _, t2, _ in _EDGES:
        if t1 == ANCHOR or t2 == ANCHOR:
            continue
        if t1 in tables and t2 in tables:
            # join chains usually: dimension attached via one parent
            pass
    # explicit deps for this schema
    hard = {
        "budget": {"expense"},
        "event": {"budget"},
        "attendance": {"event"},  # member is anchor
    }
    for t in proposed:
        preds[t] = hard.get(t, set()) & tables
    out, seen = [], set()
    remaining = list(proposed)

    def ready(t):
        return preds[t] <= seen

    while remaining:
        moved = False
        for t in list(remaining):
            if ready(t):
                out.append(t)
                seen.add(t)
                remaining.remove(t)
                moved = True
        if not moved:
            raise ValueError(f"Cycle in order: {remaining}")
    return out


@dataclass
class Metrics:
    name: str
    order: list[str]
    eel_legal: bool
    output_rows: int
    source_rows: int
    inflation: float
    member_cols_nonnull_pct: float
    zip_cols_nonnull_pct: float
    hub_member_id_null_pct: float
    coverage: dict[str, float]


def _materialize_and_measure(name: str, spec: OneNfSpec, entry: dict, src: Path) -> Metrics:
    tables_cols = {t: [] for t in entry["table_names_original"]}
    for ti, cn in entry["column_names_original"]:
        if ti >= 0:
            tables_cols[entry["table_names_original"][ti]].append({"name": cn})

    sql, display_cols = _build_select_sql(
        DB_ID, spec, tables_cols, 3, source_prefix="orig", coalesce_join_keys=True
    )

    src_rows = _row_counts(src)
    source_total = sum(src_rows.values())

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "bench.sqlite"
        con = sqlite3.connect(out)
        con.execute("ATTACH DATABASE ? AS orig", (str(src),))
        con.execute(f"CREATE TABLE wide AS {sql}")
        out_rows = con.execute("SELECT COUNT(*) FROM wide").fetchone()[0]

        # member_id column in wide (hub key propagation)
        member_id_cols = [c for c in display_cols if c.endswith("__member_id") or c == "member__member_id"]
        if not member_id_cols:
            member_id_cols = [c for c in display_cols if "member_id" in c.lower()][:1]
        mid_col = member_id_cols[0] if member_id_cols else display_cols[0]
        q = _quote = lambda c: f'"{c}"' if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", c) else c
        qc = q(mid_col)
        null_hub = con.execute(
            f"SELECT SUM(CASE WHEN {qc} IS NULL THEN 1 ELSE 0 END)*1.0/COUNT(*) FROM wide"
        ).fetchone()[0]

        # zip columns non-null %
        zip_cols = [c for c in display_cols if c.startswith("zip_code__")]
        zip_nn = 0.0
        if zip_cols:
            zc = q(zip_cols[0])
            zip_nn = con.execute(
                f"SELECT SUM(CASE WHEN {zc} IS NOT NULL THEN 1 ELSE 0 END)*1.0/COUNT(*) FROM wide"
            ).fetchone()[0]

        member_cols = [c for c in display_cols if c.startswith("member__")]
        mem_nn = 0.0
        if member_cols:
            mc = q(member_cols[0])
            mem_nn = con.execute(
                f"SELECT SUM(CASE WHEN {mc} IS NOT NULL THEN 1 ELSE 0 END)*1.0/COUNT(*) FROM wide"
            ).fetchone()[0]

        coverage = {}
        for tbl in src_rows:
            if tbl == ANCHOR:
                cols = [c for c in display_cols if c.startswith("member__")]
            else:
                cols = [c for c in display_cols if c.startswith(tbl.replace(" ", "_") + "__") or c.startswith(f"{tbl}__")]
            if not cols:
                coverage[tbl] = -1.0
                continue
            cond = " OR ".join(f"{q(c)} IS NOT NULL" for c in cols[:3])
            hit = con.execute(f"SELECT COUNT(*) FROM wide WHERE {cond}").fetchone()[0]
            coverage[tbl] = hit / max(src_rows[tbl], 1)

        con.close()

    return Metrics(
        name=name,
        order=[s[0] for s in spec.join_steps] if hasattr(spec.join_steps[0], "__getitem__") else [],
        eel_legal=True,
        output_rows=out_rows,
        source_rows=source_total,
        inflation=out_rows / max(source_total, 1),
        member_cols_nonnull_pct=mem_nn,
        zip_cols_nonnull_pct=zip_nn,
        hub_member_id_null_pct=null_hub or 0.0,
        coverage=coverage,
    )


def main():
    entry = _load_entry()
    src = DATA / "dev_databases" / DB_ID / f"{DB_ID}.sqlite"
    rows = _row_counts(src)

    orders = dict(ORDERS)
    orders["overlap"] = _topo_sort(_greedy_overlap_order(src, rows))
    orders["simpli"] = _topo_sort(_simpli_squared_order(rows))
    orders["workload"] = _topo_sort(_workload_order())

    print(f"=== {DB_ID} join-order benchmark (FOJ + COALESCE) ===\n")
    print(f"Source rows (sum of tables): {sum(rows.values())}")
    print(f"Per-table: {rows}\n")

    results: list[Metrics] = []
    spec_current = SPECS[DB_ID]

    for name, order in orders.items():
        legal = _eel_legal(order)
        try:
            if name == "current":
                spec = spec_current
            else:
                spec = _build_spec_from_order_v2(order)
            m = _materialize_and_measure(name, spec, entry, src)
            m.eel_legal = legal
            m.order = order
            results.append(m)
        except Exception as e:
            print(f"[{name}] FAILED order={order} eel={legal}: {e}\n")

    hdr = f"{'method':<10} {'legal':^5} {'out_rows':>10} {'inflate':>8} {'mem_nn%':>8} {'zip_nn%':>8} {'hub_null%':>9}"
    print(hdr)
    print("-" * len(hdr))
    for m in sorted(results, key=lambda x: x.output_rows):
        print(
            f"{m.name:<10} {str(m.eel_legal):^5} {m.output_rows:>10} {m.inflation:>8.3f} "
            f"{m.member_cols_nonnull_pct:>8.4f} {m.zip_cols_nonnull_pct:>8.4f} {m.hub_member_id_null_pct:>9.4f}"
        )

    print("\n--- Coverage (fraction of source rows with some non-null cols in wide) ---")
    for m in results:
        cov = ", ".join(f"{k}:{v:.2f}" for k, v in sorted(m.coverage.items()) if v >= 0)
        print(f"  {m.name}: {cov}")

    if not results:
        print("\nNo successful runs.")
        return
    best = min(results, key=lambda m: (m.output_rows, m.hub_member_id_null_pct))
    print(f"\nBest (fewest rows + hub nulls): {best.name} (rows={best.output_rows})")
    cur = next(m for m in results if m.name == "current")
    old = next((m for m in results if m.name == "old"), None)
    if old:
        print(
            f"current vs old: rows {cur.output_rows} vs {old.output_rows} "
            f"({old.output_rows / max(cur.output_rows,1):.1f}x inflation if old)"
        )


if __name__ == "__main__":
    main()
