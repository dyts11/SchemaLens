# Motivation narrative (s1–s5) ↔ factorial design (L×S)

This note documents how the **slide / motivation story** (steps **s1–s5**, lowercase) maps onto the **implemented experiment** (structural **L1–L6**, semantic **S1–S3**, uppercase). It then walks through **question 901** as the worked example for **s1–s4** on **Gemini 2.5 Flash**.

**Related docs:** [`experiment_design.md`](experiment_design.md) (full protocol), [`gemini_S3_error_analysis_L1_L2_L3.md`](gemini_S3_error_analysis_L1_L2_L3.md) (error taxonomy at descriptive names).

**Results source:** `results/gemini-2.5-flash__L{l}S{s}.csv` (wave 1, N = 397 per condition).

---

## 1. Naming: do not confuse s with S

| Symbol | Meaning |
|--------|---------|
| **s1–s5** | Motivation / storytelling steps in a talk or paper intro |
| **S1–S3** | **Semantic** factor in the factorial (anonymous / abbreviated / descriptive column names) |
| **L1–L6** | **Structural** factor (schema shape and observability in the prompt) |

The motivation step **s3** (“descriptive + minimal structure”) is **not** experiment level **S3** alone—it is the **pair** **L3·S3**. Similarly, **s2** is **L6·S1**, not semantic S2 (abbreviated).

---

## 2. Mapping table (narrative → conditions)

All steps below use the **same** BIRD item: natural-language question, **gold SQL**, underlying data for the condition’s DB, model **`gemini-2.5-flash`**, temperature 0, single pass. Only the **schema text in the prompt** (and L1/L2 materialised DB files when applicable) changes.

| Step | Narrative intent | Factorial condition(s) | What changes in the prompt |
|------|------------------|------------------------|----------------------------|
| **s1** | Controlled comparison: one question, fixed model and data; **vary schema only** | Any **L{i}·S{j}** on the same `question_id` | Full 6×3 grid; same evaluator |
| **s2** | Anonymous names + **richest** structure (FK + join paths) → model **still fails** | **L6·S1** | S1: `col_a`, `col_b`, …; L6: L5 + `JOIN PATHS` |
| **s3** | Descriptive names + **minimal** 3NF structure → model **succeeds** | **L3·S3** | S3: e.g. `circuit_id`, `name`, `date`; L3: table + column list only |
| **s4** | Adding structure **on top of** anonymous names **barely helps** (for this item: not at all) | **L3·S1 → L4·S1 → L5·S1 → L6·S1** | L4: + types/PK; L5: + FK comments; L6: + join paths |
| **s5** | Same questions, same data — **names** lift accuracy where **structure alone** cannot; motivates full **6×3** study | Whole grid + marginals | See §5 |

**Contrast conditions useful in slides (not s2–s4, but same Q901):**

| Condition | Role |
|-----------|------|
| **L3·S2** | Abbreviated names (`cir_id`, …) at minimal structure — also **correct** on Q901 |
| **L6·S3** | Descriptive + full structure — **correct**; extra structure redundant once names are clear |

---

## 3. Question 901 — metadata

| Field | Value |
|-------|--------|
| `question_id` | **901** |
| `db_id` | `formula_1` |
| `difficulty` | simple |
| `question_type` | retrieval |
| Gold SQL | See below |

**Gold SQL** (runs on native BIRD 3NF; same in every result row):

```sql
SELECT DISTINCT T2.name, T1.name, T1.location
FROM circuits AS T1
INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId
WHERE T2.year = 2005 AND STRFTIME('%m', T2.date) = '09'
```

**Task (paraphrase):** List **race name**, **circuit name**, and **location** for races held in **September 2005**.

---

## 4. Q901 walkthrough: s1–s4

### s1 — Hold question, model, and data fixed

| Held constant | Varied |
|---------------|--------|
| BIRD question 901, `gemini-2.5-flash`, gold SQL, evaluator | Schema prompt: **L1–L6** × **S1–S3** |

For the motivation arc we focus on the **3NF ladder** (L3–L6) so the same physical DB is used; L1/L2 use materialised wide SQLite and are not required for s2–s4.

---

### s2 — Anonymous + full structure → **fail** (`L6·S1`)

**Condition:** `structural_level=6`, `semantic_level=1` → `results/gemini-2.5-flash__L6S1.csv`

| | |
|--|--|
| **Outcome** | `wrong_answer` |
| **Correct** | `False` |

