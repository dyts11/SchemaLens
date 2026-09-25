# Qwen2.5-Coder-14B · L2·S3 wrong-answer sample (n=60)

**Source:** `results/full/qwen2.5-coder-14b-local__L2S3.csv` · **Population:** 319 failures / 397 questions · **Sample:** the same 60 questions as the L1·S3 sample (seed=42)

**Setup:** Gold SQL on 3NF SQLite; predicted SQL on `{db_id}__2nf.sqlite` (per-cluster `two_nf_*` wide tables). Multiset execution comparison (`evaluator.py`).

**Method:** every failure re-executed against the 2NF database; ambiguous cases verified by writing a corrected query and checking it against the gold result (noted in the explanations).

## Category definitions

| Category | Meaning |
| --- | --- |
| **wrong column name** | Predicted SQL references a column identifier that does not exist in the 2NF schema (execution error). |
| **wrong table name** | Predicted SQL references a table identifier that does not exist in the 2NF schema (execution error). |
| **join plan error** | All identifiers exist, but the join structure is wrong — e.g. redundantly joining clusters that already embed the same columns, causing ambiguity or wrong grain. |
| **other logic error** | All identifiers exist; the semantics are wrong — wrong filter value/case, wrong threshold, wrong existing column/table choice, wrong aggregate, wrong output shape, misapplied DISTINCT. |
| **weak duplication / recoverable artefact** | Faithful logic defeated by a denormalisation artefact that one mechanical guard (DISTINCT on a key column, or IS NOT NULL on FOJ padding) fully repairs. |
| **unrecoverable (denormalisation)** | Fan-out contaminates SUM/AVG/COUNT arithmetic; recovery requires restructuring around a dedup subquery at the original grain — beyond keyword-level repair. |

## Summary (sample)

| Primary category | Count | % of sample |
| --- | --- | --- |
| other logic error | 34 | 56.7% |
| wrong column name | 9 | 15.0% |
| wrong table name | 7 | 11.7% |
| join plan error | 2 | 3.3% |
| unrecoverable (denormalisation) | 2 | 3.3% |
| weak duplication / recoverable artefact | 1 | 1.7% |
| correct | 5 | 8.3% |
| **Total** | 60 | 100.0% |

*Compound cases (e.g. unrecoverable + logic) are tallied under their primary category. Key L1→L2 shifts: the five questions now correct were L1 failures; several L1 fan-out artefacts (Q1476, Q1493) became plain logic errors because the 2NF cluster is at the fact's native grain; several L1 in-wide-table naming errors became cross-cluster wrong-table references (Q1036, Q868, Q152, Q981).*

---

## Sampled failures

### 1. Q32 (california_schools, moderate, retrieval) — **wrong column name**

**Outcome:** `error` · References bare `percent_eligible_free_or_reduced_price_meal_k12` / `free_or_reduced_price_meal_count_k12` which do not exist (real columns carry the `frpm__` prefix), so the query fails before its other issues (extra School column, wrong metric) matter.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT 
    schools__School, 
    percent_eligible_free_or_reduced_price_meal_k12
FROM 
    two_nf_schools
WHERE 
    schools__school_ownership_code = 66
ORDER BY 
    free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### 2. Q41 (california_schools, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters `schools__Virtual = 'Yes'` but the column's domain is F/N/P, and the max-per-county + LIMIT 5 shape does not implement gold's top-5-rank-per-county logic, so the result is empty.

**Gold SQL:**

```sql
WITH ranked AS (
  SELECT s.`School`,
         s.`Virtual`,
         sc.`cname`,
         RANK() OVER (PARTITION BY sc.`cname` ORDER BY sc.`AvgScrRead` DESC) AS rnk
  FROM `schools` s
  JOIN `satscores` sc ON s.`CDSCode` = sc.`cds`
  WHERE sc.`AvgScrRead` IS NOT NULL AND rtype = 'S'
)
SELECT DISTINCT `School`
FROM ranked
WHERE `Virtual` = 'F'
  AND rnk <= 5;
```

