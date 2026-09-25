# Qwen2.5-Coder-14B (3-shot) · L3·S3 — hand-classified failures (n=250)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. This is the 3-shot (few-shot) prompting condition for qwen2.5-coder-14b-local at structural level L3 (native 3NF) / semantic level S3 (descriptive snake_case column names); the few-shot condition reserves 27 questions for the in-context example pool, so the failure/total counts here (n=250 failures / 370 total rows) don't match the zero-shot L3S3 pass (397 total rows). Predicted SQL uses S3 column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. Grouped by database, sorted by question id.

| Category | Meaning |
|---|---|
| Invalid SQL | predicted SQL fails to execute |
| Schema linking | real table/column, but the wrong one for the question |
| JOIN errors | join structure itself is wrong |
| GROUP BY errors | mismatch in the `GROUP BY` clause specifically |
| Nesting problem | missing/extra subquery, CTE, window function, or set operation |
| Predicate error | filter condition wrong (value or transformation), right column/table |
| Other | wrong aggregate function/scaling, DISTINCT/DESC, or residual |

---

## california_schools (24 failures)

### Q11 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** drops the schools table entirely (so the 'School is not NULL' filter can't be checked); also compares only enrollment_k12 instead of gold's Enrollment(K-12)+Enrollment(Ages 5-17) sum

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT county_district_school_code
FROM frpm
WHERE enrollment_k12 > 500;
```

### Q17 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the CharterNum IS NOT NULL filter gold has (join/columns otherwise all correct renames)

**Gold SQL:**

```sql
SELECT CharterNum, AvgScrWrite, 
RANK() OVER (ORDER BY AvgScrWrite DESC) AS WritingScoreRank 
FROM schools AS T1  INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds 
WHERE T2.AvgScrWrite > 499 AND CharterNum is not null AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT 
    T2.charter_number, 
    T1.average_score_writing, 
    RANK() OVER (ORDER BY T1.average_score_writing DESC) AS rank
FROM 
    satscores AS T1
JOIN 
    schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T1.average_score_writing > 499
    AND T1.record_type = 'S';
```

### Q23 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an ABS() around the enrollment difference that gold doesn't have; also drops the 'School is not NULL' filter

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT T2.School, T2.Street, T2.City, T2.State, T2.Zip 
FROM frpm AS T1 
JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE ABS(T1.enrollment_k12 - T1.enrollment_ages_5_17) > 30;
```

### Q24 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the rtype='S' filter gold has; also substitutes the precomputed percent_eligible_free_k12 field for gold's manual CAST-based ratio

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.school_name
FROM frpm AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.percent_eligible_free_k12 > 0.1
  AND T2.number_scores_1500_or_above > 0;
```

### Q25 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references frpm.school_name (schools has no such column; schools' own field is 'School', unrenamed) without frpm being joined at all; also collapses gold's GROUP BY/HAVING AVG(AvgScrMath)>400 into a plain WHERE filter with no GROUP BY

**Gold SQL:**

```sql
SELECT s.`sname`,
       sc.`FundingType`
FROM satscores AS s
JOIN schools  AS sc
  ON s.`cds` = sc.`CDSCode`
WHERE sc.`District` LIKE 'Riverside%'   AND s.rtype = 'S'
GROUP BY s.`sname`, sc.`FundingType`
HAVING AVG(s.`AvgScrMath`) > 400;
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.school_name, T2.funding_type
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.County = 'Riverside'
  AND T1.average_score_math > 400
  AND T1.record_type = 'S';
```

### Q27 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references frpm.school_name (schools has no such column) without frpm being joined; also uses INNER JOIN where gold's LEFT JOIN preserves schools with no satscores record

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT T2.school_name, T1.average_score_writing, T2.phone
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE (T2.open_date IS NOT NULL AND strftime('%Y', T2.open_date) > '1991')
   OR (T2.closed_date IS NOT NULL AND strftime('%Y', T2.closed_date) < '2000');
```

### Q31 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** drops the schools table entirely (so the 'school is not null' filter can't be checked); also uses LIMIT 9,1 (1 row) instead of gold's LIMIT 9,2 (2 rows)

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT `percent_eligible_free_k12`
FROM `frpm`
ORDER BY `enrollment_k12` DESC
LIMIT 9, 1;
```

### Q32 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references school_ownership_code (schools.SOC) without joining schools at all -- frpm alone is queried

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT `percent_eligible_free_or_reduced_price_meal_k12`
FROM `frpm`
WHERE `school_ownership_code` = 66
ORDER BY `free_or_reduced_price_meal_count_k12` DESC
LIMIT 5;
```

### Q36 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the rtype='S' filter gold has (join/columns otherwise all correct renames)

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
SELECT T2.admin_first_name_1, T2.admin_last_name_1, T2.admin_first_name_2, T2.admin_last_name_2, T2.admin_first_name_3, T2.admin_last_name_3
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
ORDER BY T1.number_scores_1500_or_above DESC
LIMIT 1;
```

### Q37 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's subquery-based exact MIN-ratio match, replacing it with ORDER BY ratio ASC LIMIT 1; also drops the NumTstTakr>0/NOT NULL guard filters, so NULL ratios (which SQLite sorts first in ASC order) could incorrectly win the ordering

**Gold SQL:**

```sql
SELECT s.Street, s.City, s.State, s.Zip 
FROM schools s JOIN satscores sat ON s.CDSCode = sat.cds 
WHERE sat.NumTstTakr > 0 AND sat.NumGE1500 IS NOT NULL AND sat.NumTstTakr IS NOT NULL  AND rtype = 'S'
AND CAST(sat.NumGE1500 AS FLOAT) / CAST(sat.NumTstTakr AS FLOAT) =
 (SELECT MIN(CAST(NumGE1500 AS FLOAT) / CAST(NumTstTakr AS FLOAT)) 
 FROM satscores WHERE NumTstTakr > 0 AND NumGE1500 IS NOT NULL AND NumTstTakr IS NOT NULL AND rtype = 'S' )
```

**Predicted SQL:**

```sql
SELECT T2.Street, T2.City, T2.State, T2.Zip
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.record_type = 'S'
ORDER BY CAST(T1.number_scores_1500_or_above AS REAL) / T1.number_test_takers ASC
LIMIT 1;
```

### Q40 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops both the rtype='S' and AvgScrRead IS NOT NULL filters gold has

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.Phone
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.District = 'Fresno Unified'
ORDER BY T1.average_score_reading ASC
LIMIT 1;
```

### Q41 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses Virtual='T' instead of gold's Virtual='F' (the opposite/wrong value) in both the outer query and the nested subquery

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
SELECT T2.School, T2.County, T1.average_score_reading
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.Virtual = 'T'
AND T1.record_type = 'S'
AND (T1.average_score_reading, T2.County) IN (
    SELECT average_score_reading, County
    FROM (
        SELECT average_score_reading, County, 
               ROW_NUMBER() OVER (PARTITION BY County ORDER BY average_score_reading DESC) as rn
        FROM satscores AS T3
        JOIN schools AS T4 ON T3.county_district_school_code = T4.county_district_school_code
        WHERE T4.Virtual = 'T'
        AND T3.record_type = 'S'
    )
    WHERE rn <= 5
)
ORDER BY T2.County, T1.average_score_reading DESC;
```

### Q46 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes educational_option_name for gold's district_ownership_code(DOC)=31 -- two different real schools columns

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.School, T2.State, T1.enrollment_k12
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.educational_option_name = 'State Special'
ORDER BY T1.enrollment_k12 DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*)) nested aggregate misuse (matches the canonical AVG(COUNT(*)) example exactly); also invents a District='Elementary School District' filter not in gold and drops the /12 scaling

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) AS avg_monthly_openings
FROM (
    SELECT open_date
    FROM schools
    WHERE County = 'Alameda' AND District = 'Elementary School District' AND strftime('%Y', open_date) = '1980'
    GROUP BY strftime('%Y-%m', open_date)
) AS monthly_openings;
```

### Q48 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T2.district_type where T2=schools (no such column); the value belongs to the already-joined frpm aliased T1; also substitutes a district_type Unified/Elementary CASE ratio for gold's DOC/StatusType='Merged' two-subquery COUNT ratio, and 'Orange County' for gold's actual stored value 'Orange'

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
    CAST(COUNT(CASE WHEN T2.district_type = 'Unified School District' THEN 1 END) AS REAL) /
    COUNT(CASE WHEN T2.district_type = 'Elementary School District' THEN 1 END) AS ratio
FROM 
    frpm AS T1
JOIN 
    schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T2.County = 'Orange County'
    AND T2.district_ownership_type = 'Merged';
```

### Q50 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the AvgScrMath IS NOT NULL filter gold has (join/columns otherwise all correct renames)

**Gold SQL:**

```sql
SELECT s.`MailStreet`   AS postal_street_address,
       s.`School`
FROM   `satscores` AS ss
JOIN   `schools`   AS s
       ON ss.`cds` = s.`CDSCode`
WHERE  ss.`rtype` = 'S'
  AND  ss.`AvgScrMath` IS NOT NULL
