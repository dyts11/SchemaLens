#!/usr/bin/env python3
"""
Placeholder figures for case studies §12–§14 (experiment_design.md).

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_case_study_templates.py
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

FIG_DIR = Path(__file__).resolve().parent.parent / "docs" / "figures"

SIZE_BUCKETS = ["small", "medium", "large"]
STRUCT_LINES = ["L3", "L4", "L5"]
LINE_COLORS = ["#7884B4", "#B4C0E4", "#484878"]

# §12: rows = L3/L4/L5, cols = size bucket; accuracy in [0,1] or use 0–100 in plot
COMPLEXITY_ACCURACY = np.full((3, 3), np.nan)

# §13: filter-query subset, best condition L5·S3 vs L5·S3+values
VALUE_NO_HINTS = np.full(3, np.nan)
VALUE_WITH_HINTS = np.full(3, np.nan)
DIFF_LABELS = ["simple", "moderate", "challenging"]

# §14: uniform S1/S2/S3 + Mix-A + Mix-B at L5
MIX_LABELS = ["S1\nuniform", "S2\nuniform", "S3\nuniform", "Mix-A\nS2+S3", "Mix-B\nS1+S3"]
MIX_ACCURACY = np.full(5, np.nan)
USE_PERCENT = True  # True: y-axis 0–100; False: 0–1


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


def _scale(y: np.ndarray) -> np.ndarray:
    if not USE_PERCENT:
        return y
    return np.where(np.isnan(y), np.nan, y * 100.0)


def _ylim() -> tuple[float, float]:
    return (0, 100) if USE_PERCENT else (0, 1.05)


def _ylabel() -> str:
    return "Execution accuracy (%)" if USE_PERCENT else "Execution accuracy"


def save_pub(fig: plt.Figure, stem: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    base = FIG_DIR / stem
    fig.savefig(f"{base}.svg", bbox_inches="tight")
    fig.savefig(f"{base}.pdf", bbox_inches="tight")
    fig.savefig(f"{base}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_schema_complexity() -> None:
    """§12 — L3 / L4 / L5 lines over schema size buckets (S3 fixed)."""
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(4.0, 2.9))
    x = np.arange(len(SIZE_BUCKETS))

    for i, (label, color) in enumerate(zip(STRUCT_LINES, LINE_COLORS)):
        y = _scale(COMPLEXITY_ACCURACY[i])
        ax.plot(
            x,
            y,
            color=color,
            linewidth=1.8,
            marker="o",
            markersize=5,
            markerfacecolor=color,
            markeredgecolor="#272727",
            markeredgewidth=0.4,
            label=label,
        )
        for xi, val in zip(x, y):
            txt = "—" if np.isnan(val) else f"{val:.0f}" if USE_PERCENT else f"{val:.2f}"
            ax.annotate(
                txt,
                (xi, val if not np.isnan(val) else 0),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                fontsize=5.5,
                color="#606060",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(SIZE_BUCKETS, fontsize=7)
    ax.set_xlabel("Schema size bucket (by table count)", fontsize=7.5)
    ax.set_ylabel(_ylabel(), fontsize=7.5)
    ax.set_ylim(*_ylim())
    ax.set_title(
        "Schema complexity moderation (S3 fixed)\nL3 / L4 / L5 · Gemini 2.5 Flash",
        fontsize=8,
        fontweight="bold",
        pad=6,
    )
    ax.legend(title="Structural", fontsize=6, title_fontsize=6.5, loc="best")
    fig.tight_layout()
    save_pub(fig, "casestudy_schema_complexity")


def plot_value_examples() -> None:
    """§13 — grouped bars: without vs with value hints, Δ on with bar."""
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(4.2, 2.9))
    n = len(DIFF_LABELS)
    x = np.arange(n)
    width = 0.34

    no_h = _scale(VALUE_NO_HINTS)
    with_h = _scale(VALUE_WITH_HINTS)
    h_no = np.where(np.isnan(no_h), 0.0, no_h)
    h_with = np.where(np.isnan(with_h), 0.0, with_h)

    bars_no = ax.bar(
        x - width / 2,
        h_no,
        width,
        label="Without value hints",
        color="#E4E4F0",
        edgecolor="#484878",
        linewidth=0.6,
    )
    bars_with = ax.bar(
        x + width / 2,
        h_with,
        width,
        label="With value hints",
        color="#7884B4",
        edgecolor="#484878",
        linewidth=0.6,
    )

    for i in range(n):
        if not np.isnan(no_h[i]):
            ax.text(
                bars_no[i].get_x() + bars_no[i].get_width() / 2,
                bars_no[i].get_height() + 1.2,
                f"{no_h[i]:.0f}" if USE_PERCENT else f"{no_h[i]:.2f}",
                ha="center",
                va="bottom",
                fontsize=6,
                color="#484878",
            )
        if not np.isnan(with_h[i]) and not np.isnan(no_h[i]):
            delta = with_h[i] - no_h[i]
            sign = "+" if delta >= 0 else ""
            dtxt = f"{sign}{delta:.0f}" if USE_PERCENT else f"{sign}{delta:.2f}"
            ax.text(
                bars_with[i].get_x() + bars_with[i].get_width() / 2,
                bars_with[i].get_height() + 1.2,
                f"{with_h[i]:.0f}\nΔ{dtxt}" if USE_PERCENT else f"{with_h[i]:.2f}\nΔ{dtxt}",
                ha="center",
                va="bottom",
                fontsize=6,
                color="#484878",
                fontweight="bold",
            )
        elif not np.isnan(with_h[i]):
            ax.text(
                bars_with[i].get_x() + bars_with[i].get_width() / 2,
                bars_with[i].get_height() + 1.2,
                "—",
                ha="center",
                va="bottom",
                fontsize=6,
                color="#484878",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(DIFF_LABELS, fontsize=7)
    ax.set_xlabel("Difficulty tier", fontsize=7.5)
    ax.set_ylabel(_ylabel(), fontsize=7.5)
    ax.set_ylim(*_ylim())
    ax.set_title(
        "Value examples on filter queries (L5·S3)\nGemini 2.5 Flash",
        fontsize=8,
        fontweight="bold",
        pad=6,
    )
    ax.legend(fontsize=6, loc="upper right")
    fig.tight_layout()
    save_pub(fig, "casestudy_value_examples")


def plot_mixed_semantics() -> None:
    """§14 — five bars: S1, S2, S3, Mix-A, Mix-B at L5."""
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(4.8, 2.9))
    x = np.arange(len(MIX_LABELS))
    y = _scale(MIX_ACCURACY)
    heights = np.where(np.isnan(y), 0.0, y)

    bars = ax.bar(
        x,
        heights,
        color="#B4C0E4",
        edgecolor="#484878",
        linewidth=0.6,
        width=0.72,
    )
    for bar, val in zip(bars, y):
        label = "—" if np.isnan(val) else (f"{val:.0f}" if USE_PERCENT else f"{val:.2f}")
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.5,
            label,
            ha="center",
            va="bottom",
            fontsize=6.5,
            color="#484878",
            fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(MIX_LABELS, fontsize=6.5)
    ax.set_xlabel("Semantic condition", fontsize=7.5)
    ax.set_ylabel(_ylabel(), fontsize=7.5)
    ax.set_ylim(*_ylim())
    ax.set_title(
        "Mixed vs uniform semantic levels (L5 fixed)\nGemini 2.5 Flash",
        fontsize=8,
        fontweight="bold",
        pad=6,
    )
    fig.tight_layout()
    save_pub(fig, "casestudy_mixed_semantics")


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))
    plot_schema_complexity()
    plot_value_examples()
    plot_mixed_semantics()
    print(f"Wrote case-study figures under {FIG_DIR}/")


if __name__ == "__main__":
    main()