**Predicted SQL:**

```sql
SELECT
  T1.col_e,
  T2.col_b,
  T2.col_c
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.col_d = T2.col_a
WHERE
  STRFTIME('%Y', T1.col_f) = '2005' AND STRFTIME('%m', T1.col_f) = '09';
```

**Interpretation:** The model uses explicit **JOIN** syntax (join paths and FK hints are present in the prompt) but still maps **`col_d` / `col_a`** incorrectly for the races→circuits link. Executable SQL returns the **wrong result set** vs gold.

---

### s3 — Descriptive + minimal structure → **succeed** (`L3·S3`)

**Condition:** `structural_level=3`, `semantic_level=3` → `results/gemini-2.5-flash__L3S3.csv`

| | |
|--|--|
| **Outcome** | `correct` |
| **Correct** | `True` |

**Predicted SQL:**

```sql
SELECT
  T1.name,
  T2.name,
  T2.location
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.circuit_id = T2.circuit_id
WHERE
  T1.date BETWEEN '2005-09-01' AND '2005-09-30';
```

**Interpretation:** With **`circuit_id`**, **`name`**, and **`date`**, the model picks the correct join key and September filter without types, FK comments, or `JOIN PATHS`.

---

### s4 — More structure on anonymous names → **still fail** on Q901

Compare **L3·S1 → L6·S1** on the same question. All four are **wrong**; structure tweaks the guess but does not fix grounding.

| Condition | Extra prompt vs L3 | Join used | Outcome |
|-----------|-------------------|-----------|---------|
| **L3·S1** | (baseline anonymous) | `T1.col_c = T2.col_a` | wrong |
| **L4·S1** | + types, PK | `T1.col_c = T2.col_a` | wrong |
| **L5·S1** | + FK comments | `T1.col_d = T2.col_a` | wrong |
| **L6·S1** | + JOIN PATHS | `T1.col_d = T2.col_a` | wrong |

**L3·S1 — predicted SQL:**

```sql
SELECT T1.col_e, T2.col_b, T2.col_c
FROM races AS T1
INNER JOIN circuits AS T2 ON T1.col_c = T2.col_a
WHERE T1.col_d BETWEEN '2005-09-01' AND '2005-09-30'
```

**L4·S1 — predicted SQL:**

```sql
SELECT T1.col_e, T2.col_b, T2.col_c
FROM races AS T1
INNER JOIN circuits AS T2 ON T1.col_c = T2.col_a
WHERE STRFTIME('%Y-%m', T1.col_f) = '2005-09'
```

**L5·S1 — predicted SQL:**

```sql
SELECT
  T1.col_e,
  T2.col_b,
  T2.col_c
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.col_d = T2.col_a
WHERE
  STRFTIME('%Y-%m', T1.col_f) = '2005-09';
```

**L6·S1:** same join as L5·S1 (see s2 above).

**Takeaway for s4:** From L3 to L6, anonymous Q901 moves from **`col_c`** to **`col_d`** on the join (FK/join-path information **does** change behaviour) but **accuracy stays at fail**. Naming at L3·S2 (`cir_id`) or L3·S3 (`circuit_id`) succeeds without that structure.

---

## 5. s5 — Factorial motivation (population summary)

Q901 is one cell; the full study generalises the pattern.

**Gemini 2.5 Flash execution accuracy (397 questions per cell)** — from [`experiment_design.md`](experiment_design.md) §6.2:

|  | **S1** (anonymous) | **S3** (descriptive) |
|--|---------------------:|---------------------:|
| **L3** (minimal) | 4.5% | **40.8%** |
| **L6** (full structure) | 15.6% | 39.0% |

Anonymous accuracy remains low even at L6; descriptive accuracy is high already at L3. Semantic richness dominates the marginal spread for this model.

**Question-level flip (same 397 IDs, 3NF anonymous ladder vs descriptive minimal):**

| Pattern | Count |
|---------|------:|
| **L3·S3** correct, **L6·S1** wrong, **L3·S1** wrong | 106 |
| Above + **L4·S1** and **L5·S1** also wrong | 87 |
| **L6·S1** correct but **L3·S1** wrong (structure helped on S1) | 46 |
| **L3·S1** and **L6·S1** both wrong | 333 |

---

## 6. Q901 — all outcomes (Gemini 2.5 Flash, 18 conditions)

