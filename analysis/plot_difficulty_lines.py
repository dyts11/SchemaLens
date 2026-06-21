#!/usr/bin/env python3
"""
§6.4–6.5 — Difficulty × structural / semantic line charts (filled from results).

Pools question outcomes per experiment_design.md:
  - §6.4: filter by difficulty, group by structural_level, pool S1–S3
  - §6.5: filter by difficulty, group by semantic_level, pool L1–L6

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_difficulty_lines.py

    .venv/bin/python analysis/plot_difficulty_lines.py --model gemini-2.5-flash
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FIG_DIR = _ROOT / "docs" / "figures"
CONDITION_RE = re.compile(r"__L(\d+)S(\d+)\.csv$", re.IGNORECASE)

DIFF_ORDER = ["simple", "moderate", "challenging"]
DIFF_COLORS = ["#7884B4", "#B4C0E4", "#484878"]  # NMI pastel family

STRUCT_LABELS_SHORT = ["L1", "L2", "L3", "L4", "L5", "L6"]
SEM_LABELS_SHORT = ["S1", "S2", "S3"]

# §6.5 S1 only: same proximity as S2/S3; directions avoid overlap (series 0,1,2)
SEMANTIC_S1_LABEL_OFFSETS: Dict[Tuple[int, int], Tuple[float, float, str]] = {
    (0, 0): (0.0, 7.0, "center"),     # simple — above
    (0, 1): (-4.0, 0.0, "right"),     # moderate — left
    (0, 2): (0.0, -6.0, "center"),    # challenging — below
}


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


def _parse_correct(value: str) -> Optional[bool]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def load_difficulty_grids(
    results_dir: Path,
    model: str,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """
    Returns:
        diff_by_struct: (3, 6) accuracy %
        diff_by_sem: (3, 3) accuracy %
        counts: diagnostic pooled n per (difficulty, axis) cell
    """
    struct_flags: Dict[str, List[List[bool]]] = {
        d: [[] for _ in range(6)] for d in DIFF_ORDER
    }
    sem_flags: Dict[str, List[List[bool]]] = {
        d: [[] for _ in range(3)] for d in DIFF_ORDER
    }

    pattern = f"{model.replace('/', '-')}__L*S*.csv"
    paths = sorted(results_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No CSVs matching {results_dir / pattern}")

    for path in paths:
        m = CONDITION_RE.search(path.name)
        if not m:
            continue
        sl, sem = int(m.group(1)) - 1, int(m.group(2)) - 1
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                diff = (row.get("difficulty") or "").strip()
                if diff not in struct_flags:
                    continue
                parsed = _parse_correct(row.get("correct", ""))
                if parsed is None:
                    continue
                struct_flags[diff][sl].append(parsed)
                sem_flags[diff][sem].append(parsed)

    diff_by_struct = np.full((3, 6), np.nan)
    diff_by_sem = np.full((3, 3), np.nan)
    counts: Dict[str, int] = {}

    for di, diff in enumerate(DIFF_ORDER):
        for si in range(6):
            flags = struct_flags[diff][si]
            counts[f"struct:{diff}:L{si+1}"] = len(flags)
            if flags:
                diff_by_struct[di, si] = 100.0 * sum(flags) / len(flags)
        for sj in range(3):
            flags = sem_flags[diff][sj]
            counts[f"sem:{diff}:S{sj+1}"] = len(flags)
            if flags:
                diff_by_sem[di, sj] = 100.0 * sum(flags) / len(flags)

    if np.isnan(diff_by_struct).any() or np.isnan(diff_by_sem).any():
        raise ValueError("Incomplete difficulty grids — missing CSV rows or difficulty labels")

    return diff_by_struct, diff_by_sem, counts


def _label_offset_points(
    series_idx: int,
    xi: int,
    val: float,
    data: np.ndarray,
    *,
    crowded_spread: float,
) -> Tuple[float, float]:
    """
    Return (dx, dy) in points for value labels.

    When several series share similar y at one x (e.g. S1), stagger vertically
    so labels do not overlap.
    """
    col = data[:, xi]
    spread = float(np.nanmax(col) - np.nanmin(col))
    if spread >= crowded_spread:
        return (0.0, 6.0)

    n = data.shape[0]
    order = sorted(range(n), key=lambda r: col[r])  # low y → high y
    rank = order.index(series_idx)
    # bottom, middle, top label stacks (lowest y → highest y)
    dy_steps = (-16.0, 4.0, 24.0) if n == 3 else tuple(-12.0 + 14.0 * r for r in range(n))
    dy = dy_steps[rank] if rank < len(dy_steps) else 6.0 + 12.0 * rank
    return (0.0, dy)


def plot_difficulty_lines(
    data: np.ndarray,
    x_labels: list[str],
    xlabel: str,
    title: str,
    subtitle: str,
    out_stem: Path,
    *,
    y_max: float,
    crowded_spread: float = 12.0,
    fixed_label_offsets: Optional[Dict[Tuple[int, int], Tuple[float, float, str]]] = None,
    x_left_pad: float = 0.0,
) -> None:
    """Three difficulty lines (simple / moderate / challenging)."""
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.9, 2.95))
    x = np.arange(len(x_labels))
    fixed_label_offsets = fixed_label_offsets or {}

    for i, (diff_name, color) in enumerate(zip(DIFF_ORDER, DIFF_COLORS)):
        y = data[i]
        ax.plot(
            x,
            y,
            color=color,
            linewidth=1.9,
            marker="o",
            markersize=5.2,
            markerfacecolor=color,
            markeredgecolor="#272727",
            markeredgewidth=0.45,
            label=diff_name.capitalize(),
            zorder=3,
        )
        for xi, val in zip(x, y):
            key = (int(xi), i)
            if key in fixed_label_offsets:
                dx, dy, ha = fixed_label_offsets[key]
            else:
                dx, dy = _label_offset_points(
                    i, int(xi), float(val), data, crowded_spread=crowded_spread
                )
                ha = "center"
            ax.annotate(
                f"{val:.1f}",
                (xi, val),
                textcoords="offset points",
                xytext=(dx, dy),
                ha=ha,
                va="center",
                fontsize=5.5,
                color="#404040",
                fontweight="medium",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7)
    ax.set_xlabel(xlabel, fontsize=7.5, labelpad=4)
    ax.set_ylabel("Execution accuracy (%)", fontsize=7.5)
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.linspace(0, y_max, 5))
    ax.set_title(title, fontsize=8, fontweight="bold", pad=6)
    ax.legend(title="Difficulty", fontsize=6, title_fontsize=6.5, loc="best")

    half = 0.5
    ax.set_xlim(-half - x_left_pad, len(x_labels) - 1 + half)

    fig.text(
        0.5,
        0.01,
        subtitle,
        ha="center",
        fontsize=5.5,
        color="#606060",
    )

    if x_left_pad > 0:
        fig.subplots_adjust(left=0.14, bottom=0.14, right=0.97, top=0.88)
    else:
        fig.tight_layout(rect=[0, 0.04, 1, 1])
    save_pub(fig, out_stem)


def print_markdown_tables(diff_by_struct: np.ndarray, diff_by_sem: np.ndarray) -> None:
    print("\n§6.4 — Accuracy by difficulty × structural (%):\n")
    print("| Difficulty | L1 | L2 | L3 | L4 | L5 | L6 |")
    print("|------------|----|----|----|----|----|-----|")
    for i, diff in enumerate(DIFF_ORDER):
        cells = " | ".join(f"{diff_by_struct[i, j]:.1f}" for j in range(6))
        print(f"| {diff} | {cells} |")

    print("\n§6.5 — Accuracy by difficulty × semantic (%):\n")
    print("| Difficulty | S1 | S2 | S3 |")
    print("|------------|----|----|-----|")
    for i, diff in enumerate(DIFF_ORDER):
        cells = " | ".join(f"{diff_by_sem[i, j]:.1f}" for j in range(3))
        print(f"| {diff} | {cells} |")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Plot §6.4–6.5 difficulty line charts.")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--results-dir", type=Path, default=_ROOT / "results")
    parser.add_argument(
        "--only",
        choices=("both", "structure", "semantics"),
        default="both",
        help="Which figure(s) to regenerate",
    )
    parser.add_argument("--no-print-table", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

    diff_struct, diff_sem, _ = load_difficulty_grids(args.results_dir, args.model)
    model_title = args.model.replace("-", " ").replace("gemini", "Gemini").title()

    if args.only in ("both", "structure"):
        plot_difficulty_lines(
            diff_struct,
            STRUCT_LABELS_SHORT,
            "Structural level",
            f"Accuracy by difficulty × structural level\n({model_title})",
            "Pooled over S1–S3: mean correctness across all semantic levels per structural level.",
            FIG_DIR / "main_experiment_difficulty_by_structure",
            y_max=50.0,
        )
        print(f"Wrote {FIG_DIR}/main_experiment_difficulty_by_structure.{{svg,pdf,png}}")

    if args.only in ("both", "semantics"):
        plot_difficulty_lines(
            diff_sem,
            SEM_LABELS_SHORT,
            "Semantic level",
            f"Accuracy by difficulty × semantic level\n({model_title})",
            "Pooled over L1–L6: mean correctness across all structural levels per semantic level.",
            FIG_DIR / "main_experiment_difficulty_by_semantics",
            y_max=60.0,
            crowded_spread=14.0,
            fixed_label_offsets=SEMANTIC_S1_LABEL_OFFSETS,
            x_left_pad=-0.32,  # pull y-axis toward S1; keep clear of moderate label
        )
        print(f"Wrote {FIG_DIR}/main_experiment_difficulty_by_semantics.{{svg,pdf,png}}")

    if not args.no_print_table:
        print_markdown_tables(diff_struct, diff_sem)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
