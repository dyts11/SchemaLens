# L1S3 aggregate failures: evaluation vs generation errors

> **Combined doc:** Full L1/L2/L3 error analysis plus this section as **Part V** → [`gemini_S3_error_analysis_L1_L2_L3.md`](gemini_S3_error_analysis_L1_L2_L3.md).

Examples from `results/llama-3.3-70b-or__L1S3.csv` (`structural_level=1`, `semantic_level=3`, `question_type=aggregate`, `outcome=wrong_answer`). The same evaluation asymmetry applies to **Gemini** `gemini-2.5-flash__L1S3.csv` (142 aggregate failures).

**Setup:** Gold SQL runs on the **3NF** database; predicted SQL runs on **`{db_id}__1nf.sqlite`** (`one_nf_0`). Results are compared as **multisets** (order-independent row bags) in `evaluator.py`.

**Definitions used here**

| Label | Meaning |
|--------|---------|
| **Generation error** | Wrong aggregate, filter, `HAVING`, column mapping, etc. |
| **Evaluation error** | SQL that is the **faithful 1NF translation of gold** (same aggregate shape, same filters) still returns a **different value on 1NF** than gold on 3NF—or needs **deduplication / subqueries** that gold does not need because 3NF has no join fan-out. |

Counterfactual SQL below was executed locally against `dev_20240627/dev_databases/`.

There are **37** aggregate `wrong_answer` rows in this run; below we document the main patterns with **one worked example each** (plus four primary cases in detail).

---

## Q100 — `COUNT` (evaluation error only)

**Question (`financial`):** Among the account opened, how many female customers who were born before 1950 and stayed in Sokolov?

**Gold SQL (3NF):**

```sql
SELECT COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'F' AND STRFTIME('%Y', T2.birth_date) < '1950' AND T1.A2 = 'Sokolov'
```

**Predicted SQL (L1S3 run):**

```sql
SELECT COUNT(client__client_id) FROM one_nf_0 WHERE client__gender = 'F' AND client__birth_date < '1950-01-01' AND district__district_name = 'Sokolov'
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **8** |
| Predicted | 1NF | **2343** |
| Counterfactual: same filters, `COUNT(DISTINCT client__client_id)` | 1NF | **8** (matches gold) |

**Generation error:** None for the *shape* of the query—the prediction mirrors gold (`COUNT` of client id with the same predicates, mapped to `one_nf_0`).

**Evaluation error:** Yes. Gold’s `district ⋈ client` yields **one row per client**; `COUNT(client_id)` counts clients. On `one_nf_0`, the same client appears on **many denormalized rows**, so the **same SQL pattern** over-counts. The benchmark still marks this wrong even though a human could argue the translation is correct.

**Note:** Adding `DISTINCT` is a **repair on 1NF**, not something gold requires on 3NF. That asymmetry is the evaluation issue, not a missing keyword in the model output for Q100 specifically.

**Also in results:** Q109 (same `COUNT` fan-out; see below for membership mismatch).

---

## Q1473 — `AVG` (generation + evaluation)

**Question (`debit_card_specializing`):** What was the average monthly consumption of customers in SME for the year 2013?

**Gold SQL:**

```sql
SELECT AVG(T2.Consumption) / 12 FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME'
```

**Predicted SQL (L1S3 run):**

```sql
SELECT AVG(yearmonth__consumption) FROM one_nf_0 WHERE customers__segment = 'SME' AND yearmonth__date LIKE '2013%'
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **≈ 459.96** |
| Predicted | 1NF | **≈ 5606.69** |
| Counterfactual: `AVG(yearmonth__consumption) / 12` (same filters) | 1NF | **≈ 467.22** (still ≠ gold) |
| Counterfactual: `AVG(c) / 12` on **distinct** `(customer_id, date, consumption)` | 1NF | **≈ 459.96** (matches gold) |

**Generation error:** Missing **`/ 12`** (evidence: “Average Monthly consumption = AVG(Consumption) / 12”).

**Evaluation error:** Yes, **even after `/ 12`**. Duplicated yearmonth rows on `one_nf_0` change the multiset passed to `AVG` (e.g. `AVG(1,2) ≠ AVG(1,1,2)`). Gold’s join does not duplicate `(CustomerID, Date, Consumption)` tuples.

