# Qwen 2.5 Coder 14B (local) · L1·S2 wrong-answer sample (n=50)

**Source:** `results/qwen2.5-coder-14b-local__L1S2.csv` · **Accuracy:** 82/397 (20.7%) · **Population:** 315 failures / 397 questions · **Sample:** seed=42, n=50

**Setup:** L1 = single wide table `one_nf_0`; S2 = abbreviated column names (`table__abbrev` in prompt). Gold SQL on 3NF SQLite; predicted SQL on `{db_id}__1nf.sqlite`. Multiset execution comparison (`evaluator.py`); S2 display names mapped at eval time via `build_l1_col_rename_map`.

## Category definitions


| Code    | Label                             | Meaning                                                                                                                              |
| ------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **(a)** | Genuine model error               | Wrong metric, filter, column, `HAVING`, missing `/12`, `MAX` vs `SUM`, etc.                                                          |
| **(b)** | Partial (missing DISTINCT)        | 1NF translation largely faithful; automated DISTINCT repair **or** clear `COUNT`/scan fan-out without DISTINCT would align with gold |
| **(c)** | Unrecoverable evaluation artefact | SQL executes but multiset ≠ gold; execution errors; or fan-out needs dedup **subquery** (SUM/AVG), not keyword DISTINCT alone        |


## Summary (sample)


| Category                            | Count | % of sample |
| ----------------------------------- | ----- | ----------- |
| **(a)** Genuine model error         | 24    | 48.0%       |
| **(b)** Partial (DISTINCT missing)  | 1     | 2.0%        |
| **(c)** Unrecoverable eval artefact | 25    | 50.0%       |
| **Total**                           | 50    | 100.0%      |


**Outcomes in sample:** `wrong_answer` 37, `error` 13

### Fine-grained failure types (sample)


| Failure type                               | Count | %     |
| ------------------------------------------ | ----- | ----- |
| logic: wrong filters/columns/order         | 14    | 28.0% |
| logic: wrong aggregate/metric              | 9     | 18.0% |
| logic: COUNT DISTINCT but wrong key/filter | 6     | 12.0% |
| exec: wrong/hallucinated prefixed column   | 5     | 10.0% |
| exec: bare column (no table__ prefix)      | 4     | 8.0%  |
| 1NF asymmetry: wide scan no dedup          | 4     | 8.0%  |
| exec: column used as table name            | 3     | 6.0%  |
| 1NF asymmetry: SUM fan-out                 | 2     | 4.0%  |
| exec: 3NF table on 1NF db                  | 1     | 2.0%  |
| logic: missing DISTINCT (repairable)       | 1     | 2.0%  |
| logic: missing HAVING/subquery             | 1     | 2.0%  |


### Full failure population (n=315, same classifier)


| Category                            | Count | %      |
| ----------------------------------- | ----- | ------ |
| **(a)** Genuine model error         | 176   | 55.9%  |
| **(b)** Partial (DISTINCT missing)  | 6     | 1.9%   |
| **(c)** Unrecoverable eval artefact | 133   | 42.2%  |
| **Total**                           | 315   | 100.0% |


### Fine-grained failure types (full population)


| Failure type                               | Count | %     |
| ------------------------------------------ | ----- | ----- |
| logic: wrong filters/columns/order         | 127   | 40.3% |
| logic: wrong aggregate/metric              | 47    | 14.9% |
| logic: COUNT DISTINCT but wrong key/filter | 33    | 10.5% |
| exec: bare column (no table__ prefix)      | 32    | 10.2% |
| exec: wrong/hallucinated prefixed column   | 23    | 7.3%  |
| exec: column used as table name            | 15    | 4.8%  |
| 1NF asymmetry: wide scan no dedup          | 12    | 3.8%  |
| logic: missing /12 scaling                 | 8     | 2.5%  |
| logic: missing DISTINCT (repairable)       | 6     | 1.9%  |
| 1NF asymmetry: SUM fan-out                 | 5     | 1.6%  |
| exec: 3NF table on 1NF db                  | 5     | 1.6%  |
| logic: missing HAVING/subquery             | 2     | 0.6%  |


