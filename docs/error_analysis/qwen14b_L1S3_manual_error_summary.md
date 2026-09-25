# Qwen2.5-Coder-14B - L1-S3 manual error taxonomy summary (n=60)

**Source sample:** `docs/error_analysis/qwen14b_L1S3_wrong_answer_sample60.md`
**Population:** 317 failures / 397 questions | **Annotated sample:** seed=42, n=60
**Annotation source:** inline labels and citations on each question header only (not `Outcome:` text).
**Default rule:** no citation beside question id -> **(a3) logic error**.

---

## Error taxonomy

| Code | Label | Meaning |
|------|--------|--------|
| **(a)** | Model generation error | Wrong table/column name, wrong filter, wrong literal, wrong logic, etc. |
| **(a1)** | Wrong table name | Hallucinated or incorrect table reference |
| **(a2)** | Wrong column name | Incorrect / un-prefixed column on `one_nf_0` |
| **(a3)** | Logic error | All other model-generation mistakes |
| **(b)** | Resolvable denorm. fan-out | Fixable by `DISTINCT` on the correct key column(s) |
| **(b1)** | Weak aggregation | `SELECT DISTINCT` suffices |
| **(b2)** | Strong aggregation | `DISTINCT` needed on key columns during filter/processing |
| **(c)** | Unrecoverable denorm. error | Fan-out or null propagation not fixable by SQL `DISTINCT` alone |

## Summary counts (n=60)

| Category | Count | % of sample |
|----------|------:|------------:|
| **(a1)** Wrong table name | 7 | 11.7% |
| **(a2)** Wrong column name | 16 | 26.7% |
| **(a3)** Logic error | 33 | 55.0% |
| **(b1)** Weak aggregation | 1 | 1.7% |
| **(b2)** Strong aggregation | 4 | 6.7% |
| **(c)** Fan-out (unrecoverable) | 5 | 8.3% |
| **(c)** Null propagation | 1 | 1.7% |
| **Compound** (dual-label questions) | 7 | 11.7% |
| **Total questions** | 60 | 100.0% |

*Subtype counts include compound questions where that tag applies: (a2) +3 from Q868, Q1422, Q1187; (a3) +4 from Q1476, Q1528, Q152, Q212; (b1) Q868; (b2) +2 from Q152, Q1422; (c) fan-out +3 from Q1476, Q1528, Q212; (c) null Q1187. Hence (a1)+(a2)+(a3) = 56 tag-(a) questions. Percentages sum above 100% because compound questions are counted in both a subtype row and the compound row.*

### Mutually exclusive assignment (n=60)

Each question counted once. Compound questions assigned by priority **b > c > a**:

| Compound QID | Labels | Assigned |
|--------------|--------|----------|
| Q152 | (b)/(a) | **(b2)** |
| Q868 | (b)/(a) | **(b1)** |
| Q1422 | (a)/(b) | **(b2)** |
| Q1476 | (c)/(a) | **(c)** fan-out |
| Q1528 | (c)/(a) | **(c)** fan-out |
| Q1187 | (a)/(c) | **(c)** null propagation |
| Q212 | (a)/(c) | **(c)** fan-out |

| Category | Count | % of sample |
|----------|------:|------------:|
| **(a1)** Wrong table name | 7 | 11.7% |
| **(a2)** Wrong column name | 13 | 21.7% |
| **(a3)** Logic error | 29 | 48.3% |
| **(b1)** Weak aggregation | 1 | 1.7% |
| **(b2)** Strong aggregation | 4 | 6.7% |
| **(c)** Fan-out (unrecoverable) | 5 | 8.3% |
| **(c)** Null propagation | 1 | 1.7% |
| **Total** | **60** | **100.0%** |

| Top-level | Count | % of sample |
|-----------|------:|------------:|
| **(a)** Model generation error | 49 | 81.7% |
| **(b)** Resolvable fan-out | 5 | 8.3% |
| **(c)** Unrecoverable denorm. error | 6 | 10.0% |
| **Total** | **60** | **100.0%** |

---

## (a) Model generation errors

### (a1) Wrong table name - 7 questions

| QID | Database | Citation |
|-----|----------|----------|
| Q1037 | european_football_2 | model generation error, wrong table name |
| Q1136 | european_football_2 | model generation error, wrong table name |
| Q981 | formula_1 | model generation error, wrong table name |
| Q1003 | formula_1 | model generation error, wrong table name |
| Q1361 | student_club | model generation error, wrong table name |
| Q1381 | student_club | wrong table name |
| Q717 | superhero | wrong table name |

### (a2) Wrong column name - 13 questions

