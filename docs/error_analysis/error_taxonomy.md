# Error Taxonomy (§5.2 shared error instrument)

Unified, mutually-exclusive failure taxonomy for all L1–L6 × S1–S3 conditions, all
methods (§5.3), and all model scales (§5.4). Replaces the two ad-hoc, mutually
inconsistent schemes currently in use:

- the L1-only `(a)/(b)/(c)` generation-vs-eval-artefact split
  (`analysis/classify_l1s3_qwen14b_sample.py`, `docs/error_analysis/qwen14b_L1S3_manual_error_summary.md`)
- the cross-level `fan-out / wrong-table / join-plan / logic / column` scheme
  (`docs/error_analysis/gemini_S3_error_analysis_L1_L2_L3.md`)

Base structure follows DIN-SQL's six-category few-shot error analysis
(Pourreza & Rafiei, 2023, §3/Figure 1 — arXiv:2304.11015), extended with two
project-specific categories: **Fan-out**, which DIN-SQL has no equivalent for
because it never evaluates against a denormalised materialised schema, and
**Predicate error**, split out of DIN-SQL's Miscellaneous bucket once manual
annotation of real failures showed "wrong literal value" and "meaning-altering
predicate transformation" were its two largest, most cleanly-separable
components (see `qwen14b_L3S3_annotation_taxonomy_review.md`).

## Categories (priority order — first match wins)

Each failure gets exactly one **primary** label, with one **subcategory**
underneath it. Checked top-down; a failure is assigned to the first category
whose condition holds. This resolves the compound-label ambiguity that both
legacy docs had to patch after the fact (the old "b > c > a" and
"column/literal-before-fanout" rules become special cases of one ordering).

