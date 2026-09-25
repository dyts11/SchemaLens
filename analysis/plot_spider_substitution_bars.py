#!/usr/bin/env python3
"""
Spider - L1*S3 vs L6*S1 substitution bar chart (figure513 style).

Grouped bars per model:
  - L1*S3 (strong semantics)
  - L6*S1 (strong structure)

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_spider_substitution_bars.py
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.bootstrap_accuracy_ci import bootstrap_accuracy_ci, load_correct_flags

FIG_DIR = _ROOT / "docs" / "figures"
RESULTS_DIR = _ROOT / "results" / "spider"

DEFAULT_MODELS: Tuple[Tuple[str, str], ...] = (
    ("Gemini", "gemini-2.5-flash"),
    ("Qwen", "qwen2.5-coder-14b-local"),
    ("Phi", "phi-4-local"),
    ("OLMo", "olmo-2-13b-local"),
)

COLOR_SEM = "#4472C4"  # L1*S3
COLOR_STRUCT = "#ED7D31"  # L6*S1


@dataclass
class ConditionBar:
    acc: float
    margin: float


@dataclass
class ModelBars:
    display: str
    l1s3: ConditionBar
    l6s1: ConditionBar

    @property
    def delta(self) -> float:
        return self.l1s3.acc - self.l6s1.acc


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


def load_model_bars(
    results_dir: Path,
    display: str,
    slug: str,
    *,
    n_bootstrap: int,
    seed: int,
) -> ModelBars:
    l1s3_flags = load_correct_flags(results_dir / f"{slug}__L1S3.csv")
    l6s1_flags = load_correct_flags(results_dir / f"{slug}__L6S1.csv")
    l1s3 = bootstrap_accuracy_ci(l1s3_flags, n_bootstrap=n_bootstrap, seed=seed)
    l6s1 = bootstrap_accuracy_ci(l6s1_flags, n_bootstrap=n_bootstrap, seed=seed + 1)
    return ModelBars(
        display=display,
        l1s3=ConditionBar(acc=l1s3.accuracy * 100.0, margin=l1s3.margin * 100.0),
        l6s1=ConditionBar(acc=l6s1.accuracy * 100.0, margin=l6s1.margin * 100.0),
    )


def plot_substitution_bars(
    model_bars: Sequence[ModelBars],
    out_stem: Path,
    *,
    y_max: float = 70.0,
) -> None:
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.8, 2.9))

    n = len(model_bars)
    x = np.arange(n)
    bar_w = 0.34

    sem_heights = [m.l1s3.acc for m in model_bars]
    sem_err = [m.l1s3.margin for m in model_bars]
    struct_heights = [m.l6s1.acc for m in model_bars]
    struct_err = [m.l6s1.margin for m in model_bars]

    ax.bar(
        x - bar_w / 2,
        sem_heights,
        width=bar_w,
        color=COLOR_SEM,
        edgecolor="#272727",
        linewidth=0.5,
        label=r"$L_1 \cdot S_3$ (strong semantics)",
        zorder=3,
    )
    ax.bar(
        x + bar_w / 2,
        struct_heights,
        width=bar_w,
        color=COLOR_STRUCT,
        edgecolor="#272727",
        linewidth=0.5,
        label=r"$L_6 \cdot S_1$ (strong structure)",
        zorder=3,
    )

    ax.errorbar(
        x - bar_w / 2,
        sem_heights,
        yerr=sem_err,
        fmt="none",
        ecolor="#1A1A1A",
        elinewidth=0.8,
        capsize=2.5,
        capthick=0.7,
        zorder=4,
    )
    ax.errorbar(
        x + bar_w / 2,
        struct_heights,
        yerr=struct_err,
        fmt="none",
        ecolor="#1A1A1A",
        elinewidth=0.8,
        capsize=2.5,
        capthick=0.7,
        zorder=4,
    )

    for i, m in enumerate(model_bars):
        top = max(m.l1s3.acc + m.l1s3.margin, m.l6s1.acc + m.l6s1.margin)
        ax.text(
            x[i],
            top + 2.0,
            rf"$\Delta = {m.delta:+.1f}$",
            ha="center",
            va="bottom",
            fontsize=7,
            fontweight="bold",
            color="#1A1A1A",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([m.display for m in model_bars], fontsize=7)
    ax.set_ylabel("EX (%)", fontsize=7.5)
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.arange(0, y_max + 1, 10))
    ax.yaxis.grid(True, linestyle="-", linewidth=0.35, color="#D8D8D8", zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=6, handlelength=1.4, handletextpad=0.5)

    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.12, top=0.96)
    save_pub(fig, out_stem)


def print_summary(model_bars: Sequence[ModelBars]) -> None:
    print("\nSpider L1*S3 vs L6*S1 EX (% +/- bootstrap half-width):\n")
    print("| Model | L1*S3 | L6*S1 | Delta |")
    print("|-------|-------|-------|-------|")
    for m in model_bars:
        print(
            f"| {m.display} | {m.l1s3.acc:.1f}+/-{m.l1s3.margin:.1f} | "
            f"{m.l6s1.acc:.1f}+/-{m.l6s1.margin:.1f} | {m.delta:+.1f} |"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Spider L1*S3 vs L6*S1 substitution bar chart (figure513 style).",
    )
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--out-stem",
        type=Path,
        default=FIG_DIR / "spider_substitution_bars",
    )
    parser.add_argument("--y-max", type=float, default=70.0)
    parser.add_argument("--n-bootstrap", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-print-table", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    model_bars: List[ModelBars] = []
    for i, (display, slug) in enumerate(DEFAULT_MODELS):
        model_bars.append(
            load_model_bars(
                args.results_dir,
                display,
                slug,
                n_bootstrap=args.n_bootstrap,
                seed=args.seed + 100 * i,
            )
        )

    plot_substitution_bars(model_bars, args.out_stem, y_max=args.y_max)
    print(f"Wrote {args.out_stem}.{{svg,pdf,png}}")

    if not args.no_print_table:
        print_summary(model_bars)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