ORDER BY ss.`AvgScrMath` DESC
LIMIT 6, 1;
```

**Predicted SQL:**

```sql
SELECT T2.School, T2.mailing_street
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.record_type = 'S'
ORDER BY T1.average_score_math DESC
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** drops the schools table entirely (counts frpm rows via COUNT(*) instead of gold's COUNT(T2.School) from the joined schools table); also compares is_charter_school to the string 'N' instead of gold's numeric Charter=0

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
WHERE county_name = 'Los Angeles' 
  AND is_charter_school = 'N' 
  AND percent_eligible_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** substitutes frpm.school_name='State Special School' (referenced via the wrong alias s=schools) for gold's schools.EdOpsCode='SSS' -- a fundamentally different real column and a fabricated literal value

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT SUM(f.enrollment_ages_5_17)
FROM frpm AS f
JOIN schools AS s ON f.county_district_school_code = s.county_district_school_code
WHERE s.school_name = 'State Special School'
  AND s.City = 'Fremont'
  AND f.academic_year = '2014-2015';
```

### Q77 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T2.school_name where T2=schools (no such column; belongs to the already-joined frpm aliased T1); also substitutes schools.grade_span_offered (GSoffered) for gold's schools.grade_span_served (GSserved), two different real columns

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT T2.school_name, T1.percent_eligible_free_ages_5_17
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.County = 'Los Angeles' AND T2.grade_span_offered = 'Kindergarten to 9th grade';
```

### Q79 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references frpm.county_name (schools has no such column; schools' own field is 'County', unrenamed) without frpm being joined; also substitutes status_type='Closed' for gold's Virtual='F', a different real column entirely

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT county_name, COUNT(*) AS num_schools
FROM schools
WHERE county_name IN ('San Diego', 'Santa Barbara') AND status_type = 'Closed'
GROUP BY county_name
ORDER BY num_schools DESC
LIMIT 1;
```

### Q82 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T2.grade_span_offered where T2=frpm (no such column; belongs to the already-joined schools aliased T1); also drops the ABS() around longitude, reversing which extreme is picked

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.grade_span_offered 
FROM schools AS T1 
JOIN frpm AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
ORDER BY T1.Longitude DESC 
LIMIT 1;
```

### Q83 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T1.grade_span_offered where T1=frpm (no such column; belongs to the already-joined schools aliased T2); also substitutes frpm.educational_option_type for gold's frpm.'NSLP Provision Status', a different real frpm column

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT T2.City, COUNT(DISTINCT T2.county_district_school_code) AS school_count
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.grade_span_offered = 'Kindergarten to 8th grade' AND T1.educational_option_type = 'Multiple Provision Types'
GROUP BY T2.City;
```

### Q85 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** precomputed percent_eligible_free_k12 substituted for gold's manually-scaled Free Meal Count K12*100/Enrollment K12 ratio; WHERE filter itself matches gold exactly

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT f.percent_eligible_free_k12, f.district_code
FROM frpm AS f
JOIN schools AS s ON f.county_district_school_code = s.county_district_school_code
WHERE s.admin_first_name_1 = 'Alusine';
```

### Q87 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's DOC=54 AND SOC=62 filters with an instruction_level_name IN (...) condition, a completely different real column; also selects an extra admin_email_3 column beyond gold's AdmEmail1/AdmEmail2

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT 
    admin_email_1, 
    admin_email_2, 
    admin_email_3 
FROM 
    schools 
WHERE 
    County = 'San Bernardino' 
    AND City = 'San Bernardino' 
    AND open_date BETWEEN '2009-01-01' AND '2010-12-31' 
    AND instruction_level_name IN ('Intermediate/Middle School', 'Unified School');
```

---

## debit_card_specializing (19 failures)

### Q1473 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's per-customer SUM derived table (grouped by CustomerID, /12 monthly average) collapsed to a flat AVG(consumption) over joined rows with no per-customer pre-aggregation and no /12 scaling

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consumption) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T1.segment = 'SME' AND SUBSTR(T2.date, 1, 4) = '2013'
```

### Q1480 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** MAX(SUM(T2.consumption)) nested-aggregate misuse; also groups by raw date instead of gold's month-only SUBSTR

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.date, MAX(SUM(T2.consumption)) 
FROM customers AS T1 
INNER JOIN yearmonth AS T2 
ON T1.customer_id = T2.customer_id 
WHERE T1.segment = 'SME' AND SUBSTR(T2.date, 1, 4) = '2013' 
GROUP BY T2.date 
ORDER BY SUM(T2.consumption) DESC 
LIMIT 1
```

### Q1481 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's 4-CTE segment/customer chain into unrelated nested scalar subqueries that don't reproduce the per-segment-minimum-customer logic

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT AVG(consumption) 
     FROM customers AS T1 
     INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id 
     WHERE T1.currency = 'CZK' AND SUBSTR(T2.date, 1, 4) = '2013' AND T1.segment = 'SME') -
    (SELECT AVG(consumption) 
     FROM customers AS T1 
     INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id 
     WHERE T1.currency = 'CZK' AND SUBSTR(T2.date, 1, 4) = '2013' AND T1.segment = 'LAM') AS diff_SME_LAM,
    
    (SELECT AVG(consumption) 
     FROM customers AS T1 
     INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id 
     WHERE T1.currency = 'CZK' AND SUBSTR(T2.date, 1, 4) = '2013' AND T1.segment = 'LAM') -
    (SELECT AVG(consumption) 
     FROM customers AS T1 
     INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id 
     WHERE T1.currency = 'CZK' AND SUBSTR(T2.date, 1, 4) = '2013' AND T1.segment = 'KAM') AS diff_LAM_KAM,
    
    (SELECT AVG(consumption) 
     FROM customers AS T1 
     INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id 
     WHERE T1.currency = 'CZK' AND SUBSTR(T2.date, 1, 4) = '2013' AND T1.segment = 'KAM') -
    (SELECT AVG(consumption) 
     FROM customers AS T1 
     INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id 
     WHERE T1.currency = 'CZK' AND SUBSTR(T2.date, 1, 4) = '2013' AND T1.segment = 'SME') AS diff_KAM_SME
```

### Q1482 (challenging, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** adds GROUP BY T1.segment producing 3 rows where gold's flat (ungrouped) query returns 1 row with 3 columns

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    T1.segment, 
    ((SUM(CASE WHEN SUBSTR(T2.date, 1, 4) = '2013' THEN T2.consumption ELSE 0 END) - SUM(CASE WHEN SUBSTR(T2.date, 1, 4) = '2012' THEN T2.consumption ELSE 0 END)) * 100.0 / SUM(CASE WHEN SUBSTR(T2.date, 1, 4) = '2012' THEN T2.consumption ELSE 0 END)) AS percentage_change
FROM 
    customers AS T1 
INNER JOIN 
    yearmonth AS T2 
ON 
    T1.customer_id = T2.customer_id 
WHERE 
    T1.currency = 'EUR' 
    AND T1.segment IN ('SME', 'LAM', 'KAM') 
GROUP BY 
    T1.segment
```

### Q1483 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN uses ISO-hyphenated date bounds ('2013-08-01'/'2013-11-30') against Date stored as plain 'YYYYMM' text, so none of customer 6's monthly rows satisfy the range

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(consumption) FROM yearmonth WHERE customer_id = 6 AND date BETWEEN '2013-08-01' AND '2013-11-30'
```

### Q1484 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic'/'Slovakia' used instead of the stored codes 'CZE'/'SVK'; also 'discount' case differs from gold's 'Discount'

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT (SELECT COUNT(*) FROM gasstations WHERE country = 'Czech Republic' AND segment = 'discount') - (SELECT COUNT(*) FROM gasstations WHERE country = 'Slovakia' AND segment = 'discount') AS difference
```

### Q1490 (moderate, aggregate) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** uses INNER JOIN where gold's LEFT JOIN preserves customers with no yearmonth rows; also drops the COUNT(DISTINCT...) per-customer dedup

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T2.consumption > 46.73, 1, 0)) AS FLOAT) * 100 / COUNT(*) AS percentage 
FROM customers AS T1 
INNER JOIN yearmonth AS T2 
ON T1.customer_id = T2.customer_id 
WHERE T1.segment = 'LAM'
```

### Q1493 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** SUBSTR(date,1,7)='2012-02' introduces a transformation/format gold's plain Date='201202' equality doesn't need, and never matches the 6-char 'YYYYMM' stored value; also joins an unneeded customers table

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T2.consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(*) AS percentage 
FROM customers AS T1 
INNER JOIN yearmonth AS T2 
ON T1.customer_id = T2.customer_id 
WHERE SUBSTR(T2.date, 1, 7) = '2012-02'
```

### Q1498 (simple, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** missing GROUP BY entirely (gold groups by month via SUBSTR(Date,5,2)); also uses MAX instead of SUM, returning the single largest reading instead of the peak month's total

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) FROM yearmonth WHERE SUBSTR(date, 1, 4) = '2012'
```

### Q1506 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic' used instead of the stored code 'CZE'

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.gas_station_id = T2.gas_station_id INNER JOIN products AS T3 ON T1.product_id = T3.product_id WHERE T2.country = 'Czech Republic'
```

### Q1509 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic' used instead of the stored code 'CZE'

**Gold SQL:**

```sql
SELECT COUNT(t.`TransactionID`)
FROM `transactions_1k` AS t
JOIN `gasstations` AS g
  ON t.`GasStationID` = g.`GasStationID`
WHERE g.`Country` = 'CZE'
  AND DATE(t.`Date`) > '2012-01-01';
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM transactions_1k AS T1 
INNER JOIN gasstations AS T2 ON T1.gas_station_id = T2.gas_station_id 
WHERE T2.country = 'Czech Republic' AND T1.date > '2012-01-01'
```

### Q1514 (simple, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** predicted omits DISTINCT and the (redundant, non-filtering) gasstations join gold itself never references any column of; duplicate currency values would appear if multiple transactions share this exact date/time

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT T1.currency FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE T2.date = '2012-08-24' AND T2.time = '16:25:00'
```

### Q1524 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares transactions_1k.amount to 548.4 instead of gold's transactions_1k.price -- both real columns, wrong one used; join/tables otherwise match gold

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT T1.country FROM gasstations AS T1 INNER JOIN transactions_1k AS T2 ON T1.gas_station_id = T2.gas_station_id WHERE T2.amount = 548.4 AND T2.date = '2012-08-24'
```

### Q1525 (simple, aggregate) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** uses SUM(CASE)/COUNT(*) over raw transaction rows instead of gold's COUNT(DISTINCT CustomerID), double-counting customers with multiple matching transactions

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T1.currency = 'EUR', 1, 0)) AS FLOAT) * 100 / COUNT(*) AS percentage 
FROM customers AS T1 
INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id 
WHERE T2.date = '2012-08-25'
```

### Q1526 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** subquery uses transactions_1k.amount=634.8 instead of gold's price=634.8 (different real column) to identify the customer; also a date-format SUBSTR(date,1,7)='2012-08' mismatch zeroes out the yearmonth sums

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN SUBSTR(T2.date, 1, 7) = '2012-08' THEN T2.consumption ELSE 0 END) - 
     SUM(CASE WHEN SUBSTR(T2.date, 1, 7) = '2013-08' THEN T2.consumption ELSE 0 END)) / 
    SUM(CASE WHEN SUBSTR(T2.date, 1, 7) = '2012-08' THEN T2.consumption ELSE 0 END) AS decrease_rate
FROM 
    customers AS T1
INNER JOIN 
    transactions_1k AS T3 ON T1.customer_id = T3.customer_id
INNER JOIN 
    yearmonth AS T2 ON T1.customer_id = T2.customer_id
WHERE 
    T3.amount = 634.8 AND T3.date = '2012-08-25'
```

### Q1528 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'premium' case differs from gold's 'Premium'

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(segment = 'premium', 1, 0)) AS FLOAT) * 100 / COUNT(*) AS percentage 
FROM gasstations 
WHERE country = 'SVK'
```

### Q1529 (moderate, aggregate) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** computes SUM(amount) instead of gold's SUM(amount*price), missing the price multiplication in both the total and August-2012 subtotal

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT 
    SUM(amount) AS total_spent, 
    SUM(IIF(SUBSTR(date, 1, 7) = '2012-08', amount, 0)) AS august_spent 
FROM 
    transactions_1k 
WHERE 
    customer_id = '38508'
```

### Q1531 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references T1.currency on transactions_1k (no such column) instead of joining customers, which holds Currency; also ranks by SUM(amount) instead of gold's SUM(amount*price) and uses AVG(price) instead of a weighted average

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT T1.customer_id, AVG(T1.price) AS avg_price_per_item, T1.currency 
FROM transactions_1k AS T1 
GROUP BY T1.customer_id, T1.currency 
ORDER BY SUM(T1.amount) DESC 
LIMIT 1
```

### Q1533 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restructures gold's Price/Amount > 29 ratio into a plain Price > 29 comparison; also the date filter LIKE '2012-08%' never matches yearmonth.Date's plain 'YYYYMM' stored format; adds an extra customer_id SELECT column

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT T1.customer_id, T2.consumption 
FROM transactions_1k AS T1 
INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id 
WHERE T1.product_id = 5 AND T1.price > 29.00 AND T2.date LIKE '2012-08%'
```

---

## european_football_2 (27 failures)

### Q1031 (challenging, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds an extra player_name column to the SELECT list that breaks gold's DISTINCT dedup over the age expression alone -- the age computation itself is equivalent to gold's

**Gold SQL:**

```sql
SELECT DISTINCT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T2.Birthday) - CASE
    WHEN strftime('%m-%d','now') < strftime('%m-%d', Birthday) THEN 1
    ELSE 0
  END AS age FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id 
