# Gemini 2.5 Flash · S3 error analysis (L1, L2, L3)

**Model:** `gemini-2.5-flash` · **Semantic level:** S3 (descriptive names)  
**Results:** `results/gemini-2.5-flash__L{1,2,3}S3.csv`


| Level  | Schema                                 | Predicted SQL runs on  |
| ------ | -------------------------------------- | ---------------------- |
| **L1** | Single wide table `one_nf_0`           | `{db}__1nf.sqlite`     |
| **L2** | Multiple 2NF cluster tables `two_nf_*` | `{db}__2nf.sqlite`     |
| **L3** | 3NF table + column names (prompt only) | Native BIRD 3NF SQLite |


Gold SQL always runs on **3NF**. Evaluation: multiset execution accuracy (`src/evaluator.py`).

---

## Part I — Cross-level summary

### Accuracy


| Level | Correct   | Accuracy  | Failures |
| ----- | --------- | --------- | -------- |
| L1·S3 | 134 / 397 | 33.8%     | 263      |
| L2·S3 | 155 / 397 | **39.0%** | 242      |
| L3·S3 | 162 / 397 | **40.8%** | 235      |


**Pairwise transitions (same questions):**


| Transition | Fixed (was wrong → correct) | New failures | Still wrong |
| ---------- | --------------------------- | ------------ | ----------- |
| L1 → L2    | 37                          | 16           | 226         |
| L2 → L3    | 38                          | 31           | 204         |
| L1 → L3    | 59                          | 31           | 204         |


L2 and L3 reach similar accuracy, but **error mixes differ sharply**.

### Primary error types (exclusive labels)

Priority order is level-specific (see Part II–IV). **Logic-related** merges wrong literals, formulas, filters, aggregate semantics, residual SQL shape, and **retrieval** cases that scan one denormalised surface without `JOIN`s.

**Fan-out (primary label)** uses the **same rule at L1 and L2:**

> Gold has `JOIN` · prediction has **no** `JOIN` · query uses **one** denormalised surface (`one_nf_0` or a single `two_nf_*` table) · `question_type = aggregate` · prediction uses `SUM` / `COUNT` / `AVG` / etc.

Retrieval questions with the same “no `JOIN` on wide storage” habit are **not** labelled fan-out; they go to **logic** (`retrieval_wide_no_join`). An earlier version of this doc used a broader L2 rule (any question type → fan-out) and **inflated L2 fan-out to 163 (67%)**; that was incorrect.


| Error type                                 | L1·S3         | L2·S3         | L3·S3         |
| ------------------------------------------ | ------------- | ------------- | ------------- |
| **Fan-out** (aggregate, strict rule above) | **85 (32%)**  | **70 (29%)**  | **2 (1%)**    |
| **Wrong table / cluster**                  | —             | —             | **74 (31%)**  |
| **Join plan**                              | —             | **10 (4%)**   | **25 (11%)**  |
| **Logic-related**                          | **174 (66%)** | **151 (62%)** | **131 (56%)** |
| **Column / attribute**                     | **4 (2%)**    | **11 (5%)**   | **3 (1%)**    |


### Structural habit: gold `JOIN`, prediction without `JOIN` (cross-cutting, all question types)

This is **broader** than the fan-out primary label (includes retrievals).


| Level | Failures | Gold `JOIN`, pred no `JOIN` (any qtype) | Of those, **aggregate** + `AGG` (strict fan-out)                              |
| ----- | -------- | --------------------------------------- | ----------------------------------------------------------------------------- |
| L1    | 263      | **212 (81%)** on `one_nf_0`             | **97** (~37% of failures; **85** after higher-priority column/literal labels) |
| L2    | 242      | **179 (74%)** on one `two_nf_*`         | **76** strict; **70** primary fan-out label                                   |
| L3    | 235      | **15 (6%)**                             | **2**                                                                         |


### Does L2 have the same errors as L1 and L3?


| Question                     | Answer                                                                                                                                                                                                                                                                                                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **L2 vs L1**                 | **Mostly yes (same family).** Both use materialised denormalised SQLite. **~74–81%** of failures skip `JOIN`s on denormalised storage; **primary fan-out** (aggregate-only) is **similar** (32% L1 vs 29% L2)—L2 does **not** have more fan-out than L1 when classified the same way. L2 fixes **37** L1 failures but **226** items stay wrong at both levels. |
| **L2 vs L3**                 | **No (different mix).** L3 accuracy is similar (+3 pp vs L2) but errors shift to **wrong 3NF table** (31%) and **join keys** (11%), with almost no wide-table fan-out. L2 does **not** behave like a stepping stone toward L3’s error profile—it remains L1-like.                                                                                              |
| **Shared across all levels** | **Logic-related** errors (literals, date encoding, wrong metric `/12`, `HAVING` vs row filter, etc.) appear at every level (~24–67% of failures). **Column** errors are a small slice at all levels.                                                                                                                                                           |


