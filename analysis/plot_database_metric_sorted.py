#!/usr/bin/env python3
"""
Cross-database pooled accuracy (Qwen2.5-Coder-14B, all 18 L x S conditions),
sorted by two alternative schema metrics instead of by accuracy:
  (a) 1NF column width (docs/schema_size_1nf_2nf_3nf.md, low -> high)
  (b) attrs/entity ratio (docs/entity_attribute_analysis_nine_db.md, low -> high)

Bars stay colored by entity-count group (same legend as
database_entity_robust_2x2.png) so the sort order can be visually checked
against that grouping.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_database_metric_sorted.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
FIG_DIR = _ROOT / "docs" / "figures"

from analysis import plot_database_entity_robust as _dbr
from analysis.plot_database_entity_robust import (
    DB_SHORT,
    _apply_pub_style,
    _colors_for_dbs,
    _entity_legend_handles,
    accuracy_by_db,
    save_pub,
)

# results/*.csv no longer holds the per-condition CSVs directly (they now
# live under results/full/); point the shared accuracy_by_db() helper there.
_dbr.RESULTS = _ROOT / "results" / "full"

MODEL_DISPLAY = "Qwen2.5-Coder-14B"

# docs/schema_size_1nf_2nf_3nf.md, "1NF" section, Total cols.
NF1_COLS: Dict[str, int] = {
    "california_schools": 89,
    "debit_card_specializing": 21,
    "european_football_2": 204,
    "financial": 55,
    "formula_1": 94,
    "student_club": 48,
    "superhero": 35,
    "thrombosis_prediction": 64,
    "toxicology": 14,
}

# docs/entity_attribute_analysis_nine_db.md, Summary table, Attrs / entity.
ATTRS_PER_ENTITY: Dict[str, float] = {
    "california_schools": 86.0,
    "debit_card_specializing": 3.8,
    "european_football_2": 38.4,
    "financial": 6.3,
    "formula_1": 5.9,
    "student_club": 5.6,
    "superhero": 2.2,
    "thrombosis_prediction": 61.0,
    "toxicology": 1.7,
}


def plot_sorted_by_metric(
    ax: plt.Axes,
    acc: Dict[str, float],
    metric: Dict[str, float],
    *,
    metric_fmt: str,
    title: str,
    panel: str,
) -> None:
    dbs = sorted(acc.keys(), key=lambda d: metric[d])
    vals = [acc[d] for d in dbs]
    colors = _colors_for_dbs(dbs)

    x = np.arange(len(dbs))
    ax.bar(x, vals, width=0.72, color=colors, edgecolor="#2A2A2A", linewidth=0.35, zorder=3)
    ax.set_ylabel("Pooled accuracy (%)", fontsize=8)
    ax.set_ylim(0, max(45, max(vals) * 1.18))
    ax.set_xticks(x)
    ax.set_xticklabels([DB_SHORT[d] for d in dbs], rotation=45, ha="right", fontsize=6.5)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#C8C8C8", zorder=0)
    ax.set_axisbelow(True)
    ax.text(-0.10, 1.06, panel, transform=ax.transAxes, fontsize=11, fontweight="bold", va="top", ha="left")
    ax.set_title(title, fontsize=8, fontweight="bold", pad=6)

    ax.legend(
        handles=_entity_legend_handles(),
        loc="upper left",
        fontsize=6,
        title="Entities",
        title_fontsize=6.5,
        frameon=False,
    )
    for i, d in enumerate(dbs):
        ax.text(i, vals[i] + 1.0, metric_fmt.format(metric[d]), ha="center", va="bottom", fontsize=5.5, color="#505050")


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(_ROOT / "analysis" / ".mplconfig"))
    _apply_pub_style()

    acc_all = accuracy_by_db(None)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))

    plot_sorted_by_metric(
        axes[0],
        acc_all,
        NF1_COLS,
        metric_fmt="{:.0f} cols",
        title="Sorted by 1NF column width (low to high)",
        panel="a",
    )
    plot_sorted_by_metric(
        axes[1],
        acc_all,
        ATTRS_PER_ENTITY,
        metric_fmt="{:.1f}",
        title="Sorted by attrs/entity (low to high)",
        panel="b",
    )

    fig.suptitle(
        f"Cross-database accuracy vs. schema-width metrics ({MODEL_DISPLAY})",
        fontsize=10,
        fontweight="bold",
        y=1.03,
    )
    fig.text(
        0.5,
        -0.02,
        "Pooled accuracy: all 18 L x S conditions per database. "
        "1NF cols: docs/schema_size_1nf_2nf_3nf.md. Attrs/entity: docs/entity_attribute_analysis_nine_db.md.",
        ha="center",
        fontsize=6,
        color="#606060",
    )

    fig.subplots_adjust(wspace=0.28, top=0.86, bottom=0.28, left=0.07, right=0.98)
    out = FIG_DIR / "database_accuracy_by_schema_width_metrics"
    save_pub(fig, out)
    print(f"Wrote {out}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
