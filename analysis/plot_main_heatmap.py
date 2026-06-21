#!/usr/bin/env python3
"""
§6.2 — Filled 6×3 execution-accuracy heatmap with bootstrap 95% CI per cell.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_main_heatmap.py

    .venv/bin/python analysis/plot_main_heatmap.py --model gemini-2.5-flash
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Allow running as script from schema_effect/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.bootstrap_accuracy_ci import bootstrap_accuracy_ci, load_correct_flags

FIG_DIR = _ROOT / "docs" / "figures"
CONDITION_RE = re.compile(r"__L(\d+)S(\d+)\.csv$", re.IGNORECASE)

STRUCT_LABELS = [
    "L1\n1NF wide",
    "L2\n2NF clusters",
    "L3\n3NF names",
    "L4\n+ types/PK",
    "L5\n+ FK edges",
    "L6\n+ JOIN paths",
]
SEM_LABELS = ["S1\nanonymous", "S2\nabbreviated", "S3\ndescriptive"]


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


def _text_color_for_value(norm: mpl.colors.Normalize, cmap: mpl.colors.Colormap, val_pct: float) -> str:
    if np.isnan(val_pct):
        return "#4D4D4D"
    r, g, b, _ = cmap(norm(val_pct))
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "white" if lum < 0.55 else "#272727"


def load_model_grid(
    results_dir: Path,
    model: str,
    *,
    n_bootstrap: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, List[Tuple[int, int, int, int]]]:
    """
  Returns accuracy_pct (6×3), margin_pct (6×3), and summary rows
  (struct, sem, n_correct, n).
    """
    acc = np.full((6, 3), np.nan)
    margin = np.full((6, 3), np.nan)
    summaries: List[Tuple[int, int, int, int]] = []

    pattern = f"{model.replace('/', '-')}__L*S*.csv"
    paths = sorted(results_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No CSVs matching {results_dir / pattern}")

    for path in paths:
        m = CONDITION_RE.search(path.name)
        if not m:
            continue
        sl, sem = int(m.group(1)), int(m.group(2))
        if not (1 <= sl <= 6 and 1 <= sem <= 3):
            continue
        flags = load_correct_flags(path)
        res = bootstrap_accuracy_ci(
            flags, n_bootstrap=n_bootstrap, alpha=alpha, seed=seed
        )
        i, j = sl - 1, sem - 1
        acc[i, j] = res.accuracy * 100.0
        margin[i, j] = res.margin * 100.0
        summaries.append((sl, sem, res.n_correct, res.n))

    if np.isnan(acc).any():
        missing = [
            f"L{sl}S{sem}"
            for sl in range(1, 7)
            for sem in range(1, 4)
            if np.isnan(acc[sl - 1, sem - 1])
        ]
        raise ValueError(f"Missing conditions for {model}: {', '.join(missing)}")

    return acc, margin, summaries


def plot_heatmap(
    acc_pct: np.ndarray,
    margin_pct: np.ndarray,
    *,
    model: str,
    out_stem: Path,
    vmax: float = 45.0,
) -> None:
    """Publication heatmap: color = accuracy; cell text = point ± CI half-width."""
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

    model_title = model.replace("-", " ").replace("gemini", "Gemini").title()
    ax.set_title(
        f"Execution accuracy by schema condition\n({model_title}, n=397 per cell)",
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


def print_markdown_table(acc_pct: np.ndarray, margin_pct: np.ndarray) -> None:
    print("\nMarkdown table (§6.2):\n")
    print("|  | **S1** | **S2** | **S3** |")
    print("|--|--------|--------|--------|")
    for i in range(6):
        cells = [
            f"{acc_pct[i, j]:.1f}% ± {margin_pct[i, j]:.1f}%"
            for j in range(3)
        ]
        print(f"| **L{i + 1}** | {cells[0]} | {cells[1]} | {cells[2]} |")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Plot §6.2 accuracy heatmap with bootstrap CI.")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--results-dir", type=Path, default=_ROOT / "results")
    parser.add_argument("--n-bootstrap", type=int, default=10000)
    parser.add_argument("--vmax", type=float, default=45.0, help="Color scale max (%% accuracy)")
    parser.add_argument("--no-print-table", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    acc, margin, _ = load_model_grid(
        args.results_dir,
        args.model,
        n_bootstrap=args.n_bootstrap,
    )
    safe = args.model.replace("/", "-")
    out_stem = FIG_DIR / f"main_experiment_{safe}_heatmap"

    plot_heatmap(acc, margin, model=args.model, out_stem=out_stem, vmax=args.vmax)

    if not args.no_print_table:
        print_markdown_table(acc, margin)

    print(f"\nWrote {out_stem}.{{svg,pdf,png}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