**Predicted SQL:**

```sql
SELECT DISTINCT schools__School
FROM two_nf_schools
WHERE schools__Virtual = 'Yes'
AND (schools__County, satscores__average_score_reading) IN (
    SELECT schools__County, MAX(satscores__average_score_reading)
    FROM two_nf_schools
    WHERE schools__Virtual = 'Yes'
    GROUP BY schools__County
    ORDER BY MAX(satscores__average_score_reading) DESC
    LIMIT 5
)
ORDER BY satscores__average_score_reading DESC;
```

### 3. Q48 (california_schools, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Filters on invented status values 'Merged Unified/Elementary School District' (StatusType domain is Active/Closed/Merged/Pending; gold splits on DOC 54 vs 52), so both counts are zero and the ratio is NULL.

**Gold SQL:**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN schools__status_type = 'Merged Unified School District' THEN schools__county_district_school_code END) AS REAL) /
       COUNT(DISTINCT CASE WHEN schools__status_type = 'Merged Elementary School District' THEN schools__county_district_school_code END) AS ratio
FROM two_nf_schools
WHERE schools__County = 'Orange';
```

### 4. Q79 (california_schools, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses `schools__Charter = 'Yes'` (nonexistent value, and gold filters `Virtual = 'F'` not Charter), so no rows match; all identifiers exist so this is a semantic choice error.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT schools__County, COUNT(DISTINCT schools__national_center_for_education_statistics_school_id) AS school_count
FROM two_nf_schools
WHERE schools__County IN ('San Diego', 'Santa Barbara') AND schools__Charter = 'Yes'
GROUP BY schools__County
ORDER BY school_count DESC
LIMIT 1;
```

### 5. Q1476 (debit_card_specializing, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Applies `strftime('%Y', yearmonth__date)` to text stored as 'YYYYMM' (e.g. '201112') so the filter matches nothing; with `SUBSTR(...,1,4)='2012'` the same query returns gold exactly (402524570.17) — the L1 fan-out is gone because `two_nf_yearmonth` is at yearmonth grain.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN customers__currency = 'CZK' THEN yearmonth__consumption ELSE 0 END) -
    SUM(CASE WHEN customers__currency = 'EUR' THEN yearmonth__consumption ELSE 0 END) AS consumption_difference
FROM 
    two_nf_yearmonth
WHERE 
    strftime('%Y', yearmonth__date) = '2012';
```

### 6. Q1493 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses date literal `LIKE '2012-02-%'` against 'YYYYMM'-format text ('201202'), so nothing matches; with the correct literal the query reproduces gold exactly (66.62).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN yearmonth__consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT yearmonth__customer_id) 
FROM two_nf_yearmonth 
WHERE yearmonth__date LIKE '2012-02-%';
```

### 7. Q1498 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Computes MAX of single-row consumption instead of gold's SUM per month with ORDER BY/LIMIT, and its strftime filter also fails on the 'YYYYMM' text format — an aggregate-shape error.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(yearmonth__consumption)
FROM two_nf_yearmonth
WHERE strftime('%Y', yearmonth__date) = '2012';
```

### 8. Q1505 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Correct structure but filters `customers__currency = 'euro'` while the stored value is 'EUR', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT yearmonth__customer_id)
FROM two_nf_yearmonth
WHERE customers__currency = 'euro' AND yearmonth__consumption > 1000;
```

### 9. Q1506 (debit_card_specializing, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Correct structure but filters `gasstations__country = 'Czech Republic'` while the stored value is 'CZE', so the result is empty.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT products__description 
FROM two_nf_transactions 
WHERE gasstations__country = 'Czech Republic';
```

### 10. Q1528 (debit_card_specializing, simple, aggregate) — **unrecoverable (denormalisation) + other logic error**

**Outcome:** `wrong_answer` · Even after fixing the model's wrong entity column (`customers__segment` for `gasstations__segment`) and lowercase 'premium', transaction-grain rows in `two_nf_transactions` fan out stations (37.93 vs gold 35.68); recovering gold requires a station-grain dedup subquery, not keyword DISTINCT.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN customers__segment = 'premium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customers__customer_id) AS percentage_premium
FROM 
    two_nf_transactions
WHERE 
    gasstations__country = 'SVK';
```

