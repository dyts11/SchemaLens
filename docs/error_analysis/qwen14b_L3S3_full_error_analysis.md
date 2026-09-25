# Qwen2.5-Coder-14B · L3·S3 full error analysis (n=284, automated)

**Source:** `results/full/qwen2.5-coder-14b-local__L3S3.csv` · **Population:** 284 failures / 397 questions (113 correct)

**Method:** rule-based classifier (`analysis/classify_l3s3_full.py`) applying the 7-category priority order from `docs/error_analysis/error_taxonomy.md` to **every** failure, not a sample. Schema existence checks use the real S3 column-rename map (`build_col_rename_map`), so "does this identifier exist" reflects exactly what the model saw. This is a mechanical classifier, not an LLM classifier — see **Known limitations** before treating category boundaries as precise.

## Summary (all 284 failures)

| Category | Count | % of failures |
|----------|------:|----------------:|
| Invalid SQL | 4 | 1.4% |
| Schema linking | 23 | 8.1% |
| JOIN errors | 72 | 25.4% |
| Fan-out | 0 | 0.0% *(N/A at L3 — no materialised denormalised surface)* |
| GROUP BY errors | 17 | 6.0% |
| Nesting problem | 8 | 2.8% |
| Other | 160 | 56.3% |
| **Total** | 284 | 100.0% |

## Subtype breakdown

### Invalid SQL

| Subtype | Count |
|---------|------:|
| other_execution_error | 3 |
| wrong_column | 1 |

### Schema linking

| Subtype | Count |
|---------|------:|
| wrong_table | 22 |
| wrong_column | 1 |

### JOIN errors

| Subtype | Count |
|---------|------:|
| extra_table | 27 |
| missing_table | 25 |
| wrong_table | 20 |

### GROUP BY errors

| Subtype | Count |
|---------|------:|
| missing_or_extra_groupby | 17 |

### Nesting problem

| Subtype | Count |
|---------|------:|
| having_mismatch | 4 |
| window_fn_mismatch | 2 |
| set_op_mismatch | 1 |
| cte_mismatch | 1 |

### Other

| Subtype | Count |
|---------|------:|
| value_or_logic | 160 |

## By database

| Database | Invalid SQL | Schema linking | JOIN errors | GROUP BY errors | Nesting problem | Other | Total |
|---|---|---|---|---|---|---|---|
| california_schools | 1 | 3 | 10 | 3 | 0 | 11 | 28 |
| debit_card_specializing | 0 | 0 | 8 | 3 | 0 | 13 | 24 |
| european_football_2 | 0 | 0 | 3 | 0 | 4 | 26 | 33 |
| financial | 0 | 2 | 10 | 2 | 0 | 9 | 23 |
| formula_1 | 0 | 10 | 11 | 2 | 0 | 17 | 40 |
| student_club | 0 | 2 | 8 | 2 | 0 | 12 | 24 |
| superhero | 1 | 0 | 2 | 2 | 1 | 19 | 25 |
| thrombosis_prediction | 1 | 2 | 6 | 1 | 1 | 38 | 49 |
| toxicology | 1 | 4 | 14 | 2 | 2 | 15 | 38 |

## Agreement with the n=60 manual sample

Checked 49 non-correct questions from the manually-labelled sample (`docs/error_analysis/qwen14b_L3S3_error_taxonomy.md`) against this automated classifier: **41/49 agree (83.7%)**.

| QID | Manual label | Automated label |
|-----|--------------|-------------------|
| Q1147 | Schema linking | Other |
| Q152 | Schema linking | Other |
| Q865 | Schema linking | Other |
| Q1403 | Schema linking | JOIN errors |
| Q1164 | Schema linking | Other |
| Q41 | Nesting problem | GROUP BY errors |
| Q95 | Other | GROUP BY errors |
| Q219 | Other | JOIN errors |

## Calibration history

This classifier went through one calibration pass against the n=60 manual sample: agreement went from **75.5% (37/49)** to **83.7% (41/49)** after two fixes, both kept in the current code:

