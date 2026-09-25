# Taxonomy review: manual annotations vs. the original 7-category scheme

**Scope:** every annotation added to [`qwen14b_L3S3_rule_based_error_details.md`](qwen14b_L3S3_rule_based_error_details.md)
across the two databases annotated so far — `california_schools` (28 failures) and
`debit_card_specializing` (24 failures), 52 of 284 total. Original categories are the 7 in
[`error_taxonomy.md`](error_taxonomy.md).

Of the 52 annotated questions: **31 have a written correction**, **4 are flagged (`!!!`) with no
written reason yet**, and **17 have no annotation at all** (implicitly accepted as correctly
labelled).

## 1. New error types/subtypes introduced

### Filter value error *(11 uses — the most-applied new label)*

> The model selects the correct filtering attribute but generates an incorrect literal value in
> the predicate. This includes incorrect string, numeric, date, or boolean values, as well as
> formatting differences (e.g. case mismatches in case-sensitive databases) that change the query
> result.

Applied to: Q28, Q77 (california_schools); Q1476, Q1479, Q1480, Q1483, Q1484, Q1493, Q1505, Q1506,
Q1509 (debit_card_specializing) — all were previously the automated classifier's generic
`Other (value_or_logic)`.

**Relation to the original scheme:** not new content — `error_taxonomy.md`'s Other category
already names "Wrong filter value" as a subcategory with almost identical wording. What's new is
**promoting it to a first-class label** rather than leaving it buried inside Other. Given it's
already 11/13 of this batch's non-flagged Other-reclassifications, that promotion looks justified
by the data: Other is currently a 55%-of-failures catch-all, and "wrong literal value" is clearly
its dominant, cleanly-identifiable component.

One boundary worth flagging: 4 of the 11 uses (Q1476, Q1479, Q1480, Q1483, Q1493) are actually
`strftime()`/date-arithmetic misuse on a text-typed `date` column, not a wrong *value* so much as a
wrong *function applied to the value's stored format*. You may want a `Wrong date encoding`
sibling (already listed as a distinct Other subtype in `error_taxonomy.md`) rather than folding
these into Filter value error — as annotated, the two are currently merged.

### Predicate semantic error *(3 uses — genuinely new content)*

> The model generates a syntactically valid predicate but changes the intended meaning of the
> condition through incorrect logical or arithmetic transformations. This includes introducing
> unnecessary functions, modifying expressions, or altering the semantics of the original
> condition while using the correct attributes.

