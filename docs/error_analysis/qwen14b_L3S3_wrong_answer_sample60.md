# Qwen2.5-Coder-14B · L3·S3 wrong-answer sample (n=60)

**Source:** `results/full/qwen2.5-coder-14b-local__L3S3.csv` · **Population:** 284 failures / 397 questions · **Sample:** the same 60 questions as the L1·S3 / L2·S3 samples (seed=42)

**Setup:** Gold SQL on 3NF SQLite; predicted SQL on the same 3NF database through TEMP VIEWs exposing S3 (descriptive snake_case) column names (`build_col_rename_map`, `evaluator.py`). Multiset execution comparison.

**Method:** every failure re-executed through the same S3 rename views the experiment used; ambiguous cases verified by writing a corrected query and checking it against the gold result.

## Category definitions

| Category | Meaning |
| --- | --- |
| **wrong column name** | Predicted SQL references a column identifier that exists nowhere in the S3 schema (execution error). |
| **wrong table name** | Predicted SQL references a table identifier that does not exist (execution error). |
| **join plan error** | All identifiers exist somewhere, but the join structure is wrong — a column attributed to a table that doesn't hold it, a nonexistent join key, or an unnecessary join that changes the aggregation grain. |
| **other logic error** | Identifiers and joins resolve; the semantics are wrong — wrong filter value/case, wrong threshold, wrong existing column/table choice, wrong aggregate or grain, tie/output-shape errors. |
| **weak duplication / recoverable artefact** | (Not applicable at L3 — the schema is the original 3NF; none observed, as expected.) |
| **unrecoverable (denormalisation)** | (Not applicable at L3 — none observed, as expected.) |

## Summary (sample)

| Primary category | Count | % of sample |
| --- | --- | --- |
| other logic error | 43 | 71.7% |
| join plan error | 6 | 10.0% |
| wrong column name | 0 | 0.0% |
| wrong table name | 0 | 0.0% |
| unrecoverable (denormalisation) | 0 | 0.0% |
| weak duplication / recoverable artefact | 0 | 0.0% |
| correct | 11 | 18.3% |
| **Total** | 60 | 100.0% |

*As expected for the normalised schema, there are no weak-duplication or unrecoverable denormalisation artefacts at L3 — and also no naming hallucinations: with real 3NF tables and S3 column views the model never invents identifiers, so failures concentrate in data-value literals (case-sensitive colours, 'EUR'/'CZE' codes, date formats), thresholds, tie handling, and aggregation grain. The few execution errors are column-to-table attribution mistakes (counted under join plan error). 11 of the 60 L1 failures are correct at L3.*

---

## Sampled failures

### 1. Q32 (california_schools, moderate, retrieval) — **join plan error**