### 11. Q1529 (debit_card_specializing, moderate, aggregate) — **wrong column name**

**Outcome:** `error` · References bare `amount`/`date` which do not exist (`transactions_1k__amount`/`transactions_1k__date`), so execution fails.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT 
    SUM(amount) AS total_spent,
    SUM(CASE WHEN date LIKE '2012-08%' THEN amount ELSE 0 END) AS august_2012_spent
FROM 
    two_nf_transactions
WHERE 
    transactions_1k__customer_id = 38508;
```

### 12. Q1036 (european_football_2, challenging, aggregate) — **wrong table name**

**Outcome:** `error` · Joins a bare `Team_Attributes` table that does not exist at L2 (its columns live inside `two_nf_team`), so execution fails.

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT DISTINCT team_home__team_long_name
FROM two_nf_match
JOIN two_nf_team ON two_nf_match.Match__home_team_api_id = two_nf_team.Team__team_api_id
JOIN Team_Attributes ON two_nf_team.Team__team_api_id = Team_Attributes.team_api_id
WHERE Team_Attributes.date LIKE '2012%'
AND Team_Attributes.buildup_play_passing > (
    SELECT AVG(buildup_play_passing)
    FROM Team_Attributes
    WHERE date LIKE '2012%'
);
```

### 13. Q1037 (european_football_2, challenging, aggregate) — **wrong column name**

**Outcome:** `error` · References bare `preferred_foot`/`player_api_id`/`birthday` which only exist with `Player_Attributes__`/`Player__` prefixes, so execution fails.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT player_api_id) 
FROM two_nf_player 
WHERE strftime('%Y', birthday) BETWEEN '1987' AND '1992';
```

### 14. Q1039 (european_football_2, simple, aggregate) — **wrong column name**

**Outcome:** `error` · References bare `long_shots` which only exists as `Player_Attributes__long_shots`, so execution fails.

**Gold SQL:**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL:**

```sql
SELECT AVG(long_shots)
FROM (
    SELECT DISTINCT Player_Attributes__id, long_shots
    FROM two_nf_player
    WHERE Player__player_name = 'Ahmed Samir Farag'
)
```

### 15. Q1068 (european_football_2, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · The self-imposed `SELECT DISTINCT (Player__id, rating)` subquery collapses legitimate duplicate ratings across snapshot dates (68.01 vs gold 68.95); a plain AVG over `two_nf_player` with gold's year filter returns gold exactly — the dedup habit itself is the error.

**Gold SQL:**

```sql
SELECT AVG(t2.overall_rating) AS avg_rating
FROM `Player` AS t1
JOIN `Player_Attributes` AS t2 ON t1.player_api_id = t2.player_api_id
WHERE t1.height > 170
  AND strftime('%Y', t2.`date`) BETWEEN '2010' AND '2015';
```

**Predicted SQL:**

```sql
SELECT AVG(Player_Attributes__overall_rating)
FROM (
    SELECT DISTINCT Player__id, Player_Attributes__overall_rating
    FROM two_nf_player
    WHERE Player__height > 170 AND Player_Attributes__date BETWEEN '2010-01-01' AND '2015-12-31'
)
```

### 16. Q1078 (european_football_2, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Returns an extra `Player__birthday` column alongside the name, so the output shape differs from gold's single-column result.

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT Player__player_name, Player__birthday
FROM two_nf_player
WHERE Player__player_name IN ('Aaron Lennon', 'Abdelaziz Barrada')
ORDER BY Player__birthday ASC
LIMIT 1;
```

