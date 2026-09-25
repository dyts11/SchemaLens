#!/usr/bin/env python3
"""
Spider - Qwen-Coder model-size scaling figure (model_size.png style).

Two stacked panels:
  - Top:    marginal EA by structural level L1-L6 vs model size
  - Bottom: marginal EA by semantic level S1-S3 vs model size

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_spider_qwen_model_size.py
"""

from __future__ import annotations

import argparse
import os
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

# (display label, model slug, params in billions for pseudo-log spacing)
QWEN_MODELS: Tuple[Tuple[str, str, float], ...] = (
    ("0.5B", "qwen2.5-coder-0.5b-local", 0.5),
    ("1.5B", "qwen2.5-coder-1.5b-local", 1.5),
    ("3B", "qwen2.5-coder-3b-local", 3.0),
    ("7B", "qwen2.5-coder-7b-local", 7.0),
    ("14B", "qwen2.5-coder-14b-local", 14.0),
)

STRUCT_SERIES = [
    {"key": "L1", "label": r"$L_1$ wide table", "group": "denorm", "color": "#E8A54B", "marker": "o", "ls": "--"},
    {"key": "L2", "label": r"$L_2$ 2NF clusters", "group": "denorm", "color": "#B5651D", "marker": "o", "ls": "-"},
    {"key": "L3", "label": r"$L_3$ names only", "group": "norm", "color": "#A8C8E8", "marker": "s", "ls": "--"},
    {"key": "L4", "label": r"$L_4$ + types/PK", "group": "norm", "color": "#6BAED6", "marker": "s", "ls": "-"},
    {"key": "L5", "label": r"$L_5$ + FK", "group": "norm", "color": "#3182BD", "marker": "s", "ls": "-"},
    {"key": "L6", "label": r"$L_6$ + join paths", "group": "norm", "color": "#08519C", "marker": "s", "ls": "-"},
]

SEM_SERIES = [
    {"key": "S1", "label": r"$S_1$ anonymous", "group": "opaque", "color": "#E8A54B", "marker": "o", "ls": "-"},
    {"key": "S2", "label": r"$S_2$ abbreviated", "group": "meaningful", "color": "#74C476", "marker": "s", "ls": "--"},
    {"key": "S3", "label": r"$S_3$ descriptive", "group": "meaningful", "color": "#238B45", "marker": "s", "ls": "-"},
]


@dataclass
class LevelCurve:
    key: str
    label: str
    acc: np.ndarray
    margin: np.ndarray


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


def load_struct_curves(
    results_dir: Path,
    models: Sequence[Tuple[str, str, float]],
    *,
    n_bootstrap: int,
    seed: int,
) -> List[LevelCurve]:
    curves: List[LevelCurve] = []
    n_models = len(models)

    for li, spec in enumerate(STRUCT_SERIES):
        L = li + 1
        acc = np.full(n_models, np.nan)
        margin = np.full(n_models, np.nan)
        for mi, (_, slug, _) in enumerate(models):
            parts = [
                load_correct_flags(results_dir / f"{slug}__L{L}S{S}.csv")
                for S in range(1, 4)
            ]
            a, m = _pool_ci(parts, n_bootstrap=n_bootstrap, seed=seed + 10 * L + mi)
            acc[mi] = a
            margin[mi] = m
        curves.append(
            LevelCurve(
                key=spec["key"],
                label=spec["label"],
                acc=acc,
                margin=margin,
            )
        )
    return curves


def load_sem_curves(
    results_dir: Path,
    models: Sequence[Tuple[str, str, float]],
    *,
    n_bootstrap: int,
    seed: int,
) -> List[LevelCurve]:
    curves: List[LevelCurve] = []
    n_models = len(models)

    for si, spec in enumerate(SEM_SERIES):
        S = si + 1
        acc = np.full(n_models, np.nan)
        margin = np.full(n_models, np.nan)
        for mi, (_, slug, _) in enumerate(models):
            parts = [
                load_correct_flags(results_dir / f"{slug}__L{L}S{S}.csv")
                for L in range(1, 7)
            ]
            a, m = _pool_ci(parts, n_bootstrap=n_bootstrap, seed=seed + 1000 + 10 * S + mi)
            acc[mi] = a
            margin[mi] = m
        curves.append(
            LevelCurve(
                key=spec["key"],
                label=spec["label"],
                acc=acc,
                margin=margin,
            )
        )
    return curves


def _model_x_positions(models: Sequence[Tuple[str, str, float]]) -> np.ndarray:
    return np.log10([m[2] for m in models])


def _draw_level_lines(
    ax: plt.Axes,
    x: np.ndarray,
    curves: Sequence[LevelCurve],
    specs: Sequence[Dict[str, str]],
) -> None:
    for curve, spec in zip(curves, specs):
        ax.errorbar(
            x,
            curve.acc,
            yerr=curve.margin,
            color=spec["color"],
            linestyle=spec["ls"],
            linewidth=1.6,
            marker=spec["marker"],
            markersize=5.0,
            markerfacecolor=spec["color"],
            markeredgecolor="#272727",
            markeredgewidth=0.4,
            capsize=2.2,
            capthick=0.7,
            elinewidth=0.8,
            label=spec["label"],
            zorder=3,
        )