### S2 execution-error patterns (full population, n=75)

At L1·S2 the prompt shows abbreviated `table__abbrev` names; the 1NF SQLite file stores S3-style physical names. The evaluator renames display → physical, but only when the model uses the **exact** prefixed name from the schema.


| Pattern                                  | Count | % of exec errors |
| ---------------------------------------- | ----- | ---------------- |
| exec: bare column (no table__ prefix)    | 32    | 42.7%            |
| exec: wrong/hallucinated prefixed column | 23    | 30.7%            |
| exec: column used as table name          | 15    | 20.0%            |
| exec: 3NF table on 1NF db                | 5     | 6.7%             |


*Sample seed=42. Classification reuses DISTINCT repair + SQL-shape rules from `analysis/classify_l1s3_gemini_sample.py` (`classify_row`). Regenerate: `python analysis/classify_l1s2_qwen_sample.py`.*

---

## Sampled failures

### 1. Q1149 (thrombosis_prediction, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['COUNT']

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN inpatient_count > outpatient_count THEN 'In-patient'
        ELSE 'Out-patient'
    END AS majority_type,
    ABS(inpatient_count - outpatient_count) * 100.0 / (inpatient_count + outpatient_count) AS deviation_percentage
FROM (
    SELECT 
        COUNT(DISTINCT CASE WHEN Patient__admission = 'In-patient' THEN Patient__ID END) AS inpatient_count,
        COUNT(DISTINCT CASE WHEN Patient__admission = 'Out-patient' THEN Patient__ID END) AS outpatient_count
    FROM one_nf_0
    WHERE Patient__sex = 'Male'
) AS counts;
```

### 2. Q1493 (debit_card_specializing, simple, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such column: consump` · **Fine type:** exec: bare column (no table__ prefix)

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: consump

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN consump > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT cust_id) 
FROM 
    one_nf_0 
WHERE 
    date BETWEEN '2012-02-01' AND '2012-02-29';
```

### 3. Q1139 (european_football_2, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT 
    Match__home_goals, 
    Match__away_goals
FROM 
    one_nf_0
WHERE 
    Match__date = '2008-09-24' 
    AND League__name = 'Belgian Jupiler League';
```

### 4. Q1098 (european_football_2, moderate, retrieval) — **(c) (**1nf denormalised join error)

**Outcome:** `wrong_answer` · **Fine type:** 1NF asymmetry: wide scan no dedup 

**Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT t2.chanceCreationPassing, t2.chanceCreationPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Ajax' ORDER BY t2.chanceCreationPassing DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(Team_Attributes__cc_pass), Team_Attributes__cc_pass_cls
FROM one_nf_0
WHERE team_home__team_nm = 'Ajax' OR team_away__team_nm = 'Ajax';
```

### 5. Q1040 (european_football_2, moderate, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such table: Player_Attributes__id` · **Fine type:** exec: column used as table name

**Category (c):** Execution failure (unrecoverable at evaluation): no such table: Player_Attributes__id

**Gold SQL:**

```sql
SELECT p.player_name
FROM Player            AS p
JOIN  Player_Attributes AS pa
      ON p.player_api_id = pa.player_api_id
WHERE p.height > 180
GROUP BY p.player_api_id, p.player_name
ORDER BY AVG(pa.heading_accuracy) DESC
LIMIT 10;
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player__plr_nm
FROM Player_Attributes__id
WHERE Player__ht > 180
ORDER BY AVG(Player_Attributes__head_acc) DESC
LIMIT 10;
```

### 6. Q1185 (thrombosis_prediction, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['COUNT', 'MAX', 'MIN']

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(Laboratory__t_cho) - MIN(Laboratory__t_cho)) / COUNT(DISTINCT Laboratory__Date) AS decrease_rate
FROM 
    one_nf_0
WHERE 
    Patient__bday = '1959-02-18' 
    AND Laboratory__Date BETWEEN '1981-11-01' AND '1981-12-31';