### 17. Q1092 (european_football_2, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · ORDER BY count DESC LIMIT 1 returns a single league while gold's HAVING = MAX returns all four leagues tied at the maximum — a tie-handling logic error.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT DISTINCT League__name
FROM two_nf_match
WHERE Match__season = '2008/2009'
GROUP BY League__name
ORDER BY COUNT(DISTINCT Match__id) DESC
LIMIT 1;
```

### 18. Q1105 (european_football_2, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters `Player_Attributes__date = '2015-05-01'` but dates are stored as '2015-05-01 00:00:00' (gold uses LIKE '2015-05-01%'), so nothing matches.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player_Attributes__attacking_work_rate
FROM two_nf_player
WHERE Player__player_name = 'Francesco Migliore'
AND Player_Attributes__date = '2015-05-01';
```

### 19. Q1136 (european_football_2, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Adds a hallucinated extra filter `attacking_work_rate = 'high'` not present in gold, excluding one of the two qualifying players (1 vs 2).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Player__id) 
FROM two_nf_player 
WHERE Player_Attributes__crossing = (
    SELECT MAX(Player_Attributes__crossing) 
    FROM two_nf_player
) 
AND Player_Attributes__preferred_foot = 'left' 
AND Player_Attributes__attacking_work_rate = 'high';
```

### 20. Q1147 (european_football_2, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Orders by `Player_Attributes__strength` instead of finding the player(s) with maximum `overall_rating`; the column exists, the choice is wrong.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player__player_name 
FROM two_nf_player 
ORDER BY Player_Attributes__strength DESC 
LIMIT 1;
```

### 21. Q95 (financial, moderate, aggregate) — **wrong table name**

**Outcome:** `error` · Joins bare `client`, `account`, and `district` tables that do not exist at L2 (all their columns are already embedded in `two_nf_disp`), so execution fails.

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT DISTINCT account__account_id
FROM two_nf_disp
JOIN client ON two_nf_disp.disp__client_id = client.client_id
JOIN account ON two_nf_disp.disp__account_id = account.account_id
JOIN district ON account.account__district_id = district.district_id
ORDER BY client.birth_date ASC, district.average_salary DESC
LIMIT 1
```

### 22. Q118 (financial, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses status 'A' where gold uses 'C'; with the literal corrected the same loan-grain query reproduces gold exactly (46.885), so the wrong filter value is the only error.

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(DISTINCT CASE WHEN loan__status = 'A' THEN loan__loan_id END) * 100.0 / COUNT(DISTINCT loan__loan_id)) AS percentage_running_no_issue
FROM 
    two_nf_loan
WHERE 
    loan__amount < 100000;
```

### 23. Q125 (financial, challenging, retrieval) — **join plan error + wrong column name**

**Outcome:** `error` · Needlessly joins `two_nf_loan` with `two_nf_disp` — both embed the district columns — making `district__district_name` ambiguous; it also references bare `status`/`amount` and a nonexistent status literal 'Running'.

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT DISTINCT 
    district__district_name, 
    district__unemployment_rate_1996 - district__unemployment_rate_1995 AS unemployment_rate_increment
FROM 
    two_nf_loan
JOIN 
    two_nf_disp ON two_nf_loan.loan__account_id = two_nf_disp.disp__account_id
WHERE 
    two_nf_loan.status = 'Running' AND two_nf_loan.amount > 0;
```

### 24. Q149 (financial, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects `account__statement_frequency` instead of gold's disp `type` and substitutes a NOT-IN-loans condition for gold's salary-range logic; the NOT IN over FOJ-NULL-padded `loan__account_id` (3818 NULLs) then guarantees an empty result.

**Gold SQL:**

```sql
SELECT DISTINCT T3.`type`
FROM `district` AS T1
JOIN `account`  AS T2 ON T1.`district_id` = T2.`district_id`
JOIN `disp`     AS T3 ON T2.`account_id`  = T3.`account_id`
WHERE T3.`type` <> 'OWNER'
  AND T1.`A11`  > 8000
  AND T1.`A11` <= 9000;
