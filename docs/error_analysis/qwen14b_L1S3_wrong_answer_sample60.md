# Qwen2.5-Coder-14B · L1·S3 wrong-answer sample (n=60)

**Source:** `results/full/qwen2.5-coder-14b-local__L1S3.csv` · **Population:** 317 failures / 397 questions · **Sample:** seed=42, n=60

**Setup:** Gold SQL on 3NF SQLite; predicted SQL on `{db_id}__1nf.sqlite` (`one_nf_0`). Multiset execution comparison (`evaluator.py`).

## Category definitions


| Code    | Label                             | Meaning                                                                                                                              |
| ------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **(a)** | Genuine model error               | Wrong metric, filter, column, `HAVING`, missing `/12`, `MAX` vs `SUM`, etc.                                                          |
| **(b)** | Partial (missing DISTINCT)        | 1NF translation largely faithful; automated DISTINCT repair **or** clear `COUNT`/scan fan-out without DISTINCT would align with gold |
| **(c)** | Unrecoverable evaluation artefact | SQL executes but multiset ≠ gold; execution errors; or fan-out needs dedup **subquery** (SUM/AVG), not keyword DISTINCT alone        |


## Summary (sample)


| Category                            | Count | % of sample |
| ----------------------------------- | ----- | ----------- |
| **(a)** Genuine model error         | 33    | 55.0%       |
| **(b)** Partial (DISTINCT missing)  | 1     | 1.7%        |
| **(c)** Unrecoverable eval artefact | 26    | 43.3%       |
| **Total**                           | 60    | 100.0%      |


### Full failure population (n=317, same classifier)


| Category                            | Count | %      |
| ----------------------------------- | ----- | ------ |
| **(a)** Genuine model error         | 172   | 54.3%  |
| **(b)** Partial (DISTINCT missing)  | 7     | 2.2%   |
| **(c)** Unrecoverable eval artefact | 138   | 43.5%  |
| **Total**                           | 317   | 100.0% |


*Sample seed=42. Classification: execute DISTINCT repairs where applicable, then SQL-shape rules (`analysis/classify_l1s3_qwen14b_sample.py`). (b) = faithful wide-table SQL missing deduplication; (c) = SUM/AVG fan-out, execution errors, or DISTINCT present but still mismatched.*

---

## Sampled failures

### 1. Q32 (california_schools, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT 
    schools__School, 
    frpm__percent_eligible_free_or_reduced_price_meal_k12
FROM 
    one_nf_0
WHERE 
    schools__school_ownership_code = 66
ORDER BY 
    frpm__free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### 2. Q41 (california_schools, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

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
SELECT DISTINCT schools__School, schools__County, satscores__average_score_reading
FROM one_nf_0
WHERE schools__Virtual = 'Yes'
ORDER BY schools__County, satscores__average_score_reading DESC
LIMIT 5;
```

### 3. Q48 (california_schools, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

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
FROM one_nf_0
WHERE schools__County = 'Orange';
```

### 4. Q79 (california_schools, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT schools__County, COUNT(DISTINCT schools__national_center_for_education_statistics_school_id) AS school_count
FROM one_nf_0
WHERE schools__County IN ('San Diego', 'Santa Barbara') AND schools__Charter = 'Yes'
GROUP BY schools__County
ORDER BY school_count DESC
LIMIT 1;
```

### 5. Q1476 (debit_card_specializing, challenging, aggregate) — **(c)/(a) (both model geenration error and fan-out error. (a) wrong filter applies to yearmoth_date due to no knowledge of the actual data type, (c) unrecoverable fan out problem from denormalisation)**

**Outcome:** `wrong_answer` · **Category (c):** SUM on fan-out 1NF rows: requires deduplicating subquery on fact keys; simple DISTINCT in SUM is insufficient

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
    one_nf_0
WHERE 
    strftime('%Y', yearmonth__date) = '2012';
```

### 6. Q1493 (debit_card_specializing, simple, aggregate) — **(a) (model error, generate wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: consumption

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customer_id) 
FROM 
    one_nf_0 
WHERE 
    date BETWEEN '2012-02-01' AND '2012-02-29';
```

### 7. Q1498 (debit_card_specializing, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['MAX']

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(yearmonth__consumption)
FROM one_nf_0
WHERE strftime('%Y', yearmonth__date) = '2012';
```