```

### 7. Q1411 (student_club, simple, retrieval) — **(a) (wrong gold sql)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT expense__exp_desc 
FROM one_nf_0 
WHERE member__fname = 'Sacha' AND member__lname = 'Harrison';
```

### 8. Q47 (california_schools, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['COUNT']; predicted uses ['AVG', 'COUNT']; missing filter 'DOC'

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(monthly_count) 
FROM (
    SELECT DISTINCT strftime('%Y-%m', schools__open_dt) AS month, COUNT(DISTINCT schools__cds_cd) AS monthly_count
    FROM one_nf_0
    WHERE schools__County = 'Alameda' AND schools__District = 'Elementary School District' AND strftime('%Y', schools__open_dt) = '1980'
    GROUP BY month
)
```

### 9. Q1390 (student_club, moderate, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such column: cost` · **Fine type:** exec: bare column (no table__ prefix)

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: cost

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT SUM(cost) 
     FROM one_nf_0 
     WHERE evt_nm = 'Yearly Kickoff') * 100.0 / 
    (SELECT SUM(cost) 
     FROM one_nf_0) AS percentage
```

### 10. Q137 (financial, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** logic: COUNT DISTINCT but wrong key/filter

**Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT account__acct_id) 
FROM one_nf_0 
WHERE district__dist_id = 1;
```

### 11. Q790 (superhero, moderate, retrieval) — **(c)**

**Outcome:** `error` · **Error:** `no such column: wt_kg` · **Fine type:** exec: bare column (no table__ prefix)

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: wt_kg

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT wt_kg FROM one_nf_0 WHERE superhero__hero_nm = 'Emil Blonsky') -
    (SELECT wt_kg FROM one_nf_0 WHERE superhero__hero_nm = 'Charles Chandler') AS weight_difference;
```

### 12. Q1506 (debit_card_specializing, moderate, retrieval) — **(a) (value locating error)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT products__descr 
FROM one_nf_0 
WHERE gasstations__ctry = 'Czech Republic';
```

### 13. Q1505 (debit_card_specializing, simple, aggregate) — **(c) (value locating error)**

**Outcome:** `wrong_answer` · **Fine type:** logic: COUNT DISTINCT but wrong key/filter

**Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT customers__cust_id)
FROM one_nf_0
WHERE customers__curr = 'euro' AND yearmonth__consump > 1000;
```

### 14. Q1399 (student_club, moderate, retrieval) — **(c)**

**Outcome:** `error` · **Error:** `no such table: attendance__evt_id` · **Fine type:** exec: column used as table name

**Category (c):** Execution failure (unrecoverable at evaluation): no such table: attendance__evt_id

**Gold SQL:**

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean' AND T3.event_name = 'Women''s Soccer'
```

**Predicted SQL:**

```sql
SELECT DISTINCT CASE WHEN T1.event_nm = 'Women''s Soccer' THEN 'YES' ELSE 'NO' END AS attended
FROM one_nf_0 AS T1
JOIN attendance__evt_id AS T2 ON T1.event__evt_id = T2.evt_id
JOIN attendance__mbr_id AS T3 ON T2.mbr_id = T3.mbr_id
WHERE T3.fname = 'Maya' AND T3.lname = 'Mclean';
```

### 15. Q1036 (european_football_2, challenging, aggregate) — **(a) (join error)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['COUNT', 'SUM']; predicted uses ['AVG']

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT DISTINCT team_home__team_nm
FROM one_nf_0
WHERE Team_Attributes__date = '2012' AND Team_Attributes__bu_pass > (
    SELECT AVG(Team_Attributes__bu_pass)
    FROM one_nf_0
    WHERE Team_Attributes__date = '2012'
);
```

### 16. Q1080 (european_football_2, moderate, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such table: Player_Attributes` · **Fine type:** exec: 3NF table on 1NF db