WHERE STRFTIME('%Y',t1."date") >= '2013' AND STRFTIME('%Y',t1."date") <= '2015' AND t1.sprint_speed >= 97
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.player_name, strftime('%Y', 'now') - strftime('%Y', p.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', p.birthday)) AS age 
FROM Player p 
JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id 
WHERE pa.sprint_speed >= 97 AND pa.date BETWEEN '2013-01-01' AND '2015-12-31'
```

### Q1032 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's tie-preserving HAVING match_count = (SELECT MAX(match_count)...) pattern to a plain ORDER BY match_count DESC LIMIT 1

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT t2.name, COUNT(*) AS match_count 
FROM Match AS t1 
INNER JOIN League AS t2 ON t1.league_id = t2.id 
GROUP BY t2.name 
ORDER BY match_count DESC 
LIMIT 1
```

### Q1037 (challenging, aggregate) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** uses SUM(CASE)/COUNT(*) over all Player_Attributes snapshot rows instead of gold's COUNT(DISTINCT id)/COUNT(DISTINCT id), which could over/under-count players with multiple attribute records

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Player_Attributes INNER JOIN Player ON Player_Attributes.player_api_id = Player.player_api_id WHERE strftime('%Y', Player.birthday) BETWEEN '1987' AND '1992'
```

### Q1076 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references t2.ball_control where t2=Player (no such column); the value belongs to the already-joined Player_Attributes aliased t1, and the whole per-player subtraction structure is bungled

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL:**

```sql
SELECT AVG(t1.ball_control) - AVG(t2.ball_control) AS difference 
FROM Player_Attributes AS t1 
JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id 
WHERE t2.player_name IN ('Abdou Diallo', 'Aaron Appindangoye') 
GROUP BY t2.player_name
```

### Q1080 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Left'/'High' case and value mismatch vs gold's 'left'/'low' -- attacking_work_rate value is flatly wrong (opposite), not just case

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player_Attributes WHERE preferred_foot = 'Left' AND attacking_work_rate = 'High'
```

### Q1084 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extraneous attacking_work_rate='High' condition gold doesn't have; also case-mismatches defensive_work_rate ('High' vs gold's 'high')

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE strftime('%Y', t1.birthday) < '1986' AND t2.attacking_work_rate = 'High' AND t2.defensive_work_rate = 'High'
```

### Q1088 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** typo'd 'vollys' (for 'volleys') doesn't exist anywhere in the schema

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.vollys > 70 AND t2.dribbling > 70
```

### Q1092 (simple, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's tie-preserving HAVING match_count = (SELECT MAX(match_count)...) pattern to a plain GROUP BY/ORDER BY DESC LIMIT 1

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2008/2009' GROUP BY t2.name ORDER BY COUNT(*) DESC LIMIT 1
```

### Q1094 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `error` · **Reason:** omits gold's two-CTE 'latest rating per named player' construct (ORDER BY date DESC LIMIT 1 per player); instead joins Player_Attributes+Player directly and references a nonexistent b.overall_rating (Player has no such column -- it lives on the already-joined Player_Attributes alias a)

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT ((a.overall_rating - b.overall_rating) * 100.0 / b.overall_rating) AS percentage_increase FROM Player_Attributes a JOIN Player b ON a.player_api_id = b.player_api_id WHERE b.player_name = 'Ariel Borysiuk' OR b.player_name = 'Paulin Puel'
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the SUBSTR(date,1,10) truncation gold uses; Player_Attributes.date is stored with a '00:00:00' time suffix, so an exact bare-date match returns zero rows

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = 77 AND t2.date = '2016-06-23' ORDER BY t1.birthday ASC LIMIT 1
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the SUBSTR(date,1,10) truncation gold uses against the time-suffixed stored date, causing the exact match to fail

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT overall_rating FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Aaron Mooy') AND date = '2016-02-04'
```

### Q1105 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's date LIKE '...%' wildcard, using a bare exact-match date literal against the time-suffixed stored value instead

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT attacking_work_rate FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Francesco Migliore') AND date = '2015-05-01'
```

### Q1107 (moderate, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** drops gold's secondary ORDER BY t2.date ASC tie-breaker after crossing DESC, so ties aren't broken the same way as gold

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT t1.date FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.player_name = 'Kevin Constant' ORDER BY t1.crossing DESC LIMIT 1
```

### Q1110 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's date LIKE '...%' wildcard, using a bare exact-match date literal against the time-suffixed stored value instead

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT t2.buildup_play_passing_class FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2.date = '2010-02-22'
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's date LIKE '...%' wildcard, using a bare exact-match date literal against the time-suffixed stored value instead

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT t2.defence_aggression_class FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2.date = '2015-09-10'
```

### Q1114 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the SUBSTR(date,1,10) truncation gold uses on the BETWEEN date-range bounds against the time-suffixed stored date, shifting the boundary comparisons

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(overall_rating) FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Marko Arnautovic') AND date BETWEEN '2007-02-22' AND '2016-04-21'
```

### Q1115 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** both date equality comparisons (t1.date/t2.date = '2013-07-12') omit gold's SUBSTR(date,1,10) truncation, so neither matches the time-suffixed stored values

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT ((t1.overall_rating - t2.overall_rating) * 100.0 / t2.overall_rating) AS percentage_difference FROM Player_Attributes AS t1 JOIN Player AS t3 ON t1.player_api_id = t3.player_api_id JOIN Player_Attributes AS t2 ON t2.player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Jordan Bowery') WHERE t3.player_name = 'Landon Donovan' AND t1.date = '2013-07-12' AND t2.date = '2013-07-12'
```

### Q1116 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's DENSE_RANK() OVER (ORDER BY height DESC) WHERE rank=1 (which preserves ties) with a plain ORDER BY height DESC LIMIT 10

**Gold SQL:**

```sql
SELECT player_name FROM (SELECT player_name, height, DENSE_RANK() OVER (ORDER BY height DESC) as rank FROM Player) WHERE rank = 1
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player ORDER BY height DESC LIMIT 10
```

### Q1122 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes Player_Attributes.strength for gold's overall_rating -- both real columns, wrong one used to find the 'best' player

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1130 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'low' invented instead of gold's actual chanceCreationPassingClass value 'Safe' (column/table correct)

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT DISTINCT t.team_short_name FROM Team t JOIN Team_Attributes ta ON t.team_api_id = ta.team_api_id WHERE ta.chance_creation_passing_class = 'low'
```

### Q1136 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes Player_Attributes.potential for gold's crossing -- both real columns; also adds an unneeded attacking_work_rate='High' filter and restricts the MAX subquery's scope, which gold's doesn't have

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player_Attributes WHERE potential = (SELECT MAX(potential) FROM Player_Attributes WHERE preferred_foot = 'Left' AND attacking_work_rate = 'High') AND preferred_foot = 'Left' AND attacking_work_rate = 'High'
```

### Q1139 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Belgian Jupiler League' vs the actual stored league name 'Belgium Jupiler League'; also drops the LIKE wildcard on the date filter (time-suffixed stored date)

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT home_team_goals, away_team_goals FROM Match WHERE date = '2008-09-24' AND league_id = (SELECT id FROM League WHERE name = 'Belgian Jupiler League')
```

### Q1141 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extraneous IN ('slow','balanced','fast') condition with wrong-case literals (actual values are capitalized), filtering out every matching row

**Gold SQL:**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL:**

```sql
SELECT DISTINCT t1.buildup_play_speed_class FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge' AND t1.buildup_play_speed_class IN ('slow', 'balanced', 'fast')
```

### Q1144 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's WHERE player_api_id IN (subquery matching MAX(weight), preserving ties/multiple snapshots) with a plain ORDER BY weight DESC LIMIT 1

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT t1.finishing, t1.curve FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id ORDER BY t2.weight DESC LIMIT 1
```

### Q1146 (moderate, retrieval) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** adds a GROUP BY team_api_id/SUM(away_team_goals) aggregation across all matches where gold's flat query just orders individual match rows by away_team_goal DESC LIMIT 1 -- a different question (season total vs single-match record)

**Gold SQL:**

```sql
SELECT t2.team_long_name FROM Match AS t1 INNER JOIN Team AS t2 ON t1.away_team_api_id = t2.team_api_id ORDER BY t1.away_team_goal DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT t.team_long_name 
FROM Team t 
JOIN Match m ON t.team_api_id = m.away_team_api_id 
GROUP BY t.team_api_id, t.team_long_name 
ORDER BY SUM(m.away_team_goals) DESC 
LIMIT 1;
```

### Q1147 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes Player_Attributes.strength for gold's overall_rating -- both real columns, wrong one used to find the 'best' player (same pattern as Q1122)

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1148 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references Player.strength (no such column; strength/attribute columns live on Player_Attributes, which isn't joined at all)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN height < 180 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Player WHERE strength > 70
```

---

## financial (17 failures)

### Q98 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents 'POPLATEK TYGROVE' (doesn't exist) instead of gold's 'POPLATEK TYDNE'; also adds an extraneous status='A' filter not in gold

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.account_id 
FROM account AS T1 
INNER JOIN loan AS T2 ON T1.account_id = T2.account_id 
WHERE T2.status = 'A' AND strftime('%Y', T2.date) = '1997' AND T1.statement_frequency = 'POPLATEK TYGROVE' 
ORDER BY T2.amount ASC 
LIMIT 1
```

### Q115 (challenging, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** drops gold's GROUP BY T2.A4 (number_inhabitants) entirely, so the male-percentage aggregate spans all south-Bohemia clients across every district instead of being isolated to the single most-populous district (ORDER BY/LIMIT becomes a no-op without a GROUP BY)

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT (COUNT(CASE WHEN T4.gender = 'M' THEN 1 END) * 100.0 / COUNT(T4.client_id)) AS male_percentage 
FROM district AS T1 
INNER JOIN client AS T4 ON T1.district_id = T4.district_id 
WHERE T1.region = 'south Bohemia' 
ORDER BY T1.number_inhabitants DESC 
LIMIT 1
```

### Q116 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T2.balance_after_transaction where T2=account (no such column); the value belongs to the already-joined trans aliased T5; also restructures the two-specific-date comparison into a MAX/MIN-over-date-range calc

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(T2.balance_after_transaction) - MIN(T2.balance_after_transaction)) / MIN(T2.balance_after_transaction) AS increase_rate
FROM 
    client AS T1
INNER JOIN 
    disp AS T3 ON T1.client_id = T3.client_id
INNER JOIN 
    account AS T2 ON T3.account_id = T2.account_id
INNER JOIN 
    loan AS T4 ON T2.account_id = T4.account_id
INNER JOIN 
    trans AS T5 ON T2.account_id = T5.account_id
WHERE 
    T4.date = '1993-07-05' AND T4.status = 'A' AND T5.date BETWEEN '1993-03-22' AND '1998-12-27'
GROUP BY 
    T1.client_id
LIMIT 1
```

### Q118 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses status='A' instead of gold's status='C' inside the CASE

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage 
FROM loan 
WHERE amount < 100000
```

### Q125 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references client.unemployment_rate_1996 (belongs to district, which isn't joined at all); the whole WHERE logic (status/amount) also diverges from gold's A12/A13 percent-change filters

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT T4.unemployment_rate_1996 - T4.unemployment_rate_1995 
FROM loan AS T1 
INNER JOIN account AS T2 ON T1.account_id = T2.account_id 
INNER JOIN disp AS T3 ON T2.account_id = T3.account_id 
INNER JOIN client AS T4 ON T3.client_id = T4.client_id 
WHERE T1.status = 'A' AND T1.amount > 0;
```

### Q129 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits the account intermediary table, joining trans directly to district via account_id=district_id (comparing incompatible ID domains); also uses 'vyber' instead of gold's 'VYDAJ' for the transaction type

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT T2.district_name 
FROM trans AS T1 
INNER JOIN district AS T2 ON T1.account_id = T2.district_id 
WHERE T1.type = 'vyber' AND T1.date LIKE '1996-01-%' 
ORDER BY T1.amount DESC 
LIMIT 10
```

### Q136 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extraneous status='A' condition gold doesn't have

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.account_id) 
FROM loan AS T1 
INNER JOIN account AS T2 ON T1.account_id = T2.account_id 
WHERE T1.date BETWEEN '1995-01-01' AND '1997-12-31' 
AND T1.amount >= 250000 
AND T2.statement_frequency = 'POPLATEK MESICNE'
AND T1.status = 'A';
```

### Q137 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents nonexistent literal values for both loan.status ('R' instead of 'C'/'D') and district.district_name ('Branch location 1', a fabricated placeholder instead of matching district_id=1 directly)

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM loan 
WHERE status = 'R' 
AND account_id IN (
    SELECT account_id 
    FROM account 
    WHERE district_id IN (
        SELECT district_id 
        FROM district 
        WHERE district_name = 'Branch location 1'
    )
)
```

### Q145 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** references trans.card (T2.card), which doesn't exist anywhere in the schema -- trans has no card-related column; the card/account link runs through disp, not trans

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.account_id 
FROM card AS T1 
INNER JOIN trans AS T2 ON T1.card_id = T2.card 
INNER JOIN disp AS T3 ON T2.account_id = T3.account_id 
WHERE T2.type = 'PRIJEM' AND T2.amount < (SELECT AVG(amount) FROM trans WHERE strftime('%Y', date) = '1998') AND strftime('%Y', T2.date) = '1998'
```

### Q149 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references account.type (no such column; type lives on disp, which is missing from the FROM clause entirely)

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
SELECT DISTINCT T1.type 
FROM account AS T1 
INNER JOIN district AS T2 ON T1.district_id = T2.district_id 
WHERE T2.average_salary BETWEEN 8000 AND 9000 
AND T1.account_id NOT IN (SELECT account_id FROM loan)
```

### Q152 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes district.number_inhabitants for gold's number_crimes_1995 throughout (both the SELECT AVG target and the WHERE threshold); also uses a direct JOIN instead of gold's DISTINCT-subquery, risking double counting per district

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(T1.number_crimes_1995) 
FROM district AS T1 
INNER JOIN account AS T2 ON T1.district_id = T2.district_id 
WHERE T1.number_inhabitants > 4000 AND strftime('%Y', T2.date) >= '1997'
```

### Q159 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes trans.type='VYBER KARTOU' for gold's trans.operation='VYBER' (both real columns/values, wrong ones used); also outputs only 2 columns instead of gold's SELECT T4.* (all trans columns)

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT T1.transaction_id, T1.amount 
FROM trans AS T1 
INNER JOIN disp AS T2 ON T1.account_id = T2.account_id 
WHERE T2.client_id = 3356 AND T1.type = 'VYBER KARTOU'
```

### Q169 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references account.amount (T2.amount, no such column); loan (which holds amount) is entirely absent from the FROM clause; also drops the disp.type='OWNER' filter

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN strftime('%Y', T2.date) = '1997' THEN T2.amount ELSE 0 END) - SUM(CASE WHEN strftime('%Y', T2.date) = '1996' THEN T2.amount ELSE 0 END)) / 
    SUM(CASE WHEN strftime('%Y', T2.date) = '1996' THEN T2.amount ELSE 0 END) AS growth_rate
FROM 
    client AS T1
INNER JOIN 
    disp AS T3 ON T1.client_id = T3.client_id
INNER JOIN 
    account AS T2 ON T3.account_id = T2.account_id
WHERE 
    T1.gender = 'M'
```

### Q173 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** references the `order` table without quoting the reserved SQL keyword, causing a syntax error; the overall join-based aggregation also diverges from gold's derived-table SUM(amount) GROUP BY account_id/k_symbol approach

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT 
    T1.statement_frequency, 
    SUM(CASE WHEN T3.amount = 3539 THEN 1 ELSE 0 END) AS debit_count 
FROM 
    account AS T1 
JOIN 
    trans AS T2 ON T1.account_id = T2.account_id 
LEFT JOIN 
    order AS T3 ON T2.transaction_id = T3.order_id 
WHERE 
    T1.account_id = 3 
GROUP BY 
    T1.statement_frequency;
```

### Q186 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps the WHERE/CASE roles: filters on gender='M' and aggregates the percentage matching a different frequency value ('POPLATEK PO OBRATU' instead of gold's 'POPLATEK TYDNE'), inverting which attribute is filtered vs measured

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.statement_frequency = 'POPLATEK PO OBRATU' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM account AS T1 
INNER JOIN disp AS T2 ON T1.account_id = T2.account_id 
INNER JOIN client AS T3 ON T2.client_id = T3.client_id 
WHERE T3.gender = 'M'
```

### Q192 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses status='A' instead of gold's status IN ('C','D')

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(T1.amount) 
FROM loan AS T1 
INNER JOIN account AS T2 ON T1.account_id = T2.account_id 
WHERE T1.status = 'A' AND T2.statement_frequency = 'POPLATEK PO OBRATU'
```

