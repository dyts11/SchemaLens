#!/usr/bin/env python3
"""
Two-panel execution-accuracy heatmap for Qwen2.5-Coder-14B: BIRD (top) and
Spider (bottom), sharing one 0-75% color scale so accuracy is directly
comparable across datasets. Axes are transposed relative to the single-
dataset heatmaps: x = structural level (L1-L6), y = semantic level (S1-S3).

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_bird_spider_heatmap_combined.py
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

STRUCT_LABELS = ["L1\n1NF wide", "L2\n2NF clusters", "L3\n3NF names", "L4\n+ types/PK", "L5\n+ FK edges", "L6\n+ JOIN paths"]
SEM_LABELS = ["S1\nanon.", "S2\nabbr.", "S3\ndesc."]


def load_grid(
    results_dir: Path,
    model: str,
    *,
    n_bootstrap: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, int]:
    """Returns accuracy_pct (3x6, rows=S1-S3, cols=L1-L6), margin_pct, n_per_cell."""
    acc = np.full((3, 6), np.nan)
    margin = np.full((3, 6), np.nan)
    n_per_cell = 0

    for sl in range(1, 7):
        for sem in range(1, 4):
            path = results_dir / f"{model}__L{sl}S{sem}.csv"
            if not path.exists():
                raise FileNotFoundError(path)
            flags = load_correct_flags(path)
            res = bootstrap_accuracy_ci(flags, n_bootstrap=n_bootstrap, alpha=alpha, seed=seed)
            acc[sem - 1, sl - 1] = res.accuracy * 100.0
            margin[sem - 1, sl - 1] = res.margin * 100.0
            n_per_cell = res.n

    return acc, margin, n_per_cell


def _draw_panel(
    ax: plt.Axes,
    acc_pct: np.ndarray,
    margin_pct: np.ndarray,
    *,
    norm: mpl.colors.Normalize,
    cmap: mpl.colors.Colormap,
    label: str,
    n_per_cell: int,
    show_xticklabels: bool,
) -> mpl.image.AxesImage:
    im = ax.imshow(acc_pct, aspect="auto", cmap=cmap, norm=norm, origin="upper")

    for i in range(3):
        for j in range(6):
            val = acc_pct[i, j]
            m = margin_pct[i, j]
            color = _text_color_for_value(norm, cmap, val)
            ax.text(
                j,
                i,
                f"{val:.1f}%\n±{m:.1f}%",
                ha="center",
                va="center",
                fontsize=10.5,
                color=color,
                fontweight="bold",
                linespacing=1.3,
            )

    ax.set_xticks(np.arange(6))
    ax.set_yticks(np.arange(3))
    ax.set_yticklabels(SEM_LABELS, fontsize=11)
    if show_xticklabels:
        ax.set_xticklabels(STRUCT_LABELS, fontsize=11)
    else:
        ax.set_xticklabels([])

    ax.set_title(f"{label}  (n={n_per_cell} per cell)", fontsize=13.5, fontweight="bold", pad=6, loc="left")

    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(2.5, -0.5)
    return im


def plot_combined(
    bird_acc: np.ndarray,
    bird_margin: np.ndarray,
    bird_n: int,
    spider_acc: np.ndarray,
    spider_margin: np.ndarray,
    spider_n: int,
    *,
    out_stem: Path,
    vmax: float = 75.0,
) -> None:
    _apply_pub_style()
    fig, axes = plt.subplots(2, 1, figsize=(9.4, 6.4), sharex=True, gridspec_kw={"hspace": 0.32})

    cmap = mpl.cm.YlGnBu.copy()
    norm = mpl.colors.Normalize(vmin=0, vmax=vmax)

    _draw_panel(axes[0], bird_acc, bird_margin, norm=norm, cmap=cmap, label="BIRD", n_per_cell=bird_n, show_xticklabels=False)
    im = _draw_panel(axes[1], spider_acc, spider_margin, norm=norm, cmap=cmap, label="Spider", n_per_cell=spider_n, show_xticklabels=True)

    cbar = fig.colorbar(im, ax=axes, fraction=0.05, pad=0.03)
    cbar.set_label("Execution accuracy (%)", fontsize=13)
    cbar.ax.tick_params(labelsize=11)

    save_pub(fig, out_stem)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Combined BIRD + Spider accuracy heatmap, shared color scale.")
    parser.add_argument("--model", default="qwen2.5-coder-14b-local")
    parser.add_argument("--bird-dir", type=Path, default=_ROOT / "results" / "full")
    parser.add_argument("--spider-dir", type=Path, default=_ROOT / "results" / "spider")
    parser.add_argument("--n-bootstrap", type=int, default=10000)
    parser.add_argument("--vmax", type=float, default=75.0)
    parser.add_argument("--out-stem", type=Path, default=None)
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    bird_acc, bird_margin, bird_n = load_grid(args.bird_dir, args.model, n_bootstrap=args.n_bootstrap)
    spider_acc, spider_margin, spider_n = load_grid(args.spider_dir, args.model, n_bootstrap=args.n_bootstrap)

    actual_max = max(np.nanmax(bird_acc), np.nanmax(spider_acc))
    vmax = max(args.vmax, actual_max)

    safe = args.model.replace("/", "-")
    out_stem = args.out_stem or (FIG_DIR / f"bird_spider_{safe}_heatmap_combined")

    plot_combined(
        bird_acc, bird_margin, bird_n,
        spider_acc, spider_margin, spider_n,
        out_stem=out_stem,
        vmax=vmax,
    )

    print(f"Wrote {out_stem}.{{svg,pdf,png}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
