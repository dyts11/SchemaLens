#!/usr/bin/env python3
"""
Attrs/entity vs. L3*S3 - L1*S3 structure gain (Qwen2.5-Coder-14B), twin
real-unit axes (attrs/entity left, gain right, zero-aligned), one pair of
bars per BIRD database, sorted by attrs/entity.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_attrs_entity_gain_relation.py
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
GAIN_COLOR = "#C2E68C"
METRIC_AXIS_COLOR = "#9C3B38"
GAIN_AXIS_COLOR = "#4F7A2A"


def _load_data() -> Tuple[Dict[str, float], Dict[str, float]]:
    acc_l3s3 = accuracy_by_db((3, 3))
    acc_l1s3 = accuracy_by_db((1, 3))
    gain = {d: acc_l3s3[d] - acc_l1s3[d] for d in acc_l3s3}
    return ATTRS_PER_ENTITY, gain


def plot_dualaxis_bar(metric: Dict[str, float], gain: Dict[str, float], out_stem: Path) -> None:
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(10.6, 3.4))
    ax2 = ax.twinx()

    dbs = sorted(gain.keys(), key=lambda d: metric[d])
    m_vals = [metric[d] for d in dbs]
    g_vals = [gain[d] for d in dbs]
    x = np.arange(len(dbs))
    w = 0.36

    ax.fill_between(x - w / 2, 0, m_vals, color=METRIC_COLOR, alpha=0.22, zorder=1, linewidth=0)
    ax2.fill_between(x + w / 2, 0, g_vals, color=GAIN_COLOR, alpha=0.22, zorder=1, linewidth=0)

    bars_m = ax.bar(x - w / 2, m_vals, width=w, color=METRIC_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Attrs/entity", zorder=3)
    bars_g = ax2.bar(x + w / 2, g_vals, width=w, color=GAIN_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Structure gain", zorder=3)

    m_max, g_max, g_min = max(m_vals), max(g_vals), min(g_vals)
    for i, d in enumerate(dbs):
        ax.text(x[i] - w / 2, m_vals[i] + m_max * 0.02, f"{metric[d]:.1f}", ha="center", va="bottom", fontsize=11, fontweight="bold", color="#2A2A2A")
        gv = g_vals[i]
        if gv >= 0:
            ax2.text(x[i] + w / 2, gv + g_max * 0.03, f"{gv:+.1f}%", ha="center", va="bottom", fontsize=11, fontweight="bold", color="#2A2A2A")
        else:
            ax2.text(x[i] + w / 2, g_max * 0.03, f"{gv:+.1f}%", ha="center", va="bottom", fontsize=11, fontweight="bold", color="#2A2A2A")

    ax.set_xticks(x)
    ax.set_xticklabels([DB_SHORT[d] for d in dbs], rotation=45, ha="right", fontsize=12)
    ax.set_xlim(-0.5, len(dbs) - 0.5)

    # Align both axes' zero baselines (same fraction of plot height below 0)
    # so the shared zero line is valid for both series, not just the gain axis.
    below_frac = 0.22
    ratio = below_frac / (1 - below_frac)
    m_top = m_max * 1.15
    g_top = g_max * 1.15

    ax.set_ylabel("Attrs / entity", fontsize=12, color=METRIC_AXIS_COLOR, fontweight="bold")
    ax.tick_params(axis="y", labelsize=10, colors=METRIC_AXIS_COLOR)
    ax.spines["left"].set_color(METRIC_AXIS_COLOR)
    ax.set_ylim(-ratio * m_top, m_top)
    ax.set_yticks(np.arange(0, m_top, 20))

    ax2.set_ylabel("Structure gain (%)", fontsize=12, color=GAIN_AXIS_COLOR, fontweight="bold")
    ax2.tick_params(axis="y", labelsize=10, colors=GAIN_AXIS_COLOR)
    ax2.spines["right"].set_color(GAIN_AXIS_COLOR)
    ax2.set_ylim(-ratio * g_top, g_top)
    ax.axhline(0, color="#2A2A2A", linewidth=0.7, zorder=2)

    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)

    ax.legend(handles=[bars_m, bars_g], loc="upper left", bbox_to_anchor=(-0.49, m_top * 0.97), bbox_transform=ax.transData, fontsize=11.5, frameon=False, handlelength=0.9, handleheight=0.8, handletextpad=0.4, borderaxespad=0.1, labelspacing=0.35)

    fig.subplots_adjust(left=0.06, right=0.93, top=0.96, bottom=0.24)
    save_pub(fig, out_stem)


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(_ROOT / "analysis" / ".mplconfig"))
    metric, gain = _load_data()
    out_stem = FIG_DIR / "attrs_entity_gain_dualaxis_bar"
    plot_dualaxis_bar(metric, gain, out_stem)
    print(f"Wrote {out_stem}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