**Aggregate questions only:**


| Level | Aggregate correct | Aggregate failures |
| ----- | ----------------- | ------------------ |
| L1    | 60                | 142                |
| L2    | 73                | 129                |
| L3    | 73                | 129                |


L2/L3 improve aggregate accuracy equally vs L1; the gain is not unique to 3NF.

---

## Part II — L1·S3 error types

**Source:** `results/gemini-2.5-flash__L1S3.csv` · **Failures:** 263


| Error type                           | Count | %   | Description                                                                                 |
| ------------------------------------ | ----- | --- | ------------------------------------------------------------------------------------------- |
| **Fan-out / wide-table aggregation** | 85    | 32% | Gold `JOIN`s 3NF tables; pred **aggregate** on `one_nf_0` without join (strict rule above). |
| **Logic-related errors**             | 174   | 66% | Filters, literals, formulas, CTEs; plus **retrieval** wide-scan without join.               |
| **Column / attribute grounding**     | 4     | 2%  | Wrong `table__attr`, exec `no such column`, price vs amount.                                |


### Logic-related — internal breakdown


| Sub-type                                     | Count | % of failures |
| -------------------------------------------- | ----- | ------------- |
| Retrieval wide-scan, no `JOIN` on `one_nf_0` | 106   | 40%           |
| Aggregate SQL shape / formula (residual)     | 43    | 16%           |
| Retrieval other                              | 11    | 4%            |
| Wrong literals / evidence                    | 7     | 3%            |
| Wrong date encoding                          | 7     | 3%            |


### Examples (L1)

- **Fan-out Q1479:** `SUM(yearmonth__consumption)` on `one_nf_0` by year; gold joins `customers` ⋈ `yearmonth`.
- **Logic Q1334:** `zip_code__state = 'IL'` vs gold `'Illinois'`.
- **Logic Q1473:** `AVG(consumption)` on wide rows; gold `AVG(per-customer SUM) / 12`.
- **Column Q758:** `superhero__race` → `no such column` (race on joined table in gold).

---

## Part III — L2·S3 error types

**Source:** `results/gemini-2.5-flash__L2S3.csv` · **Failures:** 242 (231 `wrong_answer`, 11 `error`)


| Error type                           | Count | %   | Description                                                                                 |
| ------------------------------------ | ----- | --- | ------------------------------------------------------------------------------------------- |
| **Fan-out** (aggregate, strict rule) | 70    | 29% | Gold `JOIN`; pred **aggregates** on **one** `two_nf_*` cluster without join—parallel to L1. |
| **Logic-related errors**             | 151   | 62% | Includes **85** retrieval wide-scan-without-join (not labelled fan-out).                    |
| **Column / attribute grounding**     | 11    | 5%  | Wrong `cluster__attr`, exec errors on 2NF tables (11 exec errors vs 4 at L1).               |
| **Join plan (cross-cluster)**        | 10    | 4%  | Pred joins **two** `two_nf_*` tables with wrong keys.                                       |


### Logic-related — internal breakdown


| Sub-type                                      | Count | % of failures |
| --------------------------------------------- | ----- | ------------- |
| Retrieval wide-scan, no `JOIN` on one cluster | 85    | 35%           |
| Aggregate SQL shape / formula (residual)      | 42    | 17%           |
| Retrieval other                               | 15    | 6%            |
| Wrong date encoding                           | 5     | 2%            |
| Wrong literals                                | 4     | 2%            |


### Examples (L2)

- **Fan-out Q1479:** `SUM(yearmonth__consumption)` from `two_nf_yearmonth` only; gold joins `customers` ⋈ `yearmonth`. (Same question as L1; still wrong at L2.)
- **Logic (wide retrieval) Q1344:** `event__notes` from `two_nf_event`; gold `income.notes` — wrong cluster, but **retrieval** so not primary fan-out.
- **Fixed vs L1 Q1476:** subqueries on `two_nf_yearmonth` with currency filters—**correct** at L2 (still wrong at L1 on `one_nf_0` fan-out).
- **Join plan:** rare cross-cluster joins (e.g. joining two `two_nf_*` with incorrect bridge columns).
- **Column:** invalid `cluster__column` on 2NF schema (contributes to 11 exec errors vs 4 at L1).