### Q194 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents 'high level' instead of gold's actual card.type value 'gold'

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT T1.client_id, strftime('%Y', 'now') - strftime('%Y', T1.birth_date) AS age 
FROM client AS T1 
INNER JOIN disp AS T2 ON T1.client_id = T2.client_id 
INNER JOIN card AS T3 ON T2.disposition_id = T3.disposition_id 
WHERE T3.type = 'high level' AND T2.type = 'OWNER'
```

---

## formula_1 (47 failures)

### Q850 (simple, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DISTINCT, so repeated race names across multiple years at German circuits would appear as duplicate rows

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuit_id = T1.circuit_id WHERE T1.country = 'Germany'
```

### Q854 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** matches 'Australian Grand Prix' against circuits.name instead of gold's races.name, omitting the races table entirely -- circuits.name is the physical track name, a different real attribute

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Australian Grand Prix'
```

### Q857 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** matches 'Abu Dhabi Grand Prix' against circuits.name instead of gold's races.name, omitting the races table entirely

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Abu Dhabi Grand Prix'
```

### Q861 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** reformats the qualifying time literal as '0:01:54' instead of matching gold's LIKE '1:54%' pattern against the real 'M:SS.sss' stored format

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT T1.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driver_id = T1.driver_id WHERE T1.race_id = 903 AND T1.qualifying_3_time = '0:01:54'
```

### Q865 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops both the T2.time IS NOT NULL and T1.dob IS NOT NULL filters gold has, potentially selecting a non-finishing driver or one with an unknown birthdate

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T2.race_id = 592 ORDER BY T1.date_of_birth ASC LIMIT 1
```

### Q866 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** reformats the lap-time literal as '0:01:27' instead of matching gold's LIKE '1:27%' pattern against the real 'M:SS.sss' format; also missing DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.url 
FROM drivers d 
JOIN laptimes lt ON d.driver_id = lt.driver_id 
WHERE lt.race_id = 161 AND lt.time = '0:01:27';
```

### Q868 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** matches 'Malaysian Grand Prix' against circuits.name instead of gold's races.name, omitting the races table entirely

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Malaysian Grand Prix'
```

### Q869 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorStandings for gold's constructorResults -- both real tables, but standings represents cumulative season points, not the single race's points

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.url 
FROM constructorStandings cs 
JOIN constructors c ON c.constructor_id = cs.constructor_id 
WHERE cs.race_id = 9 
ORDER BY cs.points DESC 
LIMIT 1;
```

### Q872 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** reformats the qualifying time literal as '0:01:33' instead of matching gold's LIKE '1:33%' pattern against the real 'M:SS.sss' format

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT T2.driver_code 
FROM qualifying AS T1 
INNER JOIN drivers AS T2 ON T2.driver_id = T1.driver_id 
WHERE T1.race_id = 45 AND T1.qualifying_3_time = '0:01:33'
```

### Q877 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the T2.time IS NOT NULL filter gold has, potentially selecting a non-finishing driver

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T2.race_id = 872 ORDER BY T1.date_of_birth DESC LIMIT 1
```

### Q879 (moderate, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** drops gold's CAST(fastestLapSpeed AS REAL), causing ORDER BY to sort lexicographically (as text) instead of numerically, which can select the wrong top row

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.nationality 
FROM drivers d 
JOIN results r ON d.driver_id = r.driver_id 
ORDER BY r.fastest_lap_speed DESC 
LIMIT 1;
```

### Q881 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** adds a GROUP BY driver_id/first_name/last_name that gold's single-aggregate query doesn't have, producing one row per driver instead of one overall percentage; also uses status_id=1 instead of gold's 'time IS NOT NULL' criterion

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT d.driver_id, d.first_name, d.last_name, 
       (COUNT(CASE WHEN r.status_id = 1 THEN 1 END) * 100.0 / COUNT(*)) AS completion_rate
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
JOIN races ra ON r.race_id = ra.race_id
WHERE ra.date = '1983-07-16'
GROUP BY d.driver_id, d.first_name, d.last_name;
```

### Q884 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** YEAR()/MONTH() are not valid SQLite functions (gold uses strftime('%Y', ...)/strftime('%m', ...))

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT name FROM races WHERE YEAR(date) = (SELECT MIN(YEAR(date)) FROM races) AND MONTH(date) = (SELECT MIN(MONTH(date)) FROM races)
```

### Q894 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results (per-race summary, fastestLapTime/time fields) for gold's lapTimes (individual per-lap records) -- a fundamentally different granularity

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.time, T2.first_name, T2.last_name, T1.name 
FROM races AS T1 
INNER JOIN results AS T3 ON T3.race_id = T1.race_id 
INNER JOIN drivers AS T2 ON T2.driver_id = T3.driver_id 
ORDER BY T3.fastest_lap_time ASC 
LIMIT 1;
```

### Q895 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** averages laptimes.time (a text-formatted lap-time string) instead of gold's laptimes.milliseconds (the numeric equivalent), which AVG() can't meaningfully compute over text

**Gold SQL:**

```sql
SELECT AVG(T2.milliseconds) FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.year = 2009 AND T1.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT AVG(T3.time) FROM races AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id INNER JOIN laptimes AS T3 ON T2.driver_id = T3.driver_id AND T1.race_id = T3.race_id INNER JOIN drivers AS T4 ON T2.driver_id = T4.driver_id WHERE T4.first_name = 'Lewis' AND T4.last_name = 'Hamilton' AND T1.name = 'Malaysian Grand Prix' AND T1.year = 2009
```

### Q896 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** races.winning_driver_id doesn't exist anywhere in the schema; there's no 'winner' FK on races at all (that information lives in driverStandings/results.position, which predicted's approach entirely bypasses)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT (COUNT(*) - COUNT(CASE WHEN T2.round = 1 THEN 1 END)) * 100.0 / COUNT(*) AS percentage_not_first_track
FROM drivers AS T1
JOIN races AS T2 ON T1.driver_id = T2.winning_driver_id
WHERE T1.first_name = 'Lewis' AND T1.last_name = 'Hamilton' AND T2.year >= 2010;
```

### Q897 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** drops gold's GROUP BY forename/surname/nationality + ORDER BY COUNT(wins) DESC LIMIT 1 ranking entirely, instead filtering on wins=(SELECT MAX(wins)...), a different selection criterion that can return multiple/no rows without the same ranking semantics

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.nationality, MAX(ds.points) AS max_points
FROM drivers d
JOIN driverstandings ds ON d.driver_id = ds.driver_id
WHERE ds.wins = (SELECT MAX(wins) FROM driverstandings)
```

### Q898 (simple, retrieval) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** substitutes a bare MIN(date_of_birth) aggregate (which doesn't reliably correlate first_name/last_name to the same row without GROUP BY) for gold's ORDER BY dob DESC LIMIT 1 approach; also drops the age-computation expression from SELECT entirely

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(date_of_birth), first_name, last_name FROM drivers WHERE nationality = 'Japanese'
```

### Q901 (simple, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** references T2.name, but T2 is never declared as an alias anywhere in the FROM/JOIN clause (only T1=races and T3=circuits are aliased)

**Gold SQL:**

```sql
SELECT DISTINCT T2.name, T1.name, T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.year = 2005 AND STRFTIME('%m', T2.date) = '09'
```

**Predicted SQL:**

```sql
SELECT T2.name, T3.circuit_ref_name, T3.location 
FROM races AS T1 
INNER JOIN circuits AS T3 ON T3.circuit_id = T1.circuit_id 
WHERE T1.year = 2005 AND strftime('%m', T1.date) = '09'
```

### Q902 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results.grid_position for gold's driverStandings.position -- both real but different tables/columns (starting grid position vs championship standings position)

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT T2.name FROM results AS T1 INNER JOIN races AS T2 ON T2.race_id = T1.race_id INNER JOIN drivers AS T3 ON T3.driver_id = T1.driver_id WHERE T3.first_name = 'Alex' AND T3.last_name = 'Yoong' AND T1.grid_position < 20
```

### Q904 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results.fastestLapSpeed (per-race summary metric) for gold's lapTimes.milliseconds (individual per-lap record); also orders DESC on speed instead of ASC on time -- the wrong metric entirely

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.name, T2.year FROM results AS T1 INNER JOIN races AS T2 ON T2.race_id = T1.race_id INNER JOIN drivers AS T3 ON T3.driver_id = T1.driver_id WHERE T3.first_name = 'Michael' AND T3.last_name = 'Schumacher' ORDER BY T1.fastest_lap_speed DESC LIMIT 1
```

### Q906 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references r.name where r=results (no such column); the value belongs to the already-joined races aliased ra; also substitutes results.points for gold's driverStandings.points, a different real table

**Gold SQL:**

```sql
SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT r.name, r.points 
FROM results r 
JOIN drivers d ON d.driver_id = r.driver_id 
JOIN races ra ON ra.race_id = r.race_id 
WHERE d.first_name = 'Lewis' AND d.last_name = 'Hamilton' 
ORDER BY ra.year ASC, ra.round ASC 
LIMIT 1;
```

### Q915 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** drivers has no 'country' column (the real column is nationality); 'country' exists only as an unrelated column on circuits, not reachable via any join that would supply driver nationality

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT country FROM drivers ORDER BY date_of_birth ASC LIMIT 1
```

### Q930 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes driverStandings.position for gold's results.rank=0 criterion -- two different real tables/columns; also replaces gold's IN-subquery (all matching races) with an ORDER BY/LIMIT 1 approach

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT T2.name 
FROM driverStandings AS T1 
INNER JOIN races AS T2 ON T2.race_id = T1.race_id 
INNER JOIN drivers AS T3 ON T3.driver_id = T1.driver_id 
WHERE T3.first_name = 'Lewis' AND T3.last_name = 'Hamilton' 
ORDER BY T1.position ASC 
LIMIT 1;
```

### Q937 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** race name garbled to 'AustChineseralian Grand Prix' instead of gold's 'Chinese Grand Prix' -- a nonsensical invented value, not just a case/spelling variant (the ORDER BY position ASC LIMIT 1 OFFSET 1 restructuring is functionally equivalent to gold's WHERE position=2)

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT r.time 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
WHERE ra.year = 2008 AND ra.name = 'AustChineseralian Grand Prix' 
ORDER BY r.position ASC 
LIMIT 1 OFFSET 1;
```

### Q940 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's r.time IS NOT NULL filter entirely, counting all entrants instead of only those with a valid finishing time

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT r.driver_id) 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix';
```

### Q944 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes results.fastestLapSpeed for gold's positionOrder/milliseconds-based champion-vs-last-place comparison; also confuses the year 1988 for a race_id in a nested subquery

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT 
    ((MAX(CASE WHEN r.position = 1 THEN CAST(r.fastest_lap_speed AS REAL) END) -
      MAX(CASE WHEN r.position = (SELECT COUNT(*) FROM results WHERE race_id = 1988 AND circuit_id = (SELECT circuit_id FROM races WHERE year = 1988 AND name = 'Australian Grand Prix')) THEN CAST(r.fastest_lap_speed AS REAL) END)) * 100.0) /
    MAX(CASE WHEN r.position = (SELECT COUNT(*) FROM results WHERE race_id = 1988 AND circuit_id = (SELECT circuit_id FROM races WHERE year = 1988 AND name = 'Australian Grand Prix')) THEN CAST(r.fastest_lap_speed AS REAL) END) AS percent_faster
FROM 
    results r
JOIN 
    races ra ON r.race_id = ra.race_id
WHERE 
    ra.year = 1988 
    AND ra.name = 'Australian Grand Prix';
```

### Q945 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'city' doesn't exist anywhere in the schema; the real column is circuits.location

**Gold SQL:**

```sql
SELECT COUNT(circuitId) FROM circuits WHERE location = 'Adelaide' AND country = 'Australia'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM circuits WHERE city = 'Adelaide' AND country = 'Australia';
```

### Q950 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorResults for gold's constructorStandings (two different real tables representing per-race results vs cumulative standings-at-that-race)

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT c.name FROM constructors c JOIN constructorResults cr ON c.constructor_id = cr.constructor_id WHERE cr.race_id = 291 AND cr.points = 0
```

### Q951 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorStandings for gold's constructorResults (two different real tables); also restructures the per-row points=0 filter into a SUM(points)=0 aggregate condition, a different computation entirely

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM constructors c 
JOIN constructorStandings cs ON c.constructor_id = cs.constructor_id 
WHERE c.nationality = 'Japanese' 
GROUP BY c.constructor_id 
HAVING SUM(cs.points) = 0 AND COUNT(DISTINCT cs.race_id) = 2;
```

### Q954 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** moves the year filter from WHERE into the CASE numerator (dropping the WHERE year restriction on the denominator entirely) and substitutes it for gold's actual numerator criterion (time IS NOT NULL), measuring a fundamentally different percentage

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN s.year BETWEEN 2007 AND 2009 THEN 1 END) * 100.0 / COUNT(*)) AS race_completion_percentage
FROM 
    drivers d
JOIN 
    results r ON d.driver_id = r.driver_id
JOIN 
    races s ON r.race_id = s.race_id
WHERE 
    d.nationality = 'Japanese';
```

### Q955 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes driverStandings.position for gold's results.position, and averages results.time (text) instead of gold's milliseconds/1000.0 (numeric)

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT s.year, AVG(r.time) AS avg_time_seconds
FROM seasons s
JOIN races ra ON s.year = ra.year
JOIN results r ON ra.race_id = r.race_id
JOIN driverStandings ds ON r.driver_id = ds.driver_id AND r.race_id = ds.race_id
WHERE s.year < 1975 AND ds.position = 1
GROUP BY s.year;
```

### Q959 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's T1.time LIKE '_:%:__.___' format filter, substituting an unrelated driverStandings.position=1 condition via an added join

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT r.fastest_lap_number 
FROM results r 
JOIN driverstandings ds ON r.driver_id = ds.driver_id 
JOIN races ra ON r.race_id = ra.race_id 
WHERE ds.position = 1 AND ra.year = 2009;
```

