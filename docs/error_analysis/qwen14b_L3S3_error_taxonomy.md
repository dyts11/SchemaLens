# Qwen2.5-Coder-14B · L3·S3 error analysis (7-category taxonomy)

**Source:** `results/full/qwen2.5-coder-14b-local__L3S3.csv` · **Population:** 284 failures / 397
questions · **Sample:** same n=60 (seed=42) as the L1·S3 / L2·S3 samples.

**Method:** this is a **re-labelling** of the existing human-reasoned sample in
[`qwen14b_L3S3_wrong_answer_sample60.md`](qwen14b_L3S3_wrong_answer_sample60.md) — each of the
60 SQL pairs and its written diagnosis were re-read and assigned to the shared 7-category scheme
in [`error_taxonomy.md`](error_taxonomy.md), applying that doc's priority waterfall (Invalid SQL
→ Schema linking → JOIN → Fan-out → GROUP BY → Nesting → Other) whenever a failure had more than
one plausible cause. This is step 1 of §5.2's validation procedure (human annotation under the
final scheme); it is **not** a full-population automated classification of all 284 failures —
that's the LLM-classifier step, still to be built.

Full SQL and per-question prose are in the source sample doc; this doc adds the category
decision and, where a failure had multiple candidate causes, a short note on why one was
chosen as primary.

## Summary (n=60)

| Category | Count | % of sample (n=60) | % of failures (n=49) |
|----------|------:|--------------------:|-----------------------:|
| **Correct** | 11 | 18.3% | — |
| **Schema linking** | 14 | 23.3% | 28.6% |
| **Other** | 25 | 41.7% | 51.0% |
| **JOIN errors** | 6 | 10.0% | 12.2% |
| **GROUP BY errors** | 3 | 5.0% | 6.1% |
| **Nesting problem** | 1 | 1.7% | 2.0% |
| **Invalid SQL** | 0 | 0.0% | 0.0% |
| **Fan-out** | 0 | 0.0% | 0.0% *(N/A at L3 — no materialised denormalised surface)* |
| **Total** | 60 | 100.0% | 100.0% |

**Headline finding, consistent with the original doc's own note:** zero **Invalid SQL** at L3·S3
— every execution error in the sample traced back to a real identifier used on the wrong table
(Schema linking or JOIN), never a genuinely hallucinated name. The model's grounding failures at
L3 are about *which* real table/column to use, not inventing ones that don't exist. Failures
concentrate in **Other** (data-value literals, date formats, tie handling, aggregate
formula/scaling) and **Schema linking** (wrong-but-valid table/column choice), with JOIN and
GROUP BY as smaller tails and Nesting essentially absent in this sample.

## Category definitions (recap)

See [`error_taxonomy.md`](error_taxonomy.md) for full definitions and priority order. Two
placements specific to this doc, both surfaced while doing this re-labelling and folded back into
the shared taxonomy doc:

- Four execution errors (Q32, Q79, Q194, Q959) reference a column/table that exists **somewhere**
  in the schema, just not reachable from the table it was used on. These are **not** Invalid SQL —
  they're routed to JOIN (when a missing/extra join is the fix) or Schema linking (when no join
  was needed at all, just the wrong table/column chosen outright).
- "Missing/extra `HAVING`" and "`ORDER BY … LIMIT 1` used where gold's `HAVING = MAX(...)`
  subquery preserves ties" are treated as **GROUP BY** errors (tie-handling is a grouping-semantics
  issue), not Other, per `error_taxonomy.md`'s GROUP BY subcategory.

## JOIN errors — 6 questions