---

## Q1488 — `GROUP BY` + `SUM` (generation + evaluation)

**Question (`debit_card_specializing`):** Who among KAM's customers consumed the most? How much did it consume?

**Gold SQL:**

```sql
SELECT T2.CustomerID, SUM(T2.Consumption) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'KAM' GROUP BY T2.CustomerID ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL (L1S3 run):**

```sql
SELECT customers__customer_id, MAX(yearmonth__consumption) FROM one_nf_0 WHERE customers__segment = 'KAM' GROUP BY customers__customer_id ORDER BY MAX(yearmonth__consumption) DESC LIMIT 1
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **(12459, ≈ 1.61e7)** |
| Predicted (`MAX`) | 1NF | **(12459, ≈ 2.05e6)** |
| Counterfactual: `SUM(yearmonth__consumption) … GROUP BY customers__customer_id` | 1NF | **(19182, ≈ 1.96e8)** — wrong customer and total |
| Counterfactual: `SUM` on **distinct** `(customer_id, date, consumption)` | 1NF | **(12459, ≈ 1.61e7)** (matches gold) |

**Generation error:** Uses **`MAX`** (peak month) instead of **`SUM`** (total over months).

**Evaluation error:** Yes, **after fixing to `SUM`**. Raw `SUM` on `one_nf_0` multiplies each month’s consumption by the fan-out factor (e.g. customer 12459: 19 distinct months but **190** rows), so the top customer and amount are wrong until yearmonth facts are deduplicated.

---

## Q1475 — `GROUP BY` + `HAVING` (generation + evaluation)

**Question (`debit_card_specializing`):** How many customers in KAM had a consumption of less than 30,000 for the year 2012?

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T2.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'KAM' AND SUBSTRING(T2.Date, 1, 4) = '2012' GROUP BY T2.CustomerID HAVING SUM(T2.Consumption) < 30000 ) AS t1
```

**Predicted SQL (L1S3 run):**

```sql
SELECT COUNT(DISTINCT customers__customer_id) FROM one_nf_0 WHERE yearmonth__date LIKE '2012%' AND yearmonth__consumption < 30000 AND customers__segment = 'KAM'
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **1123** |
| Predicted (row-wise `< 30000`) | 1NF | **1746** |
| Counterfactual: `GROUP BY customer HAVING SUM(consumption) < 30000` on 1NF | 1NF | **1119** |
| Counterfactual: same `HAVING`, but **distinct** `(customer_id, date, consumption)` first | 1NF | **1123** (matches gold) |

**Generation error:** Filters **`consumption < 30000` per row** instead of **`SUM(consumption) < 30000` per customer per year** (`HAVING`).

**Evaluation error:** Yes, **after correct `HAVING`**. Fan-out still shifts the count by **4** until yearmonth rows are deduplicated.

---

## Q1476 — `SUM` on joined facts (evaluation error; faithful shape)

**Question (`debit_card_specializing`):** What was the difference in gas consumption between CZK-paying customers and EUR-paying customers in 2012?

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL (L1S3 run):**

