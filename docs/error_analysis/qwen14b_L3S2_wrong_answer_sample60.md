# Qwen2.5-Coder-14B · L3·S2 wrong-answer sample (n=60)

**Source:** `results/full/qwen2.5-coder-14b-local__L3S2.csv` · **Population:** 284 failures / 397 questions · **Sample:** the same 60 questions as the L1·S3 sample (seed=42)

**Setup:** Gold SQL on 3NF SQLite; predicted SQL on the same 3NF database through TEMP VIEWs exposing S2 abbreviated column names (`cust_id`, `avg_scr_read`, …). Multiset execution comparison.

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
| other logic error | 42 | 70.0% |
| join plan error | 6 | 10.0% |
| wrong column name | 0 | 0.0% |
| wrong table name | 0 | 0.0% |
| unrecoverable (denormalisation) | 0 | 0.0% |
| weak duplication / recoverable artefact | 0 | 0.0% |
| correct | 12 | 20.0% |
| **Total** | 60 | 100.0% |

*Abbreviated names land close to S3: 12 of the 60 are correct and most failures are the same value-literal/threshold/logic errors as L3·S3. Several S3 wrong-value errors self-correct at S2 (Q1150's 'F', Q1187's GPT/ALB bindings), while four attribution slips (`TA.season`, `r.year`, `T1.year`, `d.dist_nm`) show the model occasionally pinning a real abbreviated column to the wrong table.*

---

## Sampled failures

### 1. Q32 (california_schools, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Binds `edu_opt_type` (Educational Option Type) as the ownership code and the free-meal columns instead of the FRPM count/ratio — plausible-abbreviation confusion, all names real.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT 
    sch_nm, 
    pct_free_k12
FROM 
    frpm
WHERE 
    cds_cd IN (
        SELECT 
            cds_cd
        FROM 
            frpm
        WHERE 
            edu_opt_type = '66'
        ORDER BY 
            free_meal_k12 DESC
        LIMIT 5
    )
ORDER BY 
    free_meal_k12 DESC;
```

### 2. Q41 (california_schools, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters Virtual with an invalid literal (domain is F/N/P) and uses a max-per-county shape instead of gold's rank-top-5-per-county, returning nothing.

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
JOIN satscores ss ON s.cds_cd = ss.cds
WHERE s.Virtual = 'Yes'
AND (s.County, ss.avg_scr_read) IN (
    SELECT County, MAX(avg_scr_read)
    FROM schools s2
    JOIN satscores ss2 ON s2.cds_cd = ss2.cds
    WHERE s2.Virtual = 'Yes'
    AND s2.County = s.County
    GROUP BY County
    ORDER BY MAX(avg_scr_read) DESC
    LIMIT 5
)
ORDER BY ss.avg_scr_read DESC;
```

