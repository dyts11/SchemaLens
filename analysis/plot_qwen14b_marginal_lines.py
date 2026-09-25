#!/usr/bin/env python3
"""
Qwen2.5-Coder-14B-only marginal EA line chart (figure512 layout/style), BIRD
main experiment (results/full).

Two panels:
  - Left:  EA (%) vs structural level L1-L6 (pooled over S1-S3)
  - Right: EA (%) vs semantic level S1-S3 (pooled over L1-L6)

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_qwen14b_marginal_lines.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

import matplotlib.pyplot as plt

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.plot_spider_marginal_lines import (
    STRUCT_LABELS,
    SEM_LABELS,
    DISPLAY_NAMES,
    _apply_pub_style,
    _plot_panel,
    load_marginal_series,
    save_pub,
)

FIG_DIR = _ROOT / "docs" / "figures"
BIRD_RESULTS_DIR = _ROOT / "results" / "full"

MODEL = "qwen2.5-coder-14b-local"


def print_markdown_table(series) -> None:
    name = DISPLAY_NAMES.get(series.model, series.model)
    print(f"\n{name} marginal EA, BIRD main experiment (% +/- bootstrap half-width):\n")
    print("| L1 | L2 | L3 | L4 | L5 | L6 | S1 | S2 | S3 |")
    print("|----|----|----|----|----|----|----|----|-----|")
    cells = [
        f"{acc:.1f}+/-{margin:.1f}"
        for acc, margin in list(zip(series.struct_acc, series.struct_margin))
        + list(zip(series.sem_acc, series.sem_margin))
    ]
    print("| " + " | ".join(cells) + " |")


def plot_qwen14b_marginal_lines(
    series,
    out_stem: Path,
    *,
    y_max: float = 40.0,
    n_per_cell: int = 397,
) -> None:
    _apply_pub_style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))

    _plot_panel(axes[0], [series], STRUCT_LABELS, "Structural level", y_max=y_max, show_ylabel=True)
    _plot_panel(axes[1], [series], SEM_LABELS, "Semantic level", y_max=y_max, show_ylabel=True)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=1,
        fontsize=6.5,
        bbox_to_anchor=(0.5, -0.02),
        handletextpad=0.5,
    )

    fig.text(
        0.5,
        -0.10,
        (
            f"BIRD main experiment (results/full, n={n_per_cell} per LxS cell). "
            "Left: pooled over S1-S3; right: pooled over L1-L6. "
            "Error bars: half-width of 95% bootstrap CI (10,000 replicates)."
        ),
        ha="center",
        fontsize=5.5,
        color="#606060",
    )

    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.22, top=0.96, wspace=0.22)
    save_pub(fig, out_stem)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Qwen2.5-Coder-14B-only marginal EA line chart (figure512 style).")
    parser.add_argument("--results-dir", type=Path, default=BIRD_RESULTS_DIR)
    parser.add_argument("--out-stem", type=Path, default=FIG_DIR / "qwen14b_marginal_ea")
    parser.add_argument("--y-max", type=float, default=40.0)
    parser.add_argument("--n-bootstrap", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-print-table", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    series = load_marginal_series(args.results_dir, MODEL, n_bootstrap=args.n_bootstrap, seed=args.seed)

    plot_qwen14b_marginal_lines(series, args.out_stem, y_max=args.y_max)
    print(f"Wrote {args.out_stem}.{{svg,pdf,png}}")

    if not args.no_print_table:
        print_markdown_table(series)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
