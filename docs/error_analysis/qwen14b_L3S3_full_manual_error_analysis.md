# Qwen2.5-Coder-14B · L3·S3 full error analysis (n=284, hand-read)

**Source:** `results/full/qwen2.5-coder-14b-local__L3S3.csv` · **Population:** all 284 failures /
397 questions (113 correct), across all 9 BIRD databases used at this L×S condition.

## Summary (all 284 failures)

| Category | Count | % of failures |
|----------|------:|----------------:|
| **Other** | 157 | 55.3% |
| **Schema linking** | 56 | 19.7% |
| **JOIN errors** | 34 | 12.0% |
| **GROUP BY errors** | 18 | 6.3% |
| **Nesting problem** | 14 | 4.9% |
| **Invalid SQL** | 5 | 1.8% |
| **Fan-out** | 0 | 0.0% *(N/A at L3 — no materialised denormalised surface)* |
| **Total** | 284 | 100.0% |

## By database

| Database | Invalid SQL | Schema linking | JOIN | GROUP BY | Nesting | Other | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| california_schools | 1 | 10 | 5 | 2 | 1 | 9 | 28 |
| debit_card_specializing | 0 | 1 | 5 | 3 | 0 | 15 | 24 |
| european_football_2 | 0 | 3 | 4 | 3 | 2 | 21 | 33 |
| financial | 0 | 6 | 4 | 3 | 1 | 9 | 23 |
| formula_1 | 1 | 13 | 6 | 2 | 2 | 16 | 40 |
| student_club | 0 | 5 | 5 | 2 | 0 | 12 | 24 |
| superhero | 1 | 3 | 1 | 1 | 2 | 17 | 25 |
| thrombosis_prediction | 1 | 5 | 2 | 0 | 3 | 38 | 49 |
| toxicology | 1 | 10 | 2 | 2 | 3 | 20 | 38 |
| **Total** | **5** | **56** | **34** | **18** | **14** | **157** | **284** |

## Comparison to the automated classifier

| Category | Manual (n=284) | Automated (n=284) | Manual n=60 sample |
|---|---:|---:|---:|
| Invalid SQL | 1.8% | 1.4% | 0.0% |
| Schema linking | **19.7%** | 8.1% | 23.3% |
| JOIN | **12.0%** | 25.4% | 10.0% |
| GROUP BY | 6.3% | 7.4% | 5.0% |
| Nesting | 4.9% | 1.4% | 1.7% |
| Other | 55.3% | 56.3% | 41.7% |

This confirms, at full-population scale, exactly the calibration gap the automated classifier's
own report flagged: it shifts real Schema-linking mass into JOIN. Manually, Schema linking is
~2.4× the automated rate (19.7% vs 8.1%) and JOIN is little more than half (12.0% vs 25.4%) —
both land close to the original n=60 sample's rates (23.3% / 10.0%), which used the same
by-hand reading. Two mechanisms explain nearly all of the gap:

1. **Same-table wrong-column choices** (e.g. `strength` instead of `overall_rating`, `position`
   instead of `time`, `admission_type` instead of an unrelated column) can't be caught
   structurally — table sets match exactly — and the automated pass correctly documented this as
   its dominant known limitation. Reading every case by hand recovers them as Schema linking.
2. **Extra/missing-table cases the automated pass resolves to JOIN by default** are very often
   really a wrong-table/wrong-column choice with an incidental join side-effect (e.g. joining
   `budget` to reach the wrong `category` column instead of `event.type`; joining `molecule` to
   filter `label = 'TR004'` when `molecule_id` *is* `'TR004'` directly, no join needed at all).
   The alias-resolution fix in the automated classifier catches some of these (when the wrong
   table feeds the `SELECT` list directly) but not cases where it only feeds a `WHERE`/formula
   expression.

Nesting is the one category where the automated pass *under*-counts relative to manual reading
(1.4% vs 4.9%) — the reverse of the JOIN/Schema-linking gap. The automated detector only fires on
literal `WITH`/`OVER(`/`UNION`-type keywords; manual reading also caught cases where gold's
*approach* is structurally nested (a decoupled global aggregate subquery, a derived table with
`HAVING` tie-preservation) without literally using those keywords, or where a CTE exists in gold
but the predicted table-set happened to still match after CTE-name exclusion, silently routing to
GROUP BY instead of Nesting.

