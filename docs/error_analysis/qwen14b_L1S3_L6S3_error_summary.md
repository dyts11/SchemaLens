# Error type summary across structural level, semantic level, model scale, and prompting method

Four separate comparison tables, each varying **one** axis while holding the others fixed, all
hand-classified against [`error_taxonomy.md`](error_taxonomy.md) with the same subtype
normalization throughout (JOIN errors' Wrong/Missing/Extra table merged into one row; Other's
subtypes not compared in detail since only some passes recorded them granularly):

1. **Structural level L1–L6**, fixed at S3, fixed at `qwen2.5-coder-14b-local` — below.
2. **Semantic level S1–S3**, fixed at L3, fixed at `qwen2.5-coder-14b-local` — further down.
3. **Model scale 0.5B–32B**, fixed at L3·S3 — further down still.
4. **Prompting method** (zero-shot / few-shot / reflexion / dense), fixed at L3·S3, fixed at
   `qwen2.5-coder-14b-local` — last.

## Structural level (L1–L6, S3, qwen2.5-coder-14b-local)

Category/subtype breakdown for `qwen2.5-coder-14b-local` at semantic level S3, across all six
structural levels this study covers: **L1** (1NF wide table `one_nf_0`), **L2** (2NF synthetic
clusters `two_nf_*`), **L3** (3NF baseline), **L4** (L3 + types/PK/NOT NULL), **L5** (L4 + FK
relationships), **L6** (L5 + JOIN PATH examples). L3–L6 share the same physical 3NF schema and gold
SQL; L1/L2 replace it with denormalised representations (see
[`qwen14b_L1S3_manual_error_details.md`](qwen14b_L1S3_manual_error_details.md) and
[`qwen14b_L2S3_manual_error_details.md`](qwen14b_L2S3_manual_error_details.md) for the exact
wide-table/cluster construction). This originally extended
[`qwen14b_L3S3_L6S3_error_summary.md`](qwen14b_L3S3_L6S3_error_summary.md) with the two
denormalised levels.