### 8. Q1505 (debit_card_specializing, simple, aggregate) — **(a) (correct logic, correct filter, wrong value used in filter due to no knowledge of the data, used 'euro' instead of 'eur' in customers__currency column)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT customers__customer_id)
FROM one_nf_0
WHERE customers__currency = 'euro' AND yearmonth__consumption > 1000;
```

### 9. Q1506 (debit_card_specializing, moderate, retrieval) — **(a) (model error, use wrong data value inside filter)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset 

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT products__description 
FROM one_nf_0 
WHERE gasstations__country = 'Czech Republic';
```

### 10. Q1528 (debit_card_specializing, simple, aggregate) — **(c)/(a) (i would classify as fan out error, denormalise cause fan out problem in customers_customer_id column, the model try to use distinct to resolve the error, but origin table contains duplicate customer ids, therefore, using distinct is incorrect as well, also wrong segment column used, should be gasstations segment, not customers segment)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['SUM']; predicted uses ['COUNT', 'SUM']

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN customers__segment = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT customers__customer_id)) AS percentage_premium
FROM 
    one_nf_0
WHERE 
    gasstations__country = 'SVK';
```

### 11. Q1529 (debit_card_specializing, moderate, aggregate) — **(a) (wrong column name used)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: amount

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT 
    SUM(amount) AS total_spent,
    SUM(CASE WHEN date LIKE '2012-08%' THEN amount ELSE 0 END) AS spent_in_august_2012
FROM 
    one_nf_0
WHERE 
    customers__customer_id = 38508;
```

### 12. Q1036 (european_football_2, challenging, aggregate) — **(c) (fan out problem due to normalisation, have different number of teams in 1nf database even after using distinct)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'SUM']; predicted uses ['AVG']

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT DISTINCT team_home__team_long_name
FROM one_nf_0
WHERE Team_Attributes__date LIKE '2012%'
AND Team_Attributes__buildup_play_passing > (
    SELECT AVG(Team_Attributes__buildup_play_passing)
    FROM one_nf_0
    WHERE Team_Attributes__date LIKE '2012%'
);
```

### 13. Q1037 (european_football_2, challenging, aggregate) — **(a) (model generation error, wrong table name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such table: Player_Attributes__id

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT player_api_id) 
FROM Player_Attributes__id 
WHERE strftime('%Y', birthday) BETWEEN '1987' AND '1992';
```

### 14. Q1039 (european_football_2, simple, aggregate) — **(a) (model generation error, wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: long_shots

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
    FROM one_nf_0
    WHERE Player__player_name = 'Ahmed Samir Farag'
)
```

### 15. Q1068 (european_football_2, moderate, aggregate) — **(a) (model generation error, wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: player_api_id

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
FROM (
    SELECT DISTINCT player_api_id, overall_rating
    FROM one_nf_0
    WHERE height > 170 AND date BETWEEN '2010-01-01' AND '2015-12-31'
)
```

### 16. Q1078 (european_football_2, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT Player__player_name, Player__birthday
FROM one_nf_0
WHERE Player__player_name IN ('Aaron Lennon', 'Abdelaziz Barrada')
ORDER BY Player__birthday ASC
LIMIT 1;
```

### 17. Q1092 (european_football_2, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'MAX']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT DISTINCT League__name
FROM one_nf_0
WHERE Match__season = '2008/2009'
GROUP BY League__name
ORDER BY COUNT(DISTINCT Match__id) DESC
LIMIT 1;
```

### 18. Q1105 (european_football_2, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player_Attributes__attacking_work_rate
FROM one_nf_0
WHERE Player__player_name = 'Francesco Migliore' AND Player_Attributes__date = '2015-05-01';
```

### 19. Q1136 (european_football_2, moderate, aggregate) — **(a) (model generation error, wrong table name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such table: Player_Attributes

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Player_Attributes__player_api_id)
FROM Player_Attributes
WHERE Player_Attributes__crossing = (
    SELECT MAX(crossing)
    FROM Player_Attributes
)
AND Player_Attributes__preferred_foot = 'left'
AND Player_Attributes__attacking_work_rate = 'high';
```

