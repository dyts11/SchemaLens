# Supplementary: four-database accuracy (Gemini 2.5 Flash)

**Databases:** `toxicology`, `california_schools`, `formula_1`, `superhero`  
**Model:** `gemini-2.5-flash`  
**Results:** `results/gemini-2.5-flash__L*S*.csv`  
**Metric:** execution accuracy (`correct` in CSV)

These four DBs were chosen for supplementary work (e.g. schema-complexity case studies). This note records accuracy breakdowns and difficulty mix from the main 397-question arcwise set.

---

## 1. Schema size (context)

Counts on native 3NF SQLite (`dev_20240627/dev_databases/{db_id}/{db_id}.sqlite`).

| Database | Tables | Total columns | Avg cols / table |
|----------|-------:|--------------:|-----------------:|
| `toxicology` | 4 | 11 | 2.75 |
| `superhero` | 10 | 31 | 3.10 |
| `debit_card_specializing` | 5 | 21 | 4.20 |
| `student_club` | 8 | 48 | 6.00 |
| `financial` | 8 | 55 | 6.88 |
| `formula_1` | 13 | 94 | 7.23 |
| `thrombosis_prediction` | 3 | 64 | 21.33 |
| `california_schools` | 3 | 89 | 29.67 |
| `european_football_2` | 7 | 199 | 28.43 |

**Selected four** span a range of table counts and widths; table count alone does not capture “complexity” (e.g. `california_schools` has only 3 tables but ~30 columns per table).

**Questions in the 397-question set:**

| Database | n |
|----------|--:|
| `formula_1` | 66 |
| `superhero` | 52 |
| `toxicology` | 40 |
| `california_schools` | 30 |
| **Total (4 DBs)** | **188** |

---

## 2. Difficulty mix — not matched across the four DBs

Proportions of **simple / moderate / challenging** (from `gemini-2.5-flash__L3S3.csv`; same questions at L1–L3).

| Database | n | Simple | Moderate | Challenging |
|----------|--:|--------|----------|-------------|
| `toxicology` | 40 | 12.5% | 42.5% | **45.0%** |
| `california_schools` | 30 | 26.7% | **56.7%** | **16.7%** |
| `formula_1` | 66 | **42.4%** | 39.4% | 18.2% |
| `superhero` | 52 | 26.9% | 50.0% | 23.1% |

**Pooled across these 4 DBs (188 questions):** 29.3% simple · 45.7% moderate · 25.0% challenging.

**All 397 questions:** 28.7% · 48.4% · 22.9%.

| Database | Main skew | Max gap vs 4-DB pooled % |
|----------|-----------|-------------------------|
| `toxicology` | Many **challenging** (45% vs 25% pooled) | ~20 pp |
| `formula_1` | Many **simple** (42% vs 29% pooled) | ~13 pp |
| `california_schools` | Few **challenging** (17% vs 25% pooled) | ~11 pp |
| `superhero` | Closest to pooled mix | ~4 pp |

**Takeaway:** Raw accuracy across DBs is **not** difficulty-matched. `formula_1` has the easiest mix; `toxicology` the hardest; `superhero` is the most representative of the combined pool. Stratify by difficulty when comparing DBs.

### Question counts per DB × difficulty (fixed across L1–L3)

| Database | Simple | Moderate | Challenging | Total |
|----------|-------:|---------:|------------:|------:|
| `toxicology` | 5 | 17 | 18 | 40 |
| `california_schools` | 8 | 17 | 5 | 30 |
| `formula_1` | 28 | 26 | 12 | 66 |
| `superhero` | 14 | 26 | 12 | 52 |

---

## 3. Overall accuracy by condition

### By structural level (semantic **S3** fixed)

| Level | toxicology (n=40) | california_schools (n=30) | formula_1 (n=66) | superhero (n=52) |
|-------|------------------:|--------------------------:|-----------------:|-----------------:|
| **L1** | 7.5% (3/40) | 13.3% (4/30) | 53.0% (35/66) | 61.5% (32/52) |
| **L2** | 5.0% (2/40) | 10.0% (3/30) | 50.0% (33/66) | 63.5% (33/52) |
| **L3** | 2.5% (1/40) | 10.0% (3/30) | 53.0% (35/66) | 67.3% (35/52) |
| **L4** | 10.0% (4/40) | 6.7% (2/30) | 50.0% (33/66) | 65.4% (34/52) |
| **L5** | 10.0% (4/40) | 10.0% (3/30) | 47.0% (31/66) | 63.5% (33/52) |
| **L6** | 12.5% (5/40) | 13.3% (4/30) | 50.0% (33/66) | 65.4% (34/52) |

### By semantic level (structural **L3** fixed)

