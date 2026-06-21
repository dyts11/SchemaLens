#!/usr/bin/env python3
"""
All-models grouped bar chart: execution accuracy by structural × semantic condition.

Two-row layout (readable width), 6 models by default:
  - Row 1: Gemini + Qwen 32B, 14B
  - Row 2: Qwen 7B, 3B, Phi-4
  (Excluded from chart: Qwen 1.5B/0.5B, OLMo-2; incomplete: Llama, Gemini 3.5)
  Within each row: model blocks → L1–L6 clusters → S1/S2/S3 bars.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_all_models_grouped_bars.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.bootstrap_accuracy_ci import bootstrap_accuracy_ci, load_correct_flags

FIG_DIR = _ROOT / "docs" / "figures"
CONDITION_RE = re.compile(r"__L(\d+)S(\d+)\.csv$", re.IGNORECASE)

SEM_COLORS = ["#D4D8E8", "#9AA4C8", "#484878"]
SEM_LEGEND = ["S1 (anonymous)", "S2 (abbreviated)", "S3 (descriptive)"]
STRUCT_TICKS = [f"L{i}" for i in range(1, 7)]

ROW_SPLITS: Tuple[int, ...] = (3, 3)  # 6 models → two rows

MODEL_ORDER: Sequence[str] = (
    "gemini-2.5-flash",
    "qwen2.5-coder-32b-local",
    "qwen2.5-coder-14b-local",
    "qwen2.5-coder-7b-local",
    "qwen2.5-coder-3b-local",
    "phi-4-local",
)

# Incomplete runs + models omitted from this figure
EXCLUDE_MODELS = frozenset(
    {
        "llama-3.3-70b-or",
        "gemini-3.5-flash",
        "qwen2.5-coder-1.5b-local",
        "qwen2.5-coder-0.5b-local",
        "olmo-2-13b-local",
    }
)

DISPLAY_NAMES: Dict[str, str] = {
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "qwen2.5-coder-32b-local": "Qwen2.5-Coder 32B",
    "qwen2.5-coder-14b-local": "Qwen2.5-Coder 14B",
    "qwen2.5-coder-7b-local": "Qwen2.5-Coder 7B",
    "qwen2.5-coder-3b-local": "Qwen2.5-Coder 3B",
    "qwen2.5-coder-1.5b-local": "Qwen2.5-Coder 1.5B",
    "qwen2.5-coder-0.5b-local": "Qwen2.5-Coder 0.5B",
    "phi-4-local": "Phi-4",
    "olmo-2-13b-local": "OLMo-2 13B",
}


@dataclass
class PanelLayout:
    positions: List[float]
    heights: List[float]
    yerr: List[float]
    colors: List[str]
    l_tick_x: List[float]
    l_tick_lbl: List[str]
    model_centers: List[float]
    model_labels: List[str]
    model_boundaries: List[float]
    x_max: float


# Typography (larger than default pub 7pt for readability in wide bar chart)
FONT_BASE = 9
FONT_TICK = 8.5
FONT_BAR_LABEL = 9
FONT_MODEL = 9
FONT_TITLE = 11
FONT_LEGEND = 12
FONT_NOTE = 10
LABEL_PAD_ABOVE_CI = 0.022  # data coords above error-bar cap


def _apply_pub_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": FONT_BASE,
            "axes.labelsize": FONT_BASE,
            "xtick.labelsize": FONT_TICK,
            "ytick.labelsize": FONT_TICK,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )


def save_pub(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    pad = {"pad_inches": 0.08}
    fig.savefig(f"{stem}.svg", bbox_inches="tight", **pad)
    fig.savefig(f"{stem}.pdf", bbox_inches="tight", **pad)
    fig.savefig(f"{stem}.png", dpi=600, bbox_inches="tight", **pad)
    plt.close(fig)


def _format_bar_label(acc: float) -> str:
    if acc >= 0.995:
        return "1"
    if acc < 0.1:
        return f"{acc:.2f}".lstrip("0")
    return f"{acc:.2f}".lstrip("0")


def discover_complete_models(results_dir: Path) -> List[str]:
    found: Dict[str, set] = {}
    for path in results_dir.glob("*__L*S*.csv"):
        m = CONDITION_RE.search(path.name)
        if not m:
            continue
        model = path.name.split("__", 1)[0]
        if model in EXCLUDE_MODELS:
            continue
        found.setdefault(model, set()).add((int(m.group(1)), int(m.group(2))))

    complete = [m for m in MODEL_ORDER if m in found and len(found[m]) == 18]
    for m in sorted(found):
        if len(found[m]) == 18 and m not in complete:
            complete.append(m)
    return complete


def load_cell_stats(
    results_dir: Path,
    model: str,
    *,
    n_bootstrap: int,
    seed: int,
) -> Tuple[np.ndarray, np.ndarray]:
    acc = np.full((6, 3), np.nan)
    margin = np.full((6, 3), np.nan)
    pattern = f"{model.replace('/', '-')}__L*S*.csv"
    for path in sorted(results_dir.glob(pattern)):
        m = CONDITION_RE.search(path.name)
        if not m:
            continue
        sl, sem = int(m.group(1)), int(m.group(2))
        flags = load_correct_flags(path)
        res = bootstrap_accuracy_ci(flags, n_bootstrap=n_bootstrap, seed=seed)
        acc[sl - 1, sem - 1] = res.accuracy
        margin[sl - 1, sem - 1] = res.margin
    if np.isnan(acc).any():
        missing = [
            f"L{sl}S{sem}"
            for sl in range(1, 7)
            for sem in range(1, 4)
            if np.isnan(acc[sl - 1, sem - 1])
        ]
        raise ValueError(f"Incomplete grid for {model}: {', '.join(missing)}")
    return acc, margin


def build_panel_layout(
    model_stats: List[Tuple[str, np.ndarray, np.ndarray]],
    *,
    bar_width: float = 0.22,
    l_gap: float = 0.14,
    model_gap: float = 0.6,
) -> PanelLayout:
    n_L, n_S = 6, 3
    cluster_w = n_S * bar_width + l_gap

    positions: List[float] = []
    heights: List[float] = []
    yerr: List[float] = []
    colors: List[str] = []
    l_tick_x: List[float] = []
    l_tick_lbl: List[str] = []
    model_centers: List[float] = []
    model_labels: List[str] = []
    model_boundaries: List[float] = []

    x = 0.0
    for model, acc, margin in model_stats:
        model_start = x
        for li in range(n_L):
            cluster_center = x + cluster_w / 2.0
            l_tick_x.append(cluster_center)
            l_tick_lbl.append(STRUCT_TICKS[li])
            for si in range(n_S):
                offset = (si - (n_S - 1) / 2.0) * bar_width
                positions.append(x + offset + bar_width)
                heights.append(acc[li, si])
                yerr.append(margin[li, si])
                colors.append(SEM_COLORS[si])
            x += cluster_w
        model_centers.append((model_start + x) / 2.0)
        model_labels.append(DISPLAY_NAMES.get(model, model.replace("-", " ")))
        model_boundaries.append(x)
        x += model_gap

    return PanelLayout(
        positions=positions,
        heights=heights,
        yerr=yerr,
        colors=colors,
        l_tick_x=l_tick_x,
        l_tick_lbl=l_tick_lbl,
        model_centers=model_centers,
        model_labels=model_labels,
        model_boundaries=model_boundaries,
        x_max=x - model_gap,
    )


def _draw_panel(
    ax: plt.Axes,
    layout: PanelLayout,
    *,
    ymax: float,
    bar_width: float,
    model_gap: float,
    show_labels: bool,
    show_ylabel: bool,
) -> None:
    bars = ax.bar(
        layout.positions,
        layout.heights,
        width=bar_width * 0.92,
        color=layout.colors,
        edgecolor="#2A2A2A",
        linewidth=0.35,
        zorder=3,
    )
    ax.errorbar(
        layout.positions,
        layout.heights,
        yerr=layout.yerr,
        fmt="none",
        ecolor="#1A1A1A",
        elinewidth=0.7,
        capsize=2.0,
        capthick=0.7,
        zorder=4,
    )

    if show_labels:
        for rect, h, err in zip(bars, layout.heights, layout.yerr):
            if h < 0.008:
                continue
            label_y = h + err + LABEL_PAD_ABOVE_CI
            ax.text(
                rect.get_x() + rect.get_width() / 2.0,
                label_y,
                _format_bar_label(h),
                ha="center",
                va="bottom",
                fontsize=FONT_BAR_LABEL,
                color="#1A1A1A",
                zorder=5,
            )

    y_top = ymax + (0.06 if show_labels else 0)
    ax.set_ylim(0, y_top)
    ax.set_xlim(-0.3, layout.x_max + 0.3)
    ax.set_xticks(layout.l_tick_x)
    ax.set_xticklabels(layout.l_tick_lbl, fontsize=FONT_TICK)
    ax.tick_params(axis="x", length=0, pad=4)
    ax.tick_params(axis="y", labelsize=FONT_TICK)

    for bx in layout.model_boundaries[:-1]:
        ax.axvline(bx + model_gap / 2.0, color="#1A1A1A", linewidth=0.9, zorder=2)

    trans = ax.get_xaxis_transform()
    for cx, lbl in zip(layout.model_centers, layout.model_labels):
        ax.text(
            cx,
            -0.13,
            lbl,
            transform=trans,
            ha="center",
            va="top",
            fontsize=FONT_MODEL,
            fontweight="bold",
            clip_on=False,
        )

    ax.axhline(ymax / 2.0, color="#B8B8B8", linewidth=0.6, linestyle="--", zorder=1)
    if show_ylabel:
        ax.set_ylabel("Execution accuracy", fontsize=FONT_BASE + 0.5, labelpad=8)
    ax.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter("%.1f"))


def split_model_rows(
    model_stats: List[Tuple[str, np.ndarray, np.ndarray]],
    row_splits: Sequence[int],
) -> List[List[Tuple[str, np.ndarray, np.ndarray]]]:
    rows: List[List[Tuple[str, np.ndarray, np.ndarray]]] = []
    i = 0
    for n in row_splits:
        rows.append(model_stats[i : i + n])
        i += n
    if i < len(model_stats):
        rows.append(model_stats[i:])
    return [r for r in rows if r]


def plot_grouped_bars(
    model_stats: List[Tuple[str, np.ndarray, np.ndarray]],
    *,
    out_stem: Path,
    ymax: float = 0.5,
    bar_width: float = 0.22,
    l_gap: float = 0.14,
    model_gap: float = 0.6,
    row_splits: Sequence[int] = ROW_SPLITS,
    show_labels: bool = True,
) -> None:
    _apply_pub_style()
    rows = split_model_rows(model_stats, row_splits)
    n_rows = len(rows)
    if n_rows == 0:
        raise ValueError("No model rows to plot")

    layouts = [
        build_panel_layout(row, bar_width=bar_width, l_gap=l_gap, model_gap=model_gap)
        for row in rows
    ]

    # Width from the busiest row; height scales with row count
    max_x = max(lay.x_max for lay in layouts)
    fig_w = max(9.5, 0.88 * max_x)
    fig_h = 2.9 * n_rows + 1.4

    fig, axes = plt.subplots(
        n_rows,
        1,
        figsize=(fig_w, fig_h),
        sharey=True,
        squeeze=False,
    )
    axes_flat = axes.flatten()

    for ax, row_models, layout in zip(axes_flat, rows, layouts):
        _draw_panel(
            ax,
            layout,
            ymax=ymax,
            bar_width=bar_width,
            model_gap=model_gap,
            show_labels=show_labels,
            show_ylabel=(ax is axes_flat[0]),
        )

    for ax in axes_flat:
        ax.set_yticks([0, ymax / 2.0, ymax])

    handles = [
        mpl.patches.Patch(
            facecolor=SEM_COLORS[i],
            edgecolor="#2A2A2A",
            linewidth=0.35,
            label=SEM_LEGEND[i],
        )
        for i in range(3)
    ]
    leg = fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.12),
        ncol=3,
        fontsize=FONT_LEGEND,
        handlelength=2.0,
        handleheight=1.0,
        columnspacing=2.4,
        borderaxespad=0,
    )
    leg.set_in_layout(False)

    fig.suptitle(
        "Execution accuracy by schema condition (n=397 per cell)",
        fontsize=FONT_TITLE,
        fontweight="bold",
        y=0.97,
    )
    fig.text(
        0.5,
        0.03,
        "Error bars: half-width of 95% bootstrap CI (10,000 replicates). "
        "Top row: Gemini, Qwen 32B, 14B; bottom row: Qwen 7B, 3B, Phi-4.",
        ha="center",
        va="bottom",
        fontsize=FONT_NOTE,
        color="#606060",
        transform=fig.transFigure,
    )

    fig.subplots_adjust(
        hspace=0.38,
        top=0.88,
        bottom=0.20,
        left=0.08,
        right=0.99,
    )
    save_pub(fig, out_stem)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Plot all-models grouped bar chart (two rows).")
    parser.add_argument("--results-dir", type=Path, default=_ROOT / "results")
    parser.add_argument("--n-bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ymax", type=float, default=0.5)
    parser.add_argument("--no-labels", action="store_true")
    parser.add_argument(
        "--row-splits",
        type=str,
        default="3,3",
        help="Comma-separated model counts per row (default 3,3)",
    )
    parser.add_argument(
        "--out-stem",
        type=Path,
        default=FIG_DIR / "main_experiment_all_models_grouped_bars",
    )
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))
    row_splits = tuple(int(x.strip()) for x in args.row_splits.split(",") if x.strip())

    models = discover_complete_models(args.results_dir)
    if not models:
        print("No models with complete 18-cell grids.", file=sys.stderr)
        return 1

    model_stats: List[Tuple[str, np.ndarray, np.ndarray]] = []
    for model in models:
        acc, margin = load_cell_stats(
            args.results_dir, model, n_bootstrap=args.n_bootstrap, seed=args.seed
        )
        model_stats.append((model, acc, margin))
        print(f"  loaded {model} ({DISPLAY_NAMES.get(model, model)})")

    plot_grouped_bars(
        model_stats,
        out_stem=args.out_stem,
        ymax=args.ymax,
        row_splits=row_splits,
        show_labels=not args.no_labels,
    )

    print(f"\nWrote {args.out_stem}.{{svg,pdf,png}}  ({len(models)} models, rows={row_splits})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