### 20. Q1147 (european_football_2, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT DISTINCT Player__player_name 
FROM one_nf_0 
ORDER BY Player_Attributes__strength DESC 
LIMIT 1;
```

### 21. Q95 (financial, moderate, aggregate) — **(a) (model generation error, wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: client_id

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT DISTINCT account__account_id
FROM one_nf_0
WHERE client_id = (
    SELECT client_id
    FROM one_nf_0
    ORDER BY client__birth_date ASC, district__average_salary DESC
    LIMIT 1
)
```

### 22. Q118 (financial, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN loan__status = 'A' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT loan__account_id) AS percentage_running
FROM 
    one_nf_0
WHERE 
    loan__amount < 100000;
```

### 23. Q125 (financial, challenging, retrieval) — **(a) (model generation error, wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such table: client__c

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.unemployment_rate_1996 - d.unemployment_rate_1995 AS unemployment_rate_increment
FROM one_nf_0 l
JOIN client__c ON l.loan__account_id = c.account__account_id
JOIN disp__d ON c.client_id = d.disp__client_id
JOIN district__d ON d.disp__district_id = di.district_id
WHERE l.loan__status = 'Running' AND l.loan__amount > 0;
```

### 24. Q149 (financial, challenging, retrieval) — **(a) (model generation error, wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: account__type

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
SELECT DISTINCT account__type
FROM one_nf_0
WHERE account__account_id NOT IN (
    SELECT loan__account_id
    FROM one_nf_0
)
AND district__average_salary BETWEEN 8000 AND 9000;
```

### 25. Q152 (financial, moderate, aggregate) — **(b)/(a) (fan out problem, need to apply distinct at key column, human able to get correct answer following the correct logic, strong, also suffer from model generation error, chose incorrect filter)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(district__number_crimes_1995)
FROM one_nf_0
WHERE district__number_inhabitants > 4000
AND account__date >= '1997-01-01'
GROUP BY district__district_id;
```

### 26. Q194 (financial, moderate, retrieval) — **(a) (model generation error, wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: c.client_id

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT DISTINCT c.client_id, strftime('%Y', 'now') - strftime('%Y', c.birth_date) AS age
FROM one_nf_0 c
JOIN one_nf_0 d ON c.district_id = d.district_id
JOIN one_nf_0 disp ON c.client_id = disp.client_id
JOIN one_nf_0 card ON disp.disposition_id = card.disposition_id
JOIN one_nf_0 loan ON c.client_id = loan.account_id
WHERE card.type = 'high_level' AND loan.status = 'A';
```

### 27. Q846 (formula_1, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__driver_ref_name 
FROM one_nf_0 
WHERE results__race_id = 20 AND status__status = 'Eliminated';
```

### 28. Q865 (formula_1, moderate, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT drivers__first_name, drivers__last_name
FROM one_nf_0
WHERE results__race_id = 592 AND results__position IS NOT NULL
ORDER BY drivers__date_of_birth ASC
LIMIT 1;
```

### 29. Q868 (formula_1, simple, retrieval) — **(b)/(a) (missing distinct, wrong column selected as well, weak)**

**Outcome:** `wrong_answer` · **Category (b):** Retrieval SELECT without DISTINCT on denormalised `one_nf_0` (duplicate rows)

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT circuits__location, circuits__latitude, circuits__longitude 
FROM one_nf_0 
WHERE races__name = 'Malaysian Grand Prix';
```

### 30. Q950 (formula_1, simple, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT DISTINCT constructors__name 
FROM one_nf_0 
WHERE results__race_id = 291 AND results__points = 0;
```

### 31. Q954 (formula_1, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'SUM']; predicted uses ['COUNT']

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    CAST(COUNT(DISTINCT CASE WHEN results__position IS NOT NULL THEN results__result_id END) AS REAL) * 100 / COUNT(DISTINCT results__result_id) AS race_completion_percentage
FROM 
    one_nf_0
WHERE 
    drivers__nationality = 'Japanese' 
    AND races__year BETWEEN 2007 AND 2009;
```

### 32. Q959 (formula_1, simple, retrieval) — **(b) (applied distinct in the wrong column, strong)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT DISTINCT results__fastest_lap_number
FROM one_nf_0
WHERE races__year = 2009 AND results__position = 1;
```

### 33. Q967 (formula_1, simple, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT drivers__driver_id)
FROM one_nf_0
WHERE drivers__nationality = 'Netherlandic'
ORDER BY drivers__date_of_birth DESC
LIMIT 3;
```

