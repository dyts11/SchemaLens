#!/usr/bin/env python3
"""
Combined two-panel figure: top = attrs/entity vs. L3*S3 - L1*S3 structure
gain (dual real-unit axes, zero-aligned), bottom = attrs/entity vs. pooled
accuracy (dual real-unit axes). Same 9 BIRD databases, same sort order
(ascending attrs/entity) in both panels, sharing the x-axis.

Attrs/entity sits on the left axis in both panels (consistent scale/side);
the outcome (accuracy, then gain) sits on the right axis.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_attrs_entity_combined.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Sequence

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
GAIN_COLOR = "#C2E68C"
METRIC_AXIS_COLOR = "#9C3B38"
ACCURACY_AXIS_COLOR = "#33409C"
GAIN_AXIS_COLOR = "#4F7A2A"


def _load_data():
    accuracy = accuracy_by_db(None)
    acc_l3s3 = accuracy_by_db((3, 3))
    acc_l1s3 = accuracy_by_db((1, 3))
    gain = {d: acc_l3s3[d] - acc_l1s3[d] for d in acc_l3s3}
    return ATTRS_PER_ENTITY, accuracy, gain


NOISE_DB = "toxicology"


def _trend(
    x: np.ndarray,
    y: Sequence[float],
    degree: int = 1,
    exclude: Sequence[int] | None = None,
    floor: float | None = 0.0,
) -> np.ndarray:
    """Least-squares trend line through (x, y): degree=1 -> straight (triangle-shaped)
    background, degree=2 -> a gently curved trend. Used for the shaded background
    instead of the raw values so the wedge reflects the overall direction rather than
    zig-zagging through each bar's exact height. `exclude` drops noisy points (indices
    into x/y) from the fit itself; the returned trend is still evaluated at every x so
    the excluded bar keeps a background value, it just doesn't pull on the line's slope.
    `floor` clamps the fitted line so it never dips below that value (default 0, since
    these backgrounds sit over non-negative axes)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if exclude:
        mask = np.ones(len(x), dtype=bool)
        mask[list(exclude)] = False
        coeffs = np.polyfit(x[mask], y[mask], degree)
    else:
        coeffs = np.polyfit(x, y, degree)
    fitted = np.polyval(coeffs, x)
    if floor is not None:
        fitted = np.maximum(fitted, floor)
    return fitted


def _noise_idx(dbs: Sequence[str]) -> List[int]:
    return [i for i, d in enumerate(dbs) if d == NOISE_DB]


LABEL_FONTSIZE = 29
WITHIN_CAT_STAGGER_PT = 22.0  # extra lift for the right-hand (outcome) label vs. the left-hand (metric) label
CROSS_CAT_STAGGER_PT = 38.0  # extra lift on odd categories, only for bars short enough to risk a same-height clash
SHORT_BAR_FRACTION = 0.18  # below this fraction of the axis max, a bar's label is "short" and needs the cross-category lift


def _short_lift(val: float, axis_max: float, i: int) -> float:
    """Extra lift for bars short enough that their label could sit at the same height as a
    neighboring category's label; tall bars already clear their neighbors on height alone,
    so leave them at the default offset instead of pushing them far from their own bar."""
    if axis_max and abs(val) / axis_max < SHORT_BAR_FRACTION:
        return CROSS_CAT_STAGGER_PT if i % 2 == 1 else 0.0
    return 0.0


BOUNDARY_FRACTION_GAP = 0.15
BOUNDARY_LIFT_PT = 42.0


def _boundary_lift(right_val: float, right_max: float, left_val: float, left_max: float) -> float:
    """Extra lift for a category's right-hand (outcome) label when the *next* category's
    left-hand (metric) label sits at a similar fraction of its own axis — twin axes with
    different scales can otherwise place two unrelated labels at the same pixel height
    right where their categories meet."""
    if not right_max or not left_max:
        return 0.0
    if abs(abs(right_val) / right_max - abs(left_val) / left_max) < BOUNDARY_FRACTION_GAP:
        return BOUNDARY_LIFT_PT
    return 0.0