| Sem | toxicology | california_schools | formula_1 | superhero |
|-----|------------|--------------------|-------------|-----------|
| **S1** | 2.5% (1/40) | 0.0% (0/30) | 4.5% (3/66) | 25.0% (13/52) |
| **S2** | 10.0% (4/40) | 6.7% (2/30) | 42.4% (28/66) | 67.3% (35/52) |
| **S3** | 2.5% (1/40) | 10.0% (3/30) | 53.0% (35/66) | 67.3% (35/52) |

### Pooled summaries

| Database | L1–L6 · **S3** (6 runs) | All **18** conditions |
|----------|-------------------------|------------------------|
| **superhero** | **64.4%** (201/312) | 53.1% (497/936) |
| **formula_1** | **50.5%** (200/396) | 37.0% (439/1188) |
| **california_schools** | 10.6% (19/180) | 5.9% (32/540) |
| **toxicology** | 7.9% (19/240) | 6.8% (49/720) |

**All four DBs combined (18 conditions):** 30.1% (1017/3384).

**Short read:** `superhero` and `formula_1` carry most accuracy on this subset; `toxicology` and `california_schools` stay very low (~2–13% per cell). L3·S3 is not best for toxicology (2.5%) or california_schools (10%); superhero peaks at L3·S3 (67.3%).

---

## 4. L1–L3 · S3 only — accuracy by difficulty

Execution accuracy by database and **simple / moderate / challenging** for **L1·S3**, **L2·S3**, and **L3·S3** only.

### L1·S3

| Database | Simple | Moderate | Challenging | **All** |
|----------|--------|----------|-------------|---------|
| `toxicology` | 20.0% (1/5) | 5.9% (1/17) | 5.6% (1/18) | **7.5%** (3/40) |
| `california_schools` | 25.0% (2/8) | 11.8% (2/17) | 0.0% (0/5) | **13.3%** (4/30) |
| `formula_1` | 57.1% (16/28) | 50.0% (13/26) | 50.0% (6/12) | **53.0%** (35/66) |
| `superhero` | 78.6% (11/14) | 65.4% (17/26) | 33.3% (4/12) | **61.5%** (32/52) |

### L2·S3

| Database | Simple | Moderate | Challenging | **All** |
|----------|--------|----------|-------------|---------|
| `toxicology` | 20.0% (1/5) | 5.9% (1/17) | 0.0% (0/18) | **5.0%** (2/40) |
| `california_schools` | 0.0% (0/8) | 11.8% (2/17) | 20.0% (1/5) | **10.0%** (3/30) |
| `formula_1` | 57.1% (16/28) | 46.2% (12/26) | 41.7% (5/12) | **50.0%** (33/66) |
| `superhero` | 78.6% (11/14) | 69.2% (18/26) | 33.3% (4/12) | **63.5%** (33/52) |

### L3·S3

| Database | Simple | Moderate | Challenging | **All** |
|----------|--------|----------|-------------|---------|
| `toxicology` | 20.0% (1/5) | 0.0% (0/17) | 0.0% (0/18) | **2.5%** (1/40) |
| `california_schools` | 12.5% (1/8) | 5.9% (1/17) | 20.0% (1/5) | **10.0%** (3/30) |
| `formula_1` | 42.9% (12/28) | 65.4% (17/26) | 50.0% (6/12) | **53.0%** (35/66) |
| `superhero` | 78.6% (11/14) | 69.2% (18/26) | 50.0% (6/12) | **67.3%** (35/52) |

### Pooled L1 + L2 + L3 · S3 (three conditions combined per cell)

| Database | Simple | Moderate | Challenging | **All** |
|----------|--------|----------|-------------|---------|
| `toxicology` | 20.0% (3/15) | 3.9% (2/51) | 1.9% (1/54) | **5.0%** (6/120) |
| `california_schools` | 12.5% (3/24) | 9.8% (5/51) | 13.3% (2/15) | **11.1%** (10/90) |
| `formula_1` | 52.4% (44/84) | 53.8% (42/78) | 47.2% (17/36) | **52.0%** (103/198) |
| `superhero` | 78.6% (33/42) | 67.9% (53/78) | 38.9% (14/36) | **64.1%** (100/156) |

**Caveat:** Many cells have **small n** (e.g. toxicology simple n=5, california_schools challenging n=5); per-cell percentages are noisy. `superhero` and `formula_1` stay above the other two DBs at every difficulty; `toxicology` / `california_schools` are near zero on moderate/challenging for most levels.

---

## 5. Related docs

- `docs/experiment_design.md` — §12 schema complexity buckets (table-count rules)
- `docs/gemini_S3_error_analysis_L1_L2_L3.md` — error-type analysis (all 9 DBs, L1–L3)
- `docs/main_experiment_accuracy_tables.md` — full-model accuracy tables

---

## Regeneration

```bash
cd schema_effect
# Per-DB accuracy is derived from results/gemini-2.5-flash__L*S*.csv
# Re-run analysis scripts or extend analysis/generate_accuracy_tables_md.py for automation
```