### Q963 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's CAST/SUBSTR parsing of lapTimes.time into numeric seconds, replacing it with a naive string comparison ('< 02:00.00') that doesn't correctly capture the '< 120 seconds' semantics against the real 'M:SS.sss' format

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.driver_id) 
FROM drivers AS T1 
INNER JOIN laptimes AS T2 ON T1.driver_id = T2.driver_id 
WHERE T1.nationality = 'French' 
AND T2.time < '02:00.00'
```

### Q967 (simple, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's derived-table structure (3 youngest drivers overall, then filter to Dutch), instead filtering by nationality first and taking a top-3 among only that filtered subset -- a fundamentally different selection order; also uses the invented value 'Netherlandic' instead of gold's real value 'Dutch'

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM drivers WHERE nationality = 'Netherlandic' ORDER BY date_of_birth DESC LIMIT 3
```

### Q972 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the fastestLapTime IS NOT NULL filter, replacing gold's full listing with an ORDER BY fastest_lap_speed DESC LIMIT 1 that returns a single (differently-selected) driver instead of all drivers born in 1971 with a valid fastest lap time

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT d.driver_id, d.driver_code 
FROM drivers d 
JOIN results r ON d.driver_id = r.driver_id 
WHERE strftime('%Y', d.date_of_birth) = '1971' 
ORDER BY r.fastest_lap_speed DESC 
LIMIT 1;
```

### Q977 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** substitutes a status-table lookup (LIKE '%Disqualified%') for gold's literal statusId=2, shifts the race_id bounds to inclusive BETWEEN 50-100 instead of gold's exclusive >50 AND <100, and drops the 'time IS NOT NULL' requirement (plain COUNT(*) instead of SUM(IIF(time IS NOT NULL,1,0)))

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
WHERE race_id BETWEEN 50 AND 100 
AND status_id IN (SELECT status_id FROM status WHERE status LIKE '%Disqualified%');
```

### Q978 (simple, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DISTINCT; if Austria has more than one circuits row, duplicate rows would appear

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE country = 'Austria'
```

### Q981 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T2.year where T2=qualifying (no such column); the value belongs to the already-joined races aliased T3

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(T2.year), T3.name, T3.date, T3.time 
FROM drivers AS T1 
INNER JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id 
INNER JOIN races AS T3 ON T2.race_id = T3.race_id 
ORDER BY T1.date_of_birth ASC, T2.year ASC 
LIMIT 1;
```

### Q988 (challenging, aggregate) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds an extra avg_pit_stop_duration output column beyond gold's forename/surname-only SELECT list, a column/shape mismatch

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, AVG(p.duration) AS avg_pit_stop_duration
FROM drivers d
JOIN pitStops p ON d.driver_id = p.driver_id
WHERE d.nationality = 'German' AND d.date_of_birth BETWEEN '1980-01-01' AND '1985-12-31'
GROUP BY d.driver_id
ORDER BY avg_pit_stop_duration ASC
LIMIT 3;
```

### Q989 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** matches circuits.name='Canadian Grand Prix' instead of gold's races.name; also replaces gold's time-format filter with an ORDER BY position ASC LIMIT 1 selection, a different criterion entirely

**Gold SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT r.time 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
JOIN circuits c ON ra.circuit_id = c.circuit_id 
WHERE ra.year = 2008 AND c.name = 'Canadian Grand Prix' 
ORDER BY r.position ASC 
LIMIT 1;
```

### Q990 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorStandings.position=1 for gold's results.time LIKE format-filter -- constructorStandings represents cumulative season standings, a different table/concept from the specific race result gold examines

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT c.constructor_ref_name, c.url 
FROM constructorStandings cs 
JOIN constructors c ON c.constructor_id = cs.constructor_id 
JOIN races r ON r.race_id = cs.race_id 
WHERE r.name = 'Singapore Grand Prix' AND r.year = 2009 AND cs.position = 1;
```

### Q994 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** matches circuits.name='Monaco Grand Prix' instead of gold's races.name; also substitutes constructorStandings.points for gold's constructorResults.points (cumulative standings vs per-race results)

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.points, co.name, co.nationality
FROM constructorStandings c
JOIN constructors co ON co.constructor_id = c.constructor_id
JOIN races r ON r.race_id = c.race_id
JOIN circuits ci ON ci.circuit_id = r.circuit_id
WHERE r.year BETWEEN 1980 AND 2010
  AND ci.name = 'Monaco Grand Prix'
GROUP BY co.constructor_id
ORDER BY SUM(c.points) DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes races.round=3 for what should be a filter on qualifying.q3 (confusing 'q3' the qualifying-session column with 'round 3' of the season), and substitutes qualifying.position=1 for gold's ORDER BY-parsed-q3-time ranking

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name 
FROM drivers d 
JOIN qualifying q ON d.driver_id = q.driver_id 
JOIN races r ON q.race_id = r.race_id 
JOIN circuits c ON r.circuit_id = c.circuit_id 
WHERE r.year = 2008 
AND r.round = 3 
AND c.name = 'Marina Bay Street Circuit' 
AND q.position = 1;
```

### Q1002 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references results.name (no such column; name lives on races, which isn't joined at all); also substitutes results for gold's driverStandings

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, T3.name FROM drivers AS T1 INNER JOIN driverStandings AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T2.raceId = T3.raceId ORDER BY JULIANDAY(T1.dob) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.nationality, r.name
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
WHERE d.date_of_birth = (SELECT MIN(date_of_birth) FROM drivers)
ORDER BY r.race_id ASC
LIMIT 1;
```

### Q1011 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's per-driver MIN(milliseconds) derived-table pre-aggregation, instead ordering raw individual lap records directly, which can return the same driver multiple times among the top 20 lap times instead of 20 distinct drivers' personal bests

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name 
FROM drivers d 
JOIN laptimes lt ON d.driver_id = lt.driver_id 
ORDER BY lt.milliseconds ASC 
LIMIT 20;
```

### Q1014 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references lapTimes.circuit_id (no such column; lapTimes has no direct FK to circuits, requiring races as an intermediary, which predicted omits entirely); also substitutes lapTimes.milliseconds for gold's results.FastestLapTime-based computation entirely

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(T2.milliseconds) AS fastest_lap_time
FROM circuits AS T1
INNER JOIN lapTimes AS T2 ON T2.circuit_id = T1.circuit_id
WHERE T1.country = 'Italy'
```

---

## student_club (20 failures)

### Q1322 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** join key (event_id, the S3 rename of attendance.link_to_event) and HAVING COUNT(member_id) are both correct; the real bug is the missing outer SELECT COUNT(*) FROM (derived table) wrapper -- predicted's flat GROUP BY/HAVING returns one row per qualifying event instead of the count of qualifying events

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM event AS T1 
INNER JOIN attendance AS T2 ON T1.event_id = T2.event_id 
WHERE T1.type = 'Meeting' 
GROUP BY T1.event_id 
HAVING COUNT(T2.member_id) > 10
```

### Q1338 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** collapses the required event->budget->expense chain to a nonexistent direct event->expense join; expense has no FK column to event (only to budget and member)

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT T2.is_approved FROM event AS T1 INNER JOIN expense AS T2 ON T1.event_id = T2.event_id WHERE T1.event_name = 'October Meeting' AND T2.expense_date = '2019-10-08'
```

### Q1340 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extraneous T2.type='Student_Club' filter gold doesn't have (join key and budget.spent->amount_spent rename are both correct)

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN strftime('%Y', T2.event_date) = '2019' THEN T1.amount_spent ELSE 0 END) - 
    SUM(CASE WHEN strftime('%Y', T2.event_date) = '2020' THEN T1.amount_spent ELSE 0 END) AS difference
FROM 
    budget AS T1 
JOIN 
    event AS T2 
ON 
    T1.event_id = T2.event_id
WHERE 
    T2.type = 'Student_Club'
```

### Q1344 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** queries event.notes/event_date/type instead of income.notes/date_received/source -- both tables have a notes-like column but the question asks about an income record

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE event_date = '2019-09-14' AND type = 'fundraising'
```

### Q1350 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes event.status for budget.event_status and budget.category for expense.expense_description (comparing the wrong table's column to the same literal); drops the expense table entirely

**Gold SQL:**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT T1.status FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.event_id WHERE T2.category = 'Post Cards, Posters' AND T1.event_date = '2019-08-20'
```

### Q1357 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'dues' vs gold's 'Dues' case mismatch (join and income_source rename are both correct)

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.member_id WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.income_source = 'dues'
```

### Q1359 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's ratio-of-conditional-sums with an unrelated correlated-subquery COUNT comparison that doesn't compute the same ratio at all

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM budget AS T1 
INNER JOIN event AS T2 ON T1.event_id = T2.event_id 
WHERE T1.category = 'Advertisement' 
AND T2.event_name = 'Yearly Kickoff' 
AND T1.amount > (
    SELECT amount 
    FROM budget AS T3 
    INNER JOIN event AS T4 ON T3.event_id = T4.event_id 
    WHERE T3.category = 'Advertisement' 
    AND T4.event_name = 'October Meeting'
)
```

### Q1376 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's tie-preserving HAVING ratio = (SELECT MAX(ratio)...) pattern to a plain ORDER BY (amount_spent/amount) DESC LIMIT 1

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT T1.event_name 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.event_id 
WHERE T1.status = 'Closed' 
ORDER BY (T2.amount_spent / T2.amount) DESC 
LIMIT 1
```

### Q1387 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** collapses the event->budget->expense->member chain to a nonsensical member.member_id = budget.event_id join, using budget.category='Yearly Kickoff' for what should be an event_name match, and drops the position='Treasurer' filter entirely

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name 
FROM member AS T1 
INNER JOIN budget AS T2 ON T1.member_id = T2.event_id 
WHERE T2.category = 'Yearly Kickoff'
```

### Q1389 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** collapses the required event->budget->expense chain to a nonexistent direct event->expense join, same pattern as Q1338

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.event_name 
FROM event AS T1 
INNER JOIN expense AS T2 ON T1.event_id = T2.event_id 
ORDER BY T2.cost ASC, T1.event_name ASC 
LIMIT 1
```

### Q1390 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** collapses the required event->budget->expense chain to a nonexistent direct event->expense join, same pattern as Q1338

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T2.cost ELSE 0 END) * 100.0 / SUM(T2.cost)) AS percentage
FROM 
    event AS T1
INNER JOIN 
    expense AS T2 ON T1.event_id = T2.event_id
```

### Q1398 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'advertisement' vs gold's 'Advertisement' case mismatch (join and amount_spent rename are both correct)

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.event_id WHERE T2.category = 'advertisement' ORDER BY T2.amount_spent DESC LIMIT 1
```

### Q1404 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes budget.amount for expense.cost and budget.event_status='Approved' for expense.is_approved='true'; drops the expense table entirely

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
SELECT T2.category, SUM(T2.amount) 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.event_id 
WHERE T1.event_name = 'October Meeting' AND T2.event_status = 'Approved'
```

### Q1411 (simple, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds DISTINCT that gold's flat (non-deduped) query doesn't have

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.member_id WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

### Q1422 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes budget.category (reached via an unneeded join) for event.type

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.event_id WHERE T1.location = 'MU 215'
```

### Q1427 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the T1.type='Guest Speaker' filter entirely; also missing DISTINCT (join/columns otherwise correct renames)

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT T1.category 
FROM budget AS T1 
INNER JOIN event AS T2 ON T1.event_id = T2.event_id 
WHERE T2.location = 'MU 215' AND T1.amount_spent = 0
```

### Q1432 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps the WHERE/CASE roles: filters on amount=50 plus an added income_source='Student_Club' condition while aggregating over t_shirt_size='Medium', the inverse of gold's WHERE t_shirt_size='Medium' AND position='Member' with CASE WHEN amount=50

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.t_shirt_size = 'Medium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM member AS T1 
INNER JOIN income AS T2 ON T1.member_id = T2.member_id 
WHERE T2.amount = 50 AND T2.income_source = 'Student_Club'
```

### Q1435 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'game'/'closed' vs gold's 'Game'/'Closed' case mismatch; also missing DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT event_name FROM event WHERE type = 'game' AND status = 'closed' AND event_date BETWEEN '2019-03-15' AND '2020-03-20'
```

### Q1457 (challenging, aggregate) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** omits DISTINCT so members with multiple qualifying expenses appear as duplicate rows (the dropped budget join is vestigial/non-restrictive and not the real cause)

**Gold SQL:**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name, T1.phone 
FROM member AS T1 
INNER JOIN expense AS T2 ON T1.member_id = T2.member_id 
WHERE T2.cost > (SELECT AVG(cost) FROM expense)
```

### Q1460 (challenging, retrieval) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** adds a GROUP BY T1.member_id / SUM(cost) aggregation where gold's flat query has none; also splits gold's single compound expense_description literal into three separate lowercase alternatives via IN, which likely matches nothing

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name, SUM(T2.cost) 
FROM member AS T1 
INNER JOIN expense AS T2 ON T1.member_id = T2.member_id 
WHERE T2.expense_description IN ('water', 'veggie tray', 'supplies') 
GROUP BY T1.member_id;
```

