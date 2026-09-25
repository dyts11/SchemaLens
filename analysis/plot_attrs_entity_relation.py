#!/usr/bin/env python3
"""
Attrs/entity vs. pooled accuracy (Qwen2.5-Coder-14B), same 0-1 normalized
scale, one pair of bars per BIRD database, sorted by attrs/entity.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_attrs_entity_relation.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
FIG_DIR = _ROOT / "docs" / "figures"

from analysis import plot_database_entity_robust as _dbr
from analysis.plot_database_entity_robust import DB_SHORT, _apply_pub_style, accuracy_by_db, save_pub
from analysis.plot_database_metric_sorted import ATTRS_PER_ENTITY

_dbr.RESULTS = _ROOT / "results" / "full"

METRIC_COLOR = "#F1B5B5"
ACCURACY_COLOR = "#AFB8FF"
METRIC_AXIS_COLOR = "#9C3B38"
ACCURACY_AXIS_COLOR = "#33409C"


def _load_data() -> Tuple[Dict[str, float], Dict[str, float]]:
    accuracy = accuracy_by_db(None)
    return accuracy, ATTRS_PER_ENTITY


def plot_normalized_dualbar(metric: Dict[str, float], accuracy: Dict[str, float], out_stem: Path) -> None:
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(10.6, 3.0))
    ax2 = ax.twinx()

    dbs = sorted(accuracy.keys(), key=lambda d: metric[d])
    m_vals = [metric[d] for d in dbs]
    a_vals = [accuracy[d] for d in dbs]

    x = np.arange(len(dbs))
    w = 0.36

    ax2.fill_between(x - w / 2, 0, m_vals, color=METRIC_COLOR, alpha=0.22, zorder=1, linewidth=0)
    ax.fill_between(x + w / 2, 0, a_vals, color=ACCURACY_COLOR, alpha=0.22, zorder=1, linewidth=0)

    bars_m = ax2.bar(x - w / 2, m_vals, width=w, color=METRIC_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Attrs/entity", zorder=3)
    bars_a = ax.bar(x + w / 2, a_vals, width=w, color=ACCURACY_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Accuracy", zorder=3)

    x_lo, x_hi = -0.5, len(dbs) - 0.5

    m_max, a_max = max(m_vals), max(a_vals)
    for i, d in enumerate(dbs):
        ax2.text(x[i] - w / 2, m_vals[i] + m_max * 0.02, f"{metric[d]:.1f}", ha="center", va="bottom", fontsize=14, fontweight="bold", color="#2A2A2A")
        ax.text(x[i] + w / 2, a_vals[i] + a_max * 0.02, f"{accuracy[d]:.1f}%", ha="center", va="bottom", fontsize=14, fontweight="bold", color="#2A2A2A")

    ax.set_xticks(x)
    ax.set_xticklabels([DB_SHORT[d] for d in dbs], rotation=45, ha="right", fontsize=15)
    ax.set_xlim(x_lo, x_hi)

    ax.set_ylabel("Accuracy (%)", fontsize=16, color=ACCURACY_AXIS_COLOR, fontweight="bold")
    ax.tick_params(axis="y", labelsize=13, colors=ACCURACY_AXIS_COLOR)
    ax.spines["left"].set_color(ACCURACY_AXIS_COLOR)
    ax.set_ylim(0, a_max * 1.32)

    ax2.set_ylabel("Attrs / entity", fontsize=16, color=METRIC_AXIS_COLOR, fontweight="bold")
    ax2.tick_params(axis="y", labelsize=13, colors=METRIC_AXIS_COLOR)
    ax2.spines["right"].set_color(METRIC_AXIS_COLOR)
    ax2.spines["left"].set_visible(False)
    ax2.set_ylim(0, m_max * 1.32)

    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)

    ax.legend(
        handles=[bars_m, bars_a],
        loc="upper left",
        bbox_to_anchor=(-0.49, a_max * 1.22),
        bbox_transform=ax.transData,
        fontsize=14,
        frameon=False,
        handlelength=0.9,
        handleheight=0.8,
        handletextpad=0.4,
        borderaxespad=0.1,
        labelspacing=0.35,
    )

    fig.subplots_adjust(left=0.07, right=0.93, top=0.96, bottom=0.26)
    save_pub(fig, out_stem)


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(_ROOT / "analysis" / ".mplconfig"))
    accuracy, metric = _load_data()
    out_stem = FIG_DIR / "attrs_entity_normalized_dualbar"
    plot_normalized_dualbar(metric, accuracy, out_stem)
    print(f"Wrote {out_stem}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