| QID | Database | Citation |
|-----|----------|----------|
| Q1493 | debit_card_specializing | model error, generate wrong column name |
| Q1529 | debit_card_specializing | wrong column name used |
| Q1039 | european_football_2 | model generation error, wrong column name |
| Q1068 | european_football_2 | model generation error, wrong column name |
| Q95 | financial | model generation error, wrong column name |
| Q125 | financial | model generation error, wrong column name |
| Q149 | financial | model generation error, wrong column name |
| Q194 | financial | model generation error, wrong column name |
| Q1403 | student_club | wrong column name |
| Q1409 | student_club | wrong column name |
| Q791 | superhero | wrong column name |
| Q1265 | thrombosis_prediction | wrong column name |
| Q1275 | thrombosis_prediction | wrong column name |

### (a3) Logic error - 29 questions

#### With citation (9)

| QID | Database | Citation |
|-----|----------|----------|
| Q1505 | debit_card_specializing | correct logic, correct filter, wrong value used in filter due to no knowledge of the data, used 'euro' instead of 'eur' in customers__currency column |
| Q1506 | debit_card_specializing | model error, use wrong data value inside filter |
| Q1394 | student_club | model generation error, wrong filter applied |
| Q723 | superhero | wrong filter value, should be 'Blue' instead of 'blue' |
| Q724 | superhero | wrong filter value, should be 'Blue', 'Blond' instead of 'blue', 'blond' |
| Q782 | superhero | wrong filter value, should be 'Black' instead of 'black' |
| Q1164 | thrombosis_prediction | wrong filter logic, model generation error |
| Q1209 | thrombosis_prediction | wrong filter value |
| Q1229 | thrombosis_prediction | wrong filter value |

#### Without citation - default logic error (20)

| QID | Database | Difficulty | Type |
|-----|----------|------------|------|
| Q32 | california_schools | moderate | retrieval |
| Q41 | california_schools | simple | retrieval |
| Q48 | california_schools | moderate | aggregate |
| Q79 | california_schools | moderate | aggregate |
| Q1498 | debit_card_specializing | simple | aggregate |
| Q1078 | european_football_2 | simple | retrieval |
| Q1092 | european_football_2 | simple | aggregate |
| Q1105 | european_football_2 | moderate | retrieval |
| Q1147 | european_football_2 | simple | aggregate |
| Q118 | financial | moderate | aggregate |
| Q846 | formula_1 | moderate | retrieval |
| Q865 | formula_1 | moderate | retrieval |
| Q950 | formula_1 | simple | retrieval |
| Q954 | formula_1 | challenging | aggregate |
| Q967 | formula_1 | simple | aggregate |
| Q990 | formula_1 | challenging | retrieval |
| Q1225 | thrombosis_prediction | moderate | aggregate |
| Q206 | toxicology | challenging | retrieval |
| Q219 | toxicology | challenging | aggregate |
| Q268 | toxicology | challenging | retrieval |

---

## (b) Resolvable denormalisation fan-out

### (b2) Strong aggregation - 2 questions

| QID | Database | Citation |
|-----|----------|----------|
| Q959 | formula_1 | applied distinct in the wrong column, strong |
| Q1411 | student_club | apply distinct on wrong column, strong |

---

## (c) Unrecoverable denormalisation errors

### Fan-out - 2 questions

| QID | Database | Citation |
|-----|----------|----------|
| Q1036 | european_football_2 | fan out problem due to normalisation, have different number of teams in 1nf database even after using distinct |
| Q1150 | thrombosis_prediction | fan out problem due to denormalisation, cannot use distinct to resolve |

---

## Compound labels - 7 questions (listed separately)

Questions tagged with **two error types** in the header. Both types are recorded here; they are excluded from the single-type sections above.

| QID | Database | Labels | Citation |
|-----|----------|--------|----------|
| Q1476 | debit_card_specializing | (c)/(a) | both model geenration error and fan-out error. (a) wrong filter applies to yearmoth_date due to no knowledge of the actual data type, (c) unrecoverable fan out problem from denormalisation |
| Q1528 | debit_card_specializing | (c)/(a) | i would classify as fan out error, denormalise cause fan out problem in customers_customer_id column, the model try to use distinct to resolve the error, but origin table contains duplicate customer ids, therefore, using distinct is incorrect as well, also wrong segment column used, should be gasstations segment, not customers segment |
| Q152 | financial | (b)/(a) | fan out problem, need to apply distinct at key column, human able to get correct answer following the correct logic, strong, also suffer from model generation error, chose incorrect filter |
| Q868 | formula_1 | (b)/(a) | missing distinct, wrong column selected as well, weak |
| Q1422 | student_club | (a)/(b) | wrong column selected, apply distinct on wrong column, strong |
| Q1187 | thrombosis_prediction | (a)/(c) | both wrong column applied error, and null propogation error due to denormalisation |
| Q212 | toxicology | (a)/(c) | both model generation error - wrong logic, and unrecoverable fan out error from denomralisation |

---

*Generated from header citations in `qwen14b_L1S3_wrong_answer_sample60.md` only.*