1. **CTE names are excluded from the table-set comparison** (`_tables_in` subtracts `WITH x AS (...)` names), and CTE-presence mismatch was added as its own Nesting signal alongside set-operator and window-function mismatch. Before this fix, a CTE name like `ranked` in `WITH ranked AS (...) SELECT ... FROM ranked` looked like a missing real table, misrouting the failure to JOIN.
2. **The raw "subquery count differs" signal for Nesting was removed.** It fired on ordinary `WHERE x IN (SELECT ...)` filtering subqueries that both gold and prediction use idiomatically — not a nesting *problem* by any reasonable reading. Nesting is now detected only via CTE/window-function/set-operator presence mismatches, which are real structural signals. This dropped Nesting from 28 (9.9%) to 4 (1.4%) — the manual sample's rate is 2.0% (1/49), so the two now agree.
3. **Extra/missing-table cases now check whether the prediction's own SELECT list pulls its answer from the extra table** (via alias resolution). If it does, that's reclassified from JOIN to Schema linking — an extra join whose whole purpose was sourcing the (wrong) answer column is a table-choice mistake, not a join-plan mistake. This fixed 2 of the original 4 same-pattern disagreements (Q1422, Q1187) and, combined with also treating differing-size *substitutions* (both a missing and an extra table, not just equal-size swaps) as Schema linking, fixed Q206 too. Schema linking rose from 16 (5.6%) to 23 (8.1%); JOIN fell from 84 (29.6%) to 72 (25.4%).

## Remaining disagreements (8/49) — read before trusting a specific count

- **Q1147, Q152, Q865, Q1164** (manual: Schema linking; auto: Other) — all four are **same-table wrong-column choices** (e.g. ranking by `strength` instead of `overall_rating`, both on the same joined table). Table sets match exactly, so there is no structural signal left to catch these — they fall to Other by construction. This is the single largest remaining gap: **Schema linking's true rate is still higher than this doc's 8.1%**, and Other's true rate is correspondingly lower than 56.3%.
- **Q1403** (manual: Schema linking; auto: JOIN, extra_table) — the extra joined table (`expense`) doesn't feed the SELECT list directly (the model recomputed overspend via `SUM(expense.cost) - budget.amount` instead of using the existing `budget.remaining` column), so the alias-resolution check doesn't catch it. Recognising "a column already exists for exactly this purpose and was ignored" needs semantic knowledge this classifier doesn't have.
- **Q41, Q95** (manual: Nesting / Other; auto: GROUP BY) — on inspection these are **arguably relabels, not classifier errors**: gold in both cases has no top-level `GROUP BY` (Q41 uses a window function instead; Q95 has an unrelated grouping artefact one level up) while the prediction adds one that gold doesn't have. Per `error_taxonomy.md`'s own priority order (GROUP BY checked before Nesting/Other), a genuine `GROUP BY`-presence mismatch outranks the manual labels chosen for these two during the original by-hand pass — the manual doc, not the classifier, is the looser of the two here.
- **Q219** (manual: Other; auto: JOIN, missing_table) — gold joins `atom` and the prediction drops it entirely, which is a genuine structural omission; the manual pass weighted the (also-present) invented literal values as the more salient cause. Both readings are defensible; this is a real judgment call, not a bug.

## Known limitations

- **Same-table wrong-column choices fall into "Other", not "Schema linking"** — see Q1147/Q152/Q865/Q1164 above. This is the dominant remaining gap and is not fixable without a real semantic parse of which column the question actually refers to.
- **An extra join is only reclassified to Schema linking if the SELECT list directly references it** via a resolvable alias — extra joins that only feed a `WHERE`/`ORDER BY`/aggregate expression (like Q1403) still default to JOIN.
- **JOIN key mismatches within an unchanged table set are not detected** (e.g. joining on the wrong FK column when both tables were already correct, without changing which tables are used) — these fall into GROUP BY/Nesting/Other depending on what else differs.
- **Alias resolution is regex-based, not a real SQL parser** — it can mis-attribute aliases in unusual formatting (no `AS`, nested parens, multiple statements) though this wasn't observed to matter in the n=60 spot-check.
- Treat this doc as the **full-population, mechanical complement** to the `qwen14b_L3S3_error_taxonomy.md` manual n=60: use the manual doc's category boundaries as ground truth on close calls, and this doc's per-database breakdown as the large-sample view, keeping the Schema-linking-vs-Other undercount above in mind.