### L2 vs L1 (same error family?)

**Yes.** ~~74% of L2 failures still skip `JOIN`s on denormalised storage—the same structural habit as L1 (~~81%). **Primary fan-out is not higher at L2** (70 vs 85 cases; 29% vs 32% of failures). What looked like “more fan-out” was **misclassification** of retrieval failures. Splitting into multiple clusters does **not** make the model compose joins; it mostly changes **which** wide table is queried in isolation.

---

## Part IV — L3·S3 error types

**Source:** `results/gemini-2.5-flash__L3S3.csv` · **Failures:** 235


| Error type                       | Count | %   | Description                                                                                           |
| -------------------------------- | ----- | --- | ----------------------------------------------------------------------------------------------------- |
| **Wrong table / cluster**        | 74    | 31% | Wrong fact/dimension table in 3NF (e.g. `transactions_1k` vs `yearmonth`).                            |
| **Logic-related errors**         | 131   | 56% | Filters, literals, formulas, date functions, aggregate semantics.                                     |
| **Join plan**                    | 25    | 11% | Missing `JOIN`, wrong `ON` (`cds` vs `county_district_school_code`, `link_to_member` vs `member_id`). |
| **Column / attribute grounding** | 3     | 1%  | Wrong attribute or price vs amount.                                                                   |
| **Fan-out / wrong agg grain**    | 2     | 1%  | Join present but wrong `GROUP BY` / dedup grain.                                                      |


### Logic-related — internal breakdown


| Sub-type            | Count |
| ------------------- | ----- |
| Aggregate residual  | 69    |
| Retrieval residual  | 54    |
| Wrong literals      | 4     |
| Wrong date encoding | 2     |
| SQL syntax          | 2     |


### Examples (L3)

- **Wrong table Q1476:** `transactions_1k` ⋈ `customers` instead of `yearmonth` consumption.
- **Join plan Q40:** join on `county_district_school_code` vs gold `cds = CDSCode`.
- **Logic Q1484:** country names vs `CZE`/`SVK` codes.
- **Fixed vs L1 Q1334:** correct `member` ⋈ `zip_code` with `state = 'Illinois'`.

---

## Part V — L1 aggregate failures: evaluation vs generation

This section is merged from `l1s3_aggregate_eval_examples.md` (originally worked examples on **Llama 3.3 70B** L1·S3; patterns apply to **Gemini** L1·S3 under the same evaluator).

**Setup:** Gold on **3NF**; prediction on `**{db_id}__1nf.sqlite`** (`one_nf_0`). Comparison is **multiset** (order-independent row bags).


| Label                | Meaning                                                                                                                                   |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Generation error** | Wrong aggregate, filter, `HAVING`, column mapping, etc.                                                                                   |
| **Evaluation error** | Faithful 1NF translation of gold still yields a **different multiset** on 1NF than gold on 3NF—or needs deduplication gold does not need. |


Gemini L1·S3 has **142** aggregate failures (vs 37 in the Llama run used for the original deep dives). The mechanisms below still explain a large share of L1 aggregate wrong answers.

### Q100 — `COUNT` (evaluation error only)

**Question (`financial`):** Female customers born before 1950 in Sokolov.


| Query                                              | DB  | Result               |
| -------------------------------------------------- | --- | -------------------- |
| Gold                                               | 3NF | **8**                |
| Pred `COUNT(client__client_id)` on `one_nf_0`      | 1NF | **2343**             |
| Counterfactual `COUNT(DISTINCT client__client_id)` | 1NF | **8** (matches gold) |


**Generation:** None for shape. **Evaluation:** Yes—fan-out on `one_nf_0`.

### Q1473 — `AVG` (generation + evaluation)

**Question:** Average monthly SME consumption in 2013.


| Query                                                         | Result                      |
| ------------------------------------------------------------- | --------------------------- |
| Gold `AVG(...) / 12` per joined customer-month                | **≈ 459.96**                |
| Pred `AVG(yearmonth__consumption)` on `one_nf_0`              | **≈ 5606.69**               |
| Pred with `/12` only                                          | **≈ 467.22** (still ≠ gold) |
| Pred `/12` on **distinct** `(customer_id, date, consumption)` | **≈ 459.96**                |


**Generation:** Missing `/12`. **Evaluation:** Yes—even after `/12`, duplicated rows change `AVG`.

### Q1488 — `MAX` vs `SUM` (generation + evaluation)

**Question:** KAM customer with highest total consumption.