```

**Predicted SQL:**

```sql
SELECT DISTINCT account__statement_frequency
FROM two_nf_account
WHERE account__account_id NOT IN (
    SELECT loan__account_id
    FROM two_nf_loan
)
AND district__average_salary BETWEEN 8000 AND 9000;
```

### 25. Q152 (financial, moderate, aggregate) — **wrong table name**

**Outcome:** `error` · Joins a nonexistent `two_nf_district` table (district columns are already inside `two_nf_account`), so execution fails.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(district__number_crimes_1995)
FROM two_nf_account
JOIN two_nf_district ON two_nf_account.account__district_id = two_nf_district.district_id
WHERE two_nf_district.number_inhabitants > 4000
AND strftime('%Y', two_nf_account.account__date) >= '1997';
```

### 26. Q194 (financial, moderate, retrieval) — **wrong table name**

**Outcome:** `error` · Joins a bare `card` table that does not exist at L2 (card columns live inside `two_nf_disp`), so execution fails before its wrong literals ('High Level', 'Loan') matter.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT DISTINCT client__client_id, 
       strftime('%Y', 'now') - strftime('%Y', client__birth_date) - 
       (strftime('%m-%d', 'now') < strftime('%m-%d', client__birth_date)) AS age
FROM two_nf_disp
JOIN card ON two_nf_disp.disp__disposition_id = card.card__disposition_id
WHERE card.type = 'High Level' AND two_nf_disp.type = 'Loan';
```

### 27. Q846 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Answers from `two_nf_results` with `status_id = 1` instead of using `two_nf_qualifying` ordered by qualifying-1 time as gold requires; all names exist, the source-table choice and logic are wrong.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__driver_ref_name 
FROM two_nf_results 
WHERE results__race_id = 20 AND results__status_id = 1;
```

### 28. Q865 (formula_1, moderate, retrieval) — **correct**

**Outcome:** `correct` · Correct at L2.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM two_nf_results
WHERE results__race_id = 592 AND results__status_id = 1
ORDER BY drivers__date_of_birth ASC
LIMIT 1;
```

### 29. Q868 (formula_1, simple, retrieval) — **wrong table name**

**Outcome:** `error` · Joins a nonexistent `two_nf_circuits` table (circuit columns are embedded in `two_nf_races`), so the L1 missing-DISTINCT case becomes a naming failure at L2.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT circuits__location, circuits__latitude, circuits__longitude 
FROM two_nf_races 
JOIN two_nf_circuits ON two_nf_races.races__circuit_id = two_nf_circuits.circuits__circuit_id 
WHERE two_nf_races.races__name = 'Malaysian Grand Prix';
```

### 30. Q950 (formula_1, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Reads `results__points = 0` from the results cluster while gold requires `constructorStandings.points = 0` (available in `two_nf_constructors`), returning 13 constructors instead of 6.

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT DISTINCT constructors__name 
FROM two_nf_results 
WHERE results__race_id = 291 AND results__points = 0;
```

### 31. Q954 (formula_1, challenging, aggregate) — **correct**

**Outcome:** `correct` · Correct at L2.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    CAST(COUNT(DISTINCT CASE WHEN status__status = 'Finished' THEN results__result_id END) AS REAL) * 100 / COUNT(DISTINCT results__result_id) AS race_completion_percentage
FROM 
    two_nf_results
WHERE 
    drivers__nationality = 'Japanese' 
    AND races__year BETWEEN 2007 AND 2009;
```

### 32. Q959 (formula_1, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Drops gold's `time LIKE '_:%:__.___'` finisher filter (replacing it with a standings-position subquery that matches every 2009 race) and its DISTINCT collapses legitimate duplicate fastest-lap values.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT DISTINCT results__fastest_lap_number
FROM two_nf_results
WHERE results__race_id IN (
    SELECT driverStandings__race_id
    FROM two_nf_results
    WHERE driverStandings__position = 1 AND races__year = 2009
)
```

### 33. Q967 (formula_1, simple, aggregate) — **wrong table name**

**Outcome:** `error` · Joins a bare `drivers` table that does not exist at L2 (driver columns are embedded in `two_nf_results`), so execution fails.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT drivers__driver_id)
FROM two_nf_results
JOIN drivers ON two_nf_results.results__driver_id = drivers.drivers__driver_id
WHERE drivers.nationality = 'Netherlands'
ORDER BY drivers.date_of_birth DESC
LIMIT 3;
```