def _grouped_legend(
    ax: plt.Axes,
    specs: Sequence[Dict[str, str]],
    group_titles: Tuple[str, str],
) -> None:
    groups = {group_titles[0]: [], group_titles[1]: []}
    for spec in specs:
        key = group_titles[0] if spec["group"] in ("denorm", "opaque") else group_titles[1]
        groups[key].append(spec)

    handles: List = []
    labels: List[str] = []

    for gi, (title, members) in enumerate(groups.items()):
        if gi > 0:
            handles.append(mpl.lines.Line2D([], [], linestyle="none", marker=None, alpha=0))
            labels.append("")
        handles.append(mpl.lines.Line2D([], [], linestyle="none", marker=None, alpha=0))
        labels.append(title)
        for spec in members:
            h = mpl.lines.Line2D(
                [0],
                [0],
                color=spec["color"],
                linestyle=spec["ls"],
                marker=spec["marker"],
                markersize=4.5,
                markerfacecolor=spec["color"],
                markeredgecolor="#272727",
                markeredgewidth=0.4,
                linewidth=1.4,
            )
            handles.append(h)
            labels.append(spec["label"])

    ax.legend(
        handles,
        labels,
        loc="upper left",
        fontsize=5.5,
        handlelength=1.8,
        handletextpad=0.5,
        labelspacing=0.35,
        borderpad=0.3,
    )


def plot_spider_qwen_model_size(
    struct_curves: Sequence[LevelCurve],
    sem_curves: Sequence[LevelCurve],
    models: Sequence[Tuple[str, str, float]],
    out_stem: Path,
    *,
    y_max: float = 70.0,
) -> None:
    _apply_pub_style()
    fig, axes = plt.subplots(2, 1, figsize=(3.9, 5.6), sharex=True)
    x = _model_x_positions(models)
    x_labels = [m[0] for m in models]

    _draw_level_lines(axes[0], x, struct_curves, STRUCT_SERIES)
    _draw_level_lines(axes[1], x, sem_curves, SEM_SERIES)

    for ax in axes:
        ax.set_ylim(0, y_max)
        ax.set_yticks(np.arange(0, y_max + 1, 10))
        ax.set_ylabel("EX", fontsize=7.5)
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, fontsize=7)
        ax.tick_params(axis="x", labelbottom=True)
        ax.yaxis.grid(True, linestyle="-", linewidth=0.35, color="#D8D8D8", zorder=0)
        ax.set_axisbelow(True)

    axes[1].set_xlabel("Qwen-Coder model size (parameters)", fontsize=7.5, labelpad=4)

    _grouped_legend(axes[0], STRUCT_SERIES, ("Denormalized", "Normalized (3NF)"))
    _grouped_legend(axes[1], SEM_SERIES, ("Opaque", "Meaningful"))

    fig.subplots_adjust(left=0.14, right=0.96, bottom=0.08, top=0.98, hspace=0.32)
    save_pub(fig, out_stem)


def print_summary(
    struct_curves: Sequence[LevelCurve],
    sem_curves: Sequence[LevelCurve],
    models: Sequence[Tuple[str, str, float]],
) -> None:
    print("\nSpider Qwen model-size marginal EX (%):\n")
    header = "| Level | " + " | ".join(m[0] for m in models) + " |"
    print(header)
    print("|" + "---|" * (len(models) + 1))
    for curve in struct_curves:
        cells = " | ".join(f"{v:.1f}" for v in curve.acc)
        print(f"| {curve.key} | {cells} |")
    print()
    for curve in sem_curves:
        cells = " | ".join(f"{v:.1f}" for v in curve.acc)
        print(f"| {curve.key} | {cells} |")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Spider Qwen model-size scaling figure.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--out-stem",
        type=Path,
        default=FIG_DIR / "spider_qwen_model_size",
    )
    parser.add_argument("--y-max", type=float, default=70.0)
    parser.add_argument("--n-bootstrap", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-print-table", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    struct_curves = load_struct_curves(
        args.results_dir,
        QWEN_MODELS,
        n_bootstrap=args.n_bootstrap,
        seed=args.seed,
    )
    sem_curves = load_sem_curves(
        args.results_dir,
        QWEN_MODELS,
        n_bootstrap=args.n_bootstrap,
        seed=args.seed + 5000,
    )

    plot_spider_qwen_model_size(
        struct_curves,
        sem_curves,
        QWEN_MODELS,
        args.out_stem,
        y_max=args.y_max,
    )
    print(f"Wrote {args.out_stem}.{{svg,pdf,png}}")

    if not args.no_print_table:
        print_summary(struct_curves, sem_curves, QWEN_MODELS)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