**Category (c):** Execution failure (unrecoverable at evaluation): no such table: Player_Attributes

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Player_Attributes__id) 
FROM Player_Attributes 
WHERE Player_Attributes__pref_foot = 'left' AND Player_Attributes__atk_wr = 'right';
```

### 17. Q281 (toxicology, challenging, retrieval) — **(c)**

**Outcome:** `error` · **Error:** `no such column: atom_4__elem` · **Fine type:** exec: wrong/hallucinated prefixed column

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: atom_4__elem

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_4__elem
FROM one_nf_0
WHERE molecule__lbl = 'carcinogenic'
ORDER BY connected__atm_id
LIMIT 3, 1;
```

### 18. Q168 (financial, moderate, aggregate) — **(b)**

**Outcome:** `wrong_answer` · **Fine type:** logic: missing DISTINCT (repairable)

**Category (b):** COUNT without DISTINCT on `one_nf_0`; gold JOIN avoids join fan-out on 3NF

**Gold SQL:**

```sql
SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN client__gender = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(client__client_id) AS percentage_women
FROM 
    one_nf_0
WHERE 
    district__avg_sal > 10000;
```

### 19. Q1498 (debit_card_specializing, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['MAX']

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(yearmonth__consump)
FROM one_nf_0
WHERE strftime('%Y', yearmonth__date) = '2012';
```

### 20. Q83 (california_schools, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** logic: COUNT DISTINCT but wrong key/filter

**Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT DISTINCT schools__City, COUNT(DISTINCT schools__cds_cd) AS school_count
FROM one_nf_0
WHERE frpm__low_grd = 'K' AND frpm__high_grd = '8' AND frpm__edu_opt_type = 'Multiple Provision Types'
GROUP BY schools__City;
```

### 21. Q1275 (thrombosis_prediction, moderate, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such column: Examination__centromea` · **Fine type:** exec: wrong/hallucinated prefixed column

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: Examination__centromea

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__centromea = 'normal' AND Examination__ssb = 'normal' AND Patient__sex = 'male';
```

### 22. Q782 (superhero, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT DISTINCT superhero__hero_nm 
FROM one_nf_0 
WHERE colour_eye__color = 'black' AND colour_hair__color = 'black';
```

### 23. Q1037 (european_football_2, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['COUNT']; predicted uses ['COUNT', 'SUM']

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN Player_Attributes__pref_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Player__id) 
FROM one_nf_0 
WHERE strftime('%Y', Player__bday) BETWEEN '1987' AND '1992';
```

### 24. Q208 (toxicology, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** logic: COUNT DISTINCT but wrong key/filter

**Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT molecule__lbl
FROM one_nf_0
WHERE atom_1__elem = 'H' OR atom_2__elem = 'H'
GROUP BY molecule__lbl
ORDER BY COUNT(DISTINCT molecule__mol_id) DESC
LIMIT 1;
```

### 25. Q136 (financial, moderate, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** logic: COUNT DISTINCT but wrong key/filter

**Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT loan__loan_id)
FROM one_nf_0
WHERE loan__amount >= 250000
  AND loan__date BETWEEN '1995-01-01' AND '1997-12-31'
  AND account__freq = 'monthly'
  AND loan__status = 'approved';
```

### 26. Q1144 (european_football_2, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player_Attributes__finish, Player_Attributes__curve
FROM one_nf_0
WHERE Player__wt = (SELECT MAX(Player__wt) FROM one_nf_0);
```

### 27. Q1476 (debit_card_specializing, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** 1NF asymmetry: SUM fan-out

**Category (c):** SUM on fan-out 1NF rows: requires deduplicating subquery on fact keys; simple DISTINCT in SUM is insufficient

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN customers__curr = 'CZK' THEN yearmonth__consump ELSE 0 END) -
    SUM(CASE WHEN customers__curr = 'EUR' THEN yearmonth__consump ELSE 0 END) AS consumption_difference
FROM 
    one_nf_0
WHERE 
    strftime('%Y', yearmonth__date) = '2012';
```

### 28. Q1220 (thrombosis_prediction, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__ID, Patient__sex, Patient__bday
FROM one_nf_0
WHERE Laboratory__un = 40;
```

### 29. Q948 (formula_1, simple, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such table: constructors__name` · **Fine type:** exec: column used as table name

**Category (c):** Execution failure (unrecoverable at evaluation): no such table: constructors__name