<table>
<thead>
<tr><th>#</th><th>Category</th><th>Subtype</th><th>Description</th></tr>
</thead>
<tbody>
<tr><td rowspan="3">1</td><td rowspan="3"><strong>Invalid SQL</strong></td><td>Wrong table</td><td>Referenced table doesn't exist anywhere in the schema (<code>no such table</code> error)</td></tr>
<tr><td>Wrong column</td><td>Referenced column doesn't exist anywhere in the schema (<code>no such column</code> error)</td></tr>
<tr><td>Other execution error</td><td>Syntax errors, nested-aggregate misuse (e.g. <code>AVG(COUNT(*))</code>), unsupported/non-SQLite functions, an alias referenced without being declared in <code>FROM</code>/<code>JOIN</code>, or timeout — not caused by a hallucinated identifier</td></tr>
<tr><td rowspan="2">2</td><td rowspan="2"><strong>Schema linking</strong></td><td>Wrong table</td><td>A real table in the schema, but not the one the question refers to (a same-role substitution)</td></tr>
<tr><td>Wrong column</td><td>A real column in the schema, but not the one the question refers to — includes wrong <code>col_a</code>/mapped-name grounding at S1/S2, wrong 2NF cluster, wrong 3NF table, and an alias mix-up on an already-joined table</td></tr>
<tr><td rowspan="3">3</td><td rowspan="3"><strong>JOIN errors</strong></td><td>Wrong table</td><td>Join omits a required table, or joins the wrong table (a size mismatch in the table set, not a same-role swap)</td></tr>
<tr><td>Wrong column</td><td>Right tables joined, but on the wrong key/FK column</td></tr>
<tr><td>Join type error</td><td>Correct tables and join condition, but the wrong join operation — <code>INNER</code> substituted for gold's <code>LEFT</code>/<code>RIGHT</code>/<code>FULL</code>, silently dropping rows gold preserves</td></tr>
<tr><td rowspan="2">4</td><td rowspan="2"><strong>Fan-out</strong> <em>(L1/L2 only)</em></td><td>Recoverable</td><td>A <code>DISTINCT</code>/<code>COUNT(DISTINCT …)</code> repair on the existing predicted SQL reproduces gold's result multiset</td></tr>
<tr><td>Irrecoverable</td><td>No <code>DISTINCT</code>-level repair works — needs a dedup subquery, or the wide table has lost/merged entities entirely</td></tr>
<tr><td rowspan="2">5</td><td rowspan="2"><strong>GROUP BY errors</strong></td><td>Wrong table</td><td>Grouped at the wrong entity/table granularity (e.g. grouping by order instead of by customer). Scoped strictly to the <code>GROUP BY</code> clause itself — <code>HAVING</code> mismatches of any kind belong to Nesting (category 6), not here</td></tr>
<tr><td>Wrong column</td><td>Wrong or missing grouping column within the right table</td></tr>
<tr><td rowspan="3">6</td><td rowspan="3"><strong>Nesting problem</strong></td><td>Wrong sub-query</td><td>The query needs a subquery construct — a <code>WITH … AS (…)</code> CTE, a window function (<code>OVER (…)</code>, <code>RANK()</code>, <code>DENSE_RANK()</code>, …), a derived table (<code>FROM (SELECT …)</code>), or any other embedded <code>SELECT</code> — that the prediction doesn't reproduce, or vice versa; these are all just <em>forms</em> a subquery takes, not separate failure modes</td></tr>
<tr><td><code>HAVING</code> clause mismatch</td><td>Gold/prediction differ in <code>HAVING</code> presence or condition, whether or not it contains a literal subquery — a post-aggregation filter is grouped here with nesting, not with <code>GROUP BY</code></td></tr>
<tr><td>Wrong set operation</td><td><code>UNION</code>/<code>INTERSECT</code>/<code>EXCEPT</code> missing or mismatched</td></tr>
<tr><td rowspan="2">7</td><td rowspan="2"><strong>Predicate error</strong></td><td>Filter value error</td><td>Correct column/table/operator/structure — only the compared literal value differs. Covers both a surface-form variant of the same real-world value (abbreviation vs full name, case, spelling) and a flatly wrong/invented value unrelated to the real one</td></tr>
<tr><td>Predicate semantic error</td><td>Everything else that changes a predicate's meaning: a wrong/incorrect function or transformation (e.g. <code>strftime()</code> misapplied to a text-typed date column), a restructured expression, or a condition wholesale added/dropped for a reason other than wrong column (→ Schema linking)</td></tr>
<tr><td rowspan="2">8</td><td rowspan="2"><strong>Other</strong></td><td>Wrong aggregate function or scaling</td><td>Aggregate function choice differs (e.g. <code>SUM</code> vs <code>MAX</code> vs <code>AVG</code>), or a scaling factor is missing/extra (e.g. <code>/12</code>, <code>*100</code>)</td></tr>
<tr><td>Missing/redundant <code>DISTINCT</code>/<code>DESC</code></td><td><code>DISTINCT</code> presence or <code>ASC</code>/<code>DESC</code> direction differs, and there's no materialised wide table to blame (that would be Fan-out instead)</td></tr>
</tbody>
</table>

**The wrong-table/wrong-column split is consistent across categories 1–3 and
5**, but the *meaning* of "wrong" changes by category. One cross-cutting rule
spans categories 1–3 and must be resolved before anything else:

