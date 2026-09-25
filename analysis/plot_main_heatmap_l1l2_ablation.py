#!/usr/bin/env python3
"""
6x3 execution-accuracy heatmap for Qwen2.5-Coder-14B using a prompt-consistent
main experiment: L1-L2 from results/without_denorm_notice (no denormalisation
notice, same template style as L3-L6, which never receive the notice either)
and L3-L6 from results/full. This makes the notice condition uniform across
all six structural levels. The with-notice condition for L1/L2
(results/full's L1/L2 rows) is the ablation arm here, showing how much of
L1/L2's accuracy the notice's explicit fan-out-defense instructions
contribute on top of the schema representation itself.

See docs/qwen14b_fewshot_vs_full_accuracy.md, "full vs without_denorm_notice
(L1/L2 denormalisation-notice ablation)" for the underlying numbers.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_main_heatmap_l1l2_ablation.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.bootstrap_accuracy_ci import bootstrap_accuracy_ci, load_correct_flags
from analysis.plot_main_heatmap import _apply_pub_style, _text_color_for_value, save_pub

FIG_DIR = _ROOT / "docs" / "figures"

STRUCT_LABELS = [
    "L1\n1NF wide",
    "L2\n2NF clusters",
    "L3\n3NF names",
    "L4\n+ types/PK",
    "L5\n+ FK edges",
    "L6\n+ JOIN paths",
]
SEM_LABELS = ["S1\nanonymous", "S2\nabbreviated", "S3\ndescriptive"]

MODEL_DISPLAY = {"qwen2.5-coder-14b-local": "Qwen2.5-Coder-14B"}


def load_condition(
    results_dir: Path,
    model: str,
    struct_level: int,
    sem_level: int,
    *,
    n_bootstrap: int,
    alpha: float,
    seed: int,
) -> Tuple[float, float, int, int]:
    path = results_dir / f"{model}__L{struct_level}S{sem_level}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    flags = load_correct_flags(path)
    res = bootstrap_accuracy_ci(flags, n_bootstrap=n_bootstrap, alpha=alpha, seed=seed)
    return res.accuracy * 100.0, res.margin * 100.0, res.n_correct, res.n


def load_hybrid_grid(
    *,
    model: str,
    l3l6_dir: Path,
    l1l2_dir: Path,
    l1l2_levels: Tuple[int, ...] = (1, 2),
    n_bootstrap: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, List[Tuple[int, int, int, int, str]]]:
    acc = np.full((6, 3), np.nan)
    margin = np.full((6, 3), np.nan)
    summaries: List[Tuple[int, int, int, int, str]] = []

    for sl in range(1, 7):
        source_dir = l1l2_dir if sl in l1l2_levels else l3l6_dir
        source_tag = "main, no notice" if sl in l1l2_levels else "main"
        for sem in range(1, 4):
            val, m, n_correct, n = load_condition(
                source_dir, model, sl, sem, n_bootstrap=n_bootstrap, alpha=alpha, seed=seed
            )
            acc[sl - 1, sem - 1] = val
            margin[sl - 1, sem - 1] = m
            summaries.append((sl, sem, n_correct, n, source_tag))

    return acc, margin, summaries


def plot_hybrid_heatmap(
    acc_pct: np.ndarray,
    margin_pct: np.ndarray,
    *,
    model: str,
    out_stem: Path,
    vmax: float = 45.0,
    n_per_cell: int = 397,
) -> None:
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.6, 4.0))

    cmap = mpl.cm.YlGnBu.copy()
    norm = mpl.colors.Normalize(vmin=0, vmax=vmax)
    im = ax.imshow(acc_pct, aspect="auto", cmap=cmap, norm=norm, origin="upper")

    for i in range(6):
        for j in range(3):
            val = acc_pct[i, j]
            m = margin_pct[i, j]
            color = _text_color_for_value(norm, cmap, val)
            ax.text(
                j,
                i,
                f"{val:.1f}% ± {m:.1f}%",
                ha="center",
                va="center",
                fontsize=6.5,
                color=color,
                fontweight="bold",
            )

    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(SEM_LABELS, fontsize=6.5)
    ax.set_xlabel("Semantic level", fontsize=7.5, labelpad=4)
    ax.set_yticks(np.arange(6))
    ax.set_yticklabels(STRUCT_LABELS, fontsize=6.5)
    ax.set_ylabel("Structural level", fontsize=7.5, labelpad=4)

    model_title = MODEL_DISPLAY.get(model, model)
    ax.set_title(
        f"Execution accuracy by schema condition\n({model_title}, n={n_per_cell} per cell)",
        fontsize=8,
        fontweight="bold",
        pad=8,
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Execution accuracy (%)", fontsize=7)
    cbar.ax.tick_params(labelsize=6)

    fig.text(
        0.5,
        0.01,
        "Cell labels: point estimate ± half-width of 95% bootstrap CI (10,000 replicates).",
        ha="center",
        fontsize=5.5,
        color="#606060",
    )

    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(5.5, -0.5)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    save_pub(fig, out_stem)


def print_markdown_table(
    acc_pct: np.ndarray, margin_pct: np.ndarray, summaries: List[Tuple[int, int, int, int, str]]
) -> None:
    source_by_level = {sl: tag for sl, _, _, _, tag in summaries}
    print("\nMarkdown table (main experiment: L1-L2 no-notice, L3-L6 full):\n")
    print("|  | **S1** | **S2** | **S3** | Source |")
    print("|--|--------|--------|--------|--------|")
    for i in range(6):
        cells = [f"{acc_pct[i, j]:.1f}% ± {margin_pct[i, j]:.1f}%" for j in range(3)]
        print(f"| **L{i + 1}** | {cells[0]} | {cells[1]} | {cells[2]} | {source_by_level[i + 1]} |")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plot main-experiment accuracy heatmap: L1-L2 from the without_denorm_notice condition, L3-L6 from results/full."
    )
    parser.add_argument("--model", default="qwen2.5-coder-14b-local")
    parser.add_argument("--l3l6-dir", type=Path, default=_ROOT / "results" / "full")
    parser.add_argument("--l1l2-dir", type=Path, default=_ROOT / "results" / "without_denorm_notice")
    parser.add_argument("--n-bootstrap", type=int, default=10000)
    parser.add_argument("--vmax", type=float, default=45.0)
    parser.add_argument("--out-stem", type=Path, default=None)
    parser.add_argument("--no-print-table", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    acc, margin, summaries = load_hybrid_grid(
        model=args.model,
        l3l6_dir=args.l3l6_dir,
        l1l2_dir=args.l1l2_dir,
        n_bootstrap=args.n_bootstrap,
    )
    n_per_cell = summaries[0][3] if summaries else 397
    safe = args.model.replace("/", "-")
    out_stem = args.out_stem or (FIG_DIR / f"main_experiment_{safe}_L1L2nonotice_heatmap")

    plot_hybrid_heatmap(
        acc,
        margin,
        model=args.model,
        out_stem=out_stem,
        vmax=args.vmax,
        n_per_cell=n_per_cell,
    )

    if not args.no_print_table:
        print_markdown_table(acc, margin, summaries)

    print(f"\nWrote {out_stem}.{{svg,pdf,png}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
