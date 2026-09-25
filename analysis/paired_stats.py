#!/usr/bin/env python3
"""
Paired statistical analysis of the L×S design (question-level, not cell-level).

All 18 conditions are answered by the same questions, so per-cell CIs treat
correlated outcomes as independent and cannot say anything about a *contrast*
(a difference, or a difference-of-differences). This script:

  1. Builds a long table (question_id, db_id, L, S, correct) from results CSVs.
  2. Paired cluster bootstrap: resample databases (or questions) with
     replacement, carry every question of a sampled cluster into the replicate,
     recompute all 18 cell accuracies, and take percentile CIs for contrasts:
        * S-effect within each L:            acc(L,S3) - acc(L,S1)
        * L-effect within each S:            acc(L6,S) - acc(L1,S)
        * corner contrast:                   acc(L1,S3) - acc(L6,S1)
        * semantic×structural interaction:   [acc(L1,S3)-acc(L1,S1)] - [acc(L6,S3)-acc(L6,S1)]
  3. Parametric models:
        * Linear-probability GEE, clustered by question (sandwich SE):
          correct ~ L*S. The L6:S3 interaction coefficient IS the
          difference-of-differences on the accuracy scale; a joint Wald test of
          all L×S terms tests whether the S effect varies with L.
        * Mixed-effects logistic regression with crossed random intercepts for
          question and database (statsmodels BinomialBayesMixedGLM, variational
          Bayes). Reported as a supplement: cells near 0 % accuracy (S1) put the
          logit-scale coefficients in quasi-separation territory.

Usage (from schema_effect/):
    .venv/bin/python analysis/paired_stats.py --model qwen2.5-coder-14b-local
    .venv/bin/python analysis/paired_stats.py --model gemini-2.5-flash --results-dir results/spider --cluster question
    .venv/bin/python analysis/paired_stats.py --all      # both models × BIRD/Spider -> docs/paired_stats.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
CONDITION_RE = re.compile(r"__L(\d+)S(\d+)\.csv$", re.IGNORECASE)
LEVELS = [1, 2, 3, 4, 5, 6]
SEMS = [1, 2, 3]


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def _parse_correct(v: str):
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return 1
    if s in ("false", "0", "no"):
        return 0
    return None


def load_long(results_dir: Path, model: str, l1l2_dir: Path | None = None) -> pd.DataFrame:
    """If l1l2_dir is given, L1/L2 conditions are taken from there instead of results_dir."""
    rows: List[dict] = []
    paths = sorted(results_dir.glob(f"{model}__L*S*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CSVs for {model} in {results_dir}")
    if l1l2_dir is not None:
        paths = [p for p in paths if not re.search(r"__L[12]S", p.name)]
        paths += sorted(l1l2_dir.glob(f"{model}__L[12]S*.csv"))
    for p in paths:
        m = CONDITION_RE.search(p.name)
        if not m:
            continue
        L, S = int(m.group(1)), int(m.group(2))
        if L not in LEVELS or S not in SEMS:
            continue
        with p.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                c = _parse_correct(r.get("correct", ""))
                if c is None:
                    continue
                rows.append(
                    dict(question_id=str(r["question_id"]), db_id=r["db_id"], L=L, S=S, correct=c)
                )
    df = pd.DataFrame(rows)
    found = set(map(tuple, df[["L", "S"]].drop_duplicates().values.tolist()))
    missing = [(L, S) for L in LEVELS for S in SEMS if (L, S) not in found]
    if missing:
        raise ValueError(f"{model}: missing conditions {missing}")
    # keep only questions present in all 18 conditions (fully paired panel)
    counts = df.groupby("question_id")["L"].size()
    complete = counts[counts == len(LEVELS) * len(SEMS)].index
    dropped = len(counts) - len(complete)
    if dropped:
        print(f"[warn] {model}: dropped {dropped} questions not present in all 18 conditions", file=sys.stderr)
    df = df[df.question_id.isin(complete)].reset_index(drop=True)
    return df


def to_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[Tuple[int, int], int]]:
    """Return (M [n_q × 18], db codes [n_q], qids, colindex)."""
    wide = df.pivot_table(index="question_id", columns=["L", "S"], values="correct", aggfunc="first")
    cols = [(L, S) for L in LEVELS for S in SEMS]
    wide = wide[cols]
    colidx = {c: i for i, c in enumerate(cols)}
    db = df.drop_duplicates("question_id").set_index("question_id").loc[wide.index, "db_id"]
    db_codes = pd.factorize(db)[0]
    return wide.to_numpy(dtype=float), db_codes, wide.index.to_numpy(), colidx


# --------------------------------------------------------------------------- #
# Contrasts
# --------------------------------------------------------------------------- #
def contrast_defs(colidx):
    """Each contrast is a weight vector over the 18 cells (accuracy scale)."""
    n = len(colidx)
    C: Dict[str, np.ndarray] = {}

    def w(*terms):
        v = np.zeros(n)
        for coef, cell in terms:
            v[colidx[cell]] += coef
        return v

    for L in LEVELS:
        C[f"S3-S1 | L{L}"] = w((1, (L, 3)), (-1, (L, 1)))
    for S in SEMS:
        C[f"L6-L1 | S{S}"] = w((1, (6, S)), (-1, (1, S)))
    C["corner: L1S3 - L6S1"] = w((1, (1, 3)), (-1, (6, 1)))
    C["DID: (L1S3-L1S1) - (L6S3-L6S1)"] = w((1, (1, 3)), (-1, (1, 1)), (-1, (6, 3)), (1, (6, 1)))
    C["DID: (L1S3-L1S1) - (L3S3-L3S1)"] = w((1, (1, 3)), (-1, (1, 1)), (-1, (3, 3)), (1, (3, 1)))
    C["DID: (L3S3-L3S1) - (L6S3-L6S1)"] = w((1, (3, 3)), (-1, (3, 1)), (-1, (6, 3)), (1, (6, 1)))
    return C


def cluster_bootstrap(
    M: np.ndarray,
    cluster_codes: np.ndarray,
    contrasts: Dict[str, np.ndarray],
    n_boot: int = 5000,
    alpha: float = 0.05,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_clusters = cluster_codes.max() + 1
    # per-cluster sums and sizes -> resampling clusters == weighted sums
    sums = np.zeros((n_clusters, M.shape[1]))
    sizes = np.zeros(n_clusters)
    np.add.at(sums, cluster_codes, M)
    np.add.at(sizes, cluster_codes, 1)
    W = np.stack([c for c in contrasts.values()], axis=1)  # 18 × k
    point = (M.mean(axis=0) @ W)

    draws = rng.integers(0, n_clusters, size=(n_boot, n_clusters))
    counts = np.stack([np.bincount(d, minlength=n_clusters) for d in draws])  # n_boot × n_clusters
    acc = (counts @ sums) / (counts @ sizes)[:, None]                          # n_boot × 18
    stats = acc @ W                                                            # n_boot × k
    lo = np.percentile(stats, 100 * alpha / 2, axis=0)
    hi = np.percentile(stats, 100 * (1 - alpha / 2), axis=0)
    # two-sided bootstrap p-value: 2 * min(P(stat<=0), P(stat>=0))
    p = 2 * np.minimum((stats <= 0).mean(0), (stats >= 0).mean(0))
    p = np.minimum(p, 1.0)
    return pd.DataFrame(
        {"contrast": list(contrasts), "estimate": point, "ci_low": lo, "ci_high": hi, "boot_p": p}
    )


# --------------------------------------------------------------------------- #
# Parametric models
# --------------------------------------------------------------------------- #
def fit_gee_lpm(df: pd.DataFrame):
    """Linear-probability GEE clustered by question. Returns (result, table, wald)."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    d = df.copy()
    d["L"] = pd.Categorical(d["L"], categories=LEVELS)
    d["S"] = pd.Categorical(d["S"], categories=SEMS)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.gee(
            "correct ~ C(L) * C(S)",
            groups="question_id",
            data=d,
            family=sm.families.Gaussian(),
            cov_struct=sm.cov_struct.Exchangeable(),
        ).fit()
    inter = [n for n in res.params.index if ":" in n]
    R = np.zeros((len(inter), len(res.params)))
    for i, name in enumerate(inter):
        R[i, list(res.params.index).index(name)] = 1
    wald = res.wald_test(R, scalar=True)
    ci = res.conf_int()
    tab = pd.DataFrame(
        {"coef": res.params, "se": res.bse, "ci_low": ci[0], "ci_high": ci[1], "p": res.pvalues}
    )
    return res, tab, wald