**Gold SQL:**

```sql
SELECT MAX(T1.points) FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T2.nationality = 'British'
```

**Predicted SQL:**

```sql
SELECT MAX(points) 
FROM (
    SELECT DISTINCT constructorResults__ctor_id, points 
    FROM one_nf_0 
    JOIN constructors__name ON one_nf_0.results__ctor_id = constructors__name.ctor_id 
    WHERE constructors__name.nation = 'British'
)
```

### 30. Q1208 (thrombosis_prediction, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__ID
FROM one_nf_0
WHERE Patient__sex = 'Male' AND Laboratory__gpt > 40;
```

### 31. Q1035 (european_football_2, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT Team_Attributes__fifa_team_id
FROM one_nf_0
WHERE Team_Attributes__bu_spd BETWEEN 50 AND 60;
```

### 32. Q940 (formula_1, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: missing HAVING/subquery

**Category (a):** Gold uses HAVING / per-entity subquery; prediction omits or simplifies it

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT results__drv_id) 
FROM one_nf_0 
WHERE races__year = 2008 AND races__name = 'Chinese Grand Prix' AND results__position IS NOT NULL;
```

### 33. Q1014 (formula_1, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** 1NF asymmetry: wide scan no dedup

**Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(lapTimes__time) AS min_lap_time
FROM one_nf_0
WHERE circuits__country = 'Italy';
```

### 34. Q1404 (student_club, moderate, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such column: budget__aprvd` · **Fine type:** exec: wrong/hallucinated prefixed column

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: budget__aprvd

**Gold SQL:**

```sql
SELECT
    T2.`category`,
    SUM(T3.`cost`) AS total_approved_value
FROM `event`  AS T1
JOIN `budget` AS T2 ON T1.`event_id`  = T2.`link_to_event`
JOIN `expense` AS T3 ON T2.`budget_id` = T3.`link_to_budget`
WHERE T1.`event_name` = 'October Meeting'
  AND T3.`approved` = 'true'  
GROUP BY T2.`category`;
```

**Predicted SQL:**

```sql
SELECT budget__cat, SUM(budget__amt) 
FROM one_nf_0 
WHERE event__evt_nm = 'October Meeting' AND budget__aprvd = 'Yes' 
GROUP BY budget__cat;
```

### 35. Q964 (formula_1, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__code 
FROM one_nf_0 
WHERE drivers__nation = 'American';
```

### 36. Q951 (formula_1, simple, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such column: constructorsResults__points` · **Fine type:** exec: wrong/hallucinated prefixed column

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: constructorsResults__points

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT constructors__ctor_id)
FROM one_nf_0
WHERE constructors__nation = 'Japan'
AND constructorsResults__points = 0
GROUP BY constructors__ctor_id
HAVING COUNT(DISTINCT results__race_id) = 2;
```

### 37. Q169 (financial, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** 1NF asymmetry: SUM fan-out

**Category (c):** SUM on fan-out 1NF rows: requires deduplicating subquery on fact keys; simple DISTINCT in SUM is insufficient

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN loan__date BETWEEN '1997-01-01' AND '1997-12-31' THEN loan__amount ELSE 0 END) -
     SUM(CASE WHEN loan__date BETWEEN '1996-01-01' AND '1996-12-31' THEN loan__amount ELSE 0 END)) /
     SUM(CASE WHEN loan__date BETWEEN '1996-01-01' AND '1996-12-31' THEN loan__amount ELSE 0 END) AS growth_rate
FROM 
    one_nf_0
WHERE 
    client__gender = 'M';
```

### 38. Q1124 (european_football_2, moderate, retrieval) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** 1NF asymmetry: wide scan no dedup

**Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player__plr_nm
FROM one_nf_0
WHERE Player_Attributes__atk_wr > (
    SELECT AVG(Player_Attributes__atk_wr)
    FROM one_nf_0
    WHERE Player_Attributes__atk_wr > 0
);
```

### 39. Q1528 (debit_card_specializing, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['COUNT', 'SUM']

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN customers__seg = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT customers__cust_id)) AS percentage_premium
FROM 
    one_nf_0
WHERE 
    gasstations__ctry = 'SVK';
```