Applied to: Q23 (`ABS()` added, changing which rows satisfy `enrollment_k12 - enrollment_ages_5_17
> 30`), Q24, Q82 (`ORDER BY Longitude DESC` instead of gold's `ORDER BY ABS(longitude) DESC` —
missing the same `ABS()` transformation, opposite direction of Q23's bug).

**Relation to the original scheme:** this is the one genuinely novel concept in this batch. It
doesn't map cleanly onto any existing Other subcategory — "extra/missing predicate" is about
presence/absence of a condition, not distortion of a condition's *meaning* while keeping the
right columns. Worth adding to `error_taxonomy.md`'s Other subcategory list explicitly.

### Wrong aggregation error *(2 uses)*

Inferred definition from the annotations ("predict use sum instead of count"): the model picks
the wrong aggregate function despite correct columns/tables/filters.

Applied to: Q1490, Q1525 (both `debit_card_specializing`).

**Relation to the original scheme:** already named in `error_taxonomy.md`'s Other subcategory list
("wrong aggregate function choice — `SUM` vs `MAX` vs `AVG`"). Same content as Filter value error's
situation — promoted from a buried subcategory to its own label.

### Join type error *(new JOIN subtype, 1 use)*

> The model identifies the correct tables and join condition but selects an incorrect join
> operation, causing differences in row preservation and query results.

Applied to: Q27 (gold's `LEFT JOIN schools` — preserving schools with no matching `satscores` row
— replaced by predicted's `INNER JOIN`, silently dropping those rows).

**Relation to the original scheme:** genuinely new. `error_taxonomy.md`'s JOIN category currently
only names "missing join" and "wrong join key/table" as subtypes — join *type* (INNER vs
LEFT/RIGHT/FULL) wasn't previously called out, and it's a distinct, mechanically-detectable failure
mode (same tables, same `ON` condition, different `JOIN` keyword) worth adding.

### Invalid SQL → "other execution error" *(1 use, not new — reaffirmed)*

Q47: nested aggregate misuse (`AVG(COUNT(*))`) causing a genuine SQLite error. This subtype
already existed in the rule-based classifier's own schema (`other_execution_error`); the
annotation just confirms it's a real, distinct case rather than proposing something new.

## 2. Corrections within the existing 7 categories (no new type, automated label was just wrong)

| Q | Auto label | Corrected to | Note |
|---|---|---|---|
| Q5 | JOIN (`wrong_table`) | **Invalid SQL** (wrong column) | Annotation: "join path is correct... the column doesn't exist" — the automated classifier's own execution-error routing rule (does gold join the owning table?) picked JOIN because `school_name` exists on `frpm`/`satscores`, but the annotator judges the join path itself unaffected and the column simply absent from the queried table. |
| Q12 | Other | **Schema linking** (wrong column) | |
| Q26 | Other | **Schema linking** (wrong column) | Predicted used `instruction_level_name` where gold uses `School Type` — two distinct real columns. |
| Q36 | Other | **Schema linking** (wrong column) | Framed as schema linking, though the underlying issue described (missing `rtype = 'S'` filter) reads more like a missing-predicate case — see open question below. |
| Q37 | Schema linking (`wrong_table`) | **Nesting** (wrong subquery) | Annotator sees the core failure as the subquery approach itself, not the frpm/satscores table swap. |
| Q40 | Other | **Schema linking** (wrong column) | Same missing-filter-as-schema-linking framing as Q36. |
| Q41 | GROUP BY (`missing_or_extra_groupby`) | **Nesting** (wrong subquery/operation) | Matches the reasoning already in `error_taxonomy.md`'s and the manual n=284 pass's treatment of this exact question — gold's `RANK() OVER (PARTITION BY ...)` replaced by a wrong nested IN-subquery. |
| Q46 | GROUP BY (`missing_or_extra_groupby`) | **Schema linking** (wrong column) | |
| Q50 | Other | **Schema linking** (wrong column) | |
| Q79 | Schema linking (`wrong_column`) | Schema linking (**`wrong_table`**) | Subtype-only correction, category unchanged — see open question below. |
| Q1529 | Other | **Schema linking** (wrong column) | Predicted summed `amount` instead of `amount * price` — missing the `price` column entirely. |
| Q1531 | Other | **Schema linking** (wrong column) | Same missing-`price`-column pattern as Q1529. |

## 3. Flagged without a written reason (`!!!`, no annotation text)

Q11, Q17, Q31, Q87 — all four are **JOIN errors (`missing_table`)** per the automated classifier.
Given every other JOIN-category item in this batch that *did* get a written correction was moved
elsewhere (Q5 → Invalid SQL, Q37 → Nesting), these four flags plausibly mean "I also disagree with
this JOIN label" without having written the replacement yet — worth following up on directly
rather than assuming they're fine.

## 4. Open questions for you to resolve

1. **Is "missing a required filter/predicate" Schema linking, or its own thing?** Q36, Q40, and
   arguably Q46 are annotated as Schema linking (wrong column) but the stated reasoning is about a
   *missing filter condition*, not a wrong column choice per se. `error_taxonomy.md` already has
   "extra/missing predicate" as an Other subcategory — you may want missing-predicate cases to
   route there instead, and reserve Schema linking strictly for "picked column X when Y was
   needed."
2. **Q79: is the boundary "wrong table" or "wrong column"?** `county_name` is a real column that
   exists on `frpm`/`satscores` but not `schools`. The taxonomy's current rule files this as wrong
   *column* (the identifier itself is wrong for this table); your annotation calls it wrong
   *table* (the attribute belongs to a different table). Both are defensible reads of the same
   underlying fact — worth deciding once so it's applied consistently, since this exact "column
   name borrowed from a sibling table" pattern recurs across multiple databases (california_schools,
   toxicology, financial in the earlier hand-read pass).
3. **Filter value error absorbing date-format bugs.** As noted in §1, 4 of the 11 Filter-value-error
   cases are really `strftime()`-on-text-column misuse. Confirm whether you want those merged in
   or split into their own `Wrong date encoding` bucket (already named, just unused so far).

## Next step

If you confirm the above, I can fold these into `error_taxonomy.md` as a revised taxonomy (adding
Predicate semantic error and Join type error as first-class entries, promoting Filter value error
and Wrong aggregation error out of Other) and re-run/re-annotate the remaining 7 databases against
the updated scheme.
