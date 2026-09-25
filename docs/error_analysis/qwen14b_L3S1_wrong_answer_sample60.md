# Qwen2.5-Coder-14B · L3·S1 wrong-answer sample (n=60)

**Source:** `results/full/qwen2.5-coder-14b-local__L3S1.csv` · **Population:** 387 failures / 397 questions · **Sample:** the same 60 questions as the L1·S3 sample (seed=42)

**Setup:** Gold SQL on 3NF SQLite; predicted SQL on the same 3NF database through TEMP VIEWs exposing S1 anonymous column names (`col_a`, `col_b`, …). Multiset execution comparison.

**Method:** every failure re-executed through the same rename views the experiment used; ambiguous cases verified against the gold result.

## Category definitions

| Category | Meaning |
| --- | --- |
| **wrong column name** | Predicted SQL references a column identifier that exists nowhere in the schema (execution error). |
| **wrong table name** | Predicted SQL references a table identifier that does not exist (execution error). |
| **join plan error** | All identifiers exist somewhere, but the join structure is wrong — a column attributed to a table that doesn't hold it, a misbound/nonexistent join key, or an unnecessary join that changes the aggregation grain. |
| **other logic error** | Identifiers and joins resolve; the semantics are wrong — wrong filter value/case, wrong threshold, wrong existing column/table choice, wrong aggregate or grain, tie/output-shape errors. |
| **weak duplication / recoverable artefact** | (Not applicable on the 3NF schema; none observed, as expected.) |
| **unrecoverable (denormalisation)** | (Not applicable on the 3NF schema; none observed, as expected.) |

## Summary (sample)

| Primary category | Count | % of sample |
| --- | --- | --- |
| other logic error | 37 | 61.7% |
| join plan error | 22 | 36.7% |
| wrong column name | 0 | 0.0% |
| wrong table name | 0 | 0.0% |
| unrecoverable (denormalisation) | 0 | 0.0% |
| weak duplication / recoverable artefact | 0 | 0.0% |
| correct | 1 | 1.7% |
| **Total** | 60 | 100.0% |

*With anonymous names the model can only guess which column is which, so nearly every query is a set of column-identity misbindings: filters land on IDs, aggregates on text columns, and join equations connect unrelated keys. The category split below is by the most consequential flaw (misbound join keys → join plan error; misbound filters/selects/aggregates → other logic error), but the root cause is uniform semantic opacity. Only Q717 survives, because its guessed `col_a`/`col_b` bindings happen to match the real id/name layout.*

---

## Sampled failures

### 1. Q32 (california_schools, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Guesses blind: filters `col_a` (CDSCode) = 66, orders by `col_b` (Academic Year), and selects `col_c` (County Code) — every binding wrong.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT col_c
FROM frpm
WHERE col_a = 66
ORDER BY col_b DESC
LIMIT 5;
```

### 2. Q41 (california_schools, simple, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins schools.col_a (CDSCode) to a satscores subquery keyed on col_b (rtype) — a misbound join — and filters col_c (NCESSchool) = 'Virtual'.

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
SELECT s.col_b AS school_name
FROM schools s
JOIN (
    SELECT col_c AS county, col_b AS school_id, AVG(col_d) AS avg_reading_score
    FROM satscores
    GROUP BY col_c, col_b
) ss ON s.col_a = ss.school_id
WHERE s.col_c = 'Virtual'
AND ss.avg_reading_score IN (
    SELECT AVG(col_d)
    FROM satscores
    WHERE col_c = ss.county
    GROUP BY col_b
    ORDER BY AVG(col_d) DESC
    LIMIT 5
)
ORDER BY ss.avg_reading_score DESC;
```

