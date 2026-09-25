# qwen2.5-coder-14b-local: fewshot vs full accuracy

Comparison of `results/fewshot` (3-shot prompting) vs `results/full` (zero-shot)
for `qwen2.5-coder-14b-local`, across all L1–L6 × S1–S3 conditions.

**Overall accuracy:** fewshot 1630/6660 = 24.47%, full 1343/7146 = 18.79%
(+5.7pp absolute, ~+30% relative).

## By semantic level (S, averaged over L1–L6)

| S | few-shot | zero-shot | Δ (abs) | Δ (relative) |
|---|---|---|---|---|
| S1 (anonymized: col_a, col_b...) | 10.7% | 4.4% | +6.4pp | +146% |
| S2 (partial semantic hints) | 31.7% | 25.7% | +5.9pp | +23% |
| S3 (full semantic naming) | 31.0% | 26.3% | +4.8pp | +18% |

## By structural level (L, averaged over S1–S3)

| L | few-shot | zero-shot | Δ |
|---|---|---|---|
| L1 | 21.4% | 13.7% | +7.8% |
| L2 | 19.9% | 13.0% | +6.9% |
| L3 | 25.0% | 19.8% | +5.1% |
| L4 | 25.3% | 21.6% | +3.7% |
| L5 | 27.7% | 22.5% | +5.2% |
| L6 | 27.6% | 22.2% | +5.4% |


### Full L × S cross table (cell values, BIRD vs Spider)

|    |    S1   |         |    S2   |         |    S3   |         |
|----|---------|---------|---------|---------|---------|---------|
| L  | BIRD    | Spider  | BIRD    | Spider  | BIRD    | Spider  |
| L1 | 0.0%    | 0.0%    | 20.9%   | 51.3%   | 20.2%   | 51.9%   |
| L2 | 0.0%    | 3.9%    | 19.4%   | 50.0%   | 19.6%   | 49.4%   |
| L3 | 2.5%    | 16.9%   | 28.5%   | 53.9%   | 28.5%   | 55.8%   |
| L4 | 5.0%    | 11.0%   | 29.0%   | 57.1%   | 30.7%   | 59.1%   |
| L5 | 9.8%    | 18.2%   | 28.5%   | 70.1%   | 29.2%   | 70.1%   |
| L6 | 8.8%    | 18.8%   | 28.2%   | 70.1%   | 29.5%   | 71.4%   |

## full vs din vs reflexion

Comparison of `results/full` (zero-shot baseline), `results/din` (DIN-SQL:
decomposed schema-linking + classification + generation, few-shot internally),
and `results/reflexion` (1 self-correction retry on execution failure) for
`qwen2.5-coder-14b-local`.

Note: `din` runs on the same 370-question held-out subset used by `fewshot`
(DIN-SQL uses few-shot examples internally for its schema-linking/classification
stages, so it excludes the 27 questions reserved as the example pool). `full`
and `reflexion` both use the full 397-question set per cell, so `din`'s
denominator (6660) differs from the other two (7146).

**Overall accuracy:** full 1343/7146 = 18.79%, din 1530/6660 = 22.97%,
reflexion 1605/7146 = 22.46%.

### By structural level (L, averaged over S1–S3)

`dense` has no L2 files and its L1 data includes a partial `L1S3` run
(222/397 questions) — to keep this table clean, `dense` is shown for L3–L6
only, where all cells are complete (397/cell).

| L | zero-shot | few-shot | din | reflexion | dense |
|---|---|---|---|---|---|
| L1 | 13.7% | 21.4% | 16.5% | 16.1% | — |
| L2 | 13.0% | 19.9% | 17.4% | 16.6% | — |
| L3 | 19.8% | 25.0% | 24.3% | 23.3% | 32.1% |
| L4 | 21.6% | 25.3% | 25.3% | 25.9% | 32.7% |
| L5 | 22.5% | 27.7% | 27.1% | 26.5% | 34.7% |
| L6 | 22.2% | 27.6% | 27.2% | 26.4% | 34.4% |