| QID | DB | Outcome | Reason |
|-----|----|---------|--------|
| Q32 | california_schools | error | `school_ownership_code` (a real `schools` column) referenced on `frpm` with no join to `schools` — missing join. |
| Q125 | financial | wrong_answer | Routes district through `disp`→`client` instead of gold's direct `loan`→`account`→`district` — wrong join path (extra, unnecessary tables). |
| Q194 | financial | error | Joins `card` on `ca.account_id`; `card`'s real key is `disposition_id` — wrong join key. |
| Q868 | formula_1 | wrong_answer | Filters `circuits.name` directly for a race name that only exists via `races`; missing join to `races`. |
| Q959 | formula_1 | error | Joins `driverStandings` and reads `.year`, which lives on `races` (never joined) — wrong table joined. |
| Q1528 | debit_card_specializing | wrong_answer | Joins `transactions_1k` unnecessarily, changing the aggregation grain from gasstation-rows (gold) to transaction-fanned rows — extraneous join. *(secondary: lowercase `'premium'` literal, filed under Other in isolation but this failure's primary cause is structural.)* |

## Schema linking — 14 questions

| QID | DB | Outcome | Wrong table/column |
|-----|----|---------|----------------------|
| Q48 | california_schools | wrong_answer | Answers from `frpm` (+ `'Orange County'` literal) instead of gold's `schools` (DOC/StatusType) — wrong table entirely. |
| Q79 | california_schools | error | Uses `county_name` (the sibling tables' S3 name) on `schools`, whose own name is different — wrong column, no join needed. |
| Q149 | financial | wrong_answer | Answers from `account.statement_frequency` instead of gold's `disp.type` — wrong column/table for the concept asked. |
| Q152 | financial | wrong_answer | Filters `number_inhabitants` where gold filters the crimes column (`A15`/`number_crimes_1995`) — wrong column in the `WHERE` clause. *(secondary: the added `account` join also changes the aggregation grain — a JOIN-type issue — but the wrong-column filter is checked first in the waterfall.)* |
| Q846 | formula_1 | wrong_answer | Answers from `results` (`rank = 1`) instead of gold's `qualifying` — wrong table. |
| Q865 | formula_1 | wrong_answer | Uses `position IS NOT NULL` as the "finished" condition instead of gold's `time IS NOT NULL` — wrong column, same table. |
| Q950 | formula_1 | wrong_answer | Reads points from `constructorResults` instead of gold's `constructorStandings` — wrong table. |
| Q990 | formula_1 | wrong_answer | Joins `constructorStandings` (`position = 1`) instead of gold's `results` (`time LIKE …`) — wrong table. |
| Q1147 | european_football_2 | wrong_answer | Ranks by `strength` instead of gold's `overall_rating` — wrong column. |
| Q1164 | thrombosis_prediction | wrong_answer | Filters `thrombosis_degree = MAX(...)` instead of gold's `Thrombosis = 1` — wrong column (different real attribute). *(secondary: `'女'` vs `'F'` literal, Other.)* |
| Q1187 | thrombosis_prediction | wrong_answer | Reads `aspartate_aminotransferase` where gold's `GPT` maps to `alanine_aminotransferase` — wrong column between two similarly-named lab tests. *(secondary: extra joins to `Patient`/`Examination` and date column from `Examination` instead of `Laboratory.Date` — a JOIN-type issue, checked second.)* |
| Q1403 | student_club | wrong_answer | Recomputes overspend via `SUM(expense.cost) - budget.amount` instead of using the existing `budget.remaining` column — wrong column (ignored a purpose-built field). *(secondary: `'closed'` vs `'Closed'` literal, Other.)* |
| Q1422 | student_club | wrong_answer | Selects `budget.category` instead of gold's `event.type` — wrong column. |
| Q206 | toxicology | wrong_answer | Puts the bond-id value into `molecule.label` and joins via `molecule`/`bond`, instead of gold's `connected.bond_id` — wrong table for the concept. |

## GROUP BY errors — 3 questions

| QID | DB | Outcome | Reason |
|-----|----|---------|--------|
| Q1092 | european_football_2 | wrong_answer | `ORDER BY COUNT(*) DESC LIMIT 1` instead of gold's `HAVING COUNT(...) = (SELECT MAX(...))` — collapses a 4-way tie to one row. |
| Q212 | toxicology | wrong_answer | Same tie-handling pattern: `ORDER BY … LIMIT 1` instead of gold's `HAVING COUNT(*) = (SELECT MIN(cnt) …)`. *(secondary: invented literal `'carcinogenic'` vs real `'-'`, Other.)* |
| Q1498 | debit_card_specializing | wrong_answer | No `GROUP BY` at all — takes `MAX(consumption)` over all 2012 rows instead of gold's `SUM(...) GROUP BY month ORDER BY SUM DESC LIMIT 1`. |

## Nesting problem — 1 question

| QID | DB | Outcome | Reason |
|-----|----|---------|--------|
| Q41 | california_schools | wrong_answer | Gold uses a `RANK() OVER (PARTITION BY county)` CTE to get the top-5-per-county; prediction substitutes a flat `MAX`-per-county subquery with global `LIMIT 5` — wrong nested-query structure for a per-group top-N. *(secondary: `Virtual = 'Yes'` vs `'F'` literal, Other.)* |

## Other — 25 questions

| QID | DB | Subtype | Reason |
|-----|----|---------|--------|
| Q1476 | debit_card_specializing | Wrong date encoding | `strftime('%Y', …)` applied to a `'YYYYMM'` text column instead of `SUBSTR(date,1,4)`. |
| Q1493 | debit_card_specializing | Wrong date encoding | `date BETWEEN '2012-02-01' AND '2012-02-29'` against `'YYYYMM'` text (`'201202'`). |
| Q1505 | debit_card_specializing | Wrong filter value | `currency = 'euro'` vs stored `'EUR'`. |
| Q1506 | debit_card_specializing | Wrong filter value | `country = 'Czech Republic'` vs stored `'CZE'`. |
| Q1529 | debit_card_specializing | Wrong aggregate formula | Sums `amount` (quantity) instead of gold's `Amount * Price` (spend). |
| Q1036 | european_football_2 | Missing `DISTINCT` | Reproduces gold's join/threshold but drops `DISTINCT`, so teams with multiple qualifying snapshots repeat. |
| Q1037 | european_football_2 | Wrong aggregate grain | `SUM`/`COUNT(*)` per attribute-snapshot row instead of gold's `COUNT(DISTINCT player)`. |
| Q1105 | european_football_2 | Wrong date encoding | Exact-match `date = '2015-05-01'` vs stored `'2015-05-01 00:00:00'` (gold uses `LIKE`). |
| Q1136 | european_football_2 | Wrong filter value | `'Left'`/`'High'` vs stored lowercase, plus an extra predicate (`attacking_work_rate`) not in gold. |
| Q95 | financial | Wrong sort direction | `ORDER BY birth_date ASC` (oldest) instead of gold's `DESC` (youngest) inside the subquery. |
| Q118 | financial | Wrong filter value | `status = 'A'` vs gold's `'C'`. |
| Q967 | formula_1 | Wrong filter value | Invented nationality `'Netherlandic'` (real domain value `'Dutch'`). |
| Q981 | formula_1 | Wrong sort direction | `MIN(date_of_birth)` (oldest) instead of gold's `ORDER BY dob DESC` (youngest). |
| Q1394 | student_club | Extra predicate | Adds a hallucinated `position = 'Student_Club'` filter (not a real domain value) on top of a correct join/condition. |
| Q723 | superhero | Wrong filter value | `'blue'` vs stored `'Blue'`. |
| Q724 | superhero | Wrong filter value | `'blue'`/`'blond'` vs stored `'Blue'`/`'Blond'`. |
| Q782 | superhero | Wrong filter value | `'black'` vs stored `'Black'`. |
| Q791 | superhero | Missing predicate | Omits gold's `height_cm > 0` guard. |
| Q1150 | thrombosis_prediction | Wrong filter value | `sex = 'female'` vs stored `'F'` (also changes which rows count toward the denominator). |
| Q1209 | thrombosis_prediction | Wrong filter value | Threshold `> 40` vs gold's `> 60`. |
| Q1225 | thrombosis_prediction | Wrong aggregate function | `COUNT` + wrong thresholds instead of gold's `GROUP_CONCAT(DISTINCT id)`. |
| Q1229 | thrombosis_prediction | Wrong filter value | Threshold `> 150` vs gold's `>= 200`. |
| Q1265 | thrombosis_prediction | Wrong filter value | Invented values `'normal'`/`'admitted'` vs stored `'negative'`/`'0'` and `'+'`. |
| Q1275 | thrombosis_prediction | Wrong filter value | Invented values `'normal'`/`'male'` vs stored `'negative'`/`'0'` and `'M'`. |
| Q219 | toxicology | Wrong filter value | Invented values `'triple'`/`'carcinogenic'` vs stored `'#'`/`'+'`; query structure also inverted. |

## Interpretation for §5.2/§5.4

- At L3·S3, the failure mix is dominated by **semantic/value-level mistakes** (Other, 51% of
  failures) and **schema-linking choices among valid names** (29%), not structural SQL
  composition (JOIN 12%, GROUP BY 6%, Nesting 2%) and not naming hallucination (Invalid SQL 0%).
  This is a different profile from L1/L2, where Fan-out and wide-table JOIN-avoidance dominate
  (see `gemini_S3_error_analysis_L1_L2_L3.md` for the cross-level comparison, pending re-run
  under this same 7-category scheme).
- The case-sensitivity / invented-value pattern (Q723, Q724, Q782, Q1136, Q967, Q1265, Q1275,
  Q219, Q1505, Q1506 — 10 of 25 Other cases) is the single largest identifiable failure mode in
  this sample: the model has the right table, right column, right join, and still fails purely on
  matching BIRD's stored literal casing/domain values. This is a strong candidate for a targeted
  ablation (e.g. case-insensitive comparison, or evidence-string exposure) independent of the L×S
  grid.
- Zero Fan-out and zero Invalid SQL at L3 are the expected null results given no materialised
  wide table and no denormalisation-induced naming pressure — useful as a sanity check that the
  taxonomy behaves correctly at the "easy" end of the L axis before trusting it on L1/L2.

## Next steps

1. Re-run the L1·S3 and L2·S3 manual samples through this same 7-category scheme (they currently
   use the old `(a)/(b)/(c)` and `fan-out/wrong-table/...` schemes respectively) so all three
   levels are directly comparable.
2. Build the LLM classifier prompt from `error_taxonomy.md`'s condition table and validate against
   this n=60 as the labelled set (Cohen's κ) before running it over the full 284-failure
   population and the other L×S/model/method conditions.