def _label(ax: plt.Axes, x: float, y: float, text: str, *, extra_pt: float = 0.0, va: str = "bottom") -> None:
    sign = 1 if va == "bottom" else -1
    ax.annotate(
        text,
        (x, y),
        xytext=(0, sign * (6 + extra_pt)),
        textcoords="offset points",
        ha="center",
        va=va,
        fontsize=LABEL_FONTSIZE,
        fontweight="bold",
        color="#2A2A2A",
    )


def _draw_accuracy_panel(ax: plt.Axes, metric: Dict[str, float], accuracy: Dict[str, float], dbs: Sequence[str]) -> None:
    ax2 = ax.twinx()
    m_vals = [metric[d] for d in dbs]
    a_vals = [accuracy[d] for d in dbs]
    x = np.arange(len(dbs))
    w = 0.36
    off = w / 2

    noise = _noise_idx(dbs)
    m_trend = _trend(x, m_vals, exclude=noise)
    a_trend = _trend(x, a_vals, exclude=noise)
    ax.fill_between(x - off, 0, m_trend, color=METRIC_COLOR, alpha=0.22, zorder=1, linewidth=0)
    ax2.fill_between(x + off, 0, a_trend, color=ACCURACY_COLOR, alpha=0.22, zorder=1, linewidth=0)

    bars_m = ax.bar(x - off, m_vals, width=w, color=METRIC_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Attrs/entity", zorder=3)
    bars_a = ax2.bar(x + off, a_vals, width=w, color=ACCURACY_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Accuracy", zorder=3)

    m_max, a_max = max(m_vals), max(a_vals)
    for i in range(len(dbs)):
        _label(ax, x[i] - off, m_vals[i], f"{m_vals[i]:.1f}", extra_pt=_short_lift(m_vals[i], m_max, i))
        boundary = _boundary_lift(a_vals[i], a_max, m_vals[i + 1], m_max) if i + 1 < len(dbs) else 0.0
        _label(ax2, x[i] + off, a_vals[i], f"{a_vals[i]:.1f}%", extra_pt=_short_lift(a_vals[i], a_max, i) + WITHIN_CAT_STAGGER_PT + boundary)

    m_top, a_top = m_max * 1.15, a_max * 1.32
    ax.set_ylabel("Attrs / entity", fontsize=32, color=METRIC_AXIS_COLOR, fontweight="bold")
    ax.tick_params(axis="y", labelsize=26, colors=METRIC_AXIS_COLOR)
    ax.spines["left"].set_color(METRIC_AXIS_COLOR)
    ax.set_ylim(0, m_top)

    ax2.set_ylabel("Accuracy (%)", fontsize=32, color=ACCURACY_AXIS_COLOR, fontweight="bold")
    ax2.tick_params(axis="y", labelsize=26, colors=ACCURACY_AXIS_COLOR)
    ax2.spines["right"].set_color(ACCURACY_AXIS_COLOR)
    ax2.spines["left"].set_visible(False)
    ax2.set_ylim(0, a_top)

    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)

    ax.legend(
        handles=[bars_m, bars_a],
        loc="upper left",
        bbox_to_anchor=(-0.49, m_top * 0.97),
        bbox_transform=ax.transData,
        fontsize=27,
        frameon=False,
        handlelength=0.9,
        handleheight=0.8,
        handletextpad=0.4,
        borderaxespad=0.1,
        labelspacing=0.35,
    )


def _draw_gain_panel(ax: plt.Axes, metric: Dict[str, float], gain: Dict[str, float], dbs: Sequence[str]) -> None:
    ax2 = ax.twinx()
    m_vals = [metric[d] for d in dbs]
    g_vals = [gain[d] for d in dbs]
    x = np.arange(len(dbs))
    w = 0.36
    off = w / 2

    noise = _noise_idx(dbs)
    m_trend = _trend(x, m_vals, exclude=noise)
    g_trend = _trend(x, g_vals, exclude=noise)
    ax.fill_between(x - off, 0, m_trend, color=METRIC_COLOR, alpha=0.22, zorder=1, linewidth=0)
    ax2.fill_between(x + off, 0, g_trend, color=GAIN_COLOR, alpha=0.22, zorder=1, linewidth=0)

    bars_m = ax.bar(x - off, m_vals, width=w, color=METRIC_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Attrs/entity", zorder=3)
    bars_g = ax2.bar(x + off, g_vals, width=w, color=GAIN_COLOR, edgecolor="#2A2A2A", linewidth=0.35, label="Structure gain", zorder=3)

    m_max, g_max, g_min = max(m_vals), max(g_vals), min(g_vals)
    g_abs_max = max(g_max, abs(g_min))
    for i in range(len(dbs)):
        _label(ax, x[i] - off, m_vals[i], f"{m_vals[i]:.1f}", extra_pt=_short_lift(m_vals[i], m_max, i))
        gv = g_vals[i]
        boundary = _boundary_lift(gv, g_abs_max, m_vals[i + 1], m_max) if i + 1 < len(dbs) else 0.0
        g_extra = _short_lift(gv, g_abs_max, i) + WITHIN_CAT_STAGGER_PT + boundary
        if gv >= 0:
            _label(ax2, x[i] + off, gv, f"{gv:+.1f}%", extra_pt=g_extra)
        else:
            _label(ax2, x[i] + off, 0, f"{gv:+.1f}%", extra_pt=g_extra)

    below_frac = 0.22
    ratio = below_frac / (1 - below_frac)
    m_top = m_max * 1.15
    g_top = g_max * 1.15

    ax.set_ylabel("Attrs / entity", fontsize=32, color=METRIC_AXIS_COLOR, fontweight="bold")
    ax.tick_params(axis="y", labelsize=26, colors=METRIC_AXIS_COLOR)
    ax.spines["left"].set_color(METRIC_AXIS_COLOR)
    ax.set_ylim(-ratio * m_top, m_top)
    ax.set_yticks(np.arange(0, m_top, 20))

    ax2.set_ylabel("Structure gain (%)", fontsize=32, color=GAIN_AXIS_COLOR, fontweight="bold")
    ax2.tick_params(axis="y", labelsize=26, colors=GAIN_AXIS_COLOR)
    ax2.spines["right"].set_color(GAIN_AXIS_COLOR)
    ax2.set_ylim(-ratio * g_top, g_top)
    ax2.spines["left"].set_visible(False)
    ax.axhline(0, color="#2A2A2A", linewidth=0.7, zorder=2)

    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
    ax2.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)

    ax.legend(
        handles=[bars_m, bars_g],
        loc="upper left",
        bbox_to_anchor=(-0.49, m_top * 0.97),
        bbox_transform=ax.transData,
        fontsize=27,
        frameon=False,
        handlelength=0.9,
        handleheight=0.8,
        handletextpad=0.4,
        borderaxespad=0.1,
        labelspacing=0.35,
    )


def plot_combined(metric: Dict[str, float], accuracy: Dict[str, float], gain: Dict[str, float], out_stem: Path) -> None:
    _apply_pub_style()
    dbs = sorted(accuracy.keys(), key=lambda d: metric[d])
    x = np.arange(len(dbs))

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(16.0, 8.5), sharex=True, gridspec_kw={"hspace": 0.12})

    _draw_gain_panel(ax_top, metric, gain, dbs)
    _draw_accuracy_panel(ax_bot, metric, accuracy, dbs)

    ax_bot.set_xticks(x)
    ax_bot.set_xticklabels([DB_SHORT[d] for d in dbs], rotation=45, ha="right", fontsize=29)
    ax_bot.set_xlim(-0.5, len(dbs) - 0.5)

    fig.subplots_adjust(left=0.05, right=0.96, top=0.995, bottom=0.14, hspace=0.06)
    save_pub(fig, out_stem)


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(_ROOT / "analysis" / ".mplconfig"))
    metric, accuracy, gain = _load_data()
    out_stem = FIG_DIR / "attrs_entity_accuracy_gain_combined"
    plot_combined(metric, accuracy, gain, out_stem)
    print(f"Wrote {out_stem}.{{svg,pdf,png}}")


if __name__ == "__main__":
    main()