| Query                                  | Result                   |
| -------------------------------------- | ------------------------ |
| Gold `SUM` by customer                 | **(12459, ≈ 1.61e7)**    |
| Pred `MAX(monthly consumption)`        | **(12459, ≈ 2.05e6)**    |
| Counterfactual `SUM` on raw `one_nf_0` | wrong customer and total |
| `SUM` on distinct month facts          | matches gold             |


**Generation:** `MAX` vs `SUM`. **Evaluation:** Yes after fixing to `SUM` without dedup.

### Q1475 — row filter vs `HAVING` (generation + evaluation)

**Question:** KAM customers with 2012 consumption < 30,000.


| Query                                   | Result   |
| --------------------------------------- | -------- |
| Gold subquery `HAVING SUM(...) < 30000` | **1123** |
| Pred row-wise `consumption < 30000`     | **1746** |
| Pred correct `HAVING` on 1NF            | **1119** |
| Pred `HAVING` + distinct month rows     | **1123** |


### Q1476 — faithful `SUM`, fan-out (evaluation)

**Question:** CZK vs EUR consumption difference in 2012.


| Query                           | Result       |
| ------------------------------- | ------------ |
| Gold                            | **≈ 4.03e8** |
| Pred `SUM(CASE…)` on `one_nf_0` | **≈ 6.42e8** |
| Distinct month facts            | **≈ 4.03e8** |


**Generation:** None for shape. **Evaluation:** Yes (pure duplication). *Gemini: wrong at L1, **correct** at L2 on `two_nf_yearmonth`.*

### Q1492 — entity vs row `COUNT` (generation + evaluation)

Gold: `%` on **customers** rows. Pred: `COUNT(*)` on `one_nf_0` → wrong denominator.

### Q1033 — lossy 1NF (evaluation not fixable by dedup alone)

Gold scans all `Player` rows; `one_nf_0` only contains players appearing in match denormalization → wrong population.

### Q109 — fan-out + membership mismatch

`COUNT(DISTINCT …)` fixes multiplicity but count still **25 vs 26**—1NF row set ≠ 3NF entity set.

### Pattern index


| Failure type                          | Example Q | Generation | Evaluation |
| ------------------------------------- | --------- | ---------- | ---------- |
| `COUNT` fan-out, faithful translation | 100       | No         | Yes        |
| `AVG` + missing `/12` + fan-out       | 1473      | Yes        | Yes        |
| `MAX` vs `SUM` + fan-out              | 1488      | Yes        | Yes        |
| Row filter vs `HAVING` + fan-out      | 1475      | Yes        | Yes        |
| Faithful `SUM`, fan-out               | 1476      | No         | Yes        |
| Entity vs row `%` / `COUNT`           | 1492      | Yes        | Partly     |
| Lossy wide table                      | 1033      | Yes        | Yes        |
| Fan-out + membership skew             | 109       | No         | Yes        |
| Wrong predicate / column / logic      | various   | Yes        | No         |


---

## Methodology

1. Load failures (`correct != true`) from each `gemini-2.5-flash__L*S3.csv`.
2. Assign one **primary** label per failure (level-specific priority).
3. **Fan-out at L1 and L2** must use the **same** predicate: `aggregate` + aggregate function + gold `JOIN` + no pred `JOIN` + single denormalised surface. Do **not** label retrieval failures as fan-out.
4. Logic sub-counts are descriptive, not mutually exclusive.
5. Examples spot-checked; rules under-count semantic column swaps that still execute.

### Classification audit (L1 vs L2 fan-out)


| Rule                                                               | L1 failures | L2 failures |
| ------------------------------------------------------------------ | ----------- | ----------- |
| Broad (any qtype, gold `JOIN`, pred no `JOIN`, one denorm surface) | 212         | 179         |
| **Strict fan-out** (aggregate + `AGG` only)                        | 97          | 76          |
| **Primary label `fanout`** (after column/literals first)           | **85**      | **70**      |


An earlier draft labelled **163** L2 failures as fan-out by applying the **broad** rule as the primary type—that was wrong.

---

## Related files

- `results/gemini-2.5-flash__L1S3.csv`, `L2S3.csv`, `L3S3.csv`
- `docs/l1s3_gemini_error_types.md`, `docs/l3s3_gemini_error_types.md` — short per-level extracts pointing here
- `docs/l1s3_aggregate_eval_examples.md` — stand-alone copy of Part V
- `src/evaluator.py`, `preprocess_data/to_1nf/`, `preprocess_data/to_2nf/`