---

## superhero (19 failures)

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the height_cm IS NOT NULL AND != 0 filters gold has; also adds an extra height_cm output column beyond gold's superhero_name-only SELECT

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name, T1.height_cm 
FROM superhero AS T1 
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id 
WHERE T2.publisher_name = 'Marvel Comics' 
ORDER BY T1.height_cm DESC
```

### Q728 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's RANK() OVER (ORDER BY COUNT DESC) window-function output column entirely, replacing it with a plain ORDER BY (missing a column from the SELECT list)

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT T3.colour, COUNT(*) AS count 
FROM superhero AS T1 
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id 
INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id 
WHERE T2.publisher_name = 'Marvel Comics' 
GROUP BY T3.colour 
ORDER BY count DESC
```

### Q736 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's WHERE attribute_value=(SELECT MIN(...)) subquery match (which could return multiple tied heroes) into ORDER BY ASC LIMIT 1

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Intelligence' ORDER BY T2.attribute_value ASC LIMIT 1
```

### Q740 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references hero_attribute.attribute_name (no such column; attribute_name lives on the attribute lookup table, which isn't joined at all)

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.attribute_name = 'Strength' AND T2.attribute_value = 100 AND T4.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.id) 
FROM superhero AS T1 
INNER JOIN gender AS T2 ON T1.gender_id = T2.id 
INNER JOIN hero_attribute AS T3 ON T1.id = T3.hero_id 
WHERE T2.gender = 'Female' AND T3.attribute_name = 'Strength' AND T3.attribute_value = 100
```

### Q743 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses alignment='Selfish' instead of gold's actual domain value 'Bad'

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN T1.alignment = 'Selfish' THEN T1.id END) * 100.0 / COUNT(T1.id)) AS percentage_selfish,
    COUNT(CASE WHEN T1.alignment = 'Selfish' AND T4.publisher_name = 'Marvel Comics' THEN T1.id END) AS count_marvel_selfish
FROM 
    alignment AS T1
INNER JOIN 
    superhero AS T2 ON T1.id = T2.alignment_id
INNER JOIN 
    publisher AS T4 ON T2.publisher_id = T4.id
```

### Q744 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses 'DC' instead of the actual stored publisher value 'DC Comics', so no real DC Comics heroes are counted at all; also outputs the raw count of the winning publisher instead of gold's Marvel-minus-DC difference value

**Gold SQL:**

```sql
SELECT CASE WHEN marvel_cnt > dc_cnt THEN 'Marvel Comics' ELSE 'DC Comics' END AS publisher_with_more_superheroes,
       marvel_cnt - dc_cnt AS difference
FROM (
    SELECT SUM(CASE WHEN p.`publisher_name`='Marvel Comics' THEN 1 END) AS marvel_cnt,
           SUM(CASE WHEN p.`publisher_name`='DC Comics' THEN 1 END)    AS dc_cnt
    FROM `superhero` s
    JOIN `publisher` p ON s.`publisher_id` = p.`id`
) t;
```

**Predicted SQL:**

```sql
SELECT 
    p.publisher_name, 
    COUNT(s.id) AS superhero_count
FROM 
    publisher p
JOIN 
    superhero s ON p.id = s.publisher_id
WHERE 
    p.publisher_name IN ('DC', 'Marvel Comics')
GROUP BY 
    p.publisher_name
ORDER BY 
    superhero_count DESC
LIMIT 1;
```

### Q750 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the weight_kg > 0 filter gold has, letting zero-weight placeholder entries skew the average

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(T1.weight_kg) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id WHERE T2.gender = 'Female'
```

### Q753 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** misinterprets the real colour-table value 'No Colour' as meaning 'no eye_colour_id at all', replacing gold's INNER JOIN + colour='No Colour' equality with a LEFT JOIN + IS NULL anti-join pattern; also drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name 
FROM superhero AS T1 
LEFT JOIN colour AS T2 ON T1.eye_colour_id = T2.id 
WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.id IS NULL
```

### Q758 (moderate, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DISTINCT; if multiple qualifying heroes share the same hair colour, duplicate rows would appear

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.race = 'Human' AND T1.height_cm = 185
```

### Q766 (moderate, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DISTINCT (the CTE-vs-nested-subquery restructuring is otherwise functionally equivalent to gold's max-strength match); duplicate name rows could appear if a hero has more than one hero_attribute row for Strength

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT T1.full_name 
FROM superhero AS T1 
INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id 
INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id 
WHERE T3.attribute_name = 'Strength' 
AND T2.attribute_value = (SELECT MAX(attribute_value) FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'Strength'))
```

### Q772 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** resolves eye_colour_id/hair_colour_id/skin_colour_id to their descriptive colour names via extra joins to the colour table, instead of returning gold's requested raw ID values

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT T2.colour AS eye_colour, T3.colour AS hair_colour, T4.colour AS skin_colour 
FROM superhero AS T1 
INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id 
INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id 
INNER JOIN colour AS T4 ON T1.skin_colour_id = T4.id 
INNER JOIN gender AS T5 ON T1.gender_id = T5.id 
INNER JOIN publisher AS T6 ON T1.publisher_id = T6.id 
WHERE T5.gender = 'Female' AND T6.publisher_name = 'Dark Horse Comics'
```

### Q775 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes superhero.eye_colour_id for gold's superhero.skin_colour_id -- two different real foreign keys, both joining to the same colour lookup table

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero AS T1 
INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id 
INNER JOIN gender AS T3 ON T1.gender_id = T3.id 
WHERE T3.gender = 'Female'
```

### Q788 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps the WHERE/CASE roles: filters to Marvel-only heroes in WHERE and checks gender in CASE, computing % of Marvel heroes that are female instead of gold's % of female heroes that are Marvel

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender_id = (SELECT id FROM gender WHERE gender = 'Female') THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero AS T1 
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id 
WHERE T2.publisher_name = 'Marvel Comics'
```

### Q791 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the height_cm > 0 filter gold has entirely, letting zero/placeholder heights skew the average

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### Q794 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's WHERE attribute_value=(SELECT MAX(...)) subquery match (which could return multiple tied heroes) into ORDER BY DESC LIMIT 1

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Speed' ORDER BY T2.attribute_value DESC LIMIT 1
```

### Q798 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T1.publisher_name where T1=superhero (no such column); the value belongs to the already-joined publisher aliased T2

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')
```

**Predicted SQL:**

```sql
SELECT T.publisher_name FROM ( SELECT T1.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy') GROUP BY T1.publisher_name HAVING COUNT(DISTINCT T1.superhero_name) = 3 ) AS T
```

### Q819 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** the second term substitutes 'eye_colour_id IS NULL' for gold's specific colour_id=1 match (a real, specific colour value, not a null/absence check); also drops the 'weight_kg=0' OR-condition entirely, checking only IS NULL

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM superhero WHERE weight_kg IS NULL AND eye_colour_id = (SELECT id FROM colour WHERE colour = 'Blue')) -
    (SELECT COUNT(*) FROM superhero WHERE weight_kg IS NULL AND eye_colour_id IS NULL) AS difference
```

### Q825 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes hero_attribute/attribute (numeric attributes like Strength/Speed) for gold's hero_power/superpower (named powers like 'Phoenix Force') -- two different real table pairs

**Gold SQL:**

```sql
SELECT T4.gender FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.power_name = 'Phoenix Force'
```

**Predicted SQL:**

```sql
SELECT T4.gender 
FROM superhero AS T1 
INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id 
INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id 
INNER JOIN gender AS T4 ON T1.gender_id = T4.id 
WHERE T3.attribute_name = 'Phoenix Force'
```

### Q829 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses 'DC' instead of the actual stored publisher value 'DC Comics', so no real DC Comics heroes are ever counted; also drops the CASE-based publisher_with_more_superheroes label column entirely from the output

**Gold SQL:**

```sql
SELECT CASE WHEN marvel_cnt > dc_cnt THEN 'Marvel Comics' ELSE 'DC Comics' END AS publisher_with_more_superheroes,
        dc_cnt - marvel_cnt AS difference
FROM (
    SELECT SUM(CASE WHEN p.`publisher_name`='Marvel Comics' THEN 1 END) AS marvel_cnt,
           SUM(CASE WHEN p.`publisher_name`='DC Comics' THEN 1 END)    AS dc_cnt
    FROM `superhero` s
    JOIN `publisher` p ON s.`publisher_id` = p.`id`
) t;
```

**Predicted SQL:**

```sql
SELECT (COUNT(CASE WHEN T2.publisher_name = 'DC' THEN T1.id END) - COUNT(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN T1.id END)) AS difference
FROM superhero AS T1
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id
```

---

## thrombosis_prediction (42 failures)

### Q1150 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** moves the SEX='F' filter from WHERE into the CASE condition and drops the outer WHERE entirely, changing the denominator from the female-only count to the total-patient count

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'F' AND strftime('%Y', birthday) > '1930' THEN 1 ELSE 0 END) AS FLOAT) * 100 / COUNT(*) FROM Patient;
```

### Q1155 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 245 invented instead of gold's 500 (LDH->lactate_dehydrogenase rename is correct)

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.birthday 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.lactate_dehydrogenase > 245
```

### Q1156 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes Examination.Thrombosis>0 for gold's Examination.RVVT='+' (two different real Examination columns); also computes age from first_hospital_visit_date (First Date) instead of the current date

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT T1.ID, STRFTIME('%Y', T1.first_hospital_visit_date) - STRFTIME('%Y', T1.birthday) AS age FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.thrombosis_degree > 0
```

### Q1157 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** compares thrombosis_degree to the string 'severe' instead of gold's integer code 2

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.thrombosis_degree = 'severe'
```

### Q1162 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on Patient.First Date (first_hospital_visit_date) instead of gold's Patient.Description (first_record_date) -- both real Patient date columns, wrong one used

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE sex = 'F' 
AND strftime('%Y', first_hospital_visit_date) = '1997' 
AND admission_type = '-';
```

### Q1164 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** adds an uncalled-for correlated subquery (thrombosis_degree = MAX(thrombosis_degree)) in place of gold's fixed literal Thrombosis=1; also drops the COUNT(DISTINCT ID) dedup

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
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'F' 
AND T2.thrombosis_degree = (SELECT MAX(thrombosis_degree) FROM Examination) 
AND strftime('%Y', T2.examination_date) = '1997'
```

### Q1169 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's per-sex conditional thresholds (UA<=8.0 for M, <=6.5 for F) into a single uric_acid>7.0 filter applied to both sexes, reversing the comparison direction and losing the per-sex distinction

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
WITH abnormal_uric_acid AS (
    SELECT ID, sex
    FROM Patient
    WHERE ID IN (
        SELECT ID
        FROM Laboratory
        WHERE uric_acid > 7.0  -- Assuming 7.0 mg/dL as the threshold for abnormal uric acid
    )
)
SELECT 
    CAST(SUM(CASE WHEN sex = 'M' THEN 1 ELSE 0 END) AS FLOAT) / SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM abnormal_uric_acid;
```

### Q1171 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** age filter uses < 0 instead of gold's < 18

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.birthday IS NOT NULL 
AND T2.examination_date BETWEEN '1990-01-01' AND '1993-12-31' 
AND STRFTIME('%Y', T2.examination_date) - STRFTIME('%Y', T1.birthday) < 0;
```

### Q1175 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** selects Examination.Diagnosis instead of Patient.Diagnosis -- both tables have a real Diagnosis column, wrong one used; also outputs raw birthday instead of the age-difference expression

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.birthday, E.diagnosis 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
JOIN Laboratory L ON P.ID = L.ID 
ORDER BY L.hemoglobin DESC 
LIMIT 1
```

### Q1179 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses Patient.First Date (first_hospital_visit_date) instead of gold's Patient.Description (first_record_date) to match '1994-02-19'; also selects extra aCL IgG/IgA columns beyond gold's single aCL IgM

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT T1.anticardiolipin_igg, T1.anticardiolipin_igm, T1.anticardiolipin_iga 
FROM Examination AS T1 
INNER JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T2.diagnosis = 'SLE' AND T2.first_hospital_visit_date = '1994-02-19' 
AND T1.examination_date = '1993-11-12';
```

### Q1185 (challenging, aggregate) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** uses MAX for November and MIN for December instead of gold's matching SUM/SUM, an asymmetric aggregate-function choice

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(CASE WHEN strftime('%m', T1.Date) = '11' THEN T1.total_cholesterol END) - 
     MIN(CASE WHEN strftime('%m', T1.Date) = '12' THEN T1.total_cholesterol END)) / 
    MAX(CASE WHEN strftime('%m', T1.Date) = '11' THEN T1.total_cholesterol END) AS decrease_rate
FROM 
    Laboratory AS T1 
INNER JOIN 
    Patient AS T2 
ON 
    T1.ID = T2.ID 
WHERE 
    T2.birthday = '1959-02-18' 
    AND strftime('%Y', T1.Date) = '1981'
    AND T1.total_cholesterol IS NOT NULL;
```