### By semantic level (S, averaged over L1–L6)

`dense`'s S columns are averaged over L3–L6 only, for the same reason (all
four other columns still average over the full L1–L6).

| S | zero-shot | few-shot | din | reflexion | dense |
|---|---|---|---|---|---|
| S1 | 4.4% | 10.7% | 9.7% | 5.2% | 16.6% |
| S2 | 25.7% | 31.7% | 28.5% | 30.7% | 41.6% |
| S3 | 26.3% | 31.0% | 30.7% | 31.4% | 42.2% |


### Takeaways

- **Both methods beat the zero-shot baseline by a similar overall margin**
  (din +4.2pp, reflexion +3.7pp), but din's edge is inflated somewhat by its
  easier 370-question subset — the fairer per-cell comparison below matters
  more than the pooled total.
- **din wins decisively at S1 (anonymized columns)**: 9.7% vs full's 4.4% and
  reflexion's 5.2% — more than double the baseline. DIN-SQL's explicit
  schema-linking step appears to help most exactly when column names carry no
  semantic signal, since it forces the model to reason about which columns
  are relevant independent of naming.
- **reflexion pulls ahead at S2/S3** (30.7%/31.4% vs din's 28.5%/30.7%) —
  once there's enough naming signal to write a mostly-correct query, a single
  execution-guided self-correction pass fixes more errors than decomposition
  does.
- **Neither method fixes the fundamental L1/L2 S1 collapse**: reflexion barely
  moves the needle (0.0%→0.3%) since there's nothing in the execution error to
  correct toward when the model has no idea what the columns mean; din does
  better here (0.0%→5.4-6.2%) but still far below its S2/S3 performance.

## full (S1) vs s1r

`results/s1r` only covers semantic level S1 (anonymized columns), across
L1–L6, so this compares against the S1 column of `results/full` only
(397/cell both sides).

**Naming scheme difference:** standard S1 assigns `col_a`, `col_b`, … as a
single flat sequence unique across the *entire* schema (verified in
`src/column_aliases.py:15`). S1R (`src/column_aliases_s1r.py`) instead
assigns `table_x` aliases per table and `column_y` aliases **per table**
(`get_column_name_s1r(db_id, table, column)`), so the same alias like
`column_a` is reused across different tables to mean different things —
disambiguated only by table prefix in the schema declaration, not in the
alias itself.

| L | S1 | S1 R | Δ |
|---|---|---|---|
| L1 | 0.0% | 0.3% | +0.3pp |
| L2 | 0.0% | 0.8% | +0.8pp |
| L3 | 2.5% | 0.0% | −2.5pp |
| L4 | 5.0% | 0.3% | −4.8pp |
| L5 | 9.8% | 0.3% | −9.6pp |
| L6 | 8.8% | 1.0% | −7.8pp |

**Overall:** full(S1) 104/2382 = 4.37%, s1r 10/2382 = 0.42%.

**Takeaway: S1R is substantially harder than S1, and the gap grows with
structural level — but the collision mechanism only kicks in from L3.** At
L1 and L2 the schema is flattened (one wide table for L1, per-cluster wide
tables for L2) with compound `{table_alias}__{column_alias}` identifiers, so
there's no possible name collision — `table_b__column_e` can never be
confused with `table_c__column_e`. Both full(S1) and s1r are simply pinned at
floor accuracy there (0.0–0.8%) because anonymized names give the model
almost nothing to work with either way; the apparent s1r "edge" at L1/L2
(0.3pp, 0.8pp) is just 1 and 3 lucky guesses out of 397 respectively, not a
real effect — don't read anything into it.

From L3 onward the schema is genuinely multi-table, columns are referenced
without the compound prefix, and that's where s1r's naming scheme actually
hurts: full(S1) climbs to 8.8–9.8% while s1r stays pinned near 0%. Sampled
predictions confirm the mechanism: failures are almost all `wrong_answer`
(executes fine, wrong result), not `error`, e.g. the model writes `JOIN
table_a AS T1 ... T1.column_c = T2.column_c` where `column_c` in `table_a`
and `column_c` in `table_d` are unrelated real columns that happen to share
the per-table-reused alias. The single global counter in vanilla S1 (`col_a`
always means the same physical column everywhere it appears) removes this
ambiguity; S1R's per-table reuse recreates a subtler version of the
naming-collision problem that anonymization was supposed to control for, and
it only bites once real joins enter the picture.

## full vs cot vs ev vs cot_ev

Comparison of `results/full` (zero-shot baseline), `results/cot`
(chain-of-thought instruction block), `results/ev` (BIRD `evidence`
value-mapping/domain-knowledge hints injected as a prompt block), and
`results/cot_ev` (both combined), for `qwen2.5-coder-14b-local`. All four use
the full 397-question set per cell (7146 total).

**Overall accuracy:** full 1343/7146 = 18.79%, cot 1254/7146 = 17.55%,
ev 2359/7146 = 33.01%, cot_ev 2281/7146 = 31.92%.

### By structural level (L, averaged over S1–S3)

| L | full | cot | ev | cot_ev |
|---|---|---|---|---|
| L1 | 13.7% | 13.0% | 26.3% | 26.6% |
| L2 | 13.0% | 11.4% | 24.1% | 24.3% |
| L3 | 19.8% | 19.1% | 32.4% | 31.5% |
| L4 | 21.6% | 19.7% | 36.2% | 34.3% |
| L5 | 22.5% | 21.1% | 39.8% | 37.8% |
| L6 | 22.2% | 21.0% | 39.3% | 37.1% |

### By semantic level (S, averaged over L1–L6)

| S | full | cot | ev | cot_ev |
|---|---|---|---|---|
| S1 | 4.4% | 4.1% | 7.1% | 6.8% |
| S2 | 25.7% | 23.9% | 45.8% | 44.6% |
| S3 | 26.3% | 24.7% | 46.1% | 44.4% |

### Takeaways

- **Evidence hints are by far the strongest lever tested**: `ev` nearly
  doubles baseline accuracy (+14.2pp, +76% relative) — bigger than few-shot,
  dense retrieval, DIN-SQL, or reflexion.
- **Chain-of-thought alone is a net negative**: `cot` underperforms `full` at
  every L and every S, consistently by ~1-2pp. Unstructured step-by-step
  reasoning hurts this 14B coder model more than it helps.
- **Combining cot with ev doesn't help — it mildly hurts**: `cot_ev` trails
  plain `ev` at every L4-L6 cell (e.g. L5: 37.8% vs 39.8%) and both S2/S3
  levels, suggesting CoT reasoning on top of evidence just adds noise/
  distraction rather than additional grounding.
- **S1 (anonymized columns) is the one place ev's gains are modest**
  (7.1% vs 4.4%, only +2.7pp) — evidence hints reference value semantics
  (e.g. "'EUR' refers to Euro currency"), not column names, so they can't
  compensate for a schema that hides which column to filter on in the first
  place.

## Manual error-category analysis: L1–L6 (S3, 60-sample audit)

Counts pulled as-is from the existing manually-classified samples
(`docs/qwen14b_L{1..6}S3_wrong_answer_sample60.md` for L2–L6, and the
finer-grained `docs/error_analysis/qwen14b_L1S3_manual_error_summary.md` for L1; seed=42,
n=60 each, sampled from `results/full`) — no re-classification performed
here. S3 is the only semantic level with a manually-audited sample at every
structural level, so it's the basis for this L1–L6 comparison.

**Taxonomy note:** L2–L6 share one 6-category taxonomy (defined once at L3
and reused). L1's finer-grained annotation
(`docs/error_analysis/qwen14b_L1S3_manual_error_summary.md`) uses sub-codes — (a1) wrong
table name, (a2) wrong column name, (a3) logic error, (b) resolvable
denorm. fan-out, (c) unrecoverable denorm. error — that map directly onto
the L2–L6 categories, so no approximation is needed. Using its
mutually-exclusive assignment (each of the 60 questions counted once;
compound-labelled questions resolved by priority b > c > a):

| L1 sub-code | Count | → L2–L6 category |
|---|---|---|
| (a1) wrong table name | 7 | wrong table name |
| (a2) wrong column name | 13 | wrong column name |
| (a3) logic error | 29 | other logic error |
| (b1)+(b2) resolvable fan-out | 1 + 4 = 5 | weak duplication / recoverable artefact |
| (c) fan-out + null propagation | 5 + 1 = 6 | unrecoverable (denormalisation) |

L1 has no `join plan error` equivalent (single flattened table, no joins to
mis-plan) and, since the sample was drawn from L1's own failure population,
`correct` is 0 by construction — the `correct` counts in the L2–L6 columns
instead mean "this L1-failure question became correct once evaluated at
that higher structural level" (same 60 question IDs reused throughout).

### L1–L6 (S3)

| Category | L1S3 | L2S3 | L3S3 | L4S3 | L5S3 | L6S3 |
|---|---|---|---|---|---|---|
| other logic error | 29 (48.3%) | 34 (56.7%) | 43 (71.7%) | 46 (76.7%) | 43 (71.7%) | 48 (80.0%) |
| join plan error | 0 (0.0%) | 2 (3.3%) | 6 (10.0%) | 3 (5.0%) | 6 (10.0%) | 3 (5.0%) |
| wrong column name | 13 (21.7%) | 9 (15.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| wrong table name | 7 (11.7%) | 7 (11.7%) | 0 (0.0%) | 1 (1.7%) | 0 (0.0%) | 0 (0.0%) |
| unrecoverable (denormalisation) | 6 (10.0%) | 2 (3.3%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| recoverable artefact | 5 (8.3%) | 1 (1.7%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| correct | 0 (0.0%)‡ | 5 (8.3%) | 11 (18.3%) | 10 (16.7%) | 11 (18.3%) | 9 (15.0%) |
| **Total** | 60 | 60 | 60 | 60 | 60 | 60 |

‡ zero by construction of the sampling frame, not a measured rate — see note above.

### Takeaways

- **Naming hallucinations (wrong column/table name) are worst at L1 and L2,
  vanish entirely from L3 onward.** L1: 13+7=20/60 (33.3%); L2: 9+7=16/60
  (26.7%); L3–L6: 0. Both denormalized wide-table representations (L1's
  single flattened table, L2's per-cluster wide tables) confuse the model
  about which identifiers actually exist; real 3NF tables with descriptive
  S3 columns eliminate this failure mode completely — the model never
  invents an identifier once the schema looks like a normal database.
- **L1 and L2 have nearly identical wrong-table-name rates** (7/60 each) —
  interesting given L1 is a single table and "wrong table name" there means
  referencing a source table that no longer exists post-flattening, while at
  L2 it means referencing a cluster that doesn't hold the needed columns.
  Same failure rate, different mechanism.
- **"other logic error" share climbs steadily from L1 to L6** (48.3% → 56.7%
  → 71.7% → 76.7% → 71.7% → 80.0%) as naming and denormalisation failure
  modes get squeezed out — L6 fails almost exclusively on data-value/logic
  mistakes (wrong filter value, threshold, aggregate grain) rather than
  structural confusion.
- **L1 has the highest combined denormalisation-artefact rate** (unrecoverable
  + recoverable = 6+5 = 11/60, 18.3%, vs L2's 2+1=3/60, 5.0%, vs 0 from L3
  on) — consistent with L1 being the most aggressively flattened
  representation (one wide table for the whole database vs. L2's per-cluster
  tables). This is a distinct issue from the L1S1/L2S1 alias-collision
  mechanism discussed earlier in this doc — this is about multiset/DISTINCT
  fan-out from denormalisation, not column-name ambiguity.
- **Sample matches full population closely for L1** (54.3%/2.2%/43.5% in the
  coarse (a)/(b)/(c) population count, n=317, from
  `qwen14b_L1S3_wrong_answer_sample60.md`) — the seed=42 sample used here is
  a reliable proxy for L1's failure distribution.

## full vs without_denorm_notice (L1/L2 denormalisation-notice ablation)

The L1/L2 prompts in `results/full` append a **denormalisation notice**
(`src/denormalization_notice.py`, ~3 pages) — explicit per-query-type rules
for when to use `DISTINCT`/dedup subqueries to avoid fan-out-inflated
results on the denormalised wide table (L1) / clusters (L2). This is a
confound: L1/L2's headline accuracy could come from the wide/clustered
schema representation itself, or largely from this notice explicitly
telling the model how to defend against exactly the failure mode (fan-out)
that representation introduces. `results/without_denorm_notice`
(`src/run_without_denorm_notice_experiment.py`) is the ablation arm —
identical prompts with the notice removed, matching the design in
`docs/plans/future_work_experiment_plan.md`'s Phase 5. Numbers below are execution
accuracy recomputed directly from both result sets (no new error
classification), and match the existing
`docs/figures/qwen14b_denorm_notice_ablation_L1L2_{comparison,delta}.*`
figures exactly.

### Qwen2.5-Coder-14B — L1·S3 (n=397)

| Arm | Notice | Accuracy | Δ vs full |
|-----|--------|---------:|----------:|
| full | Full | 20.15% (80/397) | — |
| without_denorm_notice | None | 8.06% (32/397) | **−12.09pp** |

### Qwen2.5-Coder-14B — L2·S3 (n=397)

| Arm | Notice | Accuracy | Δ vs full |
|-----|--------|---------:|----------:|
| full | Full | 19.65% (78/397) | — |
| without_denorm_notice | None | 15.87% (63/397) | **−3.78pp** |

### Same comparison at S1/S2 (ablation data isn't S3-only)

| L·S | full (notice) | without_denorm_notice | Δ (pp) |
|---|---:|---:|---:|
| L1·S1 | 0.00% (0/397) | 0.00% (0/397) | 0.00 |
| L1·S2 | 20.91% (83/397) | 7.56% (30/397) | **−13.35** |
| L1·S3 | 20.15% (80/397) | 8.06% (32/397) | **−12.09** |
| L2·S1 | 0.00% (0/397) | 0.25% (1/397) | +0.25 |
| L2·S2 | 19.40% (77/397) | 17.38% (69/397) | −2.02 |
| L2·S3 | 19.65% (78/397) | 15.87% (63/397) | −3.78 |

### Takeaways

- **The notice's effect is not the same at L1 vs L2.** At L1, removing it
  roughly **halves accuracy** (20.2%→8.1% at S3, 20.9%→7.6% at S2, both
  ≈−12 to −13pp) — a large share of L1's headline number is the notice doing
  the model's fan-out-defense reasoning *for* it, not the model discovering
  on its own that the wide table needs `DISTINCT`/dedup handling. At L2 the
  drop is much smaller (−3.78pp at S3, −2.02pp at S2) — well under a third
  of L1's.
- **This lines up with L1's higher denormalisation-artefact rate in the
  60-sample manual audit above** (unrecoverable+recoverable = 11/60, 18.3%
  at L1 vs 3/60, 5.0% at L2): L2's cluster design (sibling fact tables kept
  in separate clusters instead of one merged wide table) already suppresses
  most fan-out risk structurally, so there's simply less for the notice to
  be defending against — removing it costs L2 much less than L1.
- **S1 (anonymised columns) sits at/near 0% in both arms** — the notice
  can't help when the model doesn't know what the columns mean in the first
  place; this is a floor effect, not evidence the notice is irrelevant at S1.
- **Paper framing implication**: the L1 headline number should be reported
  as *notice-assisted*, not attributed to the wide-table representation
  alone — the schema representation by itself is substantially harder to
  use correctly than the L1 accuracy figure alone suggests. L2's number is
  comparatively robust to this confound and can be discussed closer to a
  "pure structure" effect.

## Per-database breakdown: qwen14b L3S3 (BIRD)

The L3S3 cell that anchors the 3NF/S3 plateau in
`docs/figures/bird_spider_qwen2.5-coder-14b-local_heatmap_combined.png`
(28.5%, 113/397) is not uniform across BIRD's 9 databases represented at
L3S3. Recomputed directly from
`results/full/qwen2.5-coder-14b-local__L3S3.csv` (397 rows, no
re-classification).

| db_id | n | correct | accuracy | correct/wrong/error | tables | cols | fks |
|---|---:|---:|---:|---|---:|---:|---:|
| superhero | 52 | 27 | 51.9% | 27/23/2 | 10 | 31 | 11 |
| student_club | 48 | 24 | 50.0% | 24/21/3 | 8 | 48 | 8 |
| formula_1 | 66 | 26 | 39.4% | 26/36/4 | 13 | 94 | 19 |
| european_football_2 | 51 | 18 | 35.3% | 18/32/1 | 7 | 199 | 29 |
| financial | 30 | 7 | 23.3% | 7/20/3 | 8 | 55 | 8 |
| debit_card_specializing | 30 | 6 | 20.0% | 6/22/2 | 5 | 21 | 1 |
| california_schools | 30 | 2 | 6.7% | 2/22/6 | 3 | 89 | 2 |
| toxicology | 40 | 2 | 5.0% | 2/36/2 | 4 | 11 | 5 |
| thrombosis_prediction | 50 | 1 | 2.0% | 1/47/2 | 3 | 64 | 2 |
| **Total** | **397** | **113** | **28.5%** | | | | |

Difficulty mix per db (simple / moderate / challenging accuracy):

| db_id | simple | moderate | challenging |
|---|---|---|---|
| superhero | 12/14 (86%) | 11/26 (42%) | 4/12 (33%) |
| student_club | 13/21 (62%) | 9/22 (41%) | 2/5 (40%) |
| formula_1 | 12/28 (43%) | 10/26 (38%) | 4/12 (33%) |
| european_football_2 | 7/14 (50%) | 8/25 (32%) | 3/12 (25%) |
| financial | 1/3 (33%) | 6/20 (30%) | 0/7 (0%) |
| debit_card_specializing | 4/14 (29%) | 2/12 (17%) | 0/4 (0%) |
| california_schools | 1/8 (12%) | 1/17 (6%) | 0/5 (0%) |
| toxicology | 1/5 (20%) | 0/17 (0%) | 1/18 (6%) |
| thrombosis_prediction | 1/7 (14%) | 0/27 (0%) | 0/16 (0%) |

Schema size (tables/cols/fks) does not predict accuracy on its own —
toxicology (4 tables, 11 cols) and thrombosis_prediction (3 tables, 64
cols) sit at the bottom despite being among the smallest/simplest schemas
by table count, while formula_1 (13 tables, 94 cols) sits mid-table.
Sampling `wrong_answer`/`error` rows per db (not a full manual audit, ~3-4
rows/db) points to at least three distinct failure regimes hiding behind
the single L3S3 average:

- **Coded/opaque value vocabulary (thrombosis_prediction, toxicology,
  partially debit_card_specializing).** The column *names* are resolvable
  at S3, but the *values* stored in those columns are domain-specific
  codes with no naming cue: thrombosis_prediction's `Admission` is coded
  `'+'`/`'-'` (model guesses `'Inpatient'`/`'Outpatient'`, Q1149/Q1152) and
  its lab thresholds are arbitrary cutoffs the model can't infer (LDH
  `>500` guessed as `>175`, Q1155); toxicology's `atom.element` is a
  lowercase single-char code (`'c'`, `'o'`) and `bond.bond_type` is a
  symbol (`'#'`, `'='`) that the model spells out as `'C'`/`'triple'`
  (Q200/Q201); debit_card's `customers.Segment` values (`'LAM'`, `'SME'`,
  `'KAM'`) are guessed rather than known (Q1472/Q1473). This is exactly
  the gap the `ev` (evidence-hint) condition is built to close — none of
  it is visible from column names alone, however descriptive.
- **Cross-table naming confusion + genuine composition errors
  (california_schools, financial).** california_schools has 6/30 hard
  `error` rows (`no such column`), not just wrong-answer — e.g. Q32 filters
  `frpm` on `school_ownership_code`, a column that actually belongs to the
  sibling `schools` table, and Q5/Q27 reference `s.school_name` on
  `schools` (whose real column is just `School`; `school_name` is
  `frpm`'s "School Name" alias) — the two tables have near-duplicate
  concepts under different original names, and S3 renaming doesn't fully
  disambiguate which table a name belongs to. On top of that, remaining
  `wrong_answer` rows are real composition mistakes: Q12 needs a computed
  ratio (`free_meal_ages_5_17 / enrollment_ages_5_17`) but the model
  substitutes a pre-existing (differently-scoped) percentage column
  instead. financial's errors are dominated by case-sensitive string
  literals (`'East Bohemia'` vs. predicted `'East Bohemia'`-adjacent
  `'North Bohemia'`/region-name casing, Q89/Q93) and one fully
  mis-scoped aggregation (Q94 answers a different question than asked).
- **Join/table-selection ambiguity (formula_1, european_football_2).**
  Here the model usually picks a plausible but wrong table or drops a
  required `DISTINCT`/`LIMIT` qualifier rather than mangling names or
  values: formula_1 Q846 queries `results.rank` instead of
  `qualifying.q1` (wrong table for "qualifying performance"); Q850/Q854
  drop `DISTINCT`, changing row cardinality. european_football_2 Q1025
  normalizes the season filter (`'2016'` vs. gold's `'2015/2016'`) and
  Q1028/Q1029 select a different-but-related column (`team_short_name`
  vs. `team_long_name`) or add unrequested columns.
- **High performers (superhero, student_club) have neither** heavily
  coded value vocabularies nor large sets of near-duplicate cross-table
  columns, so what's left is the "other logic error" tail that dominates
  every db at L3+ per the manual audit above — nothing compounds on top
  of it.

### Takeaways

- **The L3S3 average (28.5%) hides a ~26x spread** (2.0% thrombosis_prediction
  to 51.9% superhero) within a single nominal $(L, S)$ cell — the heatmap
  figure's per-cell number is a mix of very different regimes, not a
  homogeneous population.
- **Difficulty mix alone doesn't explain the ranking**: toxicology and
  thrombosis_prediction skew moderate/challenging, but so does
  california_schools, and formula_1's difficulty mix is close to
  superhero/student_club's while scoring ~11-12pp lower — the db-level
  effect is doing more work than question-level difficulty tagging.
  Likewise schema size (table/column/FK counts) doesn't rank-order
  accuracy either.
- **Value-vocabulary opacity, not naming, is the dominant floor effect**
  for the three worst databases — consistent with the project's own
  finding elsewhere in this doc that `ev` (evidence hints) roughly doubles
  baseline accuracy, since evidence is precisely what supplies the
  value-mapping (`'+'` = inpatient, `'c'` = carbon, etc.) that S3 column
  naming cannot.
- **The "wrong column name vanishes by L3" claim in the L1-L6 manual audit
  above is population-specific, not universal**: that audit resampled
  L1-failure questions re-scored at higher L, whereas california_schools'
  own L3S3 population still shows a 20% (6/30) `no such column` rate,
  driven by near-duplicate concepts across its `frpm`/`schools` tables
  that S3 renaming doesn't disambiguate.