### 34. Q981 (formula_1, moderate, retrieval) — **(a) (model generation error, wrong table name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such table: drivers

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT 
    MIN(races__year) AS first_race_year,
    races__name AS race_name,
    races__date AS race_date,
    races__time AS race_time
FROM 
    one_nf_0
JOIN 
    drivers ON one_nf_0.results__driver_id = drivers.driver_id
WHERE 
    drivers.date_of_birth IS NOT NULL
GROUP BY 
    one_nf_0.results__driver_id
ORDER BY 
    drivers.date_of_birth ASC
LIMIT 1;
```

### 35. Q990 (formula_1, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT DISTINCT constructors__constructor_ref_name, constructors__url
FROM one_nf_0
WHERE races__year = 2009 AND races__name = 'Singapore Grand Prix' AND driverStandings__position = 1;
```

### 36. Q1003 (formula_1, moderate, aggregate) — **(a) (model generation error, wrong table name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: status_id

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT status_id) 
FROM one_nf_0 
WHERE driver_id = (
    SELECT driver_id 
    FROM one_nf_0 
    WHERE races__name = 'Canadian Grand Prix' AND status_id = 19 
    GROUP BY driver_id 
    ORDER BY COUNT(DISTINCT status_id) DESC 
    LIMIT 1
)
```

### 37. Q1361 (student_club, simple, aggregate) — **(a) (model generation error, wrong table name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: cost

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) 
FROM one_nf_0 
WHERE expense_description LIKE '%pizza%'
```

### 38. Q1381 (student_club, moderate, aggregate) — **(a) (wrong table name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such table: attendance

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL:**

```sql
SELECT DISTINCT member__first_name, member__last_name
FROM one_nf_0
WHERE member__member_id IN (
    SELECT member_id
    FROM attendance
    GROUP BY member_id
    HAVING COUNT(DISTINCT event_id) > 7
)
```

### 39. Q1394 (student_club, simple, aggregate) — **(a) (model generation error, wrong filter applied)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT member__member_id) 
FROM one_nf_0 
WHERE member__position = 'Student_Club' AND major__major_name = 'Physics Teaching';
```

### 40. Q1403 (student_club, moderate, retrieval) — **(a) (wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: cost

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT event__event_name
FROM one_nf_0
WHERE event__status = 'closed'
ORDER BY (SELECT SUM(cost) FROM one_nf_0 AS sub WHERE sub.event_id = one_nf_0.event_id) - budget__amount DESC
LIMIT 1;
```

### 41. Q1409 (student_club, simple, aggregate) — **(a) (wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: expense_id

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) 
FROM (
    SELECT DISTINCT expense_id, cost 
    FROM one_nf_0 
    WHERE expense_date = '2019-08-20'
)
```

### 42. Q1411 (student_club, simple, retrieval) — **(b) (apply distinct on wrong column, strong)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT expense__expense_description 
FROM one_nf_0 
WHERE member__first_name = 'Sacha' AND member__last_name = 'Harrison';
```

### 43. Q1422 (student_club, simple, retrieval) — **(a)/(b) (wrong column selected, apply distinct on wrong column, strong)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT budget__category 
FROM one_nf_0 
WHERE event__location = 'MU 215';
```

### 44. Q717 (superhero, simple, retrieval) — **(a) (wrong table name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such table: hero_power__hero_id

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT DISTINCT sp.power_name 
FROM one_nf_0 hp 
JOIN hero_power__hero_id hpw ON hp.superhero__id = hpw.hero_id 
JOIN superpower__id sp ON hpw.power_id = sp.id 
WHERE hp.superhero__superhero_name = '3-D Man';
```

### 45. Q723 (superhero, moderate, aggregate) — **(a) (wrong filter value, should be 'Blue' instead of 'blue')**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT superhero__id)
FROM one_nf_0
WHERE colour_eye__colour = 'blue'
AND superpower__power_name = 'Agility';
```

### 46. Q724 (superhero, challenging, retrieval) — **(a) (wrong filter value, should be 'Blue', 'Blond' instead of 'blue', 'blond')**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE colour_eye__colour = 'blue' AND colour_hair__colour = 'blond';
```