### Q1187 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** applies the date-range filter to Examination.Examination_Date instead of gold's Laboratory.Date; also adds an unneeded Patient join

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT T1.ID 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
INNER JOIN Examination AS T3 ON T1.ID = T3.ID 
WHERE T3.examination_date BETWEEN '1987-07-06' AND '1996-01-31' 
AND T2.aspartate_aminotransferase > 30 
AND T2.albumin < 4;
```

### Q1189 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** the correlated subquery's average is computed over all Examination rows instead of the same Thrombosis=2/ANA Pattern='S' filtered subset gold's subquery uses

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Examination AS T1 
JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T1.thrombosis_degree = 2 
AND T1.antinuclear_antibody_pattern = 'S' 
AND T1.anticardiolipin_igm > (SELECT AVG(anticardiolipin_igm) * 1.2 FROM Examination)
```

### Q1192 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents a BETWEEN 0.3-1.2 'normal range' for T-BIL instead of gold's single <2.0 threshold

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.admission_type = '-' 
AND T2.Date BETWEEN '1991-10-01' AND '1991-10-31' 
AND T2.total_bilirubin BETWEEN 0.3 AND 1.2;
```

### Q1205 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's per-sex threshold logic (M:>8.0, F:>6.5) into a single generic BETWEEN 2.4-7.0 'normal range' check unrelated to the patient's actual sex-based comparison

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN T2.uric_acid BETWEEN 2.4 AND 7.0 THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

### Q1208 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 40 invented instead of gold's 60 (GPT->alanine_aminotransferase rename is correct)

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'M' 
AND T2.alanine_aminotransferase > 40;
```

### Q1209 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes Laboratory.GOT (aspartate_aminotransferase) for gold's Laboratory.GPT (alanine_aminotransferase) -- two different real lab columns; also wrong threshold (40 vs 60)

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT T1.diagnosis 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.aspartate_aminotransferase > 40 
ORDER BY T1.birthday ASC;
```

### Q1220 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents a BETWEEN 13-20 'normal range' for UN instead of gold's exact match =29

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.birthday 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.urea_nitrogen BETWEEN 13 AND 20;
```

### Q1225 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restructures gold's single-sided T-BIL>=2.0 threshold into an invented two-sided 'normal range' exclusion (<0.3 OR >1.2); also uses COUNT(*) instead of gold's GROUP_CONCAT(DISTINCT ID), answering a count instead of a list of IDs

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.sex, COUNT(*) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.total_bilirubin < 0.3 OR L.total_bilirubin > 1.2 
GROUP BY P.sex;
```

### Q1227 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's fixed T-CHO>=250 literal with a dynamically computed subquery threshold (AVG(total_cholesterol)) that gold doesn't have

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(STRFTIME('%Y', 'now') - STRFTIME('%Y', birthday)) AS average_age 
FROM Patient 
WHERE sex = 'M' AND ID IN (
    SELECT ID 
    FROM Laboratory 
    WHERE total_cholesterol > (SELECT AVG(total_cholesterol) FROM Laboratory)
)
```

### Q1229 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 150 invented instead of gold's 200 (TG->triglyceride rename is correct); also missing DISTINCT dedup

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.triglyceride > 150 AND 
      STRFTIME('%Y', 'now') - STRFTIME('%Y', T1.birthday) > 50
```

### Q1231 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 100 invented instead of gold's 250 (CPK->creatinine_phosphokinase rename is correct)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'M' 
AND T1.birthday BETWEEN '1936-01-01' AND '1956-12-31' 
AND T2.creatinine_phosphokinase > 100;
```

### Q1232 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's single-sided thresholds (GLU>=180, T-CHO<250) with invented two-sided 'normal ranges' on both, plus a missing-parentheses operator-precedence bug around the OR condition

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, P.sex, STRFTIME('%Y', 'now') - STRFTIME('%Y', P.birthday) AS age 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.blood_glucose < 70 OR L.blood_glucose > 110 
AND L.total_cholesterol >= 150 AND L.total_cholesterol <= 200;
```

### Q1235 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** introduces a dynamic AVG(red_blood_cell_count) subquery threshold in place of gold's fixed literal <3.5; also miscalculates age using first_hospital_visit_date instead of the current date and drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT T1.ID, STRFTIME('%Y', T1.first_hospital_visit_date) - STRFTIME('%Y', T1.birthday) AS age, T1.diagnosis 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.red_blood_cell_count < (SELECT AVG(red_blood_cell_count) FROM Laboratory)
```

### Q1238 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents a BETWEEN 13.5-17.5 'normal range' for HGB instead of gold's (10, 17) bounds

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.diagnosis = 'SLE' AND T2.hemoglobin BETWEEN 13.5 AND 17.5 
ORDER BY T1.birthday ASC 
LIMIT 1
```

### Q1239 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 45 invented instead of gold's 52 for HCT; also miscalculates age using first_hospital_visit_date instead of the current date

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT T1.ID, STRFTIME('%Y', T1.first_hospital_visit_date) - STRFTIME('%Y', T1.birthday) AS age 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.hematocrit > 45 
GROUP BY T1.ID 
HAVING COUNT(T2.ID) >= 2
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thresholds 150/450 invented instead of gold's 100/400 for platelet count; also counts rows rather than DISTINCT patient IDs

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
WITH platelet_levels AS (
    SELECT 
        P.ID,
        L.platelet_count,
        CASE 
            WHEN L.platelet_count < 150 THEN 'low'
            WHEN L.platelet_count > 450 THEN 'high'
            ELSE 'normal'
        END AS platelet_status
    FROM 
        Patient P
    INNER JOIN 
        Laboratory L ON P.ID = L.ID
)
SELECT 
    COUNT(CASE WHEN platelet_status = 'low' THEN 1 END) AS low_platelet_count,
    COUNT(CASE WHEN platelet_status = 'high' THEN 1 END) AS high_platelet_count
FROM 
    platelet_levels;
```

### Q1242 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents platelet thresholds in the wrong unit scale (150000-450000) instead of gold's 100-400

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE strftime('%Y', T2.Date) = '1984' 
AND strftime('%Y', 'now') - strftime('%Y', T1.birthday) < 50 
AND T2.platelet_count BETWEEN 150000 AND 450000;
```

### Q1243 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses an invented PT threshold (>13.5) instead of gold's given threshold (>=14); also doesn't dedupe by DISTINCT patient ID

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
WITH age_filtered AS (
    SELECT P.ID, P.sex, L.prothrombin_time
    FROM Patient P
    INNER JOIN Laboratory L ON P.ID = L.ID
    WHERE strftime('%Y', 'now') - strftime('%Y', P.birthday) > 55
),
abnormal_pt AS (
    SELECT ID, sex
    FROM age_filtered
    WHERE prothrombin_time > 13.5 -- Assuming normal PT is <= 13.5 seconds
)
SELECT 
    CAST(SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) AS FLOAT) * 100 / COUNT(*) AS percentage_female_with_abnormal_pt
FROM abnormal_pt;
```

### Q1247 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invents WBC thresholds in the wrong unit scale (4000-11000) instead of gold's 3.5-9.0; also a slightly different FG boundary (400/< instead of 450/<=)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'M' 
AND T2.white_blood_cell_count BETWEEN 4000 AND 11000 
AND (T2.fibrinogen < 150 OR T2.fibrinogen > 400)
```

### Q1251 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 1500 invented instead of gold's 2000 for IGG; also doesn't dedupe by DISTINCT patient ID

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Laboratory WHERE immunoglobulin_g > 1500;
```

### Q1252 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references Patient.symptoms (no such column; Symptoms only exists on Examination, which isn't joined at all); also compares IGG to the invented string 'normal' instead of gold's BETWEEN 900-2000

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.immunoglobulin_g = 'normal' AND T1.symptoms IS NOT NULL;
```

### Q1254 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** compares immunoglobulin_a to the invented string 'normal' instead of gold's numeric BETWEEN 80 AND 500 range

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.immunoglobulin_a = 'normal' 
AND T1.first_hospital_visit_date > '1990-01-01'
```

### Q1255 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's two-sided abnormal-range filter (IGM<=40 OR IGM>=400) with a simple >0 check, changing which patients qualify entirely

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT diagnosis, COUNT(*) AS count 
FROM Patient 
WHERE ID IN (
    SELECT ID 
    FROM Laboratory 
    WHERE immunoglobulin_m > 0
) 
GROUP BY diagnosis 
ORDER BY count DESC 
LIMIT 1
```

### Q1256 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** inverts the CRP condition (NOT IN patients who ever have a non-null CRP record) instead of gold's CRP='+' positive-result match, and drops the Description IS NULL filter entirely

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE ID NOT IN (SELECT ID FROM Laboratory WHERE c_reactive_protein IS NOT NULL)
```

### Q1257 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's single-sided CRE>=1.5 threshold with an invented two-sided 'abnormal range' (creatinine<0.8 OR >1.2), plus a missing-parentheses operator-precedence bug that detaches the age filter from the first OR branch

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Laboratory AS T1 
INNER JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T1.creatinine < 0.8 OR T1.creatinine > 1.2 
AND STRFTIME('%Y', 'now') - STRFTIME('%Y', T2.birthday) < 70;
```

### Q1265 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses 'normal' instead of gold's ('negative' OR '0') alternatives for RNP; also COUNT(*) instead of COUNT(DISTINCT ID)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.anti_ribonuclear_protein = 'normal' AND T1.admission_type = '+'
```

### Q1267 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references Patient.thrombosis_degree (no such column; Thrombosis only exists on Examination, which isn't joined at all)

**Gold SQL:**

```sql
WITH normal_sm AS (
  SELECT DISTINCT `ID`
  FROM `Laboratory`
  WHERE `SM` IN ('negative','0')
), no_thrombosis AS (
  SELECT n.`ID`
  FROM normal_sm n
  JOIN `Examination` e ON e.`ID` = n.`ID`
  GROUP BY n.`ID`
  HAVING MAX(COALESCE(e.`Thrombosis`,0)) = 0
)
SELECT COUNT(*)
FROM no_thrombosis;
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.anti_sm = 'normal' AND T1.thrombosis_degree = 'none'
```

### Q1270 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references Patient.symptoms (no such column; Symptoms only exists on Examination, which isn't joined at all)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT p.ID)
FROM `Patient`   p
JOIN `Laboratory` l ON p.ID = l.ID
WHERE p.SEX = 'F'
  AND l.SC170 IN ('negative','0')
  AND NOT EXISTS (  
        SELECT 1
        FROM `Examination` e
        WHERE e.ID = p.ID
          AND e.Symptoms IS NOT NULL
  );
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.anti_scl70 = 'normal' AND T1.sex = 'F' AND T1.symptoms IS NULL;
```

### Q1275 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses 'normal' instead of gold's ('negative' OR '0') for both anti_centromere and anti_ssb; also COUNT(*) instead of COUNT(DISTINCT ID)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'M' 
AND T2.anti_centromere = 'normal' 
AND T2.anti_ssb = 'normal';
```

### Q1281 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an OR alanine_aminotransferase>40 alternative not in gold, lowers the GOT threshold to 40 (from 60), and replaces ORDER BY Birthday DESC LIMIT 1 with MIN(birthday) (opposite direction -- oldest instead of youngest)

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(T2.birthday) 
FROM Laboratory AS T1 
INNER JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T1.aspartate_aminotransferase > 40 OR T1.alanine_aminotransferase > 40
```

### Q1302 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references creatinine_phosphokinase directly on Examination (no such column; CPK only exists on Laboratory, which isn't joined); single-table query also drops the KCT/RVVT/LAC OR-conditions entirely

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Examination 
WHERE creatinine_phosphokinase BETWEEN 10 AND 200 AND thrombosis_degree > 0;
```

---

## toxicology (35 failures)

### Q200 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects molecule.label (constant '+' for all matched rows) instead of gold's molecule_id; also uses bond_type='=' instead of gold's '#'

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT T2.label FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '=' AND T2.label = '+'
```

### Q201 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** joins atom to bond via the connected/bond_id relationship (atoms that are bond endpoints) instead of gold's direct atom.molecule_id=bond.molecule_id relationship (atoms belonging to a molecule with at least one double bond) -- a different join path/grain entirely; also uses 'C' instead of gold's lowercase 'c'

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
WITH carbon_atoms_in_double_bonds AS (
    SELECT atom.molecule_id, SUM(atom.element = 'C') AS carbon_count
    FROM atom
    JOIN connected ON atom.atom_id = connected.atom_id
    JOIN bond ON connected.bond_id = bond.bond_id
    WHERE bond.bond_type = '='
    GROUP BY atom.molecule_id
),
total_atoms_in_double_bonds AS (
    SELECT atom.molecule_id, COUNT(*) AS total_atom_count
    FROM atom
    JOIN connected ON atom.atom_id = connected.atom_id
    JOIN bond ON connected.bond_id = bond.bond_id
    WHERE bond.bond_type = '='
    GROUP BY atom.molecule_id
)
SELECT CAST(SUM(carbon_atoms_in_double_bonds.carbon_count) AS REAL) * 100 / SUM(total_atoms_in_double_bonds.total_atom_count) AS percentage_of_carbon
FROM carbon_atoms_in_double_bonds
JOIN total_atoms_in_double_bonds ON carbon_atoms_in_double_bonds.molecule_id = total_atoms_in_double_bonds.molecule_id
```

