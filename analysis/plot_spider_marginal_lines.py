#!/usr/bin/env python3
"""
Spider - four-model marginal EA line chart (figure512-style).

Two panels:
  - Left:  EA (%) vs structural level L1-L6 (pooled over S1-S3)
  - Right: EA (%) vs semantic level S1-S3 (pooled over L1-L6)

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_spider_marginal_lines.py
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
RESULTS_DIR = _ROOT / "results" / "spider"
CONDITION_RE = re.compile(r"__L(\d+)S(\d+)\.csv$", re.IGNORECASE)

STRUCT_LABELS = ["L1", "L2", "L3", "L4", "L5", "L6"]
SEM_LABELS = ["S1", "S2", "S3"]

DEFAULT_MODELS: Tuple[str, ...] = (
    "gemini-2.5-flash",
    "qwen2.5-coder-14b-local",
    "phi-4-local",
    "olmo-2-13b-local",
)

DISPLAY_NAMES: Dict[str, str] = {
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "qwen2.5-coder-14b-local": "Qwen2.5-Coder 14B",
    "phi-4-local": "Phi-4",
    "olmo-2-13b-local": "OLMo-2 13B",
}

# Match BIRD figure512 styling (model family colors + marker shapes).
MODEL_STYLE: Dict[str, Dict[str, object]] = {
    "gemini-2.5-flash": {
        "color": "#4472C4",
        "marker": "o",
        "hollow": True,
    },
    "qwen2.5-coder-14b-local": {
        "color": "#C55A11",
        "marker": "s",
        "hollow": False,
    },
    "phi-4-local": {
        "color": "#2E7D6E",
        "marker": "^",
        "hollow": False,
    },
    "olmo-2-13b-local": {
        "color": "#D4A017",
        "marker": "D",
        "hollow": False,
    },
}


@dataclass
class MarginalSeries:
    model: str
    struct_acc: np.ndarray  # (6,)
    struct_margin: np.ndarray
    sem_acc: np.ndarray  # (3,)
    sem_margin: np.ndarray


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


def _pool_ci(
    parts: Sequence[List[bool]],
    *,
    n_bootstrap: int,
    seed: int,
) -> Tuple[float, float]:
    merged: List[bool] = []
    for part in parts:
        merged.extend(part)
    res = bootstrap_accuracy_ci(merged, n_bootstrap=n_bootstrap, seed=seed)
    return res.accuracy * 100.0, res.margin * 100.0


def load_marginal_series(
    results_dir: Path,
    model: str,
    *,
    n_bootstrap: int = 10_000,
    seed: int = 42,
) -> MarginalSeries:
    model_key = model.replace("/", "-")
    struct_acc = np.full(6, np.nan)
    struct_margin = np.full(6, np.nan)
    sem_acc = np.full(3, np.nan)
    sem_margin = np.full(3, np.nan)

    for L in range(1, 7):
        parts = [
            load_correct_flags(results_dir / f"{model_key}__L{L}S{S}.csv")
            for S in range(1, 4)
        ]
        acc, margin = _pool_ci(
            parts,
            n_bootstrap=n_bootstrap,
            seed=seed + 100 * L,
        )
        struct_acc[L - 1] = acc
        struct_margin[L - 1] = margin

    for S in range(1, 4):
        parts = [
            load_correct_flags(results_dir / f"{model_key}__L{L}S{S}.csv")
            for L in range(1, 7)
        ]
        acc, margin = _pool_ci(
            parts,
            n_bootstrap=n_bootstrap,
            seed=seed + 1000 + 100 * S,
        )
        sem_acc[S - 1] = acc
        sem_margin[S - 1] = margin

    if np.isnan(struct_acc).any() or np.isnan(sem_acc).any():
        raise ValueError(f"Incomplete Spider results for {model}")

    return MarginalSeries(
        model=model,
        struct_acc=struct_acc,
        struct_margin=struct_margin,
        sem_acc=sem_acc,
        sem_margin=sem_margin,
    )


def _plot_panel(
    ax: plt.Axes,
    series_list: Sequence[MarginalSeries],
    x_labels: Sequence[str],
    xlabel: str,
    *,
    y_max: float,
    show_ylabel: bool = True,
) -> None:
    x = np.arange(len(x_labels))

    for series in series_list:
        style = MODEL_STYLE.get(series.model, {"color": "#666666", "marker": "o", "hollow": False})
        color = str(style["color"])
        marker = str(style["marker"])
        hollow = bool(style.get("hollow", False))
        label = DISPLAY_NAMES.get(series.model, series.model)

        if len(x_labels) == 6:
            y = series.struct_acc
            yerr = series.struct_margin
        else:
            y = series.sem_acc
            yerr = series.sem_margin

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            color=color,
            linewidth=1.8,
            marker=marker,
            markersize=5.5,
            markerfacecolor="white" if hollow else color,
            markeredgecolor=color,
            markeredgewidth=1.2 if hollow else 0.5,
            capsize=2.5,
            capthick=0.8,
            elinewidth=0.9,
            label=label,
            zorder=3,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7)
    ax.set_xlabel(xlabel, fontsize=7.5, labelpad=4)
    if show_ylabel:
        ax.set_ylabel("EA (%)", fontsize=7.5)
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.arange(0, y_max + 1, 20))
    ax.tick_params(axis="y", labelleft=True)
    ax.yaxis.grid(True, linestyle="-", linewidth=0.35, color="#D8D8D8", zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlim(-0.35, len(x_labels) - 0.65)


def plot_spider_marginal_lines(
    series_list: Sequence[MarginalSeries],
    out_stem: Path,
    *,
    y_max: float = 80.0,
    n_per_cell: int = 154,
) -> None:
    """Two-panel marginal EA chart for Spider (figure512 layout)."""
    _apply_pub_style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))

    _plot_panel(
        axes[0],
        series_list,
        STRUCT_LABELS,
        "Structural level",
        y_max=y_max,
        show_ylabel=True,
    )
    _plot_panel(
        axes[1],
        series_list,
        SEM_LABELS,
        "Semantic level",
        y_max=y_max,
        show_ylabel=True,
    )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=2,
        fontsize=6.5,
        bbox_to_anchor=(0.5, -0.02),
        columnspacing=1.2,
        handletextpad=0.5,
    )

    fig.text(
        0.5,
        -0.10,
        (
            f"Spider (car_1 + tvshow, n={n_per_cell} per LxS cell). "
            "Left: pooled over S1-S3; right: pooled over L1-L6. "
            "Error bars: half-width of 95% bootstrap CI (10,000 replicates)."
        ),
        ha="center",
        fontsize=5.5,
        color="#606060",
    )

    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.22, top=0.96, wspace=0.22)
    save_pub(fig, out_stem)


def print_markdown_table(series_list: Sequence[MarginalSeries]) -> None:
    print("\nSpider marginal EA (% +/- bootstrap half-width):\n")
    print("| Model | L1 | L2 | L3 | L4 | L5 | L6 | S1 | S2 | S3 |")
    print("|-------|----|----|----|----|----|----|----|----|-----|")
    for s in series_list:
        name = DISPLAY_NAMES.get(s.model, s.model)
        cells: List[str] = []
        for acc, margin in zip(s.struct_acc, s.struct_margin):
            cells.append(f"{acc:.1f}+/-{margin:.1f}")
        for acc, margin in zip(s.sem_acc, s.sem_margin):
            cells.append(f"{acc:.1f}+/-{margin:.1f}")
        print(f"| {name} | " + " | ".join(cells) + " |")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Spider four-model marginal EA line chart (figure512-style).",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Directory with Spider result CSVs",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help="Model slugs (default: gemini, qwen14b, phi4, olmo2)",
    )
    parser.add_argument(
        "--out-stem",
        type=Path,
        default=FIG_DIR / "spider_four_models_marginal_ea",
    )
    parser.add_argument("--y-max", type=float, default=80.0)
    parser.add_argument("--n-bootstrap", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-print-table", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    series_list = [
        load_marginal_series(
            args.results_dir,
            model,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
        )
        for model in args.models
    ]

    plot_spider_marginal_lines(
        series_list,
        args.out_stem,
        y_max=args.y_max,
    )
    print(f"Wrote {args.out_stem}.{{svg,pdf,png}}")

    if not args.no_print_table:
        print_markdown_table(series_list)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
