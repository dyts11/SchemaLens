# Qwen2.5-Coder 0.5B–32B (L3·S3) — error type summary across model scale

Category/subtype breakdown at fixed structural/semantic level (L3, S3 — native 3NF schema,
descriptive column names) across five model sizes. Source files:
[`qwen0.5b_L3S3_manual_error_details.md`](qwen0.5b_L3S3_manual_error_details.md),
[`qwen3b_L3S3_manual_error_details.md`](qwen3b_L3S3_manual_error_details.md),
[`qwen7b_L3S3_manual_error_details.md`](qwen7b_L3S3_manual_error_details.md),
[`qwen14b_L3S3_manual_error_details.md`](qwen14b_L3S3_manual_error_details.md),
[`qwen32b_L3S3_manual_error_details.md`](qwen32b_L3S3_manual_error_details.md) — all hand-classified
against [`error_taxonomy.md`](error_taxonomy.md). As with the cross-level summary, JOIN errors'
Wrong/Missing/Extra table subtypes are consolidated into one row; see notes at the bottom for an
important caveat about the **Other** category's subtype data.

| Category / Subtype | 0.5B (n=383) | 3B (n=331) | 7B (n=301) | 14B (n=284) | 32B (n=280) |
|---|---:|---:|---:|---:|---:|
| **Invalid SQL** | **89 (23.2%)** | **35 (10.6%)** | **20 (6.6%)** | **5 (1.8%)** | **5 (1.8%)** |
| — Wrong column | 67 (17.5%) | 19 (5.7%) | 13 (4.3%) | 1 (0.4%) | 2 (0.7%) |
| — Other execution error | 20 (5.2%) | 15 (4.5%) | 5 (1.7%) | 4 (1.4%) | 3 (1.1%) |
| — Wrong table | 2 (0.5%) | 1 (0.3%) | 2 (0.7%) | 0 (0.0%) | 0 (0.0%) |
| **Schema linking** | **215 (56.1%)** | **112 (33.8%)** | **78 (25.9%)** | **67 (23.6%)** | **64 (22.9%)** |
| — Wrong column | 113 (29.5%) | 76 (23.0%) | 64 (21.3%) | 49 (17.3%) | 52 (18.6%) |
| — Wrong table | 102 (26.6%) | 36 (10.9%) | 14 (4.7%) | 18 (6.3%) | 12 (4.3%) |
| **JOIN errors** | **45 (11.7%)** | **67 (20.2%)** | **48 (15.9%)** | **31 (10.9%)** | **13 (4.6%)** |
| — Wrong/missing/extra table | 41 (10.7%) | 62 (18.7%) | 41 (13.6%) | 25 (8.8%) | 5 (1.8%) |
| — Wrong column (incl. wrong key) | 4 (1.0%) | 5 (1.5%) | 5 (1.7%) | 5 (1.8%) | 6 (2.1%) |
| — Join type error | 0 (0.0%) | 0 (0.0%) | 2 (0.7%) | 1 (0.4%) | 2 (0.7%) |
| **GROUP BY errors** | **4 (1.0%)** | **8 (2.4%)** | **11 (3.7%)** | **8 (2.8%)** | **7 (2.5%)** |
| — Wrong column (incl. missing/extra GROUP BY) | 3 (0.8%) | 8 (2.4%) | 11 (3.7%) | 8 (2.8%) | 3 (1.1%) |
| — Wrong table | 1 (0.3%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 4 (1.4%) |
| **Nesting problem** | **3 (0.8%)** | **13 (3.9%)** | **19 (6.3%)** | **17 (6.0%)** | **15 (5.4%)** |
| — Wrong sub-query | 3 (0.8%) | 6 (1.8%) | 10 (3.3%) | 11 (3.9%) | 5 (1.8%) |
| — HAVING clause mismatch | 0 (0.0%) | 6 (1.8%) | 8 (2.7%) | 5 (1.8%) | 8 (2.9%) |
| — Wrong set operation | 0 (0.0%) | 1 (0.3%) | 1 (0.3%) | 1 (0.4%) | 2 (0.7%) |
| **Predicate error** | **23 (6.0%)** | **68 (20.5%)** | **102 (33.9%)** | **135 (47.5%)** | **155 (55.4%)** |
| — Predicate semantic error | 17 (4.4%) | 49 (14.8%) | 67 (22.3%) | 67 (23.6%) | 66 (23.6%) |
| — Filter value error | 6 (1.6%) | 19 (5.7%) | 35 (11.6%) | 68 (23.9%) | 89 (31.8%) |
| **Other** | **4 (1.0%)** | **28 (8.5%)** | **23 (7.6%)** | **21 (7.4%)** | **21 (7.5%)** |

## Observations

- **The dominant failure mode flips completely across model scale.** At 0.5B, Schema linking
  (56.1%) and Invalid SQL (23.2%) together account for ~80% of all failures — the model mostly
  fails at basic schema grounding, before it even gets to a coherent predicate/structure. By 32B,
  Predicate error alone is 55.4% and Schema linking has fallen to 22.9% — the largest model rarely
  picks the wrong table/column, but still struggles with getting literal values and predicate logic
  exactly right.
- **Invalid SQL collapses monotonically and sharply**: 23.2% → 10.6% → 6.6% → 1.8% → 1.8%
  (0.5B→3B→7B→14B→32B). This is the cleanest, most monotonic trend in the table — basic
  execution-breaking mistakes (hallucinated identifiers, non-SQLite functions, malformed syntax)
  are almost entirely a small-model problem and are functionally solved by 14B.
- **Schema linking also falls sharply and monotonically** (56.1%→33.8%→25.9%→23.6%→22.9%), but
  unlike Invalid SQL it plateaus rather than vanishing — even the 32B model still puts a wrong
  real column/table in ~23% of its failures. Within Schema linking, **Wrong table shrinks much
  faster than Wrong column** (26.6%→4.3% vs 29.5%→18.6%) — larger models get much better at picking
  the right *table*, but wrong-column confusions (e.g. a same-table sibling column) persist
  proportionally longer.
- **Predicate error rises monotonically and dramatically** (6.0%→20.5%→33.9%→47.5%→55.4%) — the
  mirror image of Schema linking/Invalid SQL. This is mostly a *compositional* effect (as the
  easier failure modes get solved, what's left is disproportionately predicate-level), but the
  **Filter value error subtype's absolute count also behaves non-monotonically in share terms**
  going from 1.6%→5.7%→11.6%→23.9%→31.8%: it grows faster than Predicate semantic error
  (4.4%→14.8%→22.3%→23.6%→23.6%, which plateaus after 14B). In other words, once a model is large
  enough to get the query's *structure and function* mostly right, its remaining errors skew
  toward getting a specific *value* wrong, not the logic.
- **JOIN errors peaks at 3B (20.2%) rather than being monotonic with scale** — 0.5B (11.7%) is
  actually lower than 3B, before falling steadily from 3B onward (20.2%→15.9%→10.9%→4.6%). A
  plausible reading: 0.5B fails so early (Invalid SQL/Schema linking) that many questions never
  reach a coherent-enough join attempt to be scored as a JOIN-specific error; 3B is capable enough
  to attempt real multi-table joins but not yet reliable at getting them right, so join-plan
  mistakes become a larger share of its failures before shrinking steadily as scale increases further.
- **Nesting problem rises then plateaus** (0.8%→3.9%→6.3%→6.0%→5.4%) — very small/no models rarely
  even attempt the subquery/CTE/window-function constructs gold needs (so no mismatch is possible),
  while mid-to-large models attempt them but don't always get them right.
- **GROUP BY errors and Other stay small across the board** (≤3.7% and ≤8.5% respectively) with no
  strong scale trend — neither was ever a dominant failure mode at any model size in this study.

## Consolidation notes and caveats

- **JOIN errors**: "Wrong table," "Missing table," and "Extra table" subtypes are combined into one
  "Wrong/missing/extra table" row, matching the cross-level summary's convention.
- **Other has no comparable subtype breakdown across models.** Only the qwen14b pass recorded
  granular Other subtypes (SELECT-list shape: 4, missing/redundant DISTINCT: 12, wrong aggregate
  function or scaling: 5); the four other model-size passes (independently run) only recorded the
  top-level "Other" category with no subtype. The category-level Other totals above are directly
  comparable across all five models; the subtype composition is not, and no subtype row is shown
  for Other in this table for that reason.
- These five classification passes were run independently (separate agents), so minor
  subtype-label spelling variants were normalized to one canonical name each per category, the same
  way as the cross-level (L3–L6) summary in
  [`qwen14b_L3S3_L6S3_error_summary.md`](qwen14b_L3S3_L6S3_error_summary.md).
- All five files are at L3·S3 specifically, so this table isolates the effect of model scale alone
  — structural/semantic prompt condition is held constant, unlike the L3–L6 summary which isolates
  the effect of prompt richness at fixed model size (14B).