Wave 1 results: `results/gemini-2.5-flash__L{l}S{s}.csv`. Evaluation: multiset execution match vs gold on the DB for that structural level (L1/L2 → materialised SQLite; L3–L6 → native `formula_1` 3NF).

### 6.1 Heatmap (correct = ✓, wrong = ✗)

|  | **S1** (anonymous) | **S2** (abbreviated) | **S3** (descriptive) |
|--|----------------------|----------------------|----------------------|
| **L1** (1NF wide) | ✗ | ✓ | ✓ |
| **L2** (2NF clusters) | ✗ | ✓ | ✓ |
| **L3** (3NF names only) | ✗ | ✓ | ✓ |
| **L4** (3NF + metadata) | ✗ | ✓ | ✓ |
| **L5** (3NF + FK) | ✗ | ✓ | ✓ |
| **L6** (3NF + join paths) | ✗ | ✓ | ✓ |

**Pattern:** **S1** is wrong at every structural level; **S2** and **S3** are correct at every structural level for this question.

### 6.2 Full condition list (with predicted SQL)

Summary table; predicted SQL for each row is copied verbatim from `results/gemini-2.5-flash__L{l}S{s}.csv` (row `question_id=901`).

| Condition | Structural | Semantic | Correct | Outcome |
|-----------|------------|----------|---------|---------|
| L1·S1 | L1 — 1NF wide table | S1 — anonymous | **No** | `wrong_answer` |
| L1·S2 | L1 — 1NF wide table | S2 — abbreviated | **Yes** | `correct` |
| L1·S3 | L1 — 1NF wide table | S3 — descriptive | **Yes** | `correct` |
| L2·S1 | L2 — 2NF clusters | S1 — anonymous | **No** | `wrong_answer` |
| L2·S2 | L2 — 2NF clusters | S2 — abbreviated | **Yes** | `correct` |
| L2·S3 | L2 — 2NF clusters | S3 — descriptive | **Yes** | `correct` |
| L3·S1 | L3 — 3NF baseline | S1 — anonymous | **No** | `wrong_answer` |
| L3·S2 | L3 — 3NF baseline | S2 — abbreviated | **Yes** | `correct` |
| L3·S3 | L3 — 3NF baseline | S3 — descriptive | **Yes** | `correct` |
| L4·S1 | L4 — 3NF + metadata | S1 — anonymous | **No** | `wrong_answer` |
| L4·S2 | L4 — 3NF + metadata | S2 — abbreviated | **Yes** | `correct` |
| L4·S3 | L4 — 3NF + metadata | S3 — descriptive | **Yes** | `correct` |
| L5·S1 | L5 — 3NF + FK | S1 — anonymous | **No** | `wrong_answer` |
| L5·S2 | L5 — 3NF + FK | S2 — abbreviated | **Yes** | `correct` |
| L5·S3 | L5 — 3NF + FK | S3 — descriptive | **Yes** | `correct` |
| L6·S1 | L6 — 3NF + join paths | S1 — anonymous | **No** | `wrong_answer` |
| L6·S2 | L6 — 3NF + join paths | S2 — abbreviated | **Yes** | `correct` |
| L6·S3 | L6 — 3NF + join paths | S3 — descriptive | **Yes** | `correct` |

**Counts:** 12 / 18 correct (66.7%); all 6 failures are **S1**; no `error` outcomes (SQL executed on the condition DB).

#### L1·S1 — incorrect

```sql
SELECT DISTINCT col_c, col_d, col_e FROM one_nf_0 WHERE col_b = 2005 AND col_a = 9
```

#### L1·S2 — correct

```sql
SELECT DISTINCT
  races__name,
  circuits__name,
  circuits__location
FROM one_nf_0
WHERE
  strftime('%Y-%m', races__date) = '2005-09';
```

#### L1·S3 — correct

```sql
SELECT DISTINCT
  races__name,
  circuits__name,
  circuits__location
FROM one_nf_0
WHERE
  races__year = 2005 AND strftime('%m', races__date) = '09';
```

#### L2·S1 — incorrect

```sql
SELECT DISTINCT col_d, col_k, col_l FROM two_nf_races WHERE col_b = 2005 AND strftime('%m', col_e) = '09'
```

#### L2·S2 — correct

```sql
SELECT DISTINCT races__name, circuits__name, circuits__location FROM two_nf_races WHERE races__year = 2005 AND SUBSTR(races__date, 6, 2) = '09'
```

#### L2·S3 — correct

