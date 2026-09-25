# Schema size: 1NF, 2NF, and 3NF (nine materialised databases)

Physical SQLite under `dev_20240627/dev_databases/{db_id}/`:

| Normal form | File |
|-------------|------|
| **3NF** | `{db_id}.sqlite` |
| **1NF** | `{db_id}__1nf.sqlite` (`one_nf_0`) |
| **2NF** | `{db_id}__2nf.sqlite` (`two_nf_*`) |

Build metadata tables (`_one_nf_build_meta`, `_two_nf_build_meta`) are excluded. **Total cols** = sum of columns over counted tables.

---

## Combined

| Database | 3NF tables | 3NF cols | 1NF tables | 1NF cols | 2NF tables | 2NF cols |
|----------|----------:|---------:|----------:|---------:|----------:|---------:|
| `california_schools` | 3 | 89 | 1 | 89 | 1 | 89 |
| `debit_card_specializing` | 5 | 21 | 1 | 21 | 2 | 24 |
| `european_football_2` | 7 | 199 | 1 | 204 | 3 | 216 |
| `financial` | 8 | 55 | 1 | 55 | 5 | 131 |
| `formula_1` | 13 | 94 | 1 | 94 | 6 | 163 |
| `student_club` | 8 | 48 | 1 | 48 | 3 | 73 |
| `superhero` | 10 | 31 | 1 | 35 | 3 | 59 |
| `thrombosis_prediction` | 3 | 64 | 1 | 64 | 2 | 71 |
| `toxicology` | 4 | 11 | 1 | 14 | 1 | 14 |
| **Total** | **61** | **612** | **9** | **624** | **26** | **840** |

---

## By normal form

### 3NF

| Database | Tables | Total cols |
|----------|-------:|-----------:|
| `california_schools` | 3 | 89 |
| `debit_card_specializing` | 5 | 21 |
| `european_football_2` | 7 | 199 |
| `financial` | 8 | 55 |
| `formula_1` | 13 | 94 |
| `student_club` | 8 | 48 |
| `superhero` | 10 | 31 |
| `thrombosis_prediction` | 3 | 64 |
| `toxicology` | 4 | 11 |

### 1NF

| Database | Tables | Total cols |
|----------|-------:|-----------:|
| `california_schools` | 1 | 89 |
| `debit_card_specializing` | 1 | 21 |
| `european_football_2` | 1 | 204 |
| `financial` | 1 | 55 |
| `formula_1` | 1 | 94 |
| `student_club` | 1 | 48 |
| `superhero` | 1 | 35 |
| `thrombosis_prediction` | 1 | 64 |
| `toxicology` | 1 | 14 |

### 2NF

| Database | Tables | Total cols |
|----------|-------:|-----------:|
| `california_schools` | 1 | 89 |
| `debit_card_specializing` | 2 | 24 |
| `european_football_2` | 3 | 216 |
| `financial` | 5 | 131 |
| `formula_1` | 6 | 163 |
| `student_club` | 3 | 73 |
| `superhero` | 3 | 59 |
| `thrombosis_prediction` | 2 | 71 |
| `toxicology` | 1 | 14 |

---

Regenerate: `python3 analysis/count_schema_sizes.py`