### 34. Q981 (formula_1, moderate, retrieval) — **wrong table name**

**Outcome:** `error` · Joins a nonexistent `two_nf_drivers` table (driver columns are embedded in `two_nf_qualifying`), so execution fails.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT MIN(races__year) AS year, races__name, races__date, races__time
FROM two_nf_qualifying
JOIN two_nf_drivers ON two_nf_qualifying.qualifying__driver_id = two_nf_drivers.drivers__driver_id
JOIN two_nf_races ON two_nf_qualifying.qualifying__race_id = two_nf_races.races__race_id
ORDER BY drivers__date_of_birth ASC, races__year ASC, races__round ASC
LIMIT 1;
```

### 35. Q990 (formula_1, challenging, retrieval) — **join plan error + wrong column name**

**Outcome:** `error` · Joins `two_nf_races` and `two_nf_constructors` onto `two_nf_results`, which already embeds both — making `constructors__constructor_ref_name` ambiguous — and also references bare `year`/`name`/`position` columns.

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT DISTINCT constructors__constructor_ref_name, constructors__url
FROM two_nf_results
JOIN two_nf_races ON two_nf_results.results__race_id = two_nf_races.races__race_id
JOIN two_nf_constructors ON two_nf_results.results__constructor_id = two_nf_constructors.constructors__constructor_id
WHERE two_nf_races.year = 2009 AND two_nf_races.name = 'Singapore Grand Prix' AND two_nf_results.position = 1;
```

### 36. Q1003 (formula_1, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · The outer count omits the `races__name = 'Canadian Grand Prix'` restriction, counting the top driver's accidents across all races (18) instead of at that race (2).

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT results__result_id) 
FROM two_nf_results 
WHERE results__driver_id = (
    SELECT results__driver_id 
    FROM two_nf_results 
    WHERE races__name = 'Canadian Grand Prix' 
    AND status__status = 'Accident' 
    GROUP BY results__driver_id 
    ORDER BY COUNT(DISTINCT results__result_id) DESC 
    LIMIT 1
)
AND status__status = 'Accident';
```

### 37. Q1361 (student_club, simple, aggregate) — **wrong column name**

**Outcome:** `error` · References bare `cost` which only exists as `expense__cost`, so execution fails (the `LIKE '%pizza%'` literal is a secondary issue).

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) 
FROM two_nf_expense 
WHERE expense_description LIKE '%pizza%'
```

### 38. Q1381 (student_club, moderate, aggregate) — **weak duplication / recoverable artefact**

**Outcome:** `wrong_answer` · The logic is right — COUNT(DISTINCT event) even neutralises the budget fan-out inside `two_nf_event` — but the FULL-OUTER-JOIN NULL-padded rows form a phantom NULL-member group that passes HAVING; adding `member__member_id IS NOT NULL` restores gold's 29 rows exactly.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL:**

```sql
SELECT DISTINCT member__first_name, member__last_name
FROM two_nf_event
GROUP BY member__member_id
HAVING COUNT(DISTINCT event__event_id) > 7;
```

### 39. Q1394 (student_club, simple, aggregate) — **correct**

**Outcome:** `correct` · Correct at L2.

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT member__member_id) 
FROM two_nf_member 
WHERE major__major_name = 'Physics Teaching';
```

### 40. Q1403 (student_club, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters `event__status = 'closed'` (stored value is 'Closed', and gold uses budget `event_status`) and omits the `remaining < 0` condition; with the corrected literal and filter the query returns gold ('September Speaker').

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT event__event_name
FROM two_nf_event
WHERE event__status = 'closed'
ORDER BY (budget__amount_spent - budget__amount) DESC
LIMIT 1;
```

### 41. Q1409 (student_club, simple, aggregate) — **wrong column name**

