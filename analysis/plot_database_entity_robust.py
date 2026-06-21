#!/usr/bin/env python3
"""
2x2 database robustness figure (entity-count groups x schema conditions).

Panels:
  (a) top-left     : pooled accuracy per database (Qwen2.5-Coder-14B), coloured by entity count group
  (b) bottom-left  : L3*S3 vs L1*S3
  (c) top-right    : L3*S3 vs L3*S1
  (d) bottom-right : L1*S3 vs L6*S1

Entity groups from docs/entity_attribute_analysis_nine_db.md:
  a: 1 entity | b: 3-6 | c: 7-10 | d: >10

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_database_entity_robust.py
"""

from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "results"
FIG_DIR = _ROOT / "docs" / "figures"
MODEL = "qwen2.5-coder-14b-local"
MODEL_DISPLAY = "Qwen2.5-Coder-14B"

ENTITIES: Dict[str, int] = {
    "california_schools": 1,
    "thrombosis_prediction": 1,
    "toxicology": 3,
    "debit_card_specializing": 4,
    "european_football_2": 5,
    "financial": 7,
    "student_club": 7,
    "superhero": 8,
    "formula_1": 13,
}

DB_SHORT: Dict[str, str] = {
    "california_schools": "ca_schools",
    "debit_card_specializing": "debit_card",
    "european_football_2": "eu_football",
    "financial": "financial",
    "formula_1": "formula_1",
    "student_club": "student_club",
    "superhero": "superhero",
    "thrombosis_prediction": "thrombosis",
    "toxicology": "toxicology",
}

GROUP_LABELS = {
    "a": "1 entity",
    "b": "3-6 entities",
    "c": "7-10 entities",
    "d": ">10 entities",
}

# Distinct hues: group a (1 entity) vs b (3-6) are easy to tell apart at a glance.
GROUP_COLORS = {
    "a": "#7EC8E8",  # light cyan
    "b": "#E8944A",  # warm orange (3-6 entities)
    "c": "#5C6FAE",  # medium blue (7-10)
    "d": "#2E3358",  # dark navy (>10)
}

CONDITION_HATCH = "///"
CONDITION_LEGEND_GRAY = "#9A9A9A"
CONDITION_RE = re.compile(r"__L(\d+)S(\d+)\.csv$")


def _entity_group(n: int) -> str:
    if n == 1:
        return "a"
    if 3 <= n <= 6:
        return "b"
    if 7 <= n <= 10:
        return "c"
    return "d"


def _entity_legend_handles() -> list:
    return [
        mpl.patches.Patch(
            facecolor=GROUP_COLORS[g],
            edgecolor="#2A2A2A",
            linewidth=0.35,
            label=GROUP_LABELS[g],
        )
        for g in ["a", "b", "c", "d"]
    ]


def _colors_for_dbs(dbs: List[str]) -> List[str]:
    return [GROUP_COLORS[_entity_group(ENTITIES[d])] for d in dbs]


def _apply_pub_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )


