#!/usr/bin/env python3
"""
Bootstrap confidence interval for execution accuracy from experiment CSVs.

Resamples question-level correct/incorrect outcomes with replacement (default
10000 replicates) and reports accuracy as point estimate ± half-width of a
percentile CI, e.g. 30.0% ± 3.0%.

Usage:
    python analysis/bootstrap_accuracy_ci.py results/llama-3.3-70b-or__L1S2.csv
    python analysis/bootstrap_accuracy_ci.py results/*.csv --alpha 0.05 --n-bootstrap 10000
    python analysis/bootstrap_accuracy_ci.py results/llama-3.3-70b-or__L1S2.csv --by db_id
"""

from __future__ import annotations

import argparse
import csv
import glob
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class BootstrapResult:
    """Accuracy point estimate and bootstrap percentile CI."""

    n: int
    n_correct: int
    accuracy: float
    ci_low: float
    ci_high: float
    n_bootstrap: int
    alpha: float

    @property
    def margin(self) -> float:
        """Half-width of the CI in the same units as accuracy (0–1)."""
        return (self.ci_high - self.ci_low) / 2.0

    def format_pct(self, decimals: int = 1) -> str:
        acc = self.accuracy * 100
        m = self.margin * 100
        lo = self.ci_low * 100
        hi = self.ci_high * 100
        pct = f"{acc:.{decimals}f}% ± {m:.{decimals}f}%"
        interval = f"[{lo:.{decimals}f}%, {hi:.{decimals}f}%]"
        return f"{pct}  (95% bootstrap CI: {interval}, n={self.n})"


def parse_correct(value: str) -> Optional[bool]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def load_correct_flags(csv_path: Path) -> List[bool]:
    """Load per-question correctness from a results CSV."""
    flags: List[bool] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "correct" not in reader.fieldnames:
            raise ValueError(f"{csv_path}: missing 'correct' column")
        for row in reader:
            parsed = parse_correct(row.get("correct", ""))
            if parsed is None:
                continue
            flags.append(parsed)
    if not flags:
        raise ValueError(f"{csv_path}: no rows with a valid 'correct' value")
    return flags


def bootstrap_accuracy_ci(
    correct: Sequence[bool],
    *,
    n_bootstrap: int = 10000,
    alpha: float = 0.05,
    seed: Optional[int] = 42,
) -> BootstrapResult:
    """
    Percentile bootstrap CI for accuracy = mean(correct).

    Args:
        correct: One bool per question (True = correct).
        n_bootstrap: Number of bootstrap replicates.
        alpha: Significance level (0.05 → 95% CI).
        seed: RNG seed for reproducibility.
    """
    n = len(correct)
    if n == 0:
        raise ValueError("empty sample")

    n_correct = sum(correct)
    point = n_correct / n

    rng = random.Random(seed)
    boot_stats: List[float] = []
    for _ in range(n_bootstrap):
        sample = [correct[rng.randrange(n)] for _ in range(n)]
        boot_stats.append(sum(sample) / n)

    boot_stats.sort()
    # Percentile method: e.g. 1000 replicates, alpha=0.05 → 2.5% and 97.5% order stats
    lo_idx = min(n_bootstrap - 1, max(0, int(n_bootstrap * (alpha / 2))))
    hi_idx = min(n_bootstrap - 1, max(0, int(n_bootstrap * (1 - alpha / 2)) - 1))

    return BootstrapResult(
        n=n,
        n_correct=n_correct,
        accuracy=point,
        ci_low=boot_stats[lo_idx],
        ci_high=boot_stats[hi_idx],
        n_bootstrap=n_bootstrap,
        alpha=alpha,
    )


def group_correct_by(
    csv_path: Path, group_col: str
) -> Dict[str, List[bool]]:
    """Group correctness flags by a CSV column (e.g. db_id, difficulty)."""
    groups: Dict[str, List[bool]] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or group_col not in reader.fieldnames:
            raise ValueError(f"{csv_path}: missing {group_col!r} column")
        for row in reader:
            parsed = parse_correct(row.get("correct", ""))
            if parsed is None:
                continue
            key = row.get(group_col, "").strip() or "(empty)"
            groups.setdefault(key, []).append(parsed)
    return groups


def expand_paths(patterns: Iterable[str]) -> List[Path]:
    paths: List[Path] = []
    for pat in patterns:
        matches = glob.glob(pat)
        if matches:
            paths.extend(Path(m) for m in sorted(matches))
        else:
            p = Path(pat)
            if p.is_file():
                paths.append(p)
    if not paths:
        raise FileNotFoundError(f"No CSV files matched: {list(patterns)}")
    return paths


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap CI for accuracy from experiment result CSVs."
    )
    parser.add_argument(
        "csv_files",
        nargs="+",
        help="Result CSV path(s) or glob (e.g. results/llama-3.3-70b-or__L1S2.csv)",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=10000,
        help="Number of bootstrap replicates (default: 10000)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level for two-sided CI (default: 0.05 → 95%%)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--by",
        dest="group_by",
        metavar="COLUMN",
        help="Also report CI per group (e.g. db_id, difficulty, question_type)",
    )
    parser.add_argument(
        "--decimals",
        type=int,
        default=1,
        help="Decimal places in percent output (default: 1)",
    )
    args = parser.parse_args(argv)

    try:
        paths = expand_paths(args.csv_files)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    ci_pct = (1 - args.alpha) * 100
    for csv_path in paths:
        print(f"\n{'=' * 60}")
        print(f"File: {csv_path}")
        print(f"Bootstrap: {args.n_bootstrap} replicates, {ci_pct:.0f}% percentile CI")
        print(f"{'=' * 60}")

        try:
            flags = load_correct_flags(csv_path)
            result = bootstrap_accuracy_ci(
                flags,
                n_bootstrap=args.n_bootstrap,
                alpha=args.alpha,
                seed=args.seed,
            )
        except ValueError as e:
            print(f"  SKIP: {e}", file=sys.stderr)
            continue

        print(f"Overall: {result.format_pct(args.decimals)}")
        print(
            f"         {result.n_correct}/{result.n} correct "
            f"({result.accuracy * 100:.2f}% raw)"
        )

        if args.group_by:
            print(f"\nBy {args.group_by}:")
            try:
                groups = group_correct_by(csv_path, args.group_by)
            except ValueError as e:
                print(f"  {e}", file=sys.stderr)
                continue
            for key in sorted(groups):
                g_flags = groups[key]
                if len(g_flags) < 2:
                    print(f"  {key}: n={len(g_flags)} (too few for bootstrap)")
                    continue
                g_result = bootstrap_accuracy_ci(
                    g_flags,
                    n_bootstrap=args.n_bootstrap,
                    alpha=args.alpha,
                    seed=args.seed,
                )
                print(f"  {key}: {g_result.format_pct(args.decimals)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