```sql
SELECT
    SUM(CASE WHEN customers__currency = 'CZK' THEN yearmonth__consumption ELSE 0 END) -
    SUM(CASE WHEN customers__currency = 'EUR' THEN yearmonth__consumption ELSE 0 END)
AS consumption_difference
FROM one_nf_0
WHERE yearmonth__date LIKE '2012%'
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **≈ 4.03e8** |
| Predicted | 1NF | **≈ 6.42e8** |
| Counterfactual: same `SUM(CASE…)` on distinct `(customer_id, date, consumption, currency)` | 1NF | **≈ 4.03e8** (matches gold) |

**Generation error:** None for aggregate shape—the `SUM(CASE …)` structure matches gold.

**Evaluation error:** Yes. Join fan-out on `one_nf_0` counts each consumption fact multiple times. Unlike Q1473, there is no missing `/12`; the failure is purely **multiset duplication**.

**Also in results:** Q1486 (similar inflation when gold aggregates on `customers` only).

---

## Q1492 — aggregate on **entity table** vs **1NF rows** (generation + evaluation)

**Question (`debit_card_specializing`):** What percentage of KAM customers pay in euros?

**Gold SQL:**

```sql
SELECT CAST(SUM(Currency = 'EUR') AS FLOAT) * 100 / COUNT(CustomerID) FROM customers WHERE Segment = 'KAM'
```

**Predicted SQL (L1S3 run):**

```sql
SELECT CAST(SUM(CASE WHEN customers__currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*)
FROM one_nf_0
WHERE customers__segment = 'KAM'
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **≈ 3.48%** |
| Predicted | 1NF | **≈ 3.26%** |
| Counterfactual: one row per `customers__customer_id` in denominator | 1NF | **≈ 3.48%** (matches gold) |

**Generation error:** Uses **`COUNT(*)`** over `one_nf_0` rows instead of **`COUNT(CustomerID)`** over customers.

**Evaluation error:** Partly—even with a correct per-customer subquery, gold defines the denominator on the **`customers`** entity; the wide table mixes one row per customer with many duplicate rows.

---

## Q1033 — **lossy 1NF** (evaluation error; incomplete entity coverage)

**Question (`european_football_2`):** What is the average height of players born between 1990 and 1995?

**Gold SQL:**

```sql
SELECT SUM(height) / COUNT(id) FROM Player WHERE SUBSTR(birthday, 1, 4) BETWEEN '1990' AND '1995'
```

**Predicted SQL (L1S3 run):**

```sql
SELECT AVG(Player__height) FROM one_nf_0 WHERE Player__birthday BETWEEN '1990-01-01' AND '1995-12-31'
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **≈ 181.40** (3360 players) |
| Predicted | 1NF | **≈ 189.52** |
| Counterfactual: `SUM(h)/COUNT(id)` on distinct `(Player__id, height)` | 1NF | **≈ 188.94** (still ≠ gold; only **189** players appear in `one_nf_0`) |

**Generation error:** Uses **`AVG(height)`** instead of gold’s **`SUM(height) / COUNT(id)`**; date filter form differs slightly.

**Evaluation error:** Yes, and **not fixable by deduplication alone**. Gold scans the full **`Player`** table; `one_nf_0` only includes players that appear in denormalized match rows, so the population is wrong even after `DISTINCT`.

---

## Q109 — `COUNT` + **1NF membership mismatch** (evaluation error)

**Question (`financial`):** How many clients opened their accounts in Jesenik branch were women?

**Gold SQL (3NF):**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' AND T2.A2 = 'Jesenik'
```

**Predicted SQL (L1S3 run):**

```sql
SELECT COUNT(client__client_id) FROM one_nf_0 WHERE client__gender = 'F' AND district__district_name = 'Jesenik'
```

| Query | DB | Result |
|--------|-----|--------|
| Gold | 3NF | **26** |
| Predicted | 1NF | **7084** |
| Counterfactual: `COUNT(DISTINCT client__client_id)` (same filters) | 1NF | **25** (still ≠ gold) |

**Generation error:** None for shape—same `COUNT(client_id)` pattern as Q100.

**Evaluation error:** Yes, and **beyond fan-out**: `COUNT(DISTINCT …)` fixes multiplicity but **not** the answer, because some gold clients are absent from `one_nf_0` and others appear spuriously (1NF materialization changes *who* is counted).

---

## Pattern index (all 37 aggregate wrong answers)

| Failure type | Example Q | Generation | Evaluation |
|--------------|-----------|------------|------------|
| `COUNT` fan-out, faithful translation | 100 | No | Yes |
| `AVG` + missing formula + fan-out | 1473 | Yes | Yes |
| `GROUP BY` wrong aggregate (`MAX` vs `SUM`) + fan-out | 1488 | Yes | Yes |
| Row filter vs `HAVING` + fan-out | 1475 | Yes | Yes |
| `SUM` faithful shape, fan-out on join | 1476 | No | Yes |
| Entity-level vs row-level `COUNT` / % | 1492 | Yes | Partly |
| Lossy wide table (missing entities) | 1033 | Yes | Yes |
| `COUNT` fan-out + membership skew | 109 | No | Yes |
| Wrong predicate / column / query logic | 862, 1491, … | Yes | No |

---

## Sources

- `schema_effect/results/llama-3.3-70b-or__L1S3.csv`
- `schema_effect/dev_20240627/dev.json`
- `schema_effect/src/evaluator.py` (L1 predicted DB, multiset compare)
