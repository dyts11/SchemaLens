# Qwen2.5-Coder-14B · L3–L6 (S3) — error type summary across structural levels

Category/subtype breakdown for `qwen2.5-coder-14b-local` at semantic level S3, across the four
structural levels that share the same physical 3NF schema and gold SQL (L3 baseline → L4 adds
types/PK/NOT NULL → L5 adds FK relationships → L6 adds JOIN PATH examples). Source files:
[`qwen14b_L3S3_manual_error_details.md`](qwen14b_L3S3_manual_error_details.md),
[`qwen14b_L4S3_manual_error_details.md`](qwen14b_L4S3_manual_error_details.md),
[`qwen14b_L5S3_manual_error_details.md`](qwen14b_L5S3_manual_error_details.md),
[`qwen14b_L6S3_manual_error_details.md`](qwen14b_L6S3_manual_error_details.md) — all hand-classified
against [`error_taxonomy.md`](error_taxonomy.md). Minor subtype-label spelling variants across the
four classification passes have been normalized to one canonical name each, and a few subtypes
have been consolidated for readability (JOIN errors' Wrong/Missing/Extra table into one row;
Other's DISTINCT/LIMIT/tie-handling/SELECT-list-shape into one row) — see notes at the bottom.

| Category / Subtype | L3·S3 (n=284) | L4·S3 (n=275) | L5·S3 (n=281) | L6·S3 (n=280) |
|---|---:|---:|---:|---:|
| **Invalid SQL** | **5 (1.8%)** | **7 (2.5%)** | **7 (2.5%)** | **8 (2.9%)** |
| — Other execution error | 4 (1.4%) | 5 (1.8%) | 5 (1.8%) | 6 (2.1%) |
| — Wrong column | 1 (0.4%) | 1 (0.4%) | 2 (0.7%) | 2 (0.7%) |
| — Wrong table | 0 (0.0%) | 1 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| **Schema linking** | **67 (23.6%)** | **64 (23.3%)** | **62 (22.1%)** | **67 (23.9%)** |
| — Wrong column | 49 (17.3%) | 48 (17.5%) | 48 (17.1%) | 50 (17.9%) |
| — Wrong table | 18 (6.3%) | 16 (5.8%) | 14 (5.0%) | 17 (6.1%) |
| **JOIN errors** | **31 (10.9%)** | **28 (10.2%)** | **25 (8.9%)** | **21 (7.5%)** |
| — Wrong/missing/extra table | 25 (8.8%) | 23 (8.4%) | 17 (6.0%) | 14 (5.0%) |
| — Wrong column (incl. wrong key) | 5 (1.8%) | 3 (1.1%) | 4 (1.4%) | 3 (1.1%) |
| — Join type error | 1 (0.4%) | 2 (0.7%) | 4 (1.4%) | 4 (1.4%) |
| **Fan-out** *(L1/L2 only — never fires at L3–L6)* | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **GROUP BY errors** | **8 (2.8%)** | **16 (5.8%)** | **6 (2.1%)** | **7 (2.5%)** |
| — Wrong column (incl. missing/extra GROUP BY) | 8 (2.8%) | 16 (5.8%) | 6 (2.1%) | 7 (2.5%) |
| — Wrong table | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **Nesting problem** | **17 (6.0%)** | **17 (6.2%)** | **16 (5.7%)** | **12 (4.3%)** |
| — Wrong sub-query | 11 (3.9%) | 12 (4.4%) | 10 (3.6%) | 8 (2.9%) |
| — HAVING clause mismatch | 5 (1.8%) | 3 (1.1%) | 4 (1.4%) | 3 (1.1%) |
| — Wrong set operation | 1 (0.4%) | 2 (0.7%) | 2 (0.7%) | 1 (0.4%) |
| **Predicate error** | **135 (47.5%)** | **125 (45.5%)** | **147 (52.3%)** | **147 (52.5%)** |
| — Filter value error | 68 (23.9%) | 67 (24.4%) | 83 (29.5%) | 82 (29.3%) |
| — Predicate semantic error | 67 (23.6%) | 58 (21.1%) | 64 (22.8%) | 65 (23.2%) |
| **Other** | **21 (7.4%)** | **18 (6.5%)** | **18 (6.4%)** | **18 (6.4%)** |
| — Missing/redundant DISTINCT, LIMIT, tie-handling, or SELECT-list shape | 16 (5.6%) | 16 (5.8%) | 16 (5.7%) | 15 (5.4%) |
| — Wrong aggregate function or scaling | 5 (1.8%) | 2 (0.7%) | 2 (0.7%) | 3 (1.1%) |

## Observations

- **Predicate error is the dominant failure mode at every level** (~46–53% of all failures), and
  grows as a *share* from L3/L4 to L5/L6 — richer schema metadata doesn't reduce value/predicate
  mistakes, it mainly eliminates some structural ones, which mechanically raises Predicate error's
  share of what's left.
- **Filter value error grows sharply from L3/L4 (~24%) to L5/L6 (~29–30%)** — the single biggest
  subtype shift in the table. FK annotations (L5) and join-path examples (L6) apparently redirect
  the model's remaining capacity toward getting structure right, at the cost of more literal-value
  slips.
- **JOIN / wrong-missing-extra-table collapses from ~8.8% (L3) to ~5.0% (L6)** — the clearest
  monotonic improvement in the table, consistent with richer relationship metadata directly
  reducing join-plan mistakes. Within this bucket, the *character* of the mistake also shifts: at
  L3/L4 it's almost entirely omitted joins; by L5/L6 a meaningful share becomes "joined the wrong
  table" instead of "forgot to join" (see the source files for the wrong-table vs missing-table
  split before consolidation).
- **Schema linking is essentially flat across all four levels** (~22–24% total, ~17% wrong-column /
  ~6% wrong-table split unchanged) — the one category totally unmoved by prompt richness. More
  metadata doesn't help the model pick the *right* real column/table any more reliably.
- **GROUP BY errors spikes at L4 (5.8%, n=16) then drops back to ~2–2.5% at L5/L6** — worth treating
  as a possible local anomaly (small n) rather than a real trend given it doesn't fit the otherwise
  monotonic pattern of the surrounding categories.
- **Nesting / wrong sub-query trends down (3.9%→2.9%, L3→L6)**, consistent with explicit schema
  structure helping the model reproduce required CTEs/window functions more reliably.
- **Invalid SQL and Other stay small and roughly flat** (~2–3% and ~6.5–7.5% respectively) across
  all four levels — neither was ever a major failure mode at this model scale, and structural
  prompt richness doesn't move them much either way.

## Consolidation notes

Two categories' subtypes were merged for this summary (per-question detail with the original,
more granular subtypes is preserved in each level's source file):

- **JOIN errors**: "Wrong table," "Missing table," and "Extra table" (all originally under the
  taxonomy's "Wrong table" subtype, but tracked separately by table-set-size direction in some
  classification passes) are combined into one "Wrong/missing/extra table" row.
- **Other**: "Missing/redundant DISTINCT," "Missing LIMIT," "Tie-handling," and "SELECT-list shape"
  are combined into one row, leaving "Wrong aggregate function or scaling" as the only other
  Other subtype.

Category-level totals (bolded rows) are unaffected by these merges and sum exactly to each level's
total failure count (n=284/275/281/280 for L3/L4/L5/L6 respectively).