> **Invalid SQL vs Schema linking vs JOIN is never decided by "does
> `outcome == error`" — it's decided by "does the identifier exist *anywhere*
> in the schema, and does reaching it need a join."** A `no such
> table`/`no such column` error message is necessary but not sufficient for
> Invalid SQL: if the identifier is real elsewhere in the schema (e.g.
> `frpm.school_ownership_code` when that column actually lives on `schools`),
> it is **not** a hallucination. Route it by *why* it was unreachable —
> genuinely absent from the whole schema → **Invalid SQL**; real, and a
> missing/wrong join would have reached it → **JOIN**; real, but no join
> relationship is involved at all (wrong single table, or a same-named column
> leaked from a sibling table) → **Schema linking** — even though the outcome
> is `"error"` in all three cases. `outcome == "wrong_answer"` never has this
> ambiguity: it's always Schema linking or JOIN directly.

## Classification guide: understanding, decision rule, and keywords per category

For every category below: **what it is** (the failure it describes), **how to
classify it** (the test that decides it applies, and how it's told apart from
neighbouring categories), and **SQL keywords/signals** to look for when reading
a gold/predicted pair. Keyword presence tells you *where to look* — several
categories (Schema linking, Predicate error, GROUP BY's "wrong table") still
need a semantic judgment on top of the keyword match, which is called out
explicitly where it applies.

### 1. Invalid SQL

**What it is:** the predicted SQL fails to execute.

**How to classify:** `outcome == "error"`, *and* the failing identifier is
genuinely absent from the whole schema (see the cross-cutting rule above) —
not reachable via any join, not a naming collision with a sibling table.

- **Wrong table** — referenced table doesn't exist anywhere. *Keywords:*
  `no such table:` in the error message; cross-check the name against the
  full table list.
- **Wrong column** — referenced column doesn't exist anywhere. *Keywords:*
  `no such column:` in the error message; strip any `alias.` prefix and
  cross-check the bare name against every table's column set.
- **Other execution error** — a construction/syntax bug unrelated to any
  specific missing identifier. *Keywords:* `no such function:` (e.g. `YEAR(`,
  `MONTH(`, `DATEDIFF(` — non-SQLite functions); `misuse of aggregate
  function` (nested aggregates like `AVG(COUNT(`, `SUM(COUNT(`); an
  `alias.column` reference where `alias` was never introduced in `FROM`/`JOIN`
  at all; timeout.

### 2. Schema linking

**What it is:** a real table or column exists — it's just not the one the
question is asking about.

**How to classify:** compare, for the same "slot"/role in the query, which
real table or column gold uses vs. which one predicted uses. No join is
missing or wrong here — either an alternative real table was substituted
wholesale, or a real-but-wrong column was picked (possibly via a wrong alias
on an already-joined table). Checked second, right after Invalid SQL, and
*before* JOIN/Fan-out/GROUP BY/Nesting/Predicate error/Other — a wrong
table/column choice always outranks a structural or value explanation for the
same failure.

- **Wrong table** — full substitution of one real table for another serving
  the same role. *Keywords:* `FROM`, `JOIN` — diff the table sets; look for a
  same-size, same-role swap (not a missing/extra table, which is JOIN).
- **Wrong column** — a real column, wrong for the question. *Keywords:*
  `alias.column` / bare column names in `SELECT`/`WHERE`/`ORDER BY` — diff
  which column fills the same role; also check whether an alias's *declared*
  table (in `FROM`/`JOIN … AS`) matches the table the column used with that
  alias actually belongs to (an alias mix-up on an already-joined table, e.g.
  `s.school_name` when `school_name` belongs to the already-joined `satscores`
  aliased `ss`).
- **Open question, unresolved:** a column name "borrowed" from a sibling table
  with *no join present at all* (e.g. `county_name` used directly on
  `schools`, which doesn't have it, in a single-table query) — is that
  wrong-column (the identifier is wrong for this table) or wrong-table (the
  attribute genuinely belongs elsewhere)? Currently classified as wrong-column;
  not clearly better than the alternative, and recurs across
  california_schools, financial, and toxicology, so worth a firm decision
  before scaling up.

### 3. JOIN errors

**What it is:** the join *structure* is wrong — which tables are connected
and how, not which table holds an attribute (that's Schema linking).

**How to classify:** scoped strictly to the join clause; a table/column
referenced correctly elsewhere in the query (e.g. the `SELECT` list) doesn't
disqualify a JOIN label if the join itself is what's broken. Checked after
Schema linking has ruled out a grounding failure outside the join.

- **Wrong table** — a required join is missing, or an extra/different table
  is joined. *Keywords:* `FROM`, `JOIN` — diff the table sets; unlike Schema
  linking's same-size swap, this is a size mismatch (one table present in only
  one side) or a table added that changes join grain without a corresponding
  removal.
- **Wrong column** — right tables joined, wrong key. *Keywords:* `ON`,
  `USING` — same two tables, different column(s) in the join condition.
- **Join type error** — right tables, right condition, wrong operation.
  *Keywords:* `JOIN`/`INNER JOIN` vs `LEFT JOIN`/`RIGHT JOIN`/`FULL JOIN` —
  same `ON`, different join keyword (an `INNER` silently drops rows gold's
  `LEFT` preserves).

### 4. Fan-out *(L1/L2 only — never fires at L3–L6)*

**What it is:** denormalisation-caused row duplication — a materialised wide
table joins multiple child rows per parent, so `SUM`/`COUNT` over it
double-counts.

**How to classify:** only applies where a materialised denormalised schema
exists at all. Checked after JOIN and Schema linking (a wrong table/column
choice outranks it even if a join is also missing — "column/literal errors
first, then fan-out"), before GROUP BY/Nesting/Predicate error/Other. At
L3–L6, JOIN and Schema linking absorb what this category would otherwise
cover (e.g. "wrong table/cluster" at L3 is just category 2).

- **Recoverable** — *Keywords:* absence of `DISTINCT`/`COUNT(DISTINCT …)` on
  an aggregate over a single wide-table scan where gold has a `JOIN`; confirm
  by testing whether adding it reproduces gold's multiset.
- **Irrecoverable** — same absence, but the `DISTINCT` patch, once tried,
  still doesn't match — needs a dedup subquery, or the wide table has
  lost/merged entities entirely.

### 5. GROUP BY errors

**What it is:** a mismatch in the `GROUP BY` clause itself — which column(s)
the query groups by. Nothing else — `HAVING` is Nesting (category 6), and
aggregate function choice is Other (category 8).

**How to classify:** compare `GROUP BY` presence and, if present in both,
the grouping column(s)/expression.

- **Wrong table** — grouped at the wrong entity/table granularity (e.g.
  grouping by order instead of by customer) — same `GROUP BY` keyword usage,
  different real-world granularity; needs semantic judgment, not just a
  keyword diff.
- **Wrong column** — wrong or missing grouping column within the right
  table. *Keywords:* `GROUP BY` — presence differs, or same presence but a
  different column/expression follows it.

### 6. Nesting problem

**What it is:** the query needs a nested/subquery construct the prediction
fails to reproduce (or adds one gold doesn't have).

**How to classify:** compare presence of each subquery form independently
between gold and predicted; any mismatch on any one of them is Nesting.

- **Wrong sub-query** — one bucket for all subquery forms, not split further.
  *Keywords:* `WITH … AS (` (CTE); `OVER (`, `RANK()`, `DENSE_RANK()`,
  `ROW_NUMBER()` (window functions); `FROM (SELECT …)` (derived table); any
  other embedded `SELECT`.
- **`HAVING` clause mismatch** — post-aggregation filter differs, whether or
  not it contains a literal subquery. *Keywords:* `HAVING` — presence differs,
  or same presence but different condition; watch specifically for a
  tie-preserving `HAVING x = (SELECT MAX(…))` pattern collapsed to a plain
  `ORDER BY … LIMIT 1` (or the reverse).
- **Wrong set operation** — *Keywords:* `UNION`, `UNION ALL`, `INTERSECT`,
  `EXCEPT` — presence/absence differs.

### 7. Predicate error

**What it is:** the predicate (filter condition) is wrong, but the
column/table are correct — split from DIN-SQL's Miscellaneous bucket once
annotation showed these were its two largest, cleanly-separable components.

**How to classify:** the column/table are already confirmed correct (ruled
out by categories 1–6); the question is only what's wrong with the condition
itself.

- **Filter value error** — the compared literal is wrong and *nothing else
  is*: same column, same operator, same structure — only the value differs.
  This covers both a surface-form variant of the same real value
  (abbreviation vs full name e.g. `'CZK'` vs `'Czech Koruna'`, case e.g.
  `'euro'` vs `'EUR'`, spelling) **and** a flatly wrong or invented domain
  value that isn't even related to the real one (e.g. `nationality =
  'Netherlandic'` where the real value is `'Dutch'`; `'normal'` invented in
  place of a real code like `'negative'`) — the distinguishing test is
  whether *only the literal* changed, not whether the wrong literal happens
  to resemble the right one. *Keywords:* literal values after `=`, `LIKE`,
  `IN (…)`, `BETWEEN` on the same column, with the rest of the predicate
  identical.
- **Predicate semantic error** — everything else: a wrong/incorrect function
  or transformation, a restructured expression, or a condition wholesale
  added/dropped for a reason other than wrong column (→ Schema linking).
  *Keywords:* functions wrapping a column in `WHERE`/`HAVING` — `strftime(`,
  `SUBSTR(`, `CAST(`, `ABS(`, `ROUND(`, `date(`, `julianday(` — present in one
  side, absent/different in the other, around the *same* underlying column;
  or a condition that moved location (`WHERE` ↔ `CASE`). The moment a function
  or transformation is involved, it's this subtype even if the surface
  symptom looks like "wrong value" — e.g. `strftime()` misapplied to a
  `'YYYYMM'` text column is a wrong transformation, not a wrong value.
  Defaults here (not to a separate bucket) for any wholesale-added/dropped
  condition whose cause isn't clearly a Schema-linking miss.

### 8. Other

**What it is:** the final catch-all, checked last, after every other category
is ruled out. No named subtypes — two flat items.

- **Wrong aggregate function or scaling** — *Keywords:* `SUM(`, `COUNT(`,
  `AVG(`, `MAX(`, `MIN(` wrapping the same underlying expression on both
  sides (a genuine function swap, not `SUM(CASE WHEN x THEN 1 ELSE 0 END)`
  vs `COUNT(CASE WHEN x THEN 1 END)` — those are mathematically identical,
  not an aggregate-function error); `/12`, `* 100`, `/ 100` near an aggregate
  — missing/extra scaling factor. Lives here, not GROUP BY, per DIN-SQL's own
  placement (its GROUP BY category is strictly the clause; "redundant
  aggregation functions" sits under Miscellaneous).
- **Missing/redundant `DISTINCT`/`DESC`, not caused by Fan-out** —
  *Keywords:* `DISTINCT`, `ASC`/`DESC` — presence/direction differs, and
  there's no materialised wide table to blame (that would be Fan-out
  instead).

## Validation procedure (for the paper's §5.2 write-up)

1. Human-annotate a fixed sample (reuse existing `qwen14b_L1S3` n=60 and a new
   S3 cross-level sample) against this 8-category scheme directly — no more
   dual-labelling then a priority-merge step after the fact.
2. Build an LLM classifier prompt from the "Classification guide" section
   above verbatim — each category's "how to classify" test and keyword list
   doubles as the classifier's decision rule.
3. Report agreement (Cohen's κ) between human labels and classifier labels on
   the annotated sample; only then run the classifier over full result sets
   for §5.3/§5.4's error-composition analysis.
4. Any failure the classifier can't confidently place under 2–7 defaults to
   Other (category 8) rather than a silent guess — keeps the "default rule"
   pattern from the old qwen14b summary but scoped to one bucket instead of
   always defaulting to "logic error".

## Migration notes

- `docs/error_analysis/qwen14b_L1S3_manual_error_summary.md` and
  `docs/error_analysis/gemini_S3_error_analysis_L1_L2_L3.md` are kept as-is (historical
  record); do not edit them in place. Re-run classification under this scheme
  as a new doc/CSV once the LLM classifier is built (§5.2 task).
- `analysis/classify_l1s3_qwen14b_sample.py`'s `_distinct_repairs` /
  `_try_repairs_match_gold` machinery is directly reusable for detecting
  category 4a (Resolvable fan-out) — only the surrounding category labels and
  priority order need to change.
- Category 7 (Predicate error) and the "Other execution error" / "Join type
  error" subcategories were added after `qwen14b_L3S3_rule_based_error_details.md`
  was manually annotated for `california_schools` and `debit_card_specializing`
  (52/284 questions) — see `qwen14b_L3S3_annotation_taxonomy_review.md` for the
  full before/after mapping. The remaining 7 databases in that file still carry
  the pre-Predicate-error labels (`Other (value_or_logic)`) and haven't been
  re-annotated against this version yet.