### 40. Q226 (toxicology, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['COUNT']; predicted uses ['COUNT', 'SUM']

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond__bnd_type = 'DOUBLE' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT bond__bnd_id) 
FROM one_nf_0 
WHERE molecule__lbl = 'TR008'
```

### 41. Q36 (california_schools, challenging, retrieval) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** 1NF asymmetry: wide scan no dedup

**Category (c):** Gold uses JOIN on 3NF; prediction aggregates one_nf_0 without equivalent deduplication — evaluation asymmetry not fixed by tried DISTINCT patches

**Gold SQL:**

```sql
SELECT s.AdmFName1,
       s.AdmLName1,
       s.AdmFName2,
       s.AdmLName2,
       s.AdmFName3,
       s.AdmLName3
FROM satscores t
JOIN schools  s ON t.cds = s.CDSCode
WHERE t.rtype = 'S'    
ORDER BY t.NumGE1500 DESC
LIMIT 1;
```

**Predicted SQL:**

```sql
SELECT DISTINCT 
    schools__adm_fname1, 
    schools__adm_lname1, 
    schools__adm_fname2, 
    schools__adm_lname2, 
    schools__adm_fname3, 
    schools__adm_lname3
FROM 
    one_nf_0
WHERE 
    satscores__num_ge_1500 = (
        SELECT MAX(satscores__num_ge_1500) 
        FROM one_nf_0
    )
```

### 42. Q1162 (thrombosis_prediction, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Patient__sex = 'Female'
  AND strftime('%Y', Patient__first_rec_dt) = '1997'
  AND Patient__admission = 'Outpatient Clinic';
```

### 43. Q1011 (formula_1, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__fname, drivers__lname
FROM one_nf_0
ORDER BY lapTimes__time ASC
LIMIT 20;
```

### 44. Q1380 (student_club, simple, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such column: cost` · **Fine type:** exec: bare column (no table__ prefix)

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: cost

**Gold SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) 
FROM one_nf_0 
WHERE exp_desc LIKE '%food%'
```

### 45. Q62 (california_schools, challenging, aggregate) — **(c)**

**Outcome:** `wrong_answer` · **Fine type:** logic: COUNT DISTINCT but wrong key/filter

**Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT schools__cds_cd) 
FROM one_nf_0 
WHERE schools__County = 'Los Angeles' 
AND frpm__is_charter = 'N' 
AND frpm__pct_free_k12 < 0.18;
```

### 46. Q866 (formula_1, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__fname, drivers__lname, drivers__url
FROM one_nf_0
WHERE lapTimes__race_id = 161 AND lapTimes__time = '0:01:27';
```

### 47. Q972 (formula_1, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__drv_id, drivers__code
FROM one_nf_0
WHERE drivers__dob LIKE '1971%' AND results__fast_lap = 1;
```

### 48. Q98 (financial, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong filters/columns/order

**Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT account__acct_id
FROM one_nf_0
WHERE loan__date LIKE '1997%'
AND account__freq = 'weekly'
ORDER BY loan__amount ASC
LIMIT 1;
```

### 49. Q1265 (thrombosis_prediction, moderate, aggregate) — **(c)**

**Outcome:** `error` · **Error:** `no such column: Examination__rnp` · **Fine type:** exec: wrong/hallucinated prefixed column

**Category (c):** Execution failure (unrecoverable at evaluation): no such column: Examination__rnp

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM one_nf_0 
WHERE Examination__rnp = 'normal' AND Patient__admission = 'yes';
```

### 50. Q1359 (student_club, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Fine type:** logic: wrong aggregate/metric

**Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT budget__bgt_id)
FROM one_nf_0
WHERE event__evt_nm = 'Yearly Kickoff' AND budget__cat = 'Advertisement' AND budget__spent > (
    SELECT budget__spent
    FROM one_nf_0
    WHERE event__evt_nm = 'October Meeting' AND budget__cat = 'Advertisement'
);
```