### Q206 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** references bond.label (no such column; label lives on molecule, which isn't joined at all); gold's actual filter is simply connected.bond_id='TR004_8_9', a specific bond identifier, not a molecule label

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.element 
FROM bond AS T1 
JOIN connected AS T2 ON T1.bond_id = T2.bond_id 
JOIN atom AS T3 ON T2.atom_id = T3.atom_id 
WHERE T1.label = 'TR004_8_9'
```

### Q208 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case mismatch: 'H' instead of gold's lowercase 'h' (the outer derived-table wrapper omission is vestigial and not the actual cause)

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'H' GROUP BY T2.label ORDER BY COUNT(*) DESC LIMIT 1
```

### Q212 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's HAVING COUNT(*) = (SELECT MIN(cnt)...) tie-preserving pattern into ORDER BY COUNT(element) ASC LIMIT 1 (the label != '+' vs label = '-' substitution is functionally equivalent given the binary domain)

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
SELECT T3.element 
FROM molecule AS T1 
JOIN atom AS T3 ON T1.molecule_id = T3.molecule_id 
WHERE T1.label != '+' 
GROUP BY T3.element 
ORDER BY COUNT(T3.element) ASC 
LIMIT 1
```

### Q213 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares atom.element (a chemical element like 'c'/'h') to atom-id-shaped literals ('TR004_8'/'TR004_20') instead of matching atom_id/atom_id2 directly; also drops the OR reverse-direction check gold has

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT T3.bond_type 
FROM atom AS T1 
JOIN connected AS T2 ON T1.atom_id = T2.atom_id 
JOIN bond AS T3 ON T2.bond_id = T3.bond_id 
WHERE T1.element = 'TR004_8' AND T2.atom_id2 IN (SELECT atom_id FROM atom WHERE element = 'TR004_20')
```

### Q215 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case mismatch: 'I'/'S' instead of gold's lowercase 'i'/'s'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
WITH single_bond_molecules AS (
    SELECT DISTINCT bond.molecule_id 
    FROM bond 
    WHERE bond.bond_type = '-'
)
SELECT 
    SUM(CASE WHEN atom.element = 'I' THEN 1 ELSE 0 END) AS iodine_count,
    SUM(CASE WHEN atom.element = 'S' THEN 1 ELSE 0 END) AS sulfur_count
FROM 
    atom
JOIN 
    single_bond_molecules 
ON 
    atom.molecule_id = single_bond_molecules.molecule_id
```

### Q218 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** adds an unneeded bond join before LEFT JOINing atom, multiplying each atom row once per bond in its molecule and inflating the non-fluorine count; also case-mismatches element 'F' instead of gold's lowercase 'f'

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T3.element != 'F', 1, 0)) AS REAL) * 100 / COUNT(DISTINCT T1.molecule_id) 
FROM bond AS T1 
INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
LEFT JOIN atom AS T3 ON T1.molecule_id = T3.molecule_id 
WHERE T2.label = '+'
```

### Q219 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses bond_type='=' instead of gold's '#'; also computes the percentage over all matching bond-molecule join rows instead of gold's COUNT(DISTINCT molecule_id), which could double-count molecules with multiple matching bonds

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T2.label = '+', 1, 0)) AS REAL) * 100 / COUNT(*) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '='
```

### Q220 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares molecule.label (a '+'/'-' indicator) to 'TR000' (a molecule_id value) instead of directly filtering atom.molecule_id='TR000' -- label can never equal an identifier-shaped string, so this subquery returns no rows at all

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE molecule_id IN (SELECT molecule_id FROM molecule WHERE label = 'TR000') ORDER BY element ASC LIMIT 3
```

### Q226 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares molecule.label (a '+'/'-' indicator) to 'TR008' (a molecule_id value) instead of directly filtering bond.molecule_id='TR008' (bond already carries molecule_id directly, no join needed at all)

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '=', 1, 0)) AS REAL) * 100 / COUNT(*) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR008'
```

### Q227 (simple, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** adds an unneeded join to bond (gold's query is single-table over molecule with no join at all), which weights each molecule by its bond count instead of counting each molecule once, distorting the percentage

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T2.label = '+', 1, 0)) AS REAL) * 100 / COUNT(*) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id
```

### Q228 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares molecule.label to 'TR206' (a molecule_id value) instead of directly filtering atom.molecule_id='TR206' (no join needed at all); also case-mismatches element='H' instead of gold's lowercase 'h'

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR206'
```

### Q230 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label='TR060' instead of gold's molecule_id='TR060' (label can never equal an identifier-shaped string, so this returns no rows); also drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT atom.element, molecule.label 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR060'
```

### Q231 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label='TR010' instead of gold's bond.molecule_id='TR010' directly (no join needed at all; label can never equal an identifier-shaped string)

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT T1.bond_type FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.bond_id) DESC LIMIT 1
```

### Q232 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects/orders by molecule.label (constant '-' for every matched row) instead of gold's molecule_id

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT T2.label 
FROM bond AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T1.bond_type = '-' AND T2.label != '+' 
ORDER BY T2.label ASC 
LIMIT 3
```

### Q234 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares connected.atom_id/atom_id2 to the bare integer 12 instead of gold's full string 'TR009_12'; also filters via a nonexistent molecule.label='TR009' match (label is only '+'/'-', never a molecule-id prefix) instead of directly matching atom_id/atom_id2

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM bond 
JOIN connected ON bond.bond_id = connected.bond_id 
JOIN molecule ON bond.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR009' AND (connected.atom_id = 12 OR connected.atom_id2 = 12)
```

### Q236 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T4.atom_id2 where T4=atom (no such column; the value is already available via the joined connected aliased T2); also filters via a nonexistent molecule.label='TR001_6_9' match instead of directly matching connected.bond_id

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT T1.bond_type, T3.atom_id, T4.atom_id2 
FROM bond AS T1 
JOIN connected AS T2 ON T1.bond_id = T2.bond_id 
JOIN atom AS T3 ON T2.atom_id = T3.atom_id 
JOIN atom AS T4 ON T2.atom_id2 = T4.atom_id 
JOIN molecule AS T5 ON T1.molecule_id = T5.molecule_id 
WHERE T5.label = 'TR001_6_9'
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's SUBSTR(atom_id,-2) suffix-matching transformation, instead comparing the full atom_id/atom_id2 strings to the bare integer 19, which can never match the real 'TRxxx_19'-shaped values

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected WHERE atom_id = 19 OR atom_id2 = 19
```

### Q240 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label='TR004' instead of gold's atom.molecule_id='TR004' directly (no join needed at all; label can never equal an identifier-shaped string)

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom.element 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR004'
```

### Q242 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's SUBSTR(atom_id,-2) suffix extraction, instead comparing the full atom_id string directly to numeric bounds 21-25, which can't correctly match the real 'TRxxx_NN'-shaped identifier strings

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.molecule_id 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T1.atom_id BETWEEN 21 AND 25 AND T2.label = '+'
```

### Q243 (moderate, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** adds an extra bond_type column to the SELECT list beyond gold's bond_id-only output; also restructures gold's IN-subquery (checking element='p' via one atom_id lookup, then 'n' via the outer atom) into a rigid double-join fixing 'p' to the atom_id side and 'n' to the atom_id2 side

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT bond.bond_id, bond.bond_type 
FROM bond 
JOIN connected ON bond.bond_id = connected.bond_id 
JOIN atom AS atom1 ON connected.atom_id = atom1.atom_id 
JOIN atom AS atom2 ON connected.atom_id2 = atom2.atom_id 
WHERE atom1.element = 'p' AND atom2.element = 'n'
```

### Q244 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's CTE-based tie-preserving MAX(cnt) match into ORDER BY COUNT(bond_id) DESC LIMIT 1

**Gold SQL:**

```sql
with sub as ( SELECT T.molecule_id, COUNT(T.bond_type) as cnt
 FROM bond AS T WHERE T.bond_type = '=' GROUP BY T.molecule_id 
) 
SELECT T1.label FROM molecule AS T1 INNER JOIN sub
 AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.cnt = (select max(cnt) from sub)
```

**Predicted SQL:**

```sql
SELECT T2.label 
FROM bond AS T1 
INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T1.bond_type = '=' 
GROUP BY T1.molecule_id 
ORDER BY COUNT(T1.bond_id) DESC 
LIMIT 1
```

### Q245 (moderate, aggregate) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** drops the '/COUNT(atom_id)' denominator entirely, computing AVG() of a single already-aggregated count (a no-op) instead of gold's bonds-per-atom ratio; also case-mismatches element 'I' instead of gold's lowercase 'i'

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
WITH iodine_bonds AS (
    SELECT COUNT(*) AS bond_count
    FROM atom AS T1
    JOIN connected AS T2 ON T1.atom_id = T2.atom_id
    WHERE T1.element = 'I'
)
SELECT AVG(bond_count) AS average_bonds
FROM iodine_bonds;
```

### Q247 (challenging, retrieval) — **Other** (Missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** drops the outer DISTINCT, so every disconnected atom's element appears as a separate row instead of gold's deduped element list (the inner subquery's DISTINCT omission is vestigial for a NOT IN test)

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE atom_id NOT IN (SELECT atom_id FROM connected)
```

### Q248 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label='TR041' instead of gold's bond.molecule_id='TR041' directly (bond already carries molecule_id; no join needed); also uses bond_type='=' instead of gold's '#', and selects an extra atom_id2 column beyond gold's atom_id

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT T3.atom_id, T3.atom_id2 
FROM molecule AS T1 
JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id 
JOIN connected AS T3 ON T2.bond_id = T3.bond_id 
WHERE T1.label = 'TR041' AND T2.bond_type = '='
```

### Q249 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label='TR144_8_19' instead of gold's connected.bond_id='TR144_8_19' directly (no molecule join needed at all; label can never equal an identifier-shaped string)

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT atom.element 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR144_8_19'
```

### Q253 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses bond_type='=' instead of gold's '#' (join/columns otherwise correct)

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.element 
FROM bond AS T1 
JOIN connected AS T2 ON T1.bond_id = T2.bond_id 
JOIN atom AS T3 ON T2.atom_id = T3.atom_id 
WHERE T1.bond_type = '='
```

### Q255 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps the WHERE/CASE roles: filters to label='+' molecules in WHERE and checks bond_type in CASE, computing % of a '+' molecule's bonds that are single bonds instead of gold's % of single bonds that belong to a '+' molecule

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) * 100 / COUNT(*) AS proportion_single_bonds_carcinogenic 
FROM bond AS T1 
INNER JOIN molecule AS T2 
ON T1.molecule_id = T2.molecule_id 
WHERE T2.label = '+'
```

### Q260 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restructures gold's second molecule-membership filter (molecules containing a p/br atom) into a direct atom.element IN ('p','br') filter, counting only p/br atoms instead of all atoms in qualifying molecules; also uses bond_type='=' instead of gold's '#'

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM atom 
WHERE molecule_id IN (
    SELECT molecule_id 
    FROM bond 
    WHERE bond_type = '='
) 
AND element IN ('p', 'br')
```

### Q263 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case mismatch: 'Cl' instead of gold's lowercase 'cl' (the CTE-based restructuring is otherwise functionally equivalent to gold)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
WITH single_bond_molecules AS (
    SELECT DISTINCT bond.molecule_id 
    FROM bond 
    WHERE bond.bond_type = '-'
),
chlorine_atoms AS (
    SELECT COUNT(*) AS chlorine_count 
    FROM atom 
    WHERE atom.element = 'Cl' AND atom.molecule_id IN (SELECT molecule_id FROM single_bond_molecules)
),
total_atoms AS (
    SELECT COUNT(*) AS total_count 
    FROM atom 
    WHERE atom.molecule_id IN (SELECT molecule_id FROM single_bond_molecules)
)
SELECT CAST(chlorine_atoms.chlorine_count AS REAL) * 100 / total_atoms.total_count AS chlorine_percentage 
FROM chlorine_atoms, total_atoms
```

### Q273 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case mismatch: 'Cl' instead of gold's lowercase 'cl'

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T3.element = 'Cl', 1, 0)) AS REAL) * 100 / COUNT(*) AS chlorine_percentage 
FROM molecule AS T1 
JOIN atom AS T3 ON T1.molecule_id = T3.molecule_id 
WHERE T1.label = '+'
```

### Q281 (challenging, retrieval) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** drops gold's GROUP BY element/COUNT(*) aggregation entirely, replacing it with an arbitrary ORDER BY atom_id LIMIT 3 OFFSET 1 row-selection; also drops the SUBSTR(atom_id,-2)='_4' suffix filter that identifies the correct atom subset

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT T3.element 
FROM molecule AS T1 
JOIN atom AS T3 ON T1.molecule_id = T3.molecule_id 
WHERE T1.label = '+' 
ORDER BY T3.atom_id 
LIMIT 3, 1
```

### Q282 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case mismatch: 'H' instead of gold's lowercase 'h'; also adds an unneeded *100 scaling that gold's plain 0-1 ratio doesn't have

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS hydrogen_ratio, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006'
```

### Q327 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** alias mix-up: references T2.label where T2=atom (no such column); the value belongs to the already-joined molecule aliased T1 (the label != '+' vs gold's label = '-' substitution is functionally equivalent given the binary domain)

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT T2.label 
FROM molecule AS T1 
JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T1.label != '+' 
GROUP BY T1.molecule_id 
HAVING COUNT(T2.atom_id) > 5
```

---

