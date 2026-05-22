#!/usr/bin/env python3
"""
Publication-style placeholder figures for the 6×3 schema-effect experiment.

Generates empty templates (no real accuracy data) to embed in
docs/experiment_design.md. Re-run after experiments by filling the
arrays below or extending this script to read results/*.csv.

Usage (from schema_effect/):
    MPLBACKEND=Agg MPLCONFIGDIR=analysis/.mplconfig \
      .venv/bin/python analysis/plot_experiment_templates.py
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Figure contract (nature-figure)
# ---------------------------------------------------------------------------
# Claim: execution accuracy varies with structural observability and semantic
#        richness; difficulty may moderate each dimension differently.
# Backend: Python / matplotlib only.

FIG_DIR = Path(__file__).resolve().parent.parent / "docs" / "figures"
HEATMAP_STEM = "main_experiment_gemini-2.5-flash"

STRUCT_LABELS_SHORT = ["L1", "L2", "L3", "L4", "L5", "L6"]
SEM_LABELS_SHORT = ["S1", "S2", "S3"]
DIFF_LABELS = ["simple", "moderate", "challenging"]
DIFF_COLORS = ["#7884B4", "#B4C0E4", "#484878"]  # NMI pastel family

STRUCT_LABELS = [
    "L1\n1NF wide",
    "L2\n2NF clusters",
    "L3\n3NF names",
    "L4\n+ types/PK",
    "L5\n+ FK edges",
    "L6\n+ JOIN paths",
]
SEM_LABELS = ["S1\nanonymous", "S2\nabbreviated", "S3\ndescriptive"]

# --- fill after experiment (NaN = placeholder) ---
ACCURACY_MATRIX = np.full((6, 3), np.nan)  # per-model heatmap

# §6.3: per model, pooled over other dimension (rows = models)
MODELS = [
    "gemini-2.5-flash",
    # "llama-3.3-70b-or",
    # "qwen2.5-coder-32b",
]
STRUCT_BY_MODEL = np.full((len(MODELS), 6), np.nan)  # mean over S1–S3
SEM_BY_MODEL = np.full((len(MODELS), 3), np.nan)  # mean over L1–L6
# Optional bootstrap half-widths (same shape); NaN → show "—" only
STRUCT_BY_MODEL_MARGIN = np.full((len(MODELS), 6), np.nan)
SEM_BY_MODEL_MARGIN = np.full((len(MODELS), 3), np.nan)

# §6.4–6.5: rows = difficulty (simple, moderate, challenging)
DIFF_BY_STRUCT = np.full((3, 6), np.nan)
DIFF_BY_SEM = np.full((3, 3), np.nan)


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


def save_pub(fig: plt.Figure, stem: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    base = FIG_DIR / stem
    fig.savefig(f"{base}.svg", bbox_inches="tight")
    fig.savefig(f"{base}.pdf", bbox_inches="tight")
    fig.savefig(f"{base}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def _fmt_cell(val: float, margin: float) -> str:
    if np.isnan(val):
        return "—"
    if np.isnan(margin):
        return f"{val:.2f}"
    return f"{val:.2f} (±{margin:.2f})"


def _build_table_matrix(
    values: np.ndarray,
    margins: np.ndarray,
    row_labels: list[str],
    col_labels: list[str],
) -> list[list[str]]:
    header = ["Model"] + col_labels
    rows = [header]
    for i, name in enumerate(row_labels):
        row = [name]
        for j in range(values.shape[1]):
            row.append(_fmt_cell(values[i, j], margins[i, j]))
        rows.append(row)
    return rows


def plot_heatmap_template() -> None:
    """§6.2 — 6×3 execution-accuracy heatmap (single model)."""
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.4, 3.8))

    cmap = mpl.cm.YlGnBu.copy()
    cmap.set_bad(color="#E8E8EC")
    masked = np.ma.masked_invalid(ACCURACY_MATRIX)

    im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=0, vmax=100, origin="upper")

    for i in range(6):
        for j in range(3):
            val = ACCURACY_MATRIX[i, j]
            text = "—" if np.isnan(val) else f"{val:.1f}"
            ax.text(j, i, text, ha="center", va="center", fontsize=8, color="#4D4D4D", fontweight="bold")

    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(SEM_LABELS, fontsize=6.5)
    ax.set_xlabel("Semantic level", fontsize=7.5, labelpad=4)
    ax.set_yticks(np.arange(6))
    ax.set_yticklabels(STRUCT_LABELS, fontsize=6.5)
    ax.set_ylabel("Structural level", fontsize=7.5, labelpad=4)
    ax.set_title(
        "Execution accuracy by schema condition\n(Gemini 2.5 Flash)",
        fontsize=8,
        fontweight="bold",
        pad=8,
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Execution accuracy (%)", fontsize=7)
    cbar.ax.tick_params(labelsize=6)
    cbar.set_ticks([0, 25, 50, 75, 100])
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(5.5, -0.5)

    fig.tight_layout()
    save_pub(fig, f"{HEATMAP_STEM}_heatmap")


def _draw_results_table(ax: plt.Axes, cell_text: list[list[str]], title: str) -> None:
    """Publication-style table (Model × level columns), like Fewshot×Model×NF layout."""
    ax.axis("off")
    nrows, ncols = len(cell_text), len(cell_text[0])
    table = ax.table(
        cellText=cell_text,
        loc="center",
        cellLoc="center",
        colWidths=[0.22] + [0.13] * (ncols - 1),
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1.0, 1.35)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#272727")
        cell.set_linewidth(0.6)
        if row == 0:
            cell.set_facecolor("#E8E8EC")
            cell.set_text_props(fontweight="bold")
        elif col == 0:
            cell.set_facecolor("#F4F4F8")
            cell.set_text_props(ha="left")
            cell.PAD = 0.08
        else:
            cell.set_facecolor("white")

    ax.set_title(title, fontsize=7.5, fontweight="bold", pad=10)


def plot_overall_marginal_tables() -> None:
    """§6.3 — Model × L1–L6 and Model × S1–S3 tables side by side."""
    _apply_pub_style()
    n_models = len(MODELS)
    fig_h = max(2.2, 0.45 * (n_models + 1))
    fig, axes = plt.subplots(1, 2, figsize=(7.4, fig_h))

    struct_cells = _build_table_matrix(
        STRUCT_BY_MODEL,
        STRUCT_BY_MODEL_MARGIN,
        MODELS,
        STRUCT_LABELS_SHORT,
    )
    sem_cells = _build_table_matrix(
        SEM_BY_MODEL,
        SEM_BY_MODEL_MARGIN,
        MODELS,
        SEM_LABELS_SHORT,
    )

    _draw_results_table(
        axes[0],
        struct_cells,
        "Overall by structural level\n(mean over S1–S3 · per model)",
    )
    _draw_results_table(
        axes[1],
        sem_cells,
        "Overall by semantic level\n(mean over L1–L6 · per model)",
    )

    fig.suptitle(
        "Marginal accuracy by model (compare L1–L6 vs S1–S3 column spread)",
        fontsize=8,
        fontweight="bold",
        y=1.04,
    )
    fig.tight_layout()
    save_pub(fig, "main_experiment_overall_marginal_tables")


def plot_difficulty_lines(
    data: np.ndarray,
    x_labels: list[str],
    xlabel: str,
    title: str,
    stem: str,
) -> None:
    """§6.4 or §6.5 — three difficulty lines over structural or semantic axis."""
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.8, 2.9))
    x = np.arange(len(x_labels))

    for i, (diff_name, color) in enumerate(zip(DIFF_LABELS, DIFF_COLORS)):
        y = data[i]
        y_plot = np.where(np.isnan(y), np.nan, y)
        ax.plot(
            x,
            y_plot,
            color=color,
            linewidth=1.8,
            marker="o",
            markersize=5,
            markerfacecolor=color,
            markeredgecolor="#272727",
            markeredgewidth=0.4,
            label=diff_name,
        )
        for xi, val in zip(x, y):
            label = "—" if np.isnan(val) else f"{val:.0f}"
            ax.annotate(
                label,
                (xi, val if not np.isnan(val) else 0),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=5.5,
                color="#606060",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7)
    ax.set_xlabel(xlabel, fontsize=7.5, labelpad=4)
    ax.set_ylabel("Execution accuracy (%)", fontsize=7.5)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title(title, fontsize=8, fontweight="bold", pad=6)
    ax.legend(title="Difficulty", fontsize=6, title_fontsize=6.5, loc="best")

    fig.tight_layout()
    save_pub(fig, stem)


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))
    plot_heatmap_template()
    plot_overall_marginal_tables()
    plot_difficulty_lines(
        DIFF_BY_STRUCT,
        STRUCT_LABELS_SHORT,
        "Structural level",
        "Accuracy by difficulty × structural level\n(pooled over S1–S3, all models)",
        "main_experiment_difficulty_by_structure",
    )
    plot_difficulty_lines(
        DIFF_BY_SEM,
        SEM_LABELS_SHORT,
        "Semantic level",
        "Accuracy by difficulty × semantic level\n(pooled over L1–L6, all models)",
        "main_experiment_difficulty_by_semantics",
    )
    print(f"Wrote figures under {FIG_DIR}/")


if __name__ == "__main__":
    main()