def fit_glmm_logit(df: pd.DataFrame):
    """Crossed random-intercept logistic GLMM (question + database), VB fit."""
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    d = df.copy()
    d["L"] = pd.Categorical(d["L"], categories=LEVELS)
    d["S"] = pd.Categorical(d["S"], categories=SEMS)
    vc = {"question": "0 + C(question_id)"}
    if d["db_id"].nunique() > 2:
        vc["db"] = "0 + C(db_id)"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = BinomialBayesMixedGLM.from_formula("correct ~ C(L) * C(S)", vc, d)
        res = model.fit_vb()
    names = model.exog_names
    k = len(names)
    mean = res.fe_mean
    sd = res.fe_sd
    tab = pd.DataFrame(
        {
            "coef_logit": mean,
            "sd": sd,
            "ci_low": mean - 1.96 * sd,
            "ci_high": mean + 1.96 * sd,
            "z": mean / sd,
        },
        index=names,
    )
    vcp = pd.Series(np.exp(res.vcp_mean), index=model.vcp_names, name="random_intercept_sd")
    return res, tab, vcp


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _fmt_pct(x):
    return f"{100*x:+.1f}"


def analyse(results_dir: Path, model: str, cluster: str, n_boot: int, seed: int, out: List[str],
            l1l2_dir: Path | None = None):
    df = load_long(results_dir, model, l1l2_dir)
    M, db_codes, qids, colidx = to_matrix(df)
    n_q = M.shape[0]
    n_db = db_codes.max() + 1
    codes = db_codes if cluster == "db" else np.arange(n_q)
    dataset = "Spider" if "spider" in str(results_dir).lower() else "BIRD"
    cell = pd.Series(M.mean(0), index=list(colidx))

    src = f"{results_dir}" + (f"; L1/L2 from {l1l2_dir}" if l1l2_dir else "")
    out.append(f"## {model} — {dataset} ({src})\n")
    out.append(f"Paired panel: {n_q} questions × 18 conditions, {n_db} databases. "
               f"Bootstrap clusters: **{cluster}** ({n_boot} replicates, seed {seed}).\n")
    out.append("Cell accuracies (%):\n")
    out.append("| | S1 | S2 | S3 |\n|--|--|--|--|")
    for L in LEVELS:
        out.append(f"| L{L} | " + " | ".join(f"{100*cell[(L,S)]:.1f}" for S in SEMS) + " |")
    out.append("")

    # ---- bootstrap ----
    C = contrast_defs(colidx)
    bt = cluster_bootstrap(M, codes, C, n_boot=n_boot, seed=seed)
    out.append(f"### Paired cluster bootstrap (by {cluster}) — contrasts on the accuracy scale (percentage points)\n")
    out.append("| contrast | estimate | 95% CI | boot p |\n|--|--|--|--|")
    for _, r in bt.iterrows():
        sig = "" if r.ci_low <= 0 <= r.ci_high else " *"
        out.append(f"| {r.contrast} | {_fmt_pct(r.estimate)} | [{_fmt_pct(r.ci_low)}, {_fmt_pct(r.ci_high)}]{sig} | {r.boot_p:.3f} |")
    out.append("\n`*` = 95% CI excludes 0.\n")

    # ---- GEE ----
    try:
        res, tab, wald = fit_gee_lpm(df)
        out.append("### Linear-probability GEE, clustered by question (sandwich SE)\n")
        out.append(f"Joint Wald test of all L×S interaction terms (H0: S effect identical across L): "
                   f"χ²({int(wald.df_denom) if hasattr(wald,'df_denom') and wald.df_denom else len([n for n in tab.index if ':' in n])}) = "
                   f"{float(np.squeeze(wald.statistic)):.2f}, p = {float(np.squeeze(wald.pvalue)):.2e}\n")
        key = [n for n in tab.index if n in ("C(L)[T.6]:C(S)[T.3]", "C(L)[T.3]:C(S)[T.3]", "C(L)[T.6]:C(S)[T.2]", "C(S)[T.3]", "C(L)[T.6]")]
        out.append("| term | coef (pp) | 95% CI | p |\n|--|--|--|--|")
        for n in key:
            r = tab.loc[n]
            out.append(f"| `{n}` | {_fmt_pct(r.coef)} | [{_fmt_pct(r.ci_low)}, {_fmt_pct(r.ci_high)}] | {r.p:.2e} |")
        out.append("\nReference cell L1·S1. `C(S)[T.3]` = S3−S1 at L1; `C(L)[T.6]` = L6−L1 at S1; "
                   "`C(L)[T.6]:C(S)[T.3]` = (L6S3−L6S1) − (L1S3−L1S1), i.e. minus the bootstrap DID.\n")
    except Exception as e:  # pragma: no cover
        out.append(f"GEE failed: {e}\n")

    # ---- GLMM ----
    try:
        res, tab, vcp = fit_glmm_logit(df)
        out.append("### Mixed-effects logistic regression, crossed random intercepts (question" +
                   (" + database" if n_db > 2 else "") + "), variational Bayes\n")
        out.append("Random-intercept SDs: " + ", ".join(f"{k} = {v:.2f}" for k, v in vcp.items()) + "\n")
        key = [n for n in tab.index if n in ("C(L)[T.6]:C(S)[T.3]", "C(L)[T.3]:C(S)[T.3]", "C(S)[T.3]", "C(L)[T.6]")]
        out.append("| term | log-odds | 95% CI | z |\n|--|--|--|--|")
        for n in key:
            r = tab.loc[n]
            out.append(f"| `{n}` | {r.coef_logit:+.2f} | [{r.ci_low:+.2f}, {r.ci_high:+.2f}] | {r.z:+.1f} |")
        inter = tab[[":" in n for n in tab.index]]
        out.append(f"\nAll {len(inter)} interaction terms: {int((np.sign(inter.ci_low)==np.sign(inter.ci_high)).sum())} have 95% CI excluding 0. "
                   "Caution: S1 cells near 0 % accuracy make logit-scale coefficients large and imprecise (quasi-separation); "
                   "prefer the accuracy-scale bootstrap/GEE for magnitudes.\n")
    except Exception as e:  # pragma: no cover
        out.append(f"GLMM failed: {e}\n")
    return bt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-coder-14b-local")
    ap.add_argument("--results-dir", default="results/full")
    ap.add_argument("--cluster", choices=["db", "question"], default="db")
    ap.add_argument("--n-boot", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--all", action="store_true", help="both models × BIRD/Spider -> docs/paired_stats.md")
    ap.add_argument("--out", default=None)
    ap.add_argument("--l1l2-dir", default=None,
                    help="take L1/L2 conditions from this dir (e.g. results/without_denorm_notice)")
    args = ap.parse_args()

    out: List[str] = ["# Paired statistics for the L×S design\n",
                      "Generated by `analysis/paired_stats.py`. All contrasts are computed on the same questions "
                      "across conditions (paired), with cluster bootstrap CIs and question-clustered GEE / crossed "
                      "random-intercept GLMM.\n"]
    if args.all:
        runs = [
            (Path("results/full"), "qwen2.5-coder-14b-local", "db"),
            (Path("results/full"), "qwen2.5-coder-14b-local", "question"),
            (Path("results/full"), "gemini-2.5-flash", "db"),
            (Path("results/full"), "gemini-2.5-flash", "question"),
            (Path("results/spider"), "qwen2.5-coder-14b-local", "question"),
            (Path("results/spider"), "gemini-2.5-flash", "question"),
        ]
        for rd, model, cl in runs:
            analyse(_ROOT / rd, model, cl, args.n_boot, args.seed, out)
        for cl in ("db", "question"):
            analyse(_ROOT / "results/full", "qwen2.5-coder-14b-local", cl, args.n_boot, args.seed, out,
                    l1l2_dir=_ROOT / "results/without_denorm_notice")
        out_path = Path(args.out or _ROOT / "docs" / "paired_stats.md")
    else:
        analyse(_ROOT / args.results_dir, args.model, args.cluster, args.n_boot, args.seed, out,
                l1l2_dir=(_ROOT / args.l1l2_dir) if args.l1l2_dir else None)
        out_path = Path(args.out) if args.out else None
    text = "\n".join(out)
    print(text)
    if out_path:
        out_path.write_text(text, encoding="utf-8")
        print(f"\n[written] {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