```sql
SELECT DISTINCT
  races__name,
  circuits__name,
  circuits__location
FROM two_nf_races
WHERE
  races__year = 2005 AND STRFTIME('%m', races__date) = '09';
```

#### L3·S1 — incorrect

```sql
SELECT T1.col_e, T2.col_b, T2.col_c FROM races AS T1 INNER JOIN circuits AS T2 ON T1.col_c = T2.col_a WHERE T1.col_d BETWEEN '2005-09-01' AND '2005-09-30'
```

#### L3·S2 — correct

```sql
SELECT T1.name, T2.name, T2.location FROM races AS T1 INNER JOIN circuits AS T2 ON T1.cir_id = T2.cir_id WHERE T1.date LIKE '2005-09-%'
```

#### L3·S3 — correct

```sql
SELECT
  T1.name,
  T2.name,
  T2.location
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.circuit_id = T2.circuit_id
WHERE
  T1.date BETWEEN '2005-09-01' AND '2005-09-30';
```

#### L4·S1 — incorrect

```sql
SELECT T1.col_e, T2.col_b, T2.col_c FROM races AS T1 INNER JOIN circuits AS T2 ON T1.col_c = T2.col_a WHERE STRFTIME('%Y-%m', T1.col_f) = '2005-09'
```

#### L4·S2 — correct

```sql
SELECT
  T1.name,
  T2.name,
  T2.location
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.cir_id = T2.cir_id
WHERE
  STRFTIME('%Y-%m', T1.date) = '2005-09';
```

#### L4·S3 — correct

```sql
SELECT
  R.name,
  C.name,
  C.location
FROM races AS R
JOIN circuits AS C
  ON R.circuit_id = C.circuit_id
WHERE
  STRFTIME('%Y-%m', R.date) = '2005-09';
```

#### L5·S1 — incorrect

```sql
SELECT
  T1.col_e,
  T2.col_b,
  T2.col_c
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.col_d = T2.col_a
WHERE
  STRFTIME('%Y-%m', T1.col_f) = '2005-09';
```

#### L5·S2 — correct

```sql
SELECT T1.name, T2.name, T2.location FROM races AS T1 INNER JOIN circuits AS T2 ON T1.cir_id = T2.cir_id WHERE STRFTIME('%Y-%m', T1.date) = '2005-09'
```

#### L5·S3 — correct

```sql
SELECT
  T1.name,
  T2.name,
  T2.location
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.circuit_id = T2.circuit_id
WHERE
  STRFTIME('%Y-%m', T1.date) = '2005-09';
```

#### L6·S1 — incorrect

```sql
SELECT
  T1.col_e,
  T2.col_b,
  T2.col_c
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.col_d = T2.col_a
WHERE
  STRFTIME('%Y', T1.col_f) = '2005' AND STRFTIME('%m', T1.col_f) = '09';
```

#### L6·S2 — correct

```sql
SELECT
  T1.name,
  T2.name,
  T2.location
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.cir_id = T2.cir_id
WHERE
  STRFTIME('%Y-%m', T1.date) LIKE '2005-09%';
```

#### L6·S3 — correct

```sql
SELECT
  T1.name,
  T2.name,
  T2.location
FROM races AS T1
INNER JOIN circuits AS T2
  ON T1.circuit_id = T2.circuit_id
WHERE
  STRFTIME('%Y-%m', T1.date) = '2005-09';
```

---

## 7. Reproducing this note

```bash
cd schema_effect/results
# Per-condition row for Q901:
rg '^901,' gemini-2.5-flash__L3S1.csv gemini-2.5-flash__L6S1.csv gemini-2.5-flash__L3S3.csv
# All 18 conditions:
for f in gemini-2.5-flash__L*S*.csv; do rg '^901,' "$f" | cut -d, -f1,11,12; done
```

Population counts: join `question_id` across `gemini-2.5-flash__L3S1.csv`, `L4S1.csv`, `L5S1.csv`, `L6S1.csv`, `L3S3.csv` on `correct` / `outcome`.

---

## 8. Alternate worked examples

| `question_id` | Best for |
|---------------|----------|
| **901** | Join / column choice under anonymity (this doc) |
| **1334** | Literal grounding (`Illinois` vs `IL`) with `student_club` |
| **1471** | Simple aggregate (`currency`) |

Same s2/s3/s4 pattern (L6·S1 fail, L3·S3 pass, L3–L6·S1 fail) holds for 1334 and 1471 on Gemini wave 1.