## Notable systematic patterns (found by reading, not by rule)

These recurring failure modes span multiple databases and are worth calling out as candidates for
targeted follow-up analysis, independent of the L×S grid:

- **Assumed-translated-value hallucination, heavily concentrated in `thrombosis_prediction` and
  `toxicology`.** The model frequently assumes BIRD's terse stored codes have been translated to
  readable strings that don't actually exist in the data — `'Inpatient'`/`'Outpatient'` instead of
  `'+'`/`'-'`, `'female'`/`'male'` instead of `'F'`/`'M'`, `'normal'` instead of numeric lab
  thresholds, `'carcinogenic'` instead of `'+'`, element names (`'chlorine'`, `'phosphorus'`)
  instead of two-letter codes (`'cl'`, `'p'`), bond types (`'double'`, `'triple'`) instead of
  symbols (`'='`, `'#'`). This single pattern accounts for a large share of `thrombosis_prediction`
  and `toxicology`'s unusually high **Other** rate (38/49 and 20/38 respectively) — both far above
  every other database's Other share.
- **`molecule_id` confused with `molecule.label`, unique to `toxicology`.** `molecule_id` values
  (`'TR004'`, `'TR060'`, …) are themselves the descriptive join key; the model routinely assumes a
  join to `molecule` and a filter on `molecule.label` (which actually holds the unrelated
  carcinogenicity flag `'+'`/`'-'`) is needed instead of filtering `molecule_id` directly. This
  drove most of toxicology's 10 Schema-linking cases (Q206, Q220, Q226, Q228, Q230, Q231, Q236,
  Q240, Q248, Q249).
- **Wrong FK used for the join, unique to `european_football_2`'s Player/Player_Attributes
  pairs.** Gold repeatedly joins on `player_fifa_api_id`; the model consistently joins on
  `player_api_id` instead (Q1107, Q1114, Q1115) — a systematic join-key preference, not
  independent mistakes.
- **Hallucinated `'Student_Club'` filter values, unique to `student_club`.** A recurring pattern of
  adding a plausible-sounding but nonexistent filter (`position = 'Student_Club'`,
  `major_name = 'Student_Club'`, `event_status = 'Student_Club'`, `income_source = 'Student_Club'`)
  across otherwise-correct queries (Q1317, Q1334, Q1340, Q1394, Q1432) — the model appears to treat
  the database's own name as a plausible enum value.
- **Case-sensitivity mismatches are pervasive and cross-cutting** (`'blue'` vs `'Blue'`,
  `'closed'` vs `'Closed'`, `'North Bohemia'` vs `'north Bohemia'`, `'advertisement'` vs
  `'Advertisement'`) — present in nearly every database, consistent with the n=60 sample's finding
  and the single largest identifiable subtype of the Other category overall.
- **Tie-handling: `ORDER BY … LIMIT 1` substituted for a tie-preserving `HAVING`/subquery-equality
  pattern**, and occasionally the reverse (a subquery-equality pattern used where gold's simple
  `LIMIT 1` was actually correct) — present in `california_schools`, `european_football_2`,
  `superhero`, and `student_club`. Classified as GROUP BY when the mismatch is in an explicit
  `GROUP BY`/`HAVING` clause, Other when it's a plain scalar subquery with no grouping involved.

## Caveats

- This is one annotator's single pass at effort appropriate for a full-population sweep, not the
  more careful multi-hour review behind the n=60 doc (which cites specific column/value evidence
  per question). Spot-checks against the n=60 labels were consistent, but no formal agreement
  score was computed for this pass, and some borderline calls (documented case-by-case where they
  arose, e.g. Q95/Q41's GROUP BY-vs-Other/Nesting boundary) reflect judgment rather than a
  mechanical rule.
- Compound-cause failures (most of them) are labelled by the same priority waterfall as
  `error_taxonomy.md` — Invalid SQL → Schema linking → JOIN → Fan-out → GROUP BY → Nesting → Other
  — so a question with both a wrong-column choice and a wrong literal value is filed under Schema
  linking, not double-counted.
- Per-question labels and reasoning were not persisted to a separate file for this pass (unlike
  the n=60 sample); the counts above are the primary artefact. If a fully auditable per-question
  table is needed later, that would mean re-running this pass with logging.