**Outcome:** `error` · References `school_ownership_code` (schools' S3 name for SOC) on `frpm` without joining `schools`, so execution fails — a column-to-table attribution error, not an invented name.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT 
    school_name, 
    percent_eligible_free_or_reduced_price_meal_k12
FROM 
    frpm
WHERE 
    school_ownership_code = 66
ORDER BY 
    free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### 2. Q41 (california_schools, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters `Virtual = 'Yes'` (domain is F/N/P) and implements max-per-county + LIMIT 5 instead of gold's rank-top-5-per-county with `Virtual = 'F'` and `rtype = 'S'`, returning nothing.

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
SELECT s.School
FROM schools s
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE s.Virtual = 'Yes'
AND (ss.county_name, ss.average_score_reading) IN (
    SELECT county_name, MAX(average_score_reading)
    FROM satscores
    GROUP BY county_name
    ORDER BY MAX(average_score_reading) DESC
    LIMIT 5
)
ORDER BY ss.average_score_reading DESC;
```

### 3. Q48 (california_schools, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Answers from `frpm.district_type` with county literal 'Orange County' (stored as 'Orange') instead of gold's schools DOC 54/52 + StatusType 'Merged' split, so both counts are zero.

**Gold SQL:**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN district_type = 'Unified School District' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN district_type = 'Elementary School District' THEN 1 ELSE 0 END) AS ratio
FROM 
    frpm
WHERE 
    county_name = 'Orange County';
```

### 4. Q79 (california_schools, moderate, aggregate) — **join plan error**

**Outcome:** `error` · References `county_name` (satscores/frpm's S3 column) on `schools`, whose own column is `County`, so execution fails; the `Virtual = 'Yes'` literal is also invalid.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT county_name, COUNT(*) AS school_count
FROM schools
WHERE county_name IN ('San Diego', 'Santa Barbara') AND Virtual = 'Yes'
GROUP BY county_name
ORDER BY school_count DESC
LIMIT 1;
```

### 5. Q1476 (debit_card_specializing, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Applies `strftime('%Y', y.date)` to 'YYYYMM' text (e.g. '201112') so the year filter matches nothing; the join itself mirrors gold.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN c.currency = 'CZK' THEN y.consumption ELSE 0 END) - 
    SUM(CASE WHEN c.currency = 'EUR' THEN y.consumption ELSE 0 END) AS consumption_difference
FROM 
    customers c
JOIN 
    yearmonth y ON c.customer_id = y.customer_id
WHERE 
    strftime('%Y', y.date) = '2012';
```

### 6. Q1493 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses `date BETWEEN '2012-02-01' AND '2012-02-29'` against 'YYYYMM' text ('201202'), so nothing matches.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(customer_id) 
FROM yearmonth 
WHERE date BETWEEN '2012-02-01' AND '2012-02-29';
```

### 7. Q1498 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Computes MAX of a single row's consumption (445279.69) instead of gold's SUM per month with ORDER BY/LIMIT — here the `LIKE '2012%'` filter even works, isolating the aggregate-shape error.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) 
FROM yearmonth 
WHERE date LIKE '2012%';
```

### 8. Q1505 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Correct join and structure but filters `currency = 'euro'` while the stored value is 'EUR', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.customer_id) 
FROM customers c 
JOIN yearmonth y ON c.customer_id = y.customer_id 
WHERE c.currency = 'euro' AND y.consumption > 1000;
```

### 9. Q1506 (debit_card_specializing, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Correct three-table join but filters `country = 'Czech Republic'` while the stored value is 'CZE', so the result is empty.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.description 
FROM products p 
JOIN transactions_1k t ON p.product_id = t.product_id 
JOIN gasstations g ON t.gas_station_id = g.gas_station_id 
WHERE g.country = 'Czech Republic';
```

### 10. Q1528 (debit_card_specializing, simple, aggregate) — **join plan error + other logic error**

**Outcome:** `wrong_answer` · Needlessly joins `transactions_1k`, changing the denominator from gasstation rows (gold) to transaction-fanned rows and dropping stations with no transactions; the lowercase 'premium' literal additionally zeroes the numerator.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN g.segment = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage_premium
FROM 
    gasstations g
JOIN 
    transactions_1k t ON g.gas_station_id = t.gas_station_id
WHERE 
    g.country = 'SVK';
```

### 11. Q1529 (debit_card_specializing, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Sums `amount` (fuel quantity, giving 148) where gold sums `Amount * Price` (spend, 88612.38) — a wrong-metric error on real columns.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_spent, 
       SUM(CASE WHEN date LIKE '2012-08%' THEN amount ELSE 0 END) AS august_2012_spent
FROM transactions_1k
WHERE customer_id = 38508;
```

### 12. Q1036 (european_football_2, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Reproduces gold's join and threshold but omits gold's DISTINCT, so teams with multiple qualifying 2012 attribute snapshots appear repeatedly in the multiset.

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T.team_long_name 
FROM Team_Attributes AS TA 
JOIN Team AS T ON TA.team_api_id = T.team_api_id 
WHERE TA.buildup_play_passing > (SELECT AVG(buildup_play_passing) FROM Team_Attributes WHERE date LIKE '2012%') 
AND TA.date LIKE '2012%';
```

### 13. Q1037 (european_football_2, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Aggregates at attribute-snapshot grain (SUM/COUNT(*) per row, 24.57) where gold counts DISTINCT players (28.87) — a wrong aggregation grain on a legitimate join.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.player_api_id = Player.player_api_id 
WHERE strftime('%Y', Player.birthday) BETWEEN '1987' AND '1992';
```

### 14. Q1039 (european_football_2, simple, aggregate) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL:**

```sql
SELECT AVG(T1.long_shots) 
FROM Player_Attributes AS T1 
JOIN Player AS T2 
ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Ahmed Samir Farag';
```

### 15. Q1068 (european_football_2, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct at L3.

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
SELECT AVG(overall_rating) 
FROM Player_Attributes 
WHERE date BETWEEN '2010-01-01' AND '2015-12-31' 
AND player_api_id IN (
    SELECT player_api_id 
    FROM Player 
    WHERE height > 170
);
```

### 16. Q1078 (european_football_2, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P1.player_name AS older_player FROM Player P1 JOIN Player P2 ON P1.birthday < P2.birthday WHERE P1.player_name = 'Aaron Lennon' AND P2.player_name = 'Abdelaziz Barrada'
```

### 17. Q1092 (european_football_2, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · ORDER BY count DESC LIMIT 1 returns one league while gold's HAVING = MAX returns the four-way tie.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League L 
JOIN Match M ON L.id = M.league_id 
WHERE M.season = '2008/2009' 
GROUP BY L.name 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### 18. Q1105 (european_football_2, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters `date = '2015-05-01'` but dates are stored with a time suffix ('2015-05-01 00:00:00'; gold uses LIKE), so nothing matches.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.attacking_work_rate 
FROM Player_Attributes AS T1 
JOIN Player AS T2 
ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Francesco Migliore' AND T1.date = '2015-05-01';
```

### 19. Q1136 (european_football_2, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses capitalised literals 'Left'/'High' (stored lowercase), adds an `attacking_work_rate` filter absent from gold, and counts rows instead of distinct players — the case error alone already yields 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE crossing = (SELECT MAX(crossing) FROM Player_Attributes) 
AND preferred_foot = 'Left' 
AND attacking_work_rate = 'High';
```

### 20. Q1147 (european_football_2, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Ranks by `strength` instead of gold's maximum `overall_rating` (and LIMIT 1 would miss ties); the column choice is the error.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### 21. Q95 (financial, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Orders `birth_date ASC` (oldest client) where gold's subquery takes `ORDER BY birth_date DESC` (youngest), returning account 3908 instead of 2836.

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT a.account_id
FROM account a
JOIN disp d ON a.account_id = d.account_id
JOIN client c ON d.client_id = c.client_id
JOIN district di ON a.district_id = di.district_id
ORDER BY c.birth_date ASC, di.average_salary DESC
LIMIT 1;
```

### 22. Q118 (financial, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses status 'A' where gold uses 'C' — a single wrong filter value (45.57 vs 46.89).

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM loan 
WHERE amount < 100000;
```

### 23. Q125 (financial, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Computes the absolute unemployment difference without gold's `/ A12 * 100` normalisation, filters status 'A' instead of 'D', and routes district through client instead of the loan account's district.

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT d.unemployment_rate_1996 - d.unemployment_rate_1995 AS unemployment_rate_increment
FROM loan l
JOIN account a ON l.account_id = a.account_id
JOIN disp d1 ON a.account_id = d1.account_id
JOIN client c ON d1.client_id = c.client_id
JOIN district d ON c.district_id = d.district_id
WHERE l.status = 'A' AND l.amount > 0;
```

### 24. Q149 (financial, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Returns two columns (frequency + salary) where gold returns one, and answers with account `statement_frequency` under a no-loan condition instead of gold's disp `type <> 'OWNER'` in the salary band.

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
SELECT DISTINCT a.statement_frequency, d.average_salary
FROM account a
JOIN district d ON a.district_id = d.district_id
WHERE a.account_id NOT IN (SELECT account_id FROM loan)
AND d.average_salary BETWEEN 8000 AND 9000;
```

### 25. Q152 (financial, moderate, aggregate) — **other logic error + join plan error**

**Outcome:** `wrong_answer` · Filters `number_inhabitants > 4000` where gold filters A15 (1995 crimes) > 4000, and the join to `account` fans districts per account so AVG is account-weighted (2184.77 vs 9675.04) instead of gold's IN-subquery at district grain.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(d.number_crimes_1995) 
FROM district d 
JOIN account a ON d.district_id = a.district_id 
WHERE d.number_inhabitants > 4000 AND strftime('%Y', a.date) >= '1997';
```

### 26. Q194 (financial, moderate, retrieval) — **join plan error**

**Outcome:** `error` · Joins `card` on `ca.account_id`, a column that does not exist on card (its key is `disposition_id`), so execution fails; the 'High level' literal (gold: 'gold') would be the next failure.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.client_id, strftime('%Y', 'now') - strftime('%Y', c.birth_date) AS age
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN card ca ON d.account_id = ca.account_id
WHERE ca.type = 'High level' AND d.type = 'OWNER'
```

### 27. Q846 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Answers from `results` with `rank = 1` instead of gold's `qualifying` table ordered by q1 time DESC LIMIT 5 — wrong source table and logic on valid names.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.driver_ref_name 
FROM drivers d 
JOIN results r ON d.driver_id = r.driver_id 
WHERE r.race_id = 20 AND r.position > 0 AND r.rank = 1;
```

### 28. Q865 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Uses `position IS NOT NULL` as the finisher condition where gold requires `time IS NOT NULL`, selecting a different (earlier-born) driver.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name 
FROM drivers 
WHERE driver_id IN (
    SELECT driver_id 
    FROM results 
    WHERE race_id = 592 AND position IS NOT NULL
) 
ORDER BY date_of_birth ASC 
LIMIT 1;
```

### 29. Q868 (formula_1, simple, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Applies the race name 'Malaysian Grand Prix' to `circuits.name` without gold's join to `races`, so no circuit matches.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Malaysian Grand Prix'
```

### 30. Q950 (formula_1, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Reads points from `constructorResults` instead of gold's `constructorStandings` — both tables exist; the source choice is wrong (11 constructors vs 6).

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT c.name 
FROM constructors c 
JOIN constructorResults cr ON c.constructor_id = cr.constructor_id 
WHERE cr.race_id = 291 AND cr.points = 0;
```

### 31. Q954 (formula_1, challenging, aggregate) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN r.status_id = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(r.driver_id)) AS completion_percentage
FROM 
    results r
JOIN 
    drivers d ON r.driver_id = d.driver_id
JOIN 
    races ra ON r.race_id = ra.race_id
WHERE 
    d.nationality = 'Japanese' 
    AND ra.year BETWEEN 2007 AND 2009;
```

### 32. Q959 (formula_1, simple, retrieval) — **join plan error**

**Outcome:** `error` · References `driverStandings.year`, a column that lives on `races` (not joined), so execution fails; the MAX() collapse of gold's multiset would be the next error.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT MAX(results.fastest_lap_number) AS fastest_lap_number
FROM results
JOIN driverStandings ON results.driver_id = driverStandings.driver_id AND results.race_id = driverStandings.race_id
WHERE driverStandings.year = 2009 AND driverStandings.position = 1;
```

### 33. Q967 (formula_1, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses the invented nationality 'Netherlandic' (stored 'Dutch') and misreads the question, counting all such drivers with a stray ORDER/LIMIT instead of counting Dutch among the three youngest.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM drivers 
WHERE nationality = 'Netherlandic' 
ORDER BY date_of_birth DESC 
LIMIT 3;
```

### 34. Q981 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects the driver with MIN(date_of_birth) (oldest) where gold wants the youngest (ORDER BY dob DESC), and that driver has no qualifying rows, so MIN(year) aggregates over an empty set to NULLs.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MIN(r.year) AS year, 
    r.name AS race_name, 
    r.date AS race_date, 
    r.time AS race_time
FROM 
    qualifying q
JOIN 
    races r ON q.race_id = r.race_id
JOIN 
    drivers d ON q.driver_id = d.driver_id
WHERE 
    d.date_of_birth = (SELECT MIN(date_of_birth) FROM drivers)
```

### 35. Q990 (formula_1, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Answers with the 2009 standings leader at Singapore (brawn) where gold asks for constructors of drivers who finished the race (`time LIKE '_:%:__.___'` → mclaren).

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT c.constructor_ref_name, c.url 
FROM constructors c 
JOIN constructorStandings cs ON c.constructor_id = cs.constructor_id 
JOIN races r ON cs.race_id = r.race_id 
WHERE r.name = 'Singapore Grand Prix' AND r.year = 2009 AND cs.position = 1;
```

### 36. Q1003 (formula_1, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS accident_count
FROM results
JOIN status ON results.status_id = status.status_id
WHERE status.status = 'Accident'
AND results.race_id IN (
    SELECT race_id
    FROM races
    WHERE name = 'Canadian Grand Prix'
)
AND results.driver_id = (
    SELECT driver_id
    FROM results
    JOIN status ON results.status_id = status.status_id
    WHERE status.status = 'Accident'
    AND results.race_id IN (
        SELECT race_id
        FROM races
        WHERE name = 'Canadian Grand Prix'
    )
    GROUP BY driver_id
    ORDER BY COUNT(*) DESC
    LIMIT 1
);
```

### 37. Q1361 (student_club, simple, aggregate) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) AS total_pizza_cost
FROM expense
WHERE expense_description LIKE '%pizza%';
```

### 38. Q1381 (student_club, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name 
FROM member m 
JOIN attendance a ON m.member_id = a.member_id 
GROUP BY m.member_id 
HAVING COUNT(a.event_id) > 7;
```

### 39. Q1394 (student_club, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Adds a hallucinated `position = 'Student_Club'` filter (no such position value) on top of gold's major-name condition, so the count is 0 — the same query was correct at L2.

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM member 
JOIN major ON member.major_id = major.major_id 
WHERE major.major_name = 'Physics Teaching' AND member.position = 'Student_Club';
```

### 40. Q1403 (student_club, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters `status = 'closed'` (stored 'Closed') and reconstructs overspend from an expense sum instead of gold's `remaining < 0`, returning nothing.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.event_name
FROM event e
JOIN budget b ON e.event_id = b.event_id
JOIN expense ex ON b.budget_id = ex.budget_id
WHERE e.status = 'closed'
GROUP BY e.event_id
ORDER BY SUM(ex.cost) - b.amount DESC
LIMIT 1;
```

### 41. Q1409 (student_club, simple, aggregate) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) AS total_expense
FROM expense
WHERE expense_date = '2019-08-20';
```

### 42. Q1411 (student_club, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT e.expense_description 
FROM expense e 
JOIN member m ON e.member_id = m.member_id 
WHERE m.first_name = 'Sacha' AND m.last_name = 'Harrison';
```

### 43. Q1422 (student_club, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects `budget.category` instead of gold's `event.type` — a wrong-column semantic choice on valid names.

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.category 
FROM budget b 
JOIN event e ON b.event_id = e.event_id 
WHERE e.location = 'MU 215';
```

### 44. Q717 (superhero, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT sp.power_name 
FROM superhero sh 
JOIN hero_power hp ON sh.id = hp.hero_id 
JOIN superpower sp ON hp.power_id = sp.id 
WHERE sh.superhero_name = '3-D Man';
```

### 45. Q723 (superhero, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Filters lowercase 'blue' while the stored colour value is 'Blue', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT s.id) 
FROM superhero s 
JOIN colour c ON s.eye_colour_id = c.id 
JOIN hero_power hp ON s.id = hp.hero_id 
JOIN superpower p ON hp.power_id = p.id 
WHERE c.colour = 'blue' AND p.power_name = 'Agility';
```

### 46. Q724 (superhero, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters lowercase 'blue'/'blond' while the stored values are 'Blue'/'Blond', so the result is empty.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name 
FROM superhero s 
JOIN colour e ON s.eye_colour_id = e.id 
JOIN colour h ON s.hair_colour_id = h.id 
WHERE e.colour = 'blue' AND h.colour = 'blond';
```

### 47. Q782 (superhero, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters lowercase 'black' while the stored value is 'Black', so the result is empty.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name 
FROM superhero s 
JOIN colour ec ON s.eye_colour_id = ec.id 
JOIN colour hc ON s.hair_colour_id = hc.id 
WHERE ec.colour = 'black' AND hc.colour = 'black';
```

### 48. Q791 (superhero, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Omits gold's `height_cm > 0` guard, so zero heights drag the average down (267.75 vs 345.04).

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### 49. Q1150 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses 'female' (stored 'F') and puts the sex condition inside the CASE with COUNT(*) over all patients as denominator, where gold restricts the denominator to female patients via WHERE.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'female' AND strftime('%Y', birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient;
```

### 50. Q1164 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Filters sex with the literal '女' (stored 'F') and equates 'most serious' with MAX(thrombosis_degree) where gold uses `Thrombosis = 1`, so the count is 0.

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
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE P.sex = '女' 
AND E.thrombosis_degree = (SELECT MAX(thrombosis_degree) FROM Examination) 
AND strftime('%Y', E.examination_date) = '1997';
```

### 51. Q1187 (thrombosis_prediction, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Joins `Examination` and filters its `examination_date` where gold filters `Laboratory.Date`, and reads aspartate aminotransferase where GPT is alanine — two wrong-source choices that shrink the result to 3 of 61 patients.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID
FROM Patient P
JOIN Examination E ON P.ID = E.ID
JOIN Laboratory L ON P.ID = L.ID
WHERE E.examination_date BETWEEN '1987-07-06' AND '1996-01-31'
AND L.aspartate_aminotransferase > 30
AND L.albumin < 4;
```

### 52. Q1209 (thrombosis_prediction, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Uses threshold `> 40` where gold requires `GPT > 60` and omits gold's DISTINCT, returning fanned duplicate diagnoses per lab row.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.diagnosis 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.alanine_aminotransferase > 40 
ORDER BY P.birthday ASC;
```

### 53. Q1225 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Counts patients per sex with thresholds `< 0.3 OR > 1.2` where gold GROUP_CONCATs the DISTINCT patient IDs with `T-BIL >= 2.0` — wrong aggregate and wrong thresholds.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.sex, COUNT(*) AS patient_count
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.total_bilirubin < 0.3 OR L.total_bilirubin > 1.2
GROUP BY P.sex;
```

### 54. Q1229 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses threshold `> 150` where gold requires `TG >= 200`, over-counting patients (147 vs 106).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID)
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.triglyceride > 150 AND 
      strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) > 50;
```

### 55. Q1265 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses invented values 'normal' and 'admitted' where the stored values are 'negative'/'0' and Admission '+', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.anti_ribonuclear_protein = 'normal' AND P.admission_type = 'admitted';
```

### 56. Q1275 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses invented values 'normal' and 'male' where the stored values are 'negative'/'0' and sex 'M', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.anti_centromere = 'normal' 
AND L.anti_ssb = 'normal' 
AND P.sex = 'male';
```

### 57. Q206 (toxicology, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Puts the bond-id value 'TR004_8_9' into `molecule.label` and joins via molecule instead of gold's `connected.bond_id` path, so nothing matches.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
JOIN bond b ON a.molecule_id = b.molecule_id 
WHERE m.label = 'TR004_8_9';
```

### 58. Q212 (toxicology, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Excludes molecules labelled 'carcinogenic' (no such label; domain is '+'/'-') so all atoms qualify, and LIMIT 1 returns one element where gold returns a three-way tie for least common.

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
SELECT element 
FROM atom 
WHERE molecule_id NOT IN (SELECT molecule_id FROM molecule WHERE label = 'carcinogenic') 
GROUP BY element 
ORDER BY COUNT(*) ASC 
LIMIT 1;
```

### 59. Q219 (toxicology, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses invented literals 'triple' and 'carcinogenic' (stored '#' and '+'), and inverts gold's structure (share of '+' molecules among '#'-bonded molecules), yielding NULL.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN b.bond_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT m.molecule_id) 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id 
WHERE m.label = 'carcinogenic';
```

### 60. Q268 (toxicology, challenging, retrieval) — **correct**

**Outcome:** `correct` · Correct at L3.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN connected c ON a.atom_id = c.atom_id 
WHERE c.bond_id = 'TR001_10_11';
```