### 47. Q782 (superhero, moderate, retrieval) — **(a) (wrong filter value, should be 'Black' instead of 'black')**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT DISTINCT superhero__superhero_name 
FROM one_nf_0 
WHERE colour_eye__colour = 'black' AND colour_hair__colour = 'black';
```

### 48. Q791 (superhero, simple, aggregate) — **(a) (wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: height_cm

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) 
FROM (
    SELECT DISTINCT superhero__id, height_cm 
    FROM one_nf_0
)
```

### 49. Q1150 (thrombosis_prediction, moderate, aggregate) — **(c) (fan out problem due to denormalisation, cannot use distinct to resolve)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN Patient__sex = 'Female' AND strftime('%Y', Patient__birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Patient__ID) 
FROM one_nf_0;
```

### 50. Q1164 (thrombosis_prediction, moderate, aggregate) — **(a) (wrong filter logic, model generation error)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

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
FROM one_nf_0
WHERE Examination__examination_date LIKE '1997%'
  AND Examination__thrombosis_degree = 'most serious'
  AND Patient__sex = 'female';
```

### 51. Q1187 (thrombosis_prediction, moderate, retrieval) — **(a)/(c) (both wrong column applied error, and null propogation error due to denormalisation)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__ID
FROM one_nf_0
WHERE Laboratory__aspartate_aminotransferase > 30
  AND Laboratory__albumin < 4
  AND Examination__examination_date BETWEEN '1987-07-06' AND '1996-01-31';
```

### 52. Q1209 (thrombosis_prediction, moderate, retrieval) — **(a) (wrong filter value)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__diagnosis
FROM one_nf_0
WHERE Laboratory__alanine_aminotransferase > 40
ORDER BY Patient__birthday ASC;
```

### 53. Q1225 (thrombosis_prediction, moderate, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT DISTINCT Patient__sex, Patient__ID, Laboratory__total_bilirubin
FROM one_nf_0
WHERE Laboratory__total_bilirubin < 0.3 OR Laboratory__total_bilirubin > 1.2
GROUP BY Patient__sex, Patient__ID;
```

### 54. Q1229 (thrombosis_prediction, moderate, aggregate) — **(a) (wrong filter value)**

**Outcome:** `wrong_answer` · **Category (c):** COUNT(DISTINCT) present but multiset still differs — wrong entity key, filters, or residual 1NF vs 3NF semantics

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Laboratory__triglyceride > 150 AND 
      strftime('%Y', 'now') - strftime('%Y', Patient__birthday) > 50;
```

### 55. Q1265 (thrombosis_prediction, moderate, aggregate) — **(a) (wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: Examination__anti_ribonuclear_protein

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID) 
FROM one_nf_0 
WHERE Examination__anti_ribonuclear_protein = 'Normal' 
AND Patient__admission_type IS NOT NULL;
```

### 56. Q1275 (thrombosis_prediction, moderate, aggregate) — **(a) (wrong column name)**

**Outcome:** `error` · **Category (c):** Execution failure (unrecoverable at evaluation): no such column: Examination__anti_centromere

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT Patient__ID)
FROM one_nf_0
WHERE Examination__anti_centromere = 'normal'
  AND Examination__anti_ssb = 'normal'
  AND Patient__sex = 'male';
```

### 57. Q206 (toxicology, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE bond__bond_id = 'TR004_8_9';
```

### 58. Q212 (toxicology, challenging, aggregate) — **(a)/(c) (both model generation error - wrong logic, and unrecoverable fan out error from denomralisation)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT', 'MIN']; predicted uses ['COUNT']

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
FROM one_nf_0
WHERE molecule__label != 'carcinogenic'
GROUP BY atom_1__element
ORDER BY COUNT(DISTINCT atom_1__atom_id) ASC
LIMIT 1;
```

### 59. Q219 (toxicology, challenging, aggregate) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Different aggregate / metric: gold uses ['COUNT']; predicted uses ['COUNT', 'SUM']

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond__bond_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT molecule__molecule_id) 
FROM one_nf_0
WHERE molecule__label = 'carcinogenic';
```

### 60. Q268 (toxicology, challenging, retrieval) — **(a)**

**Outcome:** `wrong_answer` · **Category (a):** Wrong filters, columns, ordering, LIMIT, or retrieval logic; DISTINCT repair does not restore gold multiset

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom_1__element, atom_2__element 
FROM one_nf_0 
WHERE bond__bond_id = 'TR001_10_11';
```