**Outcome:** `error` · References bare `expense_id`/`cost` which only exist as `expense__expense_id`/`expense__cost`, so execution fails.

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) 
FROM (
    SELECT DISTINCT expense_id, cost 
    FROM two_nf_expense 
    WHERE expense_date = '2019-08-20'
)
```

### 42. Q1411 (student_club, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · `two_nf_expense` is at expense grain with no duplication, so the model's habitual DISTINCT wrongly collapses legitimately repeated descriptions; the identical query without DISTINCT matches gold's multiset exactly.

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT expense__expense_description 
FROM two_nf_expense 
WHERE member__first_name = 'Sacha' AND member__last_name = 'Harrison';
```

### 43. Q1422 (student_club, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects `budget__category` instead of gold's event `type` — a wrong-column semantic choice (both columns exist).

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT budget__category 
FROM two_nf_event 
WHERE event__location = 'MU 215';
```

### 44. Q717 (superhero, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct at L2.

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT DISTINCT superpower__power_name 
FROM two_nf_hero_power 
WHERE superhero__superhero_name = '3-D Man';
```

### 45. Q723 (superhero, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct at L2.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT two_nf_superhero.superhero__id)
FROM two_nf_superhero
JOIN two_nf_hero_power ON two_nf_superhero.superhero__id = two_nf_hero_power.hero_power__hero_id
WHERE two_nf_superhero.colour_eye__colour = 'Blue' AND two_nf_hero_power.superpower__power_name = 'Agility';
```

### 46. Q724 (superhero, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters lowercase 'blue'/'blond' while the stored values are 'Blue'/'Blond', so the result is empty.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
WHERE colour_eye__colour = 'blue' AND colour_hair__colour = 'blond';
```

### 47. Q782 (superhero, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters lowercase 'black' while the stored value is 'Black', so the result is empty.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM two_nf_superhero 
WHERE colour_eye__colour = 'black' AND colour_hair__colour = 'black';
```

### 48. Q791 (superhero, simple, aggregate) — **wrong column name**

**Outcome:** `error` · References bare `height_cm` which only exists as `superhero__height_cm`, so execution fails.

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) 
FROM (
    SELECT DISTINCT superhero__id, height_cm 
    FROM two_nf_superhero
)
```

### 49. Q1150 (thrombosis_prediction, moderate, aggregate) — **unrecoverable (denormalisation) + other logic error**

**Outcome:** `wrong_answer` · Swaps gold's filter roles (WHERE birthday / CASE sex vs gold's WHERE sex / CASE birthday) and uses nonexistent 'Female'; even fully corrected, examination fan-out inside `two_nf_patient_examination` inflates the naive ratio (94.0430 vs gold 94.0371) — only a patient-grain dedup subquery recovers gold.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_examination 
WHERE strftime('%Y', Patient__birthday) > '1930';
```

### 50. Q1164 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses invented values 'most serious' and 'female' where the stored values are `thrombosis_degree = 1` and sex 'F', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID)
FROM `Patient` AS T1
JOIN `Examination` AS T2 ON T1.ID = T2.ID
WHERE T1.`SEX` = 'F'
  AND STRFTIME('%Y', T2.`Examination Date`) = '1997'
  AND T2.`Thrombosis` = 1;
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_examination
WHERE Examination__thrombosis_degree = 'most serious' AND Examination__examination_date LIKE '1997%' AND Patient__sex = 'female';
```

### 51. Q1187 (thrombosis_prediction, moderate, retrieval) — **wrong column name**

**Outcome:** `error` · References `Examination__examination_date` inside `two_nf_patient_laboratory`, where no Examination columns exist (they are a separate cluster at L2), so the L1 NULL-propagation trap becomes an execution failure; the enzyme column choice (aspartate for GPT) is also wrong.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__ID
FROM two_nf_patient_laboratory
WHERE Examination__examination_date BETWEEN '1987-07-06' AND '1996-01-31'
  AND Laboratory__aspartate_aminotransferase > 30
  AND Laboratory__albumin < 4;