### 3. Q48 (california_schools, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Binds col_c (NCESSchool) as district type and col_b (NCESDist) as county on schools, so both CASE sums are zero.

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
    CAST(SUM(CASE WHEN col_c = 'Unified School District' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN col_c = 'Elementary School District' THEN 1 ELSE 0 END) AS ratio
FROM 
    schools
WHERE 
    col_b = 'Orange County';
```

### 4. Q79 (california_schools, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Groups by col_a (CDSCode) as the county and filters col_c (NCESSchool) = 'No' — all bindings guessed wrong.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_a, COUNT(*) AS school_count
FROM schools
WHERE col_b IN ('San Diego', 'Santa Barbara') AND col_c = 'No'
GROUP BY col_a
ORDER BY school_count DESC
LIMIT 1;
```

### 5. Q1476 (debit_card_specializing, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Answers from transactions_1k instead of yearmonth, binding col_e (CardID) as currency and col_g (ProductID) as consumption.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN col_e = 'CZK' THEN col_g ELSE 0 END) - 
    SUM(CASE WHEN col_e = 'EUR' THEN col_g ELSE 0 END) AS difference
FROM 
    transactions_1k
WHERE 
    col_a LIKE '2012%';
```

### 6. Q1493 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `error` · Nests SUM inside SUM (misuse-of-aggregate error — invalid SQL) atop an invented transactions↔yearmonth join.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SUM(col_e) > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT col_a) 
FROM transactions_1k 
JOIN yearmonth ON transactions_1k.col_g = yearmonth.col_a 
WHERE yearmonth.col_b = '2012' AND yearmonth.col_c = 'February' 
GROUP BY col_a;
```

### 7. Q1498 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · MAX over a guessed amount column on transactions with col_a (TransactionID) = '2012' — wrong table, bindings, and aggregate.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(col_e) 
FROM transactions_1k 
WHERE col_a = '2012';
```

### 8. Q1505 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Binds col_e (CardID) = 'euro' on transactions and HAVING-sums a guessed column as consumption.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT col_a) 
FROM transactions_1k 
WHERE col_e = 'euro' 
GROUP BY col_a, col_b 
HAVING SUM(col_c) > 1000;
```

### 9. Q1506 (debit_card_specializing, moderate, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins transactions to products and gasstations on misbound anonymous keys, so nothing survives the chain.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.col_b 
FROM transactions_1k t 
JOIN products p ON t.col_e = p.col_a 
JOIN gasstations g ON t.col_c = g.col_a 
WHERE g.col_d = 'Czech Republic';
```

### 10. Q1528 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Runs on transactions_1k with guessed bindings for segment and country (both land on non-semantic columns), so every filter misses.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN col_b = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage_premium
FROM 
    transactions_1k
WHERE 
    col_c = 'SVK';
```

### 11. Q1529 (debit_card_specializing, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Filters col_b (Date) = 38508 as the customer and col_c (Time) = '2012-08' as the month, summing col_e (a key column) — all misbound.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(col_e) AS total_spent
FROM transactions_1k
WHERE col_b = '38508' AND col_c = '2012-08';
```

### 12. Q1036 (european_football_2, challenging, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Joins Team.col_a (id) to TA.col_a (id) instead of team_api_id, and thresholds col_j (buildUpPlayPassingClass, a text class column).

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T.col_b 
FROM Team AS T 
JOIN Team_Attributes AS TA ON T.col_a = TA.col_a 
WHERE TA.col_j > (SELECT AVG(col_j) FROM Team_Attributes WHERE strftime('%Y', col_c) = '2012') 
AND strftime('%Y', TA.col_c) = '2012';
```

### 13. Q1037 (european_football_2, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Binds col_x (balance) as preferred_foot and col_c (player_api_id) as the birthday.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_x = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player_Attributes 
WHERE col_c BETWEEN '1987-01-01' AND '1992-12-31';
```

### 14. Q1039 (european_football_2, simple, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Joins PA.id = Player.id instead of player_api_id and filters Player.col_b (player_api_id) by the player's name; the AVG lands on balance.

**Gold SQL:**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL:**

```sql
SELECT AVG(col_x) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.col_a = Player.col_a 
WHERE Player.col_b = 'Ahmed Samir Farag';
```

### 15. Q1068 (european_football_2, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Averages col_a (id) with col_b (player_fifa_api_id) as the date and col_c (player_api_id) as height.

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
SELECT AVG(col_a) 
FROM Player_Attributes 
WHERE col_b BETWEEN 2010 AND 2015 AND col_c > 170;
```

### 16. Q1078 (european_football_2, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects col_b (player_api_id) instead of the name and orders by col_d (player_fifa_api_id), returning an API id.

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM Player 
WHERE col_c = 'Aaron Lennon' OR col_c = 'Abdelaziz Barrada' 
ORDER BY col_d DESC 
LIMIT 1;
```

### 17. Q1092 (european_football_2, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · The league join is right by luck, but it filters Match.col_a (id) BETWEEN calendar dates and returns L.col_b (country_id) as the name.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT L.col_b 
FROM League L 
JOIN Match M ON L.col_a = M.col_c 
WHERE M.col_a BETWEEN '2008-08-01' AND '2009-07-31' 
GROUP BY L.col_b 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### 18. Q1105 (european_football_2, moderate, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins PA.id = Player.id (wrong key), filters col_b (player_fifa_api_id) as the date, and selects col_ac (long_shots) as the work rate.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT col_ac 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.col_a = Player.col_a 
WHERE Player.col_b = 'Francesco Migliore' AND Player_Attributes.col_b = '2015/5/1';
```

### 19. Q1136 (european_football_2, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Thresholds col_ac (long_shots) as crossing and equates col_ah (penalties) = 'left' as the preferred foot.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE col_ac = (SELECT MAX(col_ac) FROM Player_Attributes) 
AND col_ah = 'left';
```

### 20. Q1147 (european_football_2, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Returns PA.col_a (id) ordered by col_ac (long_shots) — neither the player name nor overall rating.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT col_a FROM Player_Attributes ORDER BY col_ac DESC LIMIT 1
```

### 21. Q95 (financial, moderate, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Joins account.col_b (district_id) to client.col_a (client_id) — a misbound key — and orders by AVG of A13.

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT a.col_a 
FROM account a 
JOIN client c ON a.col_b = c.col_a 
JOIN district d ON c.col_d = d.col_a 
GROUP BY a.col_a 
ORDER BY c.col_c ASC, AVG(d.col_m) DESC 
LIMIT 1;
```

### 22. Q118 (financial, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · col_g happens to be status but 'A' is still the wrong value (gold 'C'), and col_c (date) < 100000 replaces the amount filter.

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN col_g = 'A' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage_running
FROM 
    loan
WHERE 
    col_c < 100000;
```

### 23. Q125 (financial, challenging, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Chains joins on loan_id = account_id and account_id = disp_id — misbound keys — and subtracts A16 − A15 (crime counts) as the unemployment change.

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT d.col_p - d.col_o AS unemployment_rate_increment
FROM loan l
JOIN account a ON l.col_a = a.col_a
JOIN disp d1 ON a.col_a = d1.col_a
JOIN client c ON d1.col_b = c.col_a
JOIN disp d2 ON c.col_a = d2.col_a
JOIN district d ON d2.col_c = d.col_a
WHERE l.col_g IS NULL AND l.col_e < 0;
```

### 24. Q149 (financial, challenging, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins account.col_b (district_id) to client.col_a (client_id) and NOT-INs the account frequency against loan ids; the A11 range is right by luck.

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
SELECT DISTINCT a.col_c 
FROM account a 
JOIN client c ON a.col_b = c.col_a 
JOIN district d ON c.col_d = d.col_a 
WHERE a.col_c NOT IN (SELECT l.col_b FROM loan l) 
AND d.col_k BETWEEN 8000 AND 9000;
```

### 25. Q152 (financial, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · AVG and the filter both bind col_j (A10, the urban-inhabitant ratio) and the subquery returns account.frequency as district ids.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(col_j) 
FROM district 
WHERE col_j > 4000 AND col_a IN (
    SELECT col_c 
    FROM account 
    WHERE strftime('%Y', col_d) >= '1997'
)
```

### 26. Q194 (financial, moderate, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins disp.col_a (disp_id) to client.col_a (client_id) and card.col_b (disp_id) to disp.col_b (client_id) — misbound keys — with the invented literal 'HC'.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.col_a, c.col_b 
FROM client c 
JOIN disp d ON c.col_a = d.col_a 
JOIN card ca ON d.col_b = ca.col_b 
WHERE ca.col_c = 'HC' AND c.col_c = 'A';
```

### 27. Q846 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Binds col_j (points) = 'Eliminated' and col_k (laps) = 1 on results and returns resultId.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT col_a 
FROM results 
WHERE col_b = 20 AND col_j = 'Eliminated' AND col_k = 1;
```

### 28. Q865 (formula_1, moderate, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins drivers.col_a (driverId) to results.col_b (raceId) and orders by col_d (the driver code).

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.col_b, d.col_c 
FROM drivers d 
JOIN results r ON d.col_a = r.col_b 
WHERE r.col_c = 592 
ORDER BY d.col_d DESC 
LIMIT 1;
```

### 29. Q868 (formula_1, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters col_b (circuitRef) by the race name and selects name/location instead of latitude/longitude.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT col_c, col_d FROM circuits WHERE col_b = 'Malaysian Grand Prix'
```

### 30. Q950 (formula_1, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · NOT-INs constructorId against constructorStandings.col_b (raceId) with col_d (points) > 0 — misbound set membership.

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT col_b 
FROM constructors 
WHERE col_a NOT IN (SELECT col_b FROM constructorStandings WHERE col_c = 291 AND col_d > 0)
```

### 31. Q954 (formula_1, challenging, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Swaps the join keys — results.col_b (raceId) onto driverId and results.col_c (driverId) onto raceId — and filters a guessed nationality column by 'Japan'.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN results.col_j = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS completion_percentage
FROM 
    results
JOIN 
    drivers ON results.col_b = drivers.col_a
JOIN 
    races ON results.col_c = races.col_a
WHERE 
    drivers.col_g = 'Japan' 
    AND races.col_d BETWEEN 2007 AND 2009;
```

### 32. Q959 (formula_1, simple, retrieval) — **join plan error**

**Outcome:** `error` · Joins drivers to driverStandings on raceId and references unqualified col_e, which exists in both joined tables — ambiguous-column execution error.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT MIN(col_e) AS fastest_lap_number
FROM results
JOIN drivers ON results.col_b = drivers.col_a
JOIN driverStandings ON drivers.col_a = driverStandings.col_b
WHERE driverStandings.col_c = 1 AND driverStandings.col_d = 2009;
```

### 33. Q967 (formula_1, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Binds col_c (the car number) = 'Netherlands' and orders by col_d (driver code).

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM drivers 
WHERE col_c = 'Netherlands' 
ORDER BY col_d ASC 
LIMIT 3;
```

### 34. Q981 (formula_1, moderate, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Swaps raceId/driverId join keys and takes MIN(col_c) (round) as the year; the date-of-birth binding lands on the car number.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MIN(r.col_c) AS race_date, 
    r.col_d AS race_time, 
    d.col_b AS driver_name, 
    s.col_a AS year
FROM 
    drivers d
JOIN 
    results res ON d.col_a = res.col_b
JOIN 
    races r ON res.col_c = r.col_a
JOIN 
    seasons s ON r.col_e = s.col_a
WHERE 
    d.col_c = (SELECT MIN(col_c) FROM drivers)
ORDER BY 
    r.col_c ASC
LIMIT 1;
```

### 35. Q990 (formula_1, challenging, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins constructorId to constructorStandings.col_b (raceId) and filters r.col_c (round) by the race name.

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT c.col_b, c.col_c 
FROM constructors c 
JOIN constructorStandings cs ON c.col_a = cs.col_b 
JOIN races r ON cs.col_d = r.col_a 
WHERE r.col_c = 'Singapore Grand Prix' AND r.col_b = 2009 AND cs.col_e = (SELECT MAX(col_e) FROM constructorStandings WHERE col_d = r.col_a);
```

### 36. Q1003 (formula_1, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses results.col_o (rank) as the status column and filters races.col_c (round) by 'Canadian Grand Prix'.

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
JOIN races ON results.col_b = races.col_a 
WHERE races.col_c = 'Canadian Grand Prix' 
AND results.col_o = (SELECT results.col_o 
                     FROM results 
                     JOIN races ON results.col_b = races.col_a 
                     WHERE races.col_c = 'Canadian Grand Prix' 
                     GROUP BY results.col_o 
                     ORDER BY COUNT(results.col_o) DESC 
                     LIMIT 1);
```

### 37. Q1361 (student_club, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · SUMs col_c (expense_date) as the cost; the description binding is right but 'pizza' ≠ stored 'Pizza'.

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL:**

```sql
SELECT SUM(col_c) FROM expense WHERE col_b = 'pizza'
```

### 38. Q1381 (student_club, moderate, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Joins member.col_a (member_id) to attendance.col_a (link_to_event) — a misbound key — so no groups survive.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL:**

```sql
SELECT m.col_b 
FROM member m 
JOIN attendance a ON m.col_a = a.col_a 
GROUP BY m.col_a 
HAVING COUNT(a.col_b) > 7;
```

### 39. Q1394 (student_club, simple, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Joins member.col_c (last_name) to major.col_a (major_id) and filters member.col_b (first_name) = 'Student_Club'.

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM member 
JOIN major ON member.col_c = major.col_a 
WHERE member.col_b = 'Student_Club' AND major.col_b = 'Physics Teaching';
```

### 40. Q1403 (student_club, moderate, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins event.col_a (event_id) to budget.col_a (budget_id) and orders by type − spent — misbound key and columns.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.col_b 
FROM event e 
JOIN budget b ON e.col_a = b.col_a 
WHERE e.col_c = 'closed' 
ORDER BY (e.col_d - b.col_c) DESC 
LIMIT 1;
```

### 41. Q1409 (student_club, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · SUMs col_c (expense_date) filtered on col_a (expense_id) = '8/20/2019' — both bindings wrong.

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(col_c) FROM expense WHERE col_a = '8/20/2019'
```

### 42. Q1411 (student_club, simple, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Joins expense.col_a (expense_id) to member.col_a (member_id) and puts the full name into col_b (first_name).

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT e.col_c 
FROM expense e 
JOIN member m ON e.col_a = m.col_a 
WHERE m.col_b = 'Sacha Harrison';
```

### 43. Q1422 (student_club, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects col_c (event_date) where col_d (type) = 'MU 215' — the location value lands on the type column.

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT col_c FROM event WHERE col_d = 'MU 215';
```

### 44. Q717 (superhero, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct — the guessed bindings (col_a = id/hero_id, col_b = name) happen to match the real key layout of the superhero–power chain.

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT sp.col_b 
FROM superhero sh 
JOIN hero_power hp ON sh.col_a = hp.col_a 
JOIN superpower sp ON hp.col_b = sp.col_a 
WHERE sh.col_b = '3-D Man';
```

### 45. Q723 (superhero, moderate, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Joins superhero.col_c (full_name) to colour.id — a misbound key — plus the lowercase 'blue' literal.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN colour ON superhero.col_c = colour.col_a 
JOIN hero_power ON superhero.col_a = hero_power.col_a 
JOIN superpower ON hero_power.col_b = superpower.col_a 
WHERE colour.col_b = 'blue' AND superpower.col_b = 'Agility';
```

### 46. Q724 (superhero, challenging, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Invents a superhero↔attribute join with 'blue eyes'/'blond hair' as attribute values — no such relationship or values exist.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT superhero.col_b 
FROM superhero 
JOIN attribute ON superhero.col_a = attribute.col_a 
WHERE attribute.col_b = 'blue eyes' 
INTERSECT 
SELECT superhero.col_b 
FROM superhero 
JOIN attribute ON superhero.col_a = attribute.col_a 
WHERE attribute.col_b = 'blond hair';
```

### 47. Q782 (superhero, moderate, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Binds superhero.col_c (full_name) and col_d (gender_id) as the two colour foreign keys, making both colour joins meaningless.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT superhero.col_b 
FROM superhero 
JOIN colour AS eye_colour ON superhero.col_c = eye_colour.col_a 
JOIN colour AS hair_colour ON superhero.col_d = hair_colour.col_a 
WHERE eye_colour.col_b = 'black' AND hair_colour.col_b = 'black';
```

### 48. Q791 (superhero, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · AVG(col_c) lands on full_name, averaging text to 0.0.

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(col_c) FROM superhero
```

### 49. Q1150 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · The structure and the SEX/Birthday bindings are right by luck — only the literal 'Female' (stored 'F') breaks it.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN col_c > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient 
WHERE col_b = 'Female';
```

### 50. Q1164 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Binds Examination.col_b (Examination Date) = 'thrombosis' and col_c (aCL IgG) as the date — value-to-column assignments are scrambled.

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
SELECT COUNT(*) 
FROM Patient 
WHERE col_a IN (
    SELECT col_a 
    FROM Examination 
    WHERE col_b = 'thrombosis' AND strftime('%Y', col_c) = '1997' 
    ORDER BY col_d DESC 
    LIMIT 10
) AND col_e = 'female';
```

### 51. Q1187 (thrombosis_prediction, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · The ID joins are right by luck, but it thresholds col_g (TP, total protein) as GPT and takes the date from Examination instead of Laboratory.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.col_a AS patient_id
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
JOIN Laboratory L ON P.col_a = L.col_a
WHERE E.col_b BETWEEN '1987-07-06' AND '1996-01-31'
AND L.col_g > 30
AND L.col_h < 4;
```

### 52. Q1209 (thrombosis_prediction, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Returns P.col_b (SEX) as the diagnosis and thresholds E.col_c (aCL IgG) > 40.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.col_b AS Diagnosis
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_c > 40
ORDER BY P.col_d ASC;
```

### 53. Q1225 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Groups by SEX and Birthday with E.col_j (RVVT) thresholds — wrong measure, wrong grouping, wrong output shape.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.col_b AS patient_name, P.col_c AS sex, COUNT(*) AS count
FROM Patient P
JOIN Examination E ON P.col_a = E.col_a
WHERE E.col_j NOT BETWEEN 5 AND 20
GROUP BY P.col_b, P.col_c;
```

### 54. Q1229 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Compares col_c (Birthday) > 50 as the age and invents subqueries matching 'Triglyceride'/'Normal TG Range' as stored values.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_c > 50 
AND col_a IN (
    SELECT col_a 
    FROM Examination 
    WHERE col_b = 'Triglyceride' 
    AND col_c > (SELECT col_c FROM Laboratory WHERE col_b = 'Normal TG Range')
);
```

### 55. Q1265 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Binds col_b (SEX) = 'normal' and col_c (Birthday) = 'admitted'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_b = 'normal' AND col_c = 'admitted';
```

### 56. Q1275 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Binds col_a (ID) = 'male' and treats GPT/LDH as test-name/result text columns with invented values.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE col_a = 'male' 
AND col_b IN (
    SELECT col_c 
    FROM Laboratory 
    WHERE col_d = 'anti-centromere' AND col_e = 'normal'
) 
AND col_c IN (
    SELECT col_c 
    FROM Laboratory 
    WHERE col_d = 'anti-SSB' AND col_e = 'normal'
);
```

### 57. Q206 (toxicology, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Stays on the bond table, puts the bond-id value on col_c (bond_type), and returns bond columns instead of atom elements.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT col_a, col_b, col_c 
FROM bond 
WHERE col_c = 'TR004_8_9';
```

### 58. Q212 (toxicology, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · NOT-INs atom_id against molecule ids and returns col_a (atom_id) as the element, with the invented 'carcinogenic' label.

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
SELECT col_a 
FROM atom 
WHERE col_a NOT IN (SELECT col_a FROM molecule WHERE col_b = 'carcinogenic') 
GROUP BY col_a 
ORDER BY COUNT(*) ASC 
LIMIT 1;
```

### 59. Q219 (toxicology, challenging, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Joins molecule.molecule_id to connected.col_a (atom_id) — a misbound key — with the invented 'triple' bond value.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond.col_c = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM molecule 
JOIN connected ON molecule.col_a = connected.col_a 
JOIN bond ON connected.col_b = bond.col_a;
```

### 60. Q268 (toxicology, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Stays on bond, filtering col_b (molecule_id) by a bond id and returning col_a (bond_id) instead of elements.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL:**

```sql
SELECT col_a FROM bond WHERE col_b = 'TR001_10_11'
```