### 3. Q48 (california_schools, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · County 'Orange' is right at S2, but the frpm district_type approach still doesn't implement gold's Merged-status DOC split (3.67 vs 0.011).

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
    CAST(SUM(CASE WHEN dist_type = 'Unified School District' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN dist_type = 'Elementary School District' THEN 1 ELSE 0 END) AS ratio
FROM 
    frpm
WHERE 
    cnty_nm = 'Orange';
```

### 4. Q79 (california_schools, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses schools' County correctly but filters `Virtual = 'Yes'` (domain F/N/P), so nothing matches.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT County, COUNT(*) AS school_count
FROM schools
WHERE County IN ('San Diego', 'Santa Barbara') AND Virtual = 'Yes'
GROUP BY County
ORDER BY school_count DESC
LIMIT 1;
```

### 5. Q1476 (debit_card_specializing, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Applies `strftime('%Y', ...)` to 'YYYYMM' text (e.g. '201112') so the year filter matches nothing.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN curr = 'CZK' THEN consump ELSE 0 END) - 
    SUM(CASE WHEN curr = 'EUR' THEN consump ELSE 0 END) AS diff_consump
FROM 
    customers
JOIN 
    yearmonth ON customers.cust_id = yearmonth.cust_id
WHERE 
    strftime('%Y', yearmonth.date) = '2012';
```

### 6. Q1493 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses `date LIKE '2012-02-%'` / BETWEEN calendar dates against 'YYYYMM' text ('201202'), so nothing matches.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consump > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(cust_id) 
FROM yearmonth 
WHERE date BETWEEN '2012-02-01' AND '2012-02-29';
```

### 7. Q1498 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Computes MAX of a single row's consumption instead of gold's SUM per month with ORDER BY/LIMIT — an aggregate-shape error.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consump) FROM yearmonth WHERE date LIKE '2012%'
```

### 8. Q1505 (debit_card_specializing, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Correct structure but filters `currency = 'euro'` while the stored value is 'EUR', so the count is 0.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.cust_id) 
FROM customers c 
JOIN yearmonth y ON c.cust_id = y.cust_id 
WHERE c.curr = 'euro' AND y.consump > 1000;
```

### 9. Q1506 (debit_card_specializing, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Correct join chain but filters `country = 'Czech Republic'` while the stored value is 'CZE', so the result is empty.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.descr 
FROM products p 
JOIN transactions_1k t ON p.prod_id = t.prod_id 
JOIN gasstations g ON t.gs_id = g.gs_id 
WHERE g.ctry = 'Czech Republic';
```

### 10. Q1528 (debit_card_specializing, simple, aggregate) — **join plan error**

**Outcome:** `wrong_answer` · Needlessly joins transactions_1k, making the denominator transaction-fanned where gold counts station rows, plus the lowercase 'premium' literal.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN g.seg = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS premium_percentage
FROM 
    gasstations g
JOIN 
    transactions_1k t ON g.gs_id = t.gs_id
WHERE 
    g.ctry = 'SVK';
```

### 11. Q1529 (debit_card_specializing, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Sums `amt` (quantity, 148) where gold sums Amount * Price (88612.38); the month extraction itself is fine.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amt) AS total_spent, 
       SUM(CASE WHEN strftime('%Y-%m', date) = '2012-08' THEN amt ELSE 0 END) AS aug_2012_spent
FROM transactions_1k
WHERE cust_id = 38508;
```

### 12. Q1036 (european_football_2, challenging, aggregate) — **join plan error**

**Outcome:** `error` · References `TA.season` — Match's column — on Team_Attributes, so execution fails.

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T.team_nm 
FROM Team AS T 
JOIN Team_Attributes AS TA ON T.team_api_id = TA.team_api_id 
WHERE TA.season = 2012 AND TA.bu_pass > (SELECT AVG(bu_pass) FROM Team_Attributes WHERE season = 2012);
```

### 13. Q1037 (european_football_2, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Aggregates at attribute-snapshot grain (SUM/COUNT(*) per row, 24.57) where gold counts DISTINCT players (28.87).

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN pref_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.plr_api_id = Player.plr_api_id 
WHERE strftime('%Y', Player.bday) BETWEEN '1987' AND '1992';
```

### 14. Q1039 (european_football_2, simple, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL:**

```sql
SELECT AVG(T1.lng_shots) 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id 
WHERE T2.plr_nm = 'Ahmed Samir Farag';
```

### 15. Q1068 (european_football_2, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

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
SELECT AVG(ovr_rtg) 
FROM Player_Attributes 
WHERE date BETWEEN '2010-01-01' AND '2015-12-31' 
AND plr_api_id IN (SELECT plr_api_id FROM Player WHERE ht > 170);
```

### 16. Q1078 (european_football_2, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT plr_nm FROM Player WHERE plr_nm IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY bday ASC LIMIT 1
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

**Outcome:** `wrong_answer` · The date literal matches neither the stored '2015-05-01 00:00:00' format nor gold's LIKE prefix, so nothing matches.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.atk_wr FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.plr_api_id = T2.plr_api_id WHERE T2.plr_nm = 'Francesco Migliore' AND T1.date = '2015-05-01'
```

### 19. Q1136 (european_football_2, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · `cross`/`pref_foot` bind correctly, but an invented `atk_wr > 0` filter and row-level COUNT give 3 instead of gold's 2 players.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE cross = (SELECT MAX(cross) FROM Player_Attributes) 
AND pref_foot = 'left' 
AND atk_wr > 0;
```

### 20. Q1147 (european_football_2, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Ranks by `strength` instead of gold's maximum `overall_rating` — a wrong-column choice.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT plr_nm FROM Player WHERE plr_api_id = (SELECT plr_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### 21. Q95 (financial, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT a.acct_id
FROM account a
JOIN disp d ON a.acct_id = d.acct_id
JOIN client c ON d.client_id = c.client_id
JOIN district di ON c.dist_id = di.dist_id
ORDER BY c.birth_dt DESC, di.avg_sal ASC
LIMIT 1;
```

### 22. Q118 (financial, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Uses loan status 'A' where gold uses 'C' — a single wrong filter value (45.57 vs 46.89).

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

**Outcome:** `wrong_answer` · Computes the absolute unemployment difference without gold's `/ A12 * 100` normalisation, filters status 'A' instead of 'D', and routes district through client instead of the loan account.

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT d.unemp_96 - d.unemp_95 AS unemp_increment
FROM loan l
JOIN account a ON l.acct_id = a.acct_id
JOIN disp d1 ON a.acct_id = d1.acct_id
JOIN client c ON d1.client_id = c.client_id
JOIN district d ON c.dist_id = d.dist_id
WHERE l.status = 'A' AND l.amount > 0;
```

### 24. Q149 (financial, challenging, retrieval) — **join plan error**

**Outcome:** `error` · References `d.dist_nm` where alias d is disp, not district (aliased di) — an alias-attribution slip that kills execution.

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
SELECT DISTINCT d.dist_nm, c.type
FROM account a
JOIN disp d ON a.acct_id = d.acct_id
JOIN client cl ON d.client_id = cl.client_id
JOIN card c ON d.disp_id = c.disp_id
JOIN district di ON a.dist_id = di.dist_id
LEFT JOIN loan l ON a.acct_id = l.acct_id
WHERE l.loan_id IS NULL AND di.avg_sal BETWEEN 8000 AND 9000;
```

### 25. Q152 (financial, moderate, aggregate) — **other logic error + join plan error**

**Outcome:** `wrong_answer` · Filters `number_inhabitants > 4000` where gold filters A15 (1995 crimes) > 4000, and the join to account fans districts per account, making AVG account-weighted (2184.77 vs 9675.04).

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(d.crimes_95) 
FROM district d 
JOIN account a ON d.dist_id = a.dist_id 
WHERE d.num_inhab > 4000 AND strftime('%Y', a.date) >= '1997';
```

### 26. Q194 (financial, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Card literal 'HighLevel' (stored 'gold') plus an extra loan-status subquery not in gold empty the result.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.client_id, strftime('%Y', 'now') - strftime('%Y', c.birth_dt) AS age
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN card ca ON d.disp_id = ca.disp_id
WHERE ca.type = 'HighLevel' AND d.type = 'OWNER'
AND c.client_id IN (
    SELECT DISTINCT client_id
    FROM disp
    WHERE acct_id IN (
        SELECT acct_id
        FROM loan
        WHERE status = 'A'
    )
);
```

### 27. Q846 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Replaces gold's q1-ordering with a guessed blanket `status_id IN (2..20)` filter.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.drv_ref 
FROM drivers d 
JOIN results r ON d.drv_id = r.drv_id 
WHERE r.race_id = 20 AND r.position > 0 AND r.status_id IN (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20);
```

### 28. Q865 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Uses `position IS NOT NULL` as the finisher condition where gold requires `time IS NOT NULL`, selecting a different driver.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT fname, lname 
FROM drivers 
WHERE drv_id IN (
    SELECT drv_id 
    FROM results 
    WHERE race_id = 592 AND position IS NOT NULL
) 
ORDER BY dob ASC 
LIMIT 1;
```

### 29. Q868 (formula_1, simple, retrieval) — **join plan error**

**Outcome:** `wrong_answer` · Applies the race name 'Malaysian Grand Prix' to `circuits.name` without gold's join to races, so no circuit matches. (Also selects an extra location column.)

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT location, lat, lng FROM circuits WHERE name = 'Malaysian Grand Prix'
```

### 30. Q950 (formula_1, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Reads points from `constructorResults` instead of gold's `constructorStandings` — wrong existing table choice.

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT c.name 
FROM constructors c 
JOIN constructorResults cr ON c.ctor_id = cr.ctor_id 
WHERE cr.race_id = 291 AND cr.points = 0;
```

### 31. Q954 (formula_1, challenging, aggregate) — **join plan error**

**Outcome:** `error` · References `r.year` on results — races' column, and races is not joined — so execution fails.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN r.position IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(r.race_id)) AS completion_percentage
FROM 
    results r
JOIN 
    drivers d ON r.drv_id = d.drv_id
WHERE 
    d.nation = 'Japanese' 
    AND r.year BETWEEN 2007 AND 2009;
```

### 32. Q959 (formula_1, simple, retrieval) — **join plan error**

**Outcome:** `error` · References `T1.year` on results without joining races, so execution fails.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.fast_lap
FROM results AS T1
JOIN driverStandings AS T2 ON T1.drv_id = T2.drv_id AND T1.race_id = T2.race_id
WHERE T1.year = 2009 AND T2.position = 1;
```

### 33. Q967 (formula_1, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · 'Netherlands' where the stored nationality is 'Dutch', with the same count-of-3-youngest misreading.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM drivers 
WHERE nation = 'Netherlands' 
ORDER BY dob DESC 
LIMIT 3;
```

### 34. Q981 (formula_1, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects the driver with MIN(date_of_birth) (oldest) where gold wants the youngest, and that driver has no qualifying rows, so aggregates return NULLs.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(r.year), r.name, r.date, r.time
FROM races r
JOIN qualifying q ON r.race_id = q.race_id
JOIN drivers d ON q.drv_id = d.drv_id
WHERE d.dob = (SELECT MIN(dob) FROM drivers)
```

### 35. Q990 (formula_1, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Answers with the 2009 standings leader at Singapore (brawn) where gold wants constructors of drivers who finished the race (mclaren).

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT c.ctor_ref, c.url 
FROM constructors c 
JOIN constructorStandings cs ON c.ctor_id = cs.ctor_id 
JOIN races r ON cs.race_id = r.race_id 
WHERE r.name = 'Singapore Grand Prix' AND r.year = 2009 AND cs.position = 1;
```

### 36. Q1003 (formula_1, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
JOIN races ON results.race_id = races.race_id 
WHERE races.name = 'Canadian Grand Prix' 
AND results.status_id IN (SELECT status_id FROM status WHERE status LIKE '%Accident%') 
GROUP BY results.drv_id 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### 37. Q1361 (student_club, simple, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) AS total_pizza_cost
FROM expense
WHERE exp_desc LIKE '%pizza%';
```

### 38. Q1381 (student_club, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL:**

```sql
SELECT m.fname, m.lname 
FROM member m 
JOIN attendance a ON m.mbr_id = a.mbr_id 
GROUP BY m.mbr_id 
HAVING COUNT(a.evt_id) > 7;
```

### 39. Q1394 (student_club, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · The hallucinated `pos = 'Student_Club'` filter zeroes the count on top of gold's major-name condition.

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM member 
JOIN major ON member.maj_id = major.maj_id 
WHERE major.maj_nm = 'Physics Teaching' AND member.pos = 'Student_Club';
```

### 40. Q1403 (student_club, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters `status = 'closed'` (stored 'Closed') and reconstructs overspend from expense sums instead of gold's `remaining < 0`, returning nothing.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.evt_nm
FROM event e
JOIN budget b ON e.evt_id = b.evt_id
JOIN expense ex ON b.bgt_id = ex.bgt_id
WHERE e.status = 'closed'
GROUP BY e.evt_id
ORDER BY SUM(ex.cost) - b.amt DESC
LIMIT 1;
```

### 41. Q1409 (student_club, simple, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE exp_dt = '2019-08-20'
```

### 42. Q1411 (student_club, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT exp.exp_desc 
FROM expense exp 
JOIN member mem ON exp.mbr_id = mem.mbr_id 
WHERE mem.fname = 'Sacha' AND mem.lname = 'Harrison';
```

### 43. Q1422 (student_club, simple, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Selects budget `category` instead of gold's event `type` — a wrong-column semantic choice.

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.cat 
FROM budget b 
JOIN event e ON b.evt_id = e.evt_id 
WHERE e.loc = 'MU 215';
```

### 44. Q717 (superhero, simple, retrieval) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT p.pwr_nm 
FROM superhero h 
JOIN hero_power hp ON h.id = hp.hero_id 
JOIN superpower p ON hp.pwr_id = p.id 
WHERE h.hero_nm = '3-D Man';
```

### 45. Q723 (superhero, moderate, aggregate) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT h.id) 
FROM superhero h 
JOIN colour c ON h.eye_clr_id = c.id 
JOIN hero_power hp ON h.id = hp.hero_id 
JOIN superpower p ON hp.pwr_id = p.id 
WHERE c.color = 'Blue' AND p.pwr_nm = 'Agility';
```

### 46. Q724 (superhero, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters lowercase 'blue'/'blond' while the stored values are 'Blue'/'Blond', so the result is empty.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT hero_nm 
FROM superhero 
WHERE eye_clr_id = (SELECT id FROM colour WHERE color = 'blue') 
AND hair_clr_id = (SELECT id FROM colour WHERE color = 'blond');
```

### 47. Q782 (superhero, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Filters lowercase 'black' while the stored value is 'Black', so the result is empty.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT hero_nm 
FROM superhero 
WHERE eye_clr_id = (SELECT id FROM colour WHERE color = 'black') 
AND hair_clr_id = (SELECT id FROM colour WHERE color = 'black');
```

### 48. Q791 (superhero, simple, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Omits gold's `height_cm > 0` guard, so zero heights drag the average down (267.75 vs 345.04).

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(ht_cm) FROM superhero
```

### 49. Q1150 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · 'F' is right at S2; the error is structural — the denominator is all patients instead of females only (77.7 vs 94.0).

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'F' AND strftime('%Y', bday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient;
```

### 50. Q1164 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · `thrombosis = 'most serious'` — the degree is numeric (gold: `= 1`) — so the count is 0.

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
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE strftime('%Y', e.exam_dt) = '1997' AND p.sex = 'F' AND e.thrombosis = 'most serious';
```

### 51. Q1187 (thrombosis_prediction, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · GPT and ALB bind correctly at S2; the remaining error is taking the date from Examination instead of Laboratory (2 of 61 IDs).

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
WHERE E.exam_dt BETWEEN '1987-07-06' AND '1996-01-31' 
AND L.gpt > 30 
AND L.alb < 4;
```

### 52. Q1209 (thrombosis_prediction, moderate, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Threshold `> 40` where gold requires `> 60` and no DISTINCT — the GPT column itself is right at S2.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.diag 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.gpt > 40 
ORDER BY P.bday ASC;
```

### 53. Q1225 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Counts patients per sex with wrong thresholds where gold GROUP_CONCATs the DISTINCT patient IDs with `T-BIL >= 2.0` — wrong aggregate and thresholds.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.sex, COUNT(*) AS patient_count
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.t_bil < 0.3 OR L.t_bil > 1.2
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
WHERE L.tg > 150 AND strftime('%Y', 'now') - strftime('%Y', P.bday) > 50;
```

### 55. Q1265 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · `rnp = 'normal'` and `admission = 'yes'` — stored values are 'negative'/'0' and '+'/'-'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.rnp = 'normal' AND P.admission = 'yes';
```

### 56. Q1275 (thrombosis_prediction, moderate, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Invented values 'normal' and 'male' where the stored values are 'negative'/'0' and sex 'M'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.centromea = 'normal' AND L.ssb = 'normal' AND P.sex = 'male';
```

### 57. Q206 (toxicology, challenging, retrieval) — **other logic error**

**Outcome:** `wrong_answer` · Puts the bond-id value on the molecule label and joins at molecule level instead of gold's connected.bond_id path.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.elem 
FROM atom a 
JOIN molecule m ON a.mol_id = m.mol_id 
JOIN bond b ON a.mol_id = b.mol_id 
WHERE m.lbl = 'TR004_8_9';
```

### 58. Q212 (toxicology, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Excludes molecules labelled 'carcinogenic' (domain is '+'/'-') so all atoms qualify, and LIMIT 1 misses gold's three-way tie.

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
SELECT elem 
FROM atom 
WHERE mol_id NOT IN (SELECT mol_id FROM molecule WHERE lbl = 'carcinogenic') 
GROUP BY elem 
ORDER BY COUNT(*) ASC 
LIMIT 1;
```

### 59. Q219 (toxicology, challenging, aggregate) — **other logic error**

**Outcome:** `wrong_answer` · Invented literals 'triple' and 'carcinogenic' (stored '#' and '+'), so the result is NULL.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN b.bnd_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM bond b 
JOIN molecule m ON b.mol_id = m.mol_id 
WHERE m.lbl = 'carcinogenic';
```

### 60. Q268 (toxicology, challenging, retrieval) — **correct**

**Outcome:** `correct` · Correct under this condition.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.elem 
FROM atom a 
JOIN connected c ON a.atm_id = c.atm_id 
WHERE c.bnd_id = 'TR001_10_11';
```