def save_pub(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{stem}.svg", bbox_inches="tight")
    fig.savefig(f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


def accuracy_by_db(condition: Tuple[int, int] | None = None) -> Dict[str, float]:
    """Per-db accuracy (%). condition=None pools all L x S cells."""
    per_db: Dict[str, List[bool]] = defaultdict(list)
    for path in sorted(RESULTS.glob(f"{MODEL}__L*S*.csv")):
        m = CONDITION_RE.search(path.name)
        if not m:
            continue
        L, S = int(m.group(1)), int(m.group(2))
        if condition is not None and (L, S) != condition:
            continue
        for row in csv.DictReader(path.open(encoding="utf-8")):
            ok = row.get("correct", "").lower() in ("true", "1", "yes")
            per_db[row["db_id"]].append(ok)
    return {db: 100.0 * sum(v) / len(v) for db, v in per_db.items()}


def _panel_label(ax: plt.Axes, letter: str) -> None:
    ax.text(
        -0.12,
        1.06,
        letter,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
        ha="left",
    )


def plot_pooled_accuracy(ax: plt.Axes, acc: Dict[str, float]) -> None:
    dbs = sorted(acc.keys(), key=lambda d: acc[d], reverse=True)
    vals = [acc[d] for d in dbs]
    colors = _colors_for_dbs(dbs)

    x = np.arange(len(dbs))
    ax.bar(x, vals, width=0.72, color=colors, edgecolor="#2A2A2A", linewidth=0.35, zorder=3)
    ax.set_ylabel("Pooled accuracy (%)", fontsize=8)
    ax.set_ylim(0, max(45, max(vals) * 1.15))
    ax.set_xticks(x)
    ax.set_xticklabels([DB_SHORT[d] for d in dbs], rotation=45, ha="right", fontsize=6.5)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#C8C8C8", zorder=0)
    ax.set_axisbelow(True)
    _panel_label(ax, "a")
    ax.set_title("Cross-database accuracy (sorted)", fontsize=8, fontweight="bold", pad=6)

    ax.legend(
        handles=_entity_legend_handles(),
        loc="upper right",
        fontsize=6,
        title="Entities",
        title_fontsize=6.5,
        frameon=False,
    )
    for i, (d, v) in enumerate(zip(dbs, vals)):
        ax.text(i, v + 1.0, f"{ENTITIES[d]}", ha="center", va="bottom", fontsize=5.5, color="#505050")


def plot_comparison(
    ax: plt.Axes,
    acc_a: Dict[str, float],
    acc_b: Dict[str, float],
    label_a: str,
    label_b: str,
    panel: str,
    title: str,
    *,
    sort_by_gap: bool = True,
) -> None:
    dbs = sorted(set(acc_a) & set(acc_b))
    gaps = {d: acc_a[d] - acc_b[d] for d in dbs}
    if sort_by_gap:
        dbs = sorted(dbs, key=lambda d: gaps[d], reverse=True)

    x = np.arange(len(dbs))
    w = 0.36
    va = [acc_a[d] for d in dbs]
    vb = [acc_b[d] for d in dbs]
    colors = _colors_for_dbs(dbs)

    ax.bar(
        x - w / 2,
        va,
        width=w,
        color=colors,
        edgecolor="#2A2A2A",
        linewidth=0.35,
        zorder=3,
    )
    ax.bar(
        x + w / 2,
        vb,
        width=w,
        color=colors,
        hatch=CONDITION_HATCH,
        edgecolor="#2A2A2A",
        linewidth=0.35,
        zorder=3,
    )

    ax.set_ylabel("EX (%)", fontsize=8)
    ax.set_ylim(0, max(45, max(max(va), max(vb)) * 1.2))
    ax.set_xticks(x)
    ax.set_xticklabels([DB_SHORT[d] for d in dbs], rotation=45, ha="right", fontsize=6.5)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#C8C8C8", zorder=0)
    ax.set_axisbelow(True)
    _panel_label(ax, panel)
    ax.set_title(title, fontsize=8, fontweight="bold", pad=6)

    for i, d in enumerate(dbs):
        g = gaps[d]
        if abs(g) >= 0.5:
            ax.text(
                x[i] - w / 2,
                va[i] + 1.2,
                f"{g:+.1f}",
                ha="center",
                va="bottom",
                fontsize=6,
                fontweight="bold",
                color="#1A1A1A",
            )

    leg_ent = ax.legend(
        handles=_entity_legend_handles(),
        loc="upper right",
        fontsize=5.5,
        title="Entities",
        title_fontsize=6,
        frameon=False,
    )
    ax.add_artist(leg_ent)
    ax.legend(
        handles=[
            mpl.patches.Patch(
                facecolor=CONDITION_LEGEND_GRAY,
                edgecolor="#2A2A2A",
                linewidth=0.35,
                label=label_a,
            ),
            mpl.patches.Patch(
                facecolor=CONDITION_LEGEND_GRAY,
                edgecolor="#2A2A2A",
                linewidth=0.35,
                hatch=CONDITION_HATCH,
                label=label_b,
            ),
        ],
        loc="upper left",
        fontsize=6,
        title="Condition",
        title_fontsize=6,
        frameon=False,
    )


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(_ROOT / "analysis" / ".mplconfig"))
    _apply_pub_style()

    acc_all = accuracy_by_db(None)
    acc_l3s3 = accuracy_by_db((3, 3))
    acc_l1s3 = accuracy_by_db((1, 3))
    acc_l3s1 = accuracy_by_db((3, 1))
    acc_l6s1 = accuracy_by_db((6, 1))

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.0))

    plot_pooled_accuracy(axes[0, 0], acc_all)
    plot_comparison(
        axes[0, 1],
        acc_l3s3,
        acc_l3s1,
        r"$L_3 \cdot S_3$",
        r"$L_3 \cdot S_1$",
        "c",
        r"Semantic gap at L3 ($S_3$ vs $S_1$)",
    )
    plot_comparison(
        axes[1, 0],
        acc_l3s3,
        acc_l1s3,
        r"$L_3 \cdot S_3$",
        r"$L_1 \cdot S_3$",
        "b",
        r"Structure gap at S3 ($L_3$ vs $L_1$)",
    )
    plot_comparison(
        axes[1, 1],
        acc_l1s3,
        acc_l6s1,
        r"$L_1 \cdot S_3$",
        r"$L_6 \cdot S_1$",
        "d",
        r"Substitution gap ($L_1 \cdot S_3$ vs $L_6 \cdot S_1$)",
    )

    fig.suptitle(
        f"Database-level execution accuracy by entity count ({MODEL_DISPLAY})",
        fontsize=10,
        fontweight="bold",
        y=1.02,
    )
    fig.text(
        0.5,
        0.01,
        "Pooled accuracy (a): all 18 conditions per database. Comparison panels: single cell per database. "
        "Entity groups from entity_attribute_analysis_nine_db.md.",
        ha="center",
        fontsize=6,
        color="#606060",
    )

    fig.subplots_adjust(hspace=0.52, wspace=0.32, top=0.92, bottom=0.12, left=0.08, right=0.98)
    out = FIG_DIR / "database_entity_robust_2x2"
    save_pub(fig, out)
    print(f"Wrote {out}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