```

### 52. Q1209 (thrombosis_prediction, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Uses threshold `> 40` where gold requires `GPT > 60`; the (correct) alanine-aminotransferase column exists, so this is purely a wrong filter value.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__diagnosis
FROM two_nf_patient_laboratory
WHERE Laboratory__alanine_aminotransferase > 40
ORDER BY Patient__birthday ASC;
```

### 53. Q1225 (thrombosis_prediction, moderate, aggregate) — **wrong column name**

**Outcome:** `error` · References bare `total_bilirubin` which only exists as `Laboratory__total_bilirubin`, so execution fails before the wrong thresholds (<0.3 OR >1.2 vs gold >=2.0) matter.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__sex, GROUP_CONCAT(Patient__ID) AS Patients
FROM two_nf_patient_laboratory
WHERE total_bilirubin < 0.3 OR total_bilirubin > 1.2
GROUP BY Patient__sex;
```

### 54. Q1229 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses threshold `> 150` where gold requires `TG >= 200`, over-counting patients (147 vs 106).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Laboratory__triglyceride > 150 AND 
      strftime('%Y', 'now') - strftime('%Y', Patient__birthday) > 50;
```

### 55. Q1265 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses invented values 'Normal' and 'Admitted' where the stored values are 'negative'/'0' and Admission '+'; at L2 the model found the correct Laboratory RNP column (which errored at L1), leaving only the literal errors.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM two_nf_patient_laboratory 
WHERE Laboratory__anti_ribonuclear_protein = 'Normal' 
AND Patient__admission_type = 'Admitted';
```

### 56. Q1275 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses invented values 'normal' and 'male' where the stored values are 'negative'/'0' and sex 'M', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM two_nf_patient_laboratory
WHERE Laboratory__anti_centromere = 'normal' AND Laboratory__anti_ssb = 'normal' AND Patient__sex = 'male';
```

### 57. Q206 (toxicology, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Puts the bond-id value 'TR004_8_9' into the `molecule__label` filter instead of the bond-id column, and returns two element columns where gold returns one.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM two_nf_connected 
WHERE molecule__label = 'TR004_8_9';
```

### 58. Q212 (toxicology, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Filters `molecule__label != 'carcinogenic'` (domain is '+'/'-') and takes LIMIT 1 where gold returns a three-way tie; the surviving NULL-element FOJ-padded group then becomes the spurious answer.

**Gold SQL:**

```sql
SELECT `a`.`element`
FROM `atom` AS `a`
JOIN `molecule` AS `m`  ON `a`.`molecule_id` = `m`.`molecule_id`
WHERE `m`.`label` = '-'
GROUP BY `a`.`element`
HAVING COUNT(*) = (
    SELECT MIN(cnt)
    FROM (
        SELECT COUNT(*) AS cnt
        FROM `atom` AS `a2`
        JOIN `molecule` AS `m2` ON `a2`.`molecule_id` = `m2`.`molecule_id`
        WHERE `m2`.`label` = '-'
        GROUP BY `a2`.`element`
    )
);
```

**Predicted SQL:**

```sql
SELECT atom_1__element
FROM two_nf_connected
WHERE molecule__label != 'carcinogenic'
GROUP BY atom_1__element
ORDER BY COUNT(DISTINCT atom_1__atom_id) ASC
LIMIT 1;
```

### 59. Q219 (toxicology, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses invented literals 'triple' and 'carcinogenic' (stored values '#' and '+'), so nothing matches; even corrected, the row-fanned SUM numerator against a COUNT(DISTINCT molecule) denominator would still need molecule-grain dedup.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN molecule__label = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) 
FROM two_nf_connected 
WHERE bond__bond_type = 'triple';
```

### 60. Q268 (toxicology, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Returns `atom_1__element, atom_2__element` as two columns while gold returns the bond's atom elements as a single column of rows — an output-shape error.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM two_nf_connected 
WHERE connected__bond_id = 'TR001_10_11';
```