| Category / Subtype | L1·S3 (n=317) | L2·S3 (n=319) | L3·S3 (n=284) | L4·S3 (n=275) | L5·S3 (n=281) | L6·S3 (n=280) |
|---|---:|---:|---:|---:|---:|---:|
| **Invalid SQL** | **76 (24.0%)** | **101 (31.7%)** | **5 (1.8%)** | **7 (2.5%)** | **7 (2.5%)** | **8 (2.9%)** |
| — Wrong column | 50 (15.8%) | 48 (15.0%) | 1 (0.4%) | 1 (0.4%) | 2 (0.7%) | 2 (0.7%) |
| — Wrong table | 23 (7.3%) | 49 (15.4%) | 0 (0.0%) | 1 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| — Other execution error | 3 (0.9%) | 4 (1.3%) | 4 (1.4%) | 5 (1.8%) | 5 (1.8%) | 6 (2.1%) |
| **Schema linking** | **66 (20.8%)** | **59 (18.5%)** | **67 (23.6%)** | **64 (23.3%)** | **62 (22.1%)** | **67 (23.9%)** |
| — Wrong column | 57 (18.0%) | 47 (14.7%) | 49 (17.3%) | 48 (17.5%) | 48 (17.1%) | 50 (17.9%) |
| — Wrong table | 9 (2.8%) | 12 (3.8%) | 18 (6.3%) | 16 (5.8%) | 14 (5.0%) | 17 (6.1%) |
| **JOIN errors** | **0 (0.0%)** | **4 (1.3%)** | **31 (10.9%)** | **28 (10.2%)** | **25 (8.9%)** | **21 (7.5%)** |
| — Wrong/missing/extra table | 0 (0.0%) | 4 (1.3%) | 25 (8.8%) | 23 (8.4%) | 17 (6.0%) | 14 (5.0%) |
| — Wrong column (incl. wrong key) | 0 (0.0%) | 0 (0.0%) | 5 (1.8%) | 3 (1.1%) | 4 (1.4%) | 3 (1.1%) |
| — Join type error | 0 (0.0%) | 0 (0.0%) | 1 (0.4%) | 2 (0.7%) | 4 (1.4%) | 4 (1.4%) |
| **Fan-out** | **22 (6.9%)** | **15 (4.7%)** | **0 (0.0%)** | **0 (0.0%)** | **0 (0.0%)** | **0 (0.0%)** |
| — Irrecoverable | 12 (3.8%) | 8 (2.5%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| — Recoverable | 10 (3.2%) | 7 (2.2%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **GROUP BY errors** | **7 (2.2%)** | **9 (2.8%)** | **8 (2.8%)** | **16 (5.8%)** | **6 (2.1%)** | **7 (2.5%)** |
| **Nesting problem** | **13 (4.1%)** | **13 (4.1%)** | **17 (6.0%)** | **17 (6.2%)** | **16 (5.7%)** | **12 (4.3%)** |
| — Wrong sub-query | 9 (2.8%) | 8 (2.5%) | 11 (3.9%) | 12 (4.4%) | 10 (3.6%) | 8 (2.9%) |
| — HAVING clause mismatch | 4 (1.3%) | 4 (1.3%) | 5 (1.8%) | 3 (1.1%) | 4 (1.4%) | 3 (1.1%) |
| — Wrong set operation | 0 (0.0%) | 1 (0.3%) | 1 (0.4%) | 2 (0.7%) | 2 (0.7%) | 1 (0.4%) |
| **Predicate error** | **113 (35.6%)** | **104 (32.6%)** | **135 (47.5%)** | **125 (45.5%)** | **147 (52.3%)** | **147 (52.5%)** |
| — Filter value error | 52 (16.4%) | 43 (13.5%) | 68 (23.9%) | 67 (24.4%) | 83 (29.5%) | 82 (29.3%) |
| — Predicate semantic error | 61 (19.2%) | 61 (19.1%) | 67 (23.6%) | 58 (21.1%) | 64 (22.8%) | 65 (23.2%) |
| **Other** | **20 (6.3%)** | **14 (4.4%)** | **21 (7.4%)** | **18 (6.5%)** | **18 (6.4%)** | **18 (6.4%)** |

### Observations

- **Invalid SQL is the single starkest structural-level effect in this whole study.** It's ~24–32%
  at L1/L2 — by far the largest category at those two levels — and collapses to ~2–3% at L3–L6, a
  ~12x drop. This tracks the mechanical fragility of the denormalised naming convention:
  `table__column`-style wide-table names require the model to get a compound identifier exactly
  right (correct stem *and* correct mapped name, or a required table-prefix at all), where L3–L6's
  plain single-word column names are much harder to typo or malform. **L2 is actually worse than
  L1 on this** (31.7% vs 24.0%, driven almost entirely by Wrong table: 15.4% vs 7.3%) — despite L2
  being the "less denormalised" level, its multiple `two_nf_*` cluster tables apparently make it
  *easier* for the model to reference a table that doesn't exist (wrong cluster name, or a bare
  3NF table name that was never materialised) than L1's single `one_nf_0` target.
- **JOIN errors is the mirror image**: literally 0% at L1 (there is nothing to join — one flat
  table), a residual 1.3% at L2 (only fires when a question's answer genuinely needs two different
  clusters joined together), then jumps to ~10.9% at L3 and declines steadily to 7.5% by L6 as
  richer relationship metadata helps. Denormalisation doesn't reduce join mistakes so much as
  **remove the possibility of making them** — a structural, not a skill, effect.
- **Fan-out exists only at L1/L2 by construction** (0% everywhere else, since it requires a
  materialised denormalised view to occur at all) — but **L1's rate is ~1.5x L2's** (6.9% vs 4.7%).
  This is a direct, measurable payoff of L2's cluster design choice to keep sibling fact tables
  (e.g. `trans`/`loan`/`order`, or `hero_attribute`/`hero_power`) in **separate** clusters rather
  than merging them into one wide table — exactly the failure mode that design was meant to avoid.
- **Predicate error is lowest exactly where Invalid SQL is highest** (L1: 35.6%, L2: 32.6%) and
  rises steadily from L3 (47.5%) to L6 (52.5%) — consistent with a compositional effect: when a
  large share of failures never even execute (L1/L2's Invalid SQL), predicate-level mistakes can't
  dominate the failure mix the way they do once execution errors become rare (L3+).
- **Schema linking is remarkably stable across all six levels** (18.5–23.9%, no clear monotonic
  trend by level) — the one category that seems genuinely indifferent to *both* denormalisation
  and prompt-metadata richness. Picking the wrong real column/table for a question's intent appears
  to be a stable, structure-independent error mode for this model.
- **GROUP BY errors, Nesting problem, and Other all stay in a narrow band** (2.1–5.8%, 4.1–6.2%,
  4.4–7.4% respectively) across every level, with no strong level-linked trend beyond L4's isolated
  GROUP BY spike (5.8%, likely noise at n=16 — flagged the same way in the L3–L6-only summary).

### Two regimes, not one smooth trend

Read together with [`qwen14b_L3S3_L6S3_error_summary.md`](qwen14b_L3S3_L6S3_error_summary.md)'s
finding that Predicate error keeps rising and JOIN errors keeps falling from L3→L6, the full L1–L6
picture is really **two distinct regimes** rather than one continuous six-point trend:

1. **L1/L2 (denormalised)**: dominated by execution-breaking Invalid SQL and level-specific
   Fan-out, both structural artifacts of the flattened schema representation itself, not deep
   reasoning failures.
2. **L3–L6 (normalised, increasing metadata)**: Invalid SQL and Fan-out are essentially solved;
   the failure mix is a smooth, monotonic trade-off between JOIN errors (falling, as relationship
   metadata richens) and Predicate error (rising, as the model's remaining errors concentrate in
   value/predicate-level mistakes once structure is mostly right).

The jump between regimes (L2→L3) is far larger than any single step within either regime — the
choice of *whether* to denormalise the schema matters more to the error profile than *how much*
metadata is added on top of a normalised one.

## Semantic level (S1–S3, L3, qwen2.5-coder-14b-local)

Everything above holds semantic level fixed at S3 and varies structural level. This table does the
opposite — fixes structural level at **L3** (native 3NF) and varies semantic level: **S1**
(anonymised `col_a`, `col_b`, … columns, assigned per-table positionally — see
[`qwen14b_L3S1_manual_error_details.md`](qwen14b_L3S1_manual_error_details.md) for the exact
decoding mechanism), **S2** (abbreviated column names, e.g. `cds_cd`), **S3** (descriptive column
names, e.g. `county_district_school_code`). Same gold SQL and physical schema at all three — only
the column-naming scheme shown to the model changes. All three hand-classified against
[`error_taxonomy.md`](error_taxonomy.md); same subtype normalization as above (JOIN errors'
Wrong/Missing/Extra table merged into one row; Other's subtypes not compared in detail).

| Category / Subtype | L3·S1 (n=387) | L3·S2 (n=284) | L3·S3 (n=284) |
|---|---:|---:|---:|
| **Invalid SQL** | **24 (6.2%)** | **10 (3.5%)** | **5 (1.8%)** |
| — Wrong column | 6 (1.6%) | 1 (0.4%) | 1 (0.4%) |
| — Other execution error | 18 (4.7%) | 9 (3.2%) | 4 (1.4%) |
| **Schema linking** | **198 (51.2%)** | **75 (26.4%)** | **67 (23.6%)** |
| — Wrong column | 158 (40.8%) | 58 (20.4%) | 49 (17.3%) |
| — Wrong table | 40 (10.3%) | 17 (6.0%) | 18 (6.3%) |
| **JOIN errors** | **156 (40.3%)** | **29 (10.2%)** | **31 (10.9%)** |
| — Wrong/missing/extra table | 110 (28.4%) | 22 (7.7%) | 25 (8.8%) |
| — Wrong column (incl. wrong key) | 46 (11.9%) | 5 (1.8%) | 5 (1.8%) |
| — Join type error | 0 (0.0%) | 2 (0.7%) | 1 (0.4%) |
| **GROUP BY errors** | **0 (0.0%)** | **8 (2.8%)** | **8 (2.8%)** |
| **Nesting problem** | **1 (0.3%)** | **10 (3.5%)** | **17 (6.0%)** |
| — Wrong sub-query | 0 (0.0%) | 6 (2.1%) | 11 (3.9%) |
| — HAVING clause mismatch | 1 (0.3%) | 3 (1.1%) | 5 (1.8%) |
| — Wrong set operation | 0 (0.0%) | 1 (0.4%) | 1 (0.4%) |
| **Predicate error** | **7 (1.8%)** | **129 (45.4%)** | **135 (47.5%)** |
| — Filter value error | 4 (1.0%) | 70 (24.6%) | 68 (23.9%) |
| — Predicate semantic error | 3 (0.8%) | 59 (20.8%) | 67 (23.6%) |
| **Other** | **1 (0.3%)** | **23 (8.1%)** | **21 (7.4%)** |

### Observations

- **S1 collapses even more completely than L1/L2 did, and for a related but distinct reason.**
  Schema linking + JOIN errors alone account for **91.5%** of S1's failures (vs. L1's 20.8%+0%=20.8%
  and L2's 18.5%+1.3%=19.8% for the same two categories) — at S1 the model has zero naming signal
  at all (every column is `col_a`, `col_b`, … reused per-table), so it can't reliably pick the right
  real column *or* the right real join key almost regardless of how well-structured the schema
  otherwise is. This is a **naming-signal collapse**, distinct from L1/L2's **schema-representation
  collapse** (dominated by Invalid SQL instead) — both produce a similarly lopsided failure profile,
  but for different underlying reasons, and they don't compound in the same category (S1's dominant
  failure mode is picking the wrong real identifier; L1/L2's is failing to construct a valid
  identifier at all).
- **JOIN errors is dramatically larger at S1 (40.3%) than anywhere else in this entire study** —
  more than triple L3·S3's 10.9%, and even bigger than L1/L2's Invalid SQL rates. Without column
  names to reason about, the model still generally recognises *that* two tables need connecting
  (join structure survives anonymisation reasonably well) but frequently guesses the wrong
  positional column as the join key. Note that `docs/error_analysis/qwen14b_L3S1_manual_error_details.md` was
  classified before this project's category-boundary rule was finalized (Schema linking wins over
  JOIN errors when an independently-severe wrong-column bug coexists with a wrong join key) —
  a later audit of that file's Schema-linking entries found the rule was already being applied
  correctly there in practice, but its JOIN errors entries have not been re-audited against the
  same standard, so the 40.3% JOIN errors figure for S1 should be treated as a reasonable estimate
  rather than a fully reconciled number.
- **Predicate error is almost entirely absent at S1 (1.8%) then jumps to ~45–47% at S2/S3** — the
  single largest swing of any category on any axis in this whole study (a ~25x relative jump from
  S1 to S2). This makes sense structurally: a model that can't reliably find the right column or
  join key essentially never gets far enough into a *correct* query skeleton for a subtler
  value/predicate-level mistake to be the deciding factor — Predicate error requires everything
  else to already be right. S2's partial naming signal (abbreviations) is already enough to close
  almost the entire gap to S3's full descriptive names (45.4% vs 47.5%) — most of the value here
  comes from having *any* real naming signal at all, not from how rich it is.
- **GROUP BY errors and Nesting problem are essentially zero at S1** (0.0%, 0.3%) and only appear
  once real naming is available (S2: 2.8%/3.5%, S3: 2.8%/6.0%) — mirroring the Predicate error
  pattern: these are "polish" failure modes that presuppose the model already got far enough into a
  structurally sound query to have a `GROUP BY` or subquery worth getting subtly wrong in the first
  place.
- **Invalid SQL falls monotonically as naming signal increases** (6.2% → 3.5% → 1.8%), the same
  direction as the L1→L6 structural trend but starting from a much smaller base — S1 still executes
  successfully far more often than L1/L2 do, because unlike the denormalised wide-table naming
  convention, a bare `col_a` reference is always syntactically valid (it just may be semantically
  wrong), whereas a malformed `table__column` compound identifier often isn't valid SQL at all.

This third axis reinforces the same overall message as the L1–L6 comparison: **whichever ingredient
of "enough signal to build a structurally sound query" is missing — normalised schema structure, or
real column names — the failure profile collapses toward the same two categories (Schema linking
and, depending on which ingredient is missing, either Invalid SQL or JOIN errors), and the
"interesting," paper-worthy failure modes (Predicate error, Nesting problem, GROUP BY errors) only
show up once the model has enough to work with to get most of a query right.**

## Model scale (0.5B–32B, L3·S3)

Category/subtype breakdown at fixed structural/semantic level (L3, S3 — native 3NF schema,
descriptive column names) across five model sizes. Source files:
[`qwen0.5b_L3S3_manual_error_details.md`](qwen0.5b_L3S3_manual_error_details.md),
[`qwen3b_L3S3_manual_error_details.md`](qwen3b_L3S3_manual_error_details.md),
[`qwen7b_L3S3_manual_error_details.md`](qwen7b_L3S3_manual_error_details.md),
[`qwen14b_L3S3_manual_error_details.md`](qwen14b_L3S3_manual_error_details.md),
[`qwen32b_L3S3_manual_error_details.md`](qwen32b_L3S3_manual_error_details.md). This isolates the
effect of model scale alone — structural/semantic prompt condition is held constant, unlike the
first two tables above which isolate prompt-condition effects at fixed (14B) model size.

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

### Observations

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

### Consolidation notes and caveats

- **Other has no comparable subtype breakdown across models.** Only the qwen14b pass recorded
  granular Other subtypes (SELECT-list shape: 4, missing/redundant DISTINCT: 12, wrong aggregate
  function or scaling: 5); the four other model-size passes (independently run) only recorded the
  top-level "Other" category with no subtype. The category-level Other totals above are directly
  comparable across all five models; the subtype composition is not, and no subtype row is shown
  for Other in this table for that reason.
- These five classification passes were run independently (separate agents), so minor
  subtype-label spelling variants were normalized to one canonical name each per category.

## Prompting method (zero-shot / few-shot / reflexion / dense, L3·S3, qwen2.5-coder-14b-local)

Category/subtype breakdown at fixed structural/semantic level (L3, S3) and fixed model
(`qwen2.5-coder-14b-local`), varying the prompting/inference method: **zero-shot** (baseline,
`results/full/`), **few-shot** (3 in-context examples, `results/fewshot/`, evaluated on a
held-out 370-question subset excluding the 27 reserved as the example pool — so its `n` is smaller
than the others by construction, not because more questions were answered correctly), **reflexion**
(zero-shot generation + 1 self-correction retry triggered on execution failure, `results/reflexion/`),
**dense** (few-shot with dense-retrieval example selection — the 3 in-context examples are the most
semantically similar questions per-question, via sentence-embedding cosine similarity over a
same-`db_id` pool, rather than few-shot's fixed per-database example set, `results/dense/`).
Source files: [`qwen14b_L3S3_manual_error_details.md`](qwen14b_L3S3_manual_error_details.md),
[`qwen14b_fewshot_L3S3_manual_error_details.md`](qwen14b_fewshot_L3S3_manual_error_details.md),
[`qwen14b_reflexion_L3S3_manual_error_details.md`](qwen14b_reflexion_L3S3_manual_error_details.md),
[`qwen14b_dense_L3S3_manual_error_details.md`](qwen14b_dense_L3S3_manual_error_details.md).

| Category / Subtype | Zero-shot (n=284) | Few-shot (n=250) | Reflexion (n=263) | Dense (n=234) |
|---|---:|---:|---:|---:|
| **Invalid SQL** | **5 (1.8%)** | **9 (3.6%)** | **15 (5.7%)** | **4 (1.7%)** |
| — Wrong column | 1 (0.4%) | 4 (1.6%) | 3 (1.1%) | 1 (0.4%) |
| — Other execution error | 4 (1.4%) | 5 (2.0%) | 12 (4.6%) | 3 (1.3%) |
| **Schema linking** | **67 (23.6%)** | **67 (26.8%)** | **71 (27.0%)** | **55 (23.5%)** |
| — Wrong column | 49 (17.3%) | 50 (20.0%) | 55 (20.9%) | 42 (17.9%) |
| — Wrong table | 18 (6.3%) | 17 (6.8%) | 16 (6.1%) | 13 (5.6%) |
| **JOIN errors** | **31 (10.9%)** | **28 (11.2%)** | **7 (2.7%)** | **19 (8.1%)** |
| — Wrong/missing/extra table | 25 (8.8%) | 27 (10.8%) | 6 (2.3%) | 14 (6.0%) |
| — Wrong column (incl. wrong key) | 5 (1.8%) | 0 (0.0%) | 0 (0.0%) | 2 (0.9%) |
| — Join type error | 1 (0.4%) | 1 (0.4%) | 1 (0.4%) | 3 (1.3%) |
| **GROUP BY errors** | **8 (2.8%)** | **8 (3.2%)** | **5 (1.9%)** | **6 (2.6%)** |
| **Nesting problem** | **17 (6.0%)** | **21 (8.4%)** | **15 (5.7%)** | **28 (12.0%)** |
| — Wrong sub-query | 11 (3.9%) | 18 (7.2%) | 11 (4.2%) | 23 (9.8%) |
| — HAVING clause mismatch | 5 (1.8%) | 3 (1.2%) | 4 (1.5%) | 5 (2.1%) |
| — Wrong set operation | 1 (0.4%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **Predicate error** | **135 (47.5%)** | **98 (39.2%)** | **131 (49.8%)** | **79 (33.8%)** |
| — Filter value error | 68 (23.9%) | 48 (19.2%) | 66 (25.1%) | 35 (15.0%) |
| — Predicate semantic error | 67 (23.6%) | 50 (20.0%) | 65 (24.7%) | 44 (18.8%) |
| **Other** | **21 (7.4%)** | **19 (7.6%)** | **19 (7.2%)** | **43 (18.4%)** |

### Observations

- **JOIN errors collapses under reflexion (2.7%) while staying essentially flat under few-shot
  (11.2% vs zero-shot's 10.9%)** — the most striking single number in this table. Reflexion's retry
  only triggers on an *execution failure*, not on a `wrong_answer`, so this drop implies a
  meaningful share of zero-shot's join-structure mistakes (missing/extra table, wrong key) actually
  manifest as hard errors (a query referencing a column only reachable via the missing join) rather
  than silently wrong results — and once the model sees that error message, a join-structure fix is
  apparently one of the easier things for it to self-correct. Few-shot, by contrast, doesn't reduce
  JOIN errors at all — worked examples don't obviously teach correct join structure the way seeing
  your own execution error does.
- **Invalid SQL rises under reflexion (5.7%) instead of falling**, which is initially counter to
  the "self-correction fixes execution errors" intuition — but this is consistent with the JOIN
  errors finding: reflexion is trading one failure type for another. Some of what used to be a
  JOIN-structural execution error gets "fixed" into a still-wrong-but-executing query (moving into
  Schema linking or Predicate error instead), while in other cases the retry's fix attempt
  introduces a *new* execution error the original attempt didn't have (confirmed directly in the
  source file — e.g. debit_card_specializing Q1490/Q1525, where the retry added an unqualified
  `COUNT(DISTINCT customer_id)` that's ambiguous across two joined tables, turning a `wrong_answer`
  into a hard `error`). Reflexion is not a strict improvement per failure — it reshuffles which
  category a given failure lands in as much as it fixes them outright.
- **Predicate error drops further under dense retrieval (33.8%) — the lowest of any method tested**,
  below even few-shot's 39.2% (zero-shot 47.5%, reflexion 49.8%). Dense's only mechanical difference
  from few-shot is *which* 3 examples are shown (nearest-neighbor by embedding similarity to the test
  question, vs. a fixed per-database set) — so this is consistent with semantically-similar worked
  examples transferring predicate structure/literal-value conventions more directly than an arbitrary
  fixed set, on top of the effect few-shot already shows over zero-shot.
- **Nesting problem is highest under dense (12.0%), roughly double zero-shot's 6.0%** and above
  even few-shot's 8.4% (reflexion lowest at 5.7%) — driven almost entirely by Wrong sub-query
  (9.8% vs. 3.9–7.2% elsewhere). Plausible mechanism: nearest-neighbor retrieval disproportionately
  surfaces other *hard* questions from the same database as similar to a hard test question, and
  BIRD's harder questions skew toward requiring nested constructs — so dense both primes more
  subquery *attempts* and pulls in more subquery-shaped near-misses than a fixed example set would.
- **Other spikes sharply under dense (18.4%) — more than double every other method (7.2–7.6%)**,
  and the increase is spread across both subtypes it shares with the other passes rather than
  concentrated in one: missing/redundant DISTINCT (9.0% vs. 1.9–6.0% elsewhere) and wrong aggregate
  function or scaling (6.0% vs. 1.6–2.7% elsewhere). Combined with the Nesting-problem finding above,
  dense's failures skew toward "attempted something more elaborate than the gold query and got a
  structural/scalar detail wrong" rather than toward schema misidentification — consistent with
  similarity-retrieved examples encouraging more ambitious query shapes without reliably teaching the
  exact aggregation/dedup convention the gold SQL uses.
- **JOIN errors under dense (8.1%) sits between reflexion's outlier-low 2.7% and zero-shot/few-shot's
  ~11%**, closer to the zero-shot/few-shot cluster — dense is still single-shot generation with no
  retry mechanism, so (unlike reflexion) it has no execution-error feedback loop to correct join
  structure against; the modest drop from zero-shot is plausibly just retrieved examples occasionally
  demonstrating the correct join path for a structurally similar question.
- **Schema linking is the most stable category across methods** (23.6% / 26.8% / 27.0% / 23.5% for
  zero-shot/few-shot/reflexion/dense), the same pattern already seen across structural levels and
  semantic levels in this document — no intervention tested anywhere in this study meaningfully moves
  the rate at which the model picks a real-but-wrong column or table.
- **GROUP BY errors stays small and roughly flat across all four methods** (1.9–3.2%), consistent
  with every other axis in this document. Other is the exception to "stays flat" (see above) — it is
  the one category dense visibly disturbs.
