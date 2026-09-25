# Qwen2.5-Coder-14B · L3·S3 — hand-classified failures (n=284)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. This supersedes `qwen14b_L3S3_rule_based_error_details.md`, which was built under an earlier 6-category taxonomy with no Predicate-error split and HAVING mismatches filed under GROUP BY -- this file reclassifies all 284 failures under the current 8-category taxonomy (see error_taxonomy.md) for direct comparability with qwen14b_L4S3_manual_error_details.md / L5S3 / L6S3. Predicted SQL uses S3 (descriptive snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. Grouped by database, sorted by question id.

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

## california_schools (28 failures)

### Q5 (simple, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** school_name misattributed to schools alias s; belongs to the already-joined satscores (ss); also Virtual value wrong ('Yes' vs 'F')

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT `T2`.`CDSCode`)
FROM `satscores` AS T1
JOIN `schools`  AS T2 ON T1.`cds` = T2.`CDSCode`
WHERE T2.`Virtual` = 'F'
  AND T1.`AvgScrMath` > 400 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT s.school_name) 
FROM schools s 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
WHERE ss.average_score_math > 400 AND s.Virtual = 'Yes';
```

### Q11 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** omits the schools join needed for the 'School is not NULL' filter; also drops the '+ Enrollment (Ages 5-17)' term

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

### Q12 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** divides NumGE1500 by enrollment_grade_12 instead of number_test_takers in the WHERE ratio; also swaps SELECT to a precomputed percent column and drops rtype/enrollment filters

**Gold SQL:**

```sql
SELECT MAX(
         CAST(f.`Free Meal Count (Ages 5-17)` AS REAL) /
         f.`Enrollment (Ages 5-17)`
       ) AS max_eligible_free_rate
FROM frpm      AS f
JOIN satscores AS s
     ON f.`CDSCode` = s.`cds`
WHERE s.`rtype` = 'S'                  
  AND s.`NumTstTakr`  > 0               
  AND f.`Enrollment (Ages 5-17)` > 0    
  AND CAST(s.`NumGE1500` AS REAL) / s.`NumTstTakr` > 0.3;
```

**Predicted SQL:**

```sql
SELECT MAX(f.percent_eligible_free_ages_5_17) 
FROM frpm f 
JOIN satscores s ON f.county_district_school_code = s.county_district_school_code 
WHERE s.number_scores_1500_or_above / s.enrollment_grade_12 > 0.3;
```

### Q17 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** charter_number lives on schools; predicted queries satscores alone

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
    charter_number, 
    average_score_writing, 
    RANK() OVER (ORDER BY average_score_writing DESC) as rank
FROM 
    satscores
WHERE 
    average_score_writing > 499;
```

### Q23 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds ABS() around the enrollment difference that gold doesn't have

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT s.School, s.Street, s.City, s.State, s.Zip
FROM frpm f
JOIN schools s ON f.county_district_school_code = s.county_district_school_code
WHERE ABS(f.enrollment_k12 - f.enrollment_ages_5_17) > 30;
```

### Q24 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing rtype='S' filter

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.school_name 
FROM frpm f 
JOIN satscores s ON f.county_district_school_code = s.county_district_school_code 
WHERE f.percent_eligible_free_k12 > 0.1 AND s.number_scores_1500_or_above > 0;
```

### Q25 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** gold's per-group HAVING AVG(AvgScrMath)>400 (with GROUP BY sname,FundingType) collapsed to a flat per-row WHERE filter with no GROUP BY

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
SELECT s.School, s.funding_type 
FROM schools s 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
WHERE s.County = 'Riverside' AND ss.average_score_math > 400;
```

### Q26 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses percent_eligible_free_or_reduced_price_meal_ages_5_17 (a percentage) where gold compares the raw FRPM Count Ages 5-17; also instruction_level_name substituted for school_type

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    s.Street, 
    s.City, 
    s.State, 
    s.Zip
FROM 
    frpm f
JOIN 
    schools s ON f.county_district_school_code = s.county_district_school_code
WHERE 
    f.county_name = 'Monterey' 
    AND f.percent_eligible_free_or_reduced_price_meal_ages_5_17 > 800
    AND s.instruction_level_name = 'High School';
```

### Q27 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** school_name misattributed to schools alias; belongs to the already-joined satscores

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT 
    s.school_name, 
    ss.average_score_writing, 
    s.phone
FROM 
    schools s
JOIN 
    satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE 
    (s.open_date > '1991-12-31' OR s.closed_date < '2000-01-01')
```

### Q28 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Locally Funded' (case) vs gold's 'Locally funded'

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT s.School, s.district_ownership_type
FROM schools s
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE f.enrollment_k12 - f.enrollment_ages_5_17 > (
    SELECT AVG(f.enrollment_k12 - f.enrollment_ages_5_17)
    FROM frpm f
    JOIN schools s ON f.county_district_school_code = s.county_district_school_code
    WHERE s.funding_type = 'Locally Funded'
)
AND s.funding_type = 'Locally Funded';
```

### Q31 (moderate, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** missing join to schools for the 'School is not null' filter

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT percent_eligible_free_k12
FROM frpm
ORDER BY enrollment_k12 DESC
LIMIT 9, 2;
```

### Q32 (moderate, retrieval) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** school_ownership_code (SOC) lives on schools; predicted queries frpm alone

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

### Q36 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing rtype='S' filter

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
SELECT 
    s.admin_first_name_1, 
    s.admin_last_name_1, 
    s.admin_first_name_2, 
    s.admin_last_name_2, 
    s.admin_first_name_3, 
    s.admin_last_name_3
FROM 
    satscores ss
JOIN 
    schools s ON ss.county_district_school_code = s.county_district_school_code
ORDER BY 
    ss.number_scores_1500_or_above DESC
LIMIT 1;
```

### Q37 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes frpm's percent_eligible_free_or_reduced_price_meal_k12 subquery for gold's satscores NumGE1500/NumTstTakr MIN-ratio subquery

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
SELECT 
    Street, 
    City, 
    State, 
    Zip 
FROM 
    schools 
WHERE 
    county_district_school_code = (
        SELECT 
            county_district_school_code 
        FROM 
            frpm 
        ORDER BY 
            percent_eligible_free_or_reduced_price_meal_k12 ASC 
        LIMIT 1
    )
```

### Q40 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops rtype='S' and AvgScrRead IS NOT NULL filters; adds a redundant County='Fresno' condition

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.Phone
FROM schools s
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE s.County = 'Fresno' AND s.District = 'Fresno Unified'
ORDER BY ss.average_score_reading ASC
LIMIT 1;
```

### Q41 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's RANK() OVER (PARTITION BY county ORDER BY AvgScrRead DESC) window function with a GROUP BY/IN approximation; also wrong Virtual value

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

### Q46 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters educational_option_name='Special' instead of gold's district_ownership_code=31; also adds an unneeded GROUP BY/MAX aggregation

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.School, s.State, MAX(f.enrollment_k12) AS TotalEnrollment
FROM schools s
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE s.educational_option_name = 'Special'
GROUP BY s.School, s.State
ORDER BY TotalEnrollment DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*)) nested aggregate misuse

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) AS avg_schools_opened
FROM (
    SELECT open_date
    FROM schools
    WHERE County = 'Alameda' AND District = 'Elementary School District' AND strftime('%Y', open_date) = '1980'
    GROUP BY open_date
);
```

### Q48 (moderate, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** queries frpm (district_type/county_name) instead of schools (DOC/DOCType/StatusType/County); also collapses gold's two independent COUNT(*) subqueries into one CASE-based aggregate

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

### Q50 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops rtype='S' and AvgScrMath IS NOT NULL filters

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
SELECT s.School, s.mailing_street 
FROM satscores ss 
JOIN schools s ON ss.county_district_school_code = s.county_district_school_code 
ORDER BY ss.average_score_math DESC 
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) — **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** uses precomputed percent_eligible_free_k12 without gold's *100 scaling on the Free Meal Count/Enrollment ratio

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
WHERE county_name = 'Los Angeles' 
AND is_charter_school = 0 
AND percent_eligible_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** EdOpsCode/City live on schools; predicted queries frpm alone with wrong county_name/school_name substitutes

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT SUM(enrollment_ages_5_17) 
FROM frpm 
WHERE academic_year = '2014-2015' 
AND county_name = 'Fremont' 
AND school_name LIKE '%State Special School%';
```

### Q77 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** grade_span_offered used instead of grade_span_served for the GSserved='K-9' filter

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    f.percent_eligible_free_ages_5_17
FROM 
    schools s
JOIN 
    frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE 
    s.County = 'Los Angeles' 
    AND s.grade_span_offered = 'Kindergarten to 9th grade';
```

### Q79 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** county_name (belongs to frpm/satscores) used directly on schools with no join present

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

### Q82 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing ABS() around longitude, reversing which extreme is picked

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT grade_span_offered 
FROM schools 
ORDER BY Longitude DESC 
LIMIT 1;
```

### Q83 (challenging, aggregate) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** NSLP Provision Status lives on frpm; predicted queries schools alone substituting educational_option_name

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT 
    City, 
    COUNT(*) AS school_count
FROM 
    schools
WHERE 
    grade_span_offered = 'Kindergarten to 8th' 
    AND educational_option_name = 'Multiple Provision Types'
GROUP BY 
    City;
```

### Q85 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** precomputed percent_eligible_free_k12 substituted for gold's manually-scaled Free Meal Count K12*100/Enrollment K12 ratio; WHERE filter itself matches gold exactly

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT f.percent_eligible_free_k12, f.district_code
FROM frpm f
JOIN schools s ON f.county_district_school_code = s.county_district_school_code
WHERE s.admin_first_name_1 = 'Alusine';
```

### Q87 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** replaces SOC=62 (school_ownership_code) with instruction_level_name OR conditions; also drops DOC=54 filter and uses wrong City value

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT 
    admin_email_1, 
    admin_email_2 
FROM 
    schools 
WHERE 
    County = 'San Bernardino' 
    AND City = 'San Bernardino City Unified' 
    AND open_date BETWEEN '2009-01-01' AND '2010-12-31' 
    AND (instruction_level_name = 'Intermediate/Middle School' OR instruction_level_name = 'Unified School');
```

---

## debit_card_specializing (24 failures)

### Q1472 (moderate, aggregate) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** omits customers/Segment='LAM' filter entirely; also fails to SUM per customer, comparing to a global MIN reading instead

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT customer_id
FROM yearmonth
WHERE date LIKE '2012%' AND consumption = (SELECT MIN(consumption) FROM yearmonth WHERE date LIKE '2012%')
```

### Q1473 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) misapplied to yearmonth's 'YYYYMM' text format returns NULL, so the WHERE filter matches zero rows; also drops the per-customer SUM/derived-table + /12 scaling structure

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consumption) 
FROM yearmonth 
JOIN customers ON yearmonth.customer_id = customers.customer_id 
WHERE customers.segment = 'SME' AND strftime('%Y', yearmonth.date) = '2013';
```

### Q1476 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', y.date) misapplied to yearmonth.Date, stored as 'YYYYMM' text, not an ISO date string, so it returns NULL for all rows unlike gold's SUBSTR(Date,1,4)='2012'

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

### Q1479 (moderate, aggregate) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** groups by strftime('%Y', date) (NULL for all rows since Date is 'YYYYMM' text) instead of gold's SUBSTR(Date,1,4), collapsing all years into one group

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT strftime('%Y', date) AS year, SUM(consumption) AS total_consumption
FROM yearmonth
JOIN customers ON yearmonth.customer_id = customers.customer_id
WHERE customers.currency = 'CZK'
GROUP BY year
ORDER BY total_consumption DESC
LIMIT 1;
```

### Q1480 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) misapplied to 'YYYYMM' text returns NULL, so the WHERE filter matches zero rows; the also-wrong month-extraction/aggregate-choice in GROUP BY/ORDER BY are moot

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT date, MAX(consumption) AS peak_consumption
FROM yearmonth
JOIN customers ON yearmonth.customer_id = customers.customer_id
WHERE customers.segment = 'SME' AND strftime('%Y', yearmonth.date) = '2013'
GROUP BY date
ORDER BY peak_consumption DESC
LIMIT 1;
```

### Q1481 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** subqueries reference `consumption` directly on `customers` (no join to yearmonth in that scope) - a column that only exists on yearmonth; overall logic diverges hugely from gold's segment-comparison CTEs

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT AVG(consumption) 
     FROM yearmonth 
     WHERE date BETWEEN '2013-01-01' AND '2013-12-31' 
       AND customer_id IN (
           SELECT customer_id 
           FROM customers 
           WHERE currency = 'CZK' 
           ORDER BY consumption ASC 
           LIMIT 1
       )
    ) - 
    (SELECT AVG(consumption) 
     FROM yearmonth 
     WHERE date BETWEEN '2013-01-01' AND '2013-12-31' 
       AND customer_id IN (
           SELECT customer_id 
           FROM customers 
           WHERE currency = 'CZK' 
           ORDER BY consumption DESC 
           LIMIT 1
       )
    ) AS diff_sme_lam,
    
    (SELECT AVG(consumption) 
     FROM yearmonth 
     WHERE date BETWEEN '2013-01-01' AND '2013-12-31' 
       AND customer_id IN (
           SELECT customer_id 
           FROM customers 
           WHERE currency = 'CZK' 
           ORDER BY consumption ASC 
           LIMIT 1
       )
    ) - 
    (SELECT AVG(consumption) 
     FROM yearmonth 
     WHERE date BETWEEN '2013-01-01' AND '2013-12-31' 
       AND customer_id IN (
           SELECT customer_id 
           FROM customers 
           WHERE currency = 'CZK' 
           ORDER BY consumption DESC 
           LIMIT 1
       )
    ) AS diff_lam_kam,
    
    (SELECT AVG(consumption) 
     FROM yearmonth 
     WHERE date BETWEEN '2013-01-01' AND '2013-12-31' 
       AND customer_id IN (
           SELECT customer_id 
           FROM customers 
           WHERE currency = 'CZK' 
           ORDER BY consumption ASC 
           LIMIT 1
       )
    ) - 
    (SELECT AVG(consumption) 
     FROM yearmonth 
     WHERE date BETWEEN '2013-01-01' AND '2013-12-31' 
       AND customer_id IN (
           SELECT customer_id 
           FROM customers 
           WHERE currency = 'CZK' 
           ORDER BY consumption DESC 
           LIMIT 1
       )
    ) AS diff_kam_sme;
```

### Q1482 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) misapplied to yearmonth's 'YYYYMM' text returns NULL for every CASE WHEN comparison, zeroing out all three sums; also restructures gold's three scalar sums into a GROUP BY c.segment aggregation

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    c.segment,
    ((SUM(CASE WHEN strftime('%Y', y.date) = '2013' THEN y.consumption ELSE 0 END) - SUM(CASE WHEN strftime('%Y', y.date) = '2012' THEN y.consumption ELSE 0 END)) * 100.0 / SUM(CASE WHEN strftime('%Y', y.date) = '2012' THEN y.consumption ELSE 0 END)) AS percentage_change
FROM 
    customers c
JOIN 
    yearmonth y ON c.customer_id = y.customer_id
WHERE 
    c.currency = 'EUR' AND c.segment IN ('SME', 'LAM', 'KAM')
GROUP BY 
    c.segment;
```

### Q1483 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN uses ISO-hyphenated date bounds ('2013-08-01'/'2013-11-30') against Date stored as plain 'YYYYMM' text, so none of customer 6's monthly rows satisfy the range

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(consumption) 
FROM yearmonth 
WHERE customer_id = 6 
AND date BETWEEN '2013-08-01' AND '2013-11-30';
```

### Q1484 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic'/'Slovakia' used instead of the stored codes 'CZE'/'SVK'; also 'discount' case differs from gold's 'Discount'

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM gasstations WHERE country = 'Czech Republic' AND segment = 'discount') - 
    (SELECT COUNT(*) FROM gasstations WHERE country = 'Slovakia' AND segment = 'discount') AS difference;
```

### Q1486 (simple, aggregate) — **JOIN errors** (extra table)

**Outcome:** `wrong_answer` · **Reason:** unnecessary JOIN to transactions_1k multiplies each customer row by their transaction count, inflating the SUM

**Gold SQL:**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN c.currency = 'CZK' THEN 1 ELSE 0 END) - 
    SUM(CASE WHEN c.currency = 'EUR' THEN 1 ELSE 0 END) AS difference
FROM 
    customers c
JOIN 
    transactions_1k t ON c.customer_id = t.customer_id
WHERE 
    c.segment = 'SME';
```

### Q1490 (moderate, aggregate) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** uses INNER JOIN where gold's LEFT JOIN preserves customers with no yearmonth rows; also drops the COUNT(DISTINCT...) per-customer dedup

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consumption > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM yearmonth 
JOIN customers ON yearmonth.customer_id = customers.customer_id 
WHERE customers.segment = 'LAM';
```

### Q1493 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN '2012-02-01' AND '2012-02-29' (ISO-date literals) applied to Date stored as 'YYYYMM' text ('201202') never matches lexicographically, causing zero rows instead of gold's exact match Date='201202'

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

### Q1498 (simple, aggregate) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** missing GROUP BY entirely (gold groups by month); also uses MAX instead of SUM, returning the single largest individual reading instead of the peak month's total

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

### Q1505 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** currency='euro' instead of the stored code 'EUR'

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

### Q1506 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country='Czech Republic' instead of the stored code 'CZE'

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

### Q1509 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country='Czech Republic' instead of the stored code 'CZE'

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
FROM transactions_1k 
JOIN gasstations ON transactions_1k.gas_station_id = gasstations.gas_station_id 
WHERE gasstations.country = 'Czech Republic' AND transactions_1k.date > '2012-01-01';
```

### Q1514 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** predicted omits DISTINCT and the (redundant, non-filtering) gasstations join that gold itself never references any column of; if multiple transactions share this exact date/time, duplicate currency values would appear

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT c.currency 
FROM customers c 
JOIN transactions_1k t 
ON c.customer_id = t.customer_id 
WHERE t.date = '2012-08-24' AND t.time = '16:25:00';
```

### Q1524 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `error` · **Reason:** joins customers instead of gasstations for the Country lookup (both are 1-hop lookup joins from transactions_1k); also uses amount instead of price

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT c.country 
FROM customers c 
JOIN transactions_1k t 
ON c.customer_id = t.customer_id 
WHERE t.date = '2012-08-24' AND t.amount = 548.4;
```

### Q1525 (simple, aggregate) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** uses COUNT(*)/SUM(CASE) over raw transaction rows instead of gold's COUNT(DISTINCT CustomerID), double-counting customers with multiple matching transactions

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM customers 
JOIN transactions_1k ON customers.customer_id = transactions_1k.customer_id 
WHERE transactions_1k.date = '2012-08-25';
```

### Q1526 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** subquery uses amount=634.8 instead of gold's price=634.8 (different real column) to identify the customer; also misses the per-year SUM aggregation, self-joining yearmonth month-rows directly

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT 
    (y2012.consumption - y2013.consumption) / y2012.consumption AS consumption_decrease_rate
FROM 
    yearmonth y2012
JOIN 
    yearmonth y2013 ON y2012.customer_id = y2013.customer_id
WHERE 
    y2012.date LIKE '2012%' AND y2013.date LIKE '2013%'
    AND y2012.customer_id = (
        SELECT 
            customer_id 
        FROM 
            transactions_1k 
        WHERE 
            date = '2012-08-25' AND amount = 634.8
    );
```

### Q1528 (simple, aggregate) — **JOIN errors** (extra table)

**Outcome:** `wrong_answer` · **Reason:** unnecessary JOIN to transactions_1k multiplies each gas station row by its transaction count, inflating COUNT(*)/SUM; also 'premium' case differs from gold's 'Premium'

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

### Q1529 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects amount alone instead of amount*price (the combined quantity needed for 'total spent')

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

### Q1531 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** ranks/selects the top customer by SUM(amount) alone instead of gold's SUM(amount*price); computes avg_price_per_item as plain AVG(price) instead of the amount-weighted average; also collapses gold's subquery+outer-query structure

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT c.customer_id, AVG(t.price) AS avg_price_per_item, c.currency
FROM customers c
JOIN transactions_1k t ON c.customer_id = t.customer_id
GROUP BY c.customer_id, c.currency
ORDER BY SUM(t.amount) DESC
LIMIT 1;
```

### Q1533 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date filter uses LIKE '2012-08-%' (a hyphenated format) against yearmonth.Date stored as plain 'YYYYMM' text, matching zero rows instead of gold's exact Date='201208'; also drops the Price/Amount division, comparing raw Price instead

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT y.consumption
FROM yearmonth y
JOIN customers c ON y.customer_id = c.customer_id
JOIN transactions_1k t ON c.customer_id = t.customer_id
WHERE t.product_id = 5 AND t.price > 29.00 AND y.date LIKE '2012-08-%';
```

---

## european_football_2 (33 failures)

### Q1025 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2016' instead of gold's '2015/2016'

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League L 
JOIN Match M ON L.id = M.league_id 
WHERE M.season = '2016' 
GROUP BY L.name 
ORDER BY SUM(M.home_team_goals + M.away_team_goals) DESC 
LIMIT 1;
```

### Q1028 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects team_short_name instead of gold's team_long_name; also collapses the tie-preserving HAVING COUNT(*) = (SELECT MAX...) into ORDER BY COUNT(*) DESC LIMIT 1

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T3.team_short_name 
FROM Match AS T1 
JOIN League AS T2 ON T1.league_id = T2.id 
JOIN Team AS T3 ON T1.away_team_api_id = T3.team_api_id 
WHERE T2.name = 'Scotland Premier League' AND T1.season = '2010' AND T1.away_team_goals > T1.home_team_goals 
GROUP BY T3.team_short_name 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1029 (moderate, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** adds an extra team_long_name column gold's SELECT list doesn't have

**Gold SQL:**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT 
    team_long_name, 
    buildup_play_speed 
FROM 
    Team_Attributes 
JOIN 
    Team ON Team_Attributes.team_api_id = Team.team_api_id 
ORDER BY 
    buildup_play_speed DESC 
LIMIT 4;
```

### Q1030 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2016' instead of gold's '2015/2016'

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.name 
FROM League L 
JOIN Match M ON L.id = M.league_id 
WHERE M.season = '2016' AND M.home_team_goals = M.away_team_goals 
GROUP BY L.name 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1031 (challenging, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT (also selects an extra player_name column)

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
SELECT 
    P.player_name, 
    strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM 
    Player P
JOIN 
    Player_Attributes PA ON P.player_api_id = PA.player_api_id
WHERE 
    PA.sprint_speed >= 97
    AND PA.date BETWEEN '2013-01-01' AND '2015-12-31';
```

### Q1032 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** tie-preserving HAVING COUNT(m.id) = (SELECT MAX(match_count)...) collapsed to a plain ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(*) AS match_count
FROM League L
JOIN Match M ON L.id = M.league_id
GROUP BY L.id
ORDER BY match_count DESC
LIMIT 1;
```

### Q1035 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT, otherwise identical to gold

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT team_fifa_api_id FROM Team_Attributes WHERE buildup_play_speed > 50 AND buildup_play_speed < 60
```

### Q1036 (challenging, aggregate) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT; a team can have multiple 2012 Team_Attributes snapshots

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

### Q1037 (challenging, aggregate) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** uses COUNT(*)/SUM instead of gold's COUNT(DISTINCT id), double-counting players with multiple Player_Attributes rows

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

### Q1080 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attacking_work_rate='High' instead of gold's 'low'; also 'Left' case differs; COUNT(*) not deduped

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE preferred_foot = 'Left' AND attacking_work_rate = 'High';
```

### Q1084 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra attacking_work_rate='High' condition gold doesn't have; also defensive_work_rate case differs

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT pa.player_api_id) 
FROM Player_Attributes pa 
JOIN Player p ON pa.player_api_id = p.player_api_id 
WHERE strftime('%Y', p.birthday) < '1986' 
AND pa.attacking_work_rate = 'High' 
AND pa.defensive_work_rate = 'High';
```

### Q1088 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** outer query lacks DISTINCT; if Player has duplicate rows per player_api_id the un-deduped output would differ from gold's SELECT DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT player_name 
FROM Player 
WHERE player_api_id IN (
    SELECT player_api_id 
    FROM Player_Attributes 
    WHERE volleys > 70 AND dribbling > 70
);
```

### Q1091 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** splits the League.name filter across country.name + a truncated league name ('Jupiler League') instead of gold's single exact match on 'Belgium Jupiler League'; also adds a vestigial Country join

**Gold SQL:**

```sql
SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND SUBSTR(t2."date", 1, 7) = '2009-04'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Match m
JOIN League l ON m.league_id = l.id
JOIN Country c ON l.country_id = c.id
WHERE c.name = 'Belgium' AND l.name = 'Jupiler League' AND strftime('%Y-%m', m.date) = '2009-04';
```

### Q1092 (simple, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** tie-preserving HAVING COUNT(t2.id) = (SELECT MAX(match_count)...) collapsed to ORDER BY COUNT(*) DESC LIMIT 1

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

### Q1094 (challenging, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** omits gold's per-player 'most recent snapshot' CTEs (ORDER BY date DESC LIMIT 1), instead joining all historical Player_Attributes rows for each player without narrowing to the latest one

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT 
    ((a.overall_rating - b.overall_rating) * 100.0 / b.overall_rating) AS percentage_difference
FROM 
    Player_Attributes a
JOIN 
    Player p1 ON a.player_api_id = p1.player_api_id
JOIN 
    Player_Attributes b
JOIN 
    Player p2 ON b.player_api_id = p2.player_api_id
WHERE 
    p1.player_name = 'Ariel Borysiuk' AND p2.player_name = 'Paulin Puel';
```

### Q1098 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters team_short_name='Ajax' instead of gold's team_long_name='Ajax'; also mixes MAX() with a non-aggregated column without GROUP BY

**Gold SQL:**

```sql
SELECT t2.chanceCreationPassing, t2.chanceCreationPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Ajax' ORDER BY t2.chanceCreationPassing DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(T2.chance_creation_passing), T2.chance_creation_passing_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id 
WHERE T1.team_short_name = 'Ajax';
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses exact date='2016-06-23' instead of gold's SUBSTR(date,1,10)='2016-06-23'; Player_Attributes.date likely includes a time suffix so exact equality fails

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.player_name 
FROM Player P 
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id 
WHERE PA.overall_rating = 77 AND PA.date = '2016-06-23' 
ORDER BY P.birthday ASC 
LIMIT 1;
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses exact date='2016-02-04' instead of gold's SUBSTR(date,1,10)='2016-02-04'

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT overall_rating 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.player_api_id = Player.player_api_id 
WHERE Player.player_name = 'Aaron Mooy' AND Player_Attributes.date = '2016-02-04';
```

### Q1105 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses exact date='2015-05-01' instead of gold's LIKE '2015-05-01%' pattern

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

### Q1107 (moderate, retrieval) — **JOIN errors** (wrong column (key))

**Outcome:** `wrong_answer` · **Reason:** joins Player_Attributes to Player via player_api_id instead of gold's player_fifa_api_id

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.date 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Kevin Constant' 
ORDER BY T1.crossing DESC 
LIMIT 1;
```

### Q1110 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses exact date='2010-02-22' instead of gold's LIKE '2010-02-22%' pattern

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT ta.buildup_play_passing_class 
FROM Team_Attributes ta 
JOIN Team t ON ta.team_api_id = t.team_api_id 
WHERE t.team_long_name = 'FC Lorient' AND ta.date = '2010-02-22';
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses exact date='2015-09-10' instead of gold's LIKE '2015-09-10%' pattern

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT T2.defence_aggression_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 
ON T1.team_api_id = T2.team_api_id 
WHERE T1.team_long_name = 'Hannover 96' AND T2.date = '2015-09-10';
```

### Q1114 (challenging, aggregate) — **JOIN errors** (wrong column (key))

**Outcome:** `wrong_answer` · **Reason:** joins Player_Attributes to Player via player_api_id instead of gold's player_fifa_api_id

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(overall_rating) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.player_api_id = Player.player_api_id 
WHERE Player.player_name = 'Marko Arnautovic' 
AND Player_Attributes.date BETWEEN '2007-02-22' AND '2016-04-21';
```

### Q1115 (challenging, aggregate) — **JOIN errors** (wrong column (key))

**Outcome:** `wrong_answer` · **Reason:** joins on player_api_id (via Player) instead of gold's player_fifa_api_id

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT 
    ((L.overall_rating - J.overall_rating) * 100.0 / J.overall_rating) AS percentage_difference
FROM 
    Player_Attributes L
JOIN 
    Player_Attributes J ON L.date = J.date
JOIN 
    Player PL ON L.player_api_id = PL.player_api_id
JOIN 
    Player PJ ON J.player_api_id = PJ.player_api_id
WHERE 
    PL.player_name = 'Landon Donovan' 
    AND PJ.player_name = 'Jordan Bowery' 
    AND L.date = '2013-07-12';
```

### Q1116 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** missing DENSE_RANK() OVER (ORDER BY height DESC) window function; uses ORDER BY/LIMIT 10 instead, which drops ties and returns 10 rows not all rank=1 ties

**Gold SQL:**

```sql
SELECT player_name FROM (SELECT player_name, height, DENSE_RANK() OVER (ORDER BY height DESC) as rank FROM Player) WHERE rank = 1
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player ORDER BY height DESC LIMIT 10
```

### Q1122 (simple, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** subquery ranks by strength instead of gold's overall_rating

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1130 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** chance_creation_passing_class='Low' instead of gold's 'Safe'; also missing DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T.team_short_name 
FROM Team_Attributes AS TA 
JOIN Team AS T ON TA.team_api_id = T.team_api_id 
WHERE TA.chance_creation_passing_class = 'Low';
```

### Q1136 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra attacking_work_rate='High' condition gold doesn't have; also uses COUNT(*) instead of COUNT(DISTINCT player_api_id)

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

### Q1139 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** league name spelled 'Belgian Jupiler League' instead of the stored 'Belgium Jupiler League'

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT 
    home_team_goals, 
    away_team_goals 
FROM 
    Match 
WHERE 
    date = '2008-09-24' 
    AND league_id = (SELECT id FROM League WHERE name = 'Belgian Jupiler League');
```

### Q1144 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** missing subquery finding ALL players tied for MAX(weight); collapses to ORDER BY/LIMIT 1, dropping ties

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT pa.finishing, pa.curve
FROM Player_Attributes pa
JOIN Player p ON pa.player_api_id = p.player_api_id
ORDER BY p.weight DESC
LIMIT 1;
```

### Q1145 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2015-2016' (hyphen) instead of gold's '2015/2016' (slash)

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(*) AS game_count
FROM League L
JOIN Match M ON L.id = M.league_id
WHERE M.season = '2015-2016'
GROUP BY L.name
ORDER BY game_count DESC
LIMIT 4;
```

### Q1147 (simple, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** subquery ranks by strength instead of gold's overall_rating

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1148 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** references `strength` (a Player_Attributes-only column) directly on Player with no join present at all; also substitutes overall_rating>70 with strength>70

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN height < 180 AND strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player;
```

---

## financial (23 failures)

### Q89 (moderate, aggregate) — **JOIN errors** (extra table)

**Outcome:** `wrong_answer` · **Reason:** joins in `trans` (not needed) and filters on trans.type='issuance' instead of gold's account.frequency='POPLATEK PO OBRATU'; also 'East Bohemia' case differs

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT a.account_id) 
FROM account a 
JOIN district d ON a.district_id = d.district_id 
JOIN trans t ON a.account_id = t.account_id 
WHERE d.region = 'East Bohemia' AND t.type = 'issuance';
```

### Q93 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'North Bohemia' (case) doesn't match gold's stored 'north Bohemia'

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.client_id)
FROM client c
JOIN district d ON c.district_id = d.district_id
WHERE c.gender = 'M'
AND d.region = 'North Bohemia'
AND d.average_salary > 8000;
```

### Q94 (challenging, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's independent scalar subquery (MAX(A11)-MIN(A11) over ALL districts) with an aggregate MAX/MIN over districts of only female clients; also fails to first narrow to the single oldest female client before joining

**Gold SQL:**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    a.account_id AS oldest_female_client_account, 
    MAX(d.average_salary) - MIN(d.average_salary) AS salary_gap
FROM 
    client c
JOIN 
    disp d ON c.client_id = d.client_id
JOIN 
    account a ON d.account_id = a.account_id
JOIN 
    district d ON c.district_id = d.district_id
WHERE 
    c.gender = 'F'
ORDER BY 
    c.birth_date ASC
LIMIT 1;
```

### Q95 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** omits gold's subquery pinning to the single (youngest) client via ORDER BY birth_date DESC LIMIT 1; instead sorts the full joined set by birth_date ASC (wrong direction) with average_salary as a tiebreak

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

### Q98 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra l.status='A' condition gold doesn't have; also translates frequency to English 'weekly' instead of the stored Czech value 'POPLATEK TYDNE'

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE l.date LIKE '1997%' AND l.status = 'A' AND a.statement_frequency = 'weekly'
ORDER BY l.amount ASC
LIMIT 1;
```

### Q99 (moderate, retrieval) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** introduces GROUP BY account_id and drops the LIMIT 1, returning all qualifying accounts instead of the single top loan amount

**Gold SQL:**

```sql
SELECT T1.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T2.date) = '1993' AND T1.duration > 12 ORDER BY T1.amount DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id, MAX(l.amount) AS approved_amount
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE l.duration_months > 12 AND strftime('%Y', a.date) = '1993'
GROUP BY a.account_id
ORDER BY approved_amount DESC;
```

### Q112 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** district_name lives on district, which predicted never joins (aliases disp as 'd' and mistakenly references district_name through it)

**Gold SQL:**

```sql
SELECT DISTINCT d.A2
FROM `client`  c
JOIN `disp`    di ON di.`client_id` = c.`client_id`
JOIN `account`  a  ON a.`account_id` = di.`account_id`
JOIN `district` d  ON d.`district_id` = a.`district_id`
WHERE c.`gender` = 'F'
  AND c.`birth_date` = '1976-01-29';
```

**Predicted SQL:**

```sql
SELECT d.district_name 
FROM client c 
JOIN disp d ON c.client_id = d.client_id 
JOIN account a ON d.account_id = a.account_id 
WHERE c.gender = 'F' AND c.birth_date = '1976-01-29';
```

### Q115 (challenging, aggregate) — **JOIN errors** (extra table)

**Outcome:** `wrong_answer` · **Reason:** joins disp+account (unneeded), which can multiply client rows in the percentage calculation; also drops the GROUP BY A4/ORDER BY A4 DESC LIMIT 1 logic, computing over all South Bohemia clients at once

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN c.gender = 'M' THEN 1 ELSE 0 END) * 100.0 / COUNT(c.client_id)) AS male_percentage
FROM 
    client c
JOIN 
    disp d ON c.client_id = d.client_id
JOIN 
    account a ON d.account_id = a.account_id
JOIN 
    district di ON a.district_id = di.district_id
WHERE 
    di.region = 'South Bohemia'
ORDER BY 
    di.number_inhabitants DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) — **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** computes (MAX(balance)-MIN(balance))/MIN(balance) over the whole date range instead of gold's SUM(IIF(date=exact_date,balance,0)) at two specific dates; also adds unneeded client/disp joins

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(t.balance_after_transaction) - MIN(t.balance_after_transaction)) / MIN(t.balance_after_transaction) AS increase_rate
FROM 
    client c
JOIN 
    disp d ON c.client_id = d.client_id
JOIN 
    account a ON d.account_id = a.account_id
JOIN 
    loan l ON a.account_id = l.account_id
JOIN 
    trans t ON a.account_id = t.account_id
WHERE 
    l.status = 'A' AND l.date = '1993-07-05'
    AND t.date BETWEEN '1993-03-22' AND '1998-12-27';
```

### Q118 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='A' instead of gold's status='C'

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

### Q125 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** computes a plain difference (rate_1996 - rate_1995) instead of gold's percentage-change formula; also wrong status value ('A' vs 'D') and substitutes loan.amount>0 for district.A12 IS NOT NULL/A12>0

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

### Q129 (moderate, retrieval) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** introduces GROUP BY district_name + SUM(amount) ranking (highest total amount) instead of gold's simple ORDER BY per-transaction ranking, no aggregation; also translates type to English 'withdrawal' instead of the stored code 'VYDAJ'

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT d.district_name
FROM district d
JOIN client c ON d.district_id = c.district_id
JOIN disp dp ON c.client_id = dp.client_id
JOIN account a ON dp.account_id = a.account_id
JOIN trans t ON a.account_id = t.account_id
WHERE t.type = 'withdrawal' AND t.date BETWEEN '1996-01-01' AND '1996-01-31'
GROUP BY d.district_name
ORDER BY SUM(t.amount) DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra status='A' condition gold doesn't have; also uses 'M' instead of the actual stored value 'POPLATEK MESICNE'

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM loan 
JOIN account ON loan.account_id = account.account_id 
WHERE loan.amount >= 250000 
AND loan.status = 'A' 
AND account.statement_frequency = 'M' 
AND loan.date BETWEEN '1995-01-01' AND '1997-12-31';
```

### Q137 (moderate, aggregate) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** entirely omits the loan join and status IN ('C','D') filter, counting all accounts in district 1 instead of just those with a completed/defaulted loan

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM account 
WHERE district_id = 1;
```

### Q145 (moderate, aggregate) — **JOIN errors** (wrong column (key))

**Outcome:** `error` · **Reason:** joins card via a nonexistent c.account_id; card only has disp_id, requiring a join through disp to reach account_id; also substitutes operation='VYBER KARTOU' with card.type='credit'

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT t.account_id
FROM trans t
JOIN card c ON t.account_id = c.account_id
WHERE c.type = 'credit' AND t.amount < (SELECT AVG(amount) FROM trans WHERE strftime('%Y', date) = '1998') AND strftime('%Y', t.date) = '1998';
```

### Q149 (challenging, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** replaces disp.type entirely with an unrelated 'account NOT IN loan' condition and selects statement_frequency/average_salary instead of disp.type

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

### Q152 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters number_inhabitants>4000 instead of gold's A15 (number_crimes_1995)>4000; also replaces gold's DISTINCT-subquery join with a raw JOIN that could duplicate district rows

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

### Q159 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra t.type='withdrawal' condition not in gold; uses transaction_operation='cash' instead of the stored Czech code 'VYBER'; also selects only 3 columns instead of all trans.* columns

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT t.transaction_id, t.date, t.amount
FROM trans t
JOIN disp d ON t.account_id = d.account_id
WHERE d.client_id = 3356 AND t.type = 'withdrawal' AND t.transaction_operation = 'cash';
```

### Q169 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the disp.type='OWNER' filter entirely, including all disponents not just account owners

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN strftime('%Y', l.date) = '1997' THEN l.amount ELSE 0 END) - SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END)) * 100.0 / 
    SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END) AS growth_rate
FROM 
    loan l
JOIN 
    account a ON l.account_id = a.account_id
JOIN 
    disp d ON a.account_id = d.account_id
JOIN 
    client c ON d.client_id = c.client_id
WHERE 
    c.gender = 'M';
```

### Q173 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** queries `trans` (realized transactions) instead of gold's `"order"` (standing orders) table; also drops the k_symbol/SUM/GROUP BY subquery structure

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT 
    statement_frequency, 
    SUM(amount) AS total_debit_amount
FROM 
    account
JOIN 
    trans ON account.account_id = trans.account_id
WHERE 
    account.account_id = 3 AND trans.amount = 3539
GROUP BY 
    statement_frequency;
```

### Q186 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps which condition is the WHERE-filter vs. the CASE-numerator - filters WHERE gender='M' and counts weekly-frequency within that population, inverting gold's structure

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN a.statement_frequency = 'weekly' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM account a 
JOIN disp d ON a.account_id = d.account_id 
JOIN client c ON d.client_id = c.client_id 
WHERE c.gender = 'M';
```

### Q192 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='A' instead of IN ('C','D'); statement_frequency='A' (an invalid value) instead of 'POPLATEK PO OBRATU'

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(loan.amount) 
FROM loan 
JOIN account ON loan.account_id = account.account_id 
WHERE loan.status = 'A' AND account.statement_frequency = 'A';
```

### Q194 (moderate, retrieval) — **JOIN errors** (wrong column (key))

**Outcome:** `error` · **Reason:** joins card via a nonexistent ca.account_id (card only has disp_id); also 'High level' is not a valid card type value (gold's actual value is 'gold')

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

---

## formula_1 (40 failures)

### Q846 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results for qualifying (both per-race driver-performance tables)

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

### Q850 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT, otherwise identical to gold

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT races.name 
FROM races 
JOIN circuits ON races.circuit_id = circuits.circuit_id 
WHERE circuits.country = 'Germany';
```

### Q854 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** omits the races join, filtering on circuits.name='Australian Grand Prix' instead of races.name

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Australian Grand Prix'
```

### Q857 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** omits the races join, filtering on circuits.name='Abu Dhabi Grand Prix' instead of races.name

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Abu Dhabi Grand Prix'
```

### Q861 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time = '0:01:54' (wrong format) doesn't match the stored 'M:SS.mmm' format that gold's LIKE '1:54%' matches

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT number 
FROM qualifying 
WHERE race_id = 903 AND qualifying_3_time = '0:01:54';
```

### Q865 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters results.position IS NOT NULL instead of gold's results.time IS NOT NULL - a different real column with different NULL semantics for DNF drivers

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

### Q866 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** time='0:01:27' (wrong format) instead of gold's LIKE '1:27%' pattern match; also missing DISTINCT

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

### Q868 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** omits the races join, filtering on circuits.name='Malaysian Grand Prix' instead of races.name

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Malaysian Grand Prix'
```

### Q869 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorStandings for constructorResults (per-race points earned vs cumulative standings)

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.url 
FROM constructors c 
JOIN constructorStandings cs ON c.constructor_id = cs.constructor_id 
WHERE cs.race_id = 9 
ORDER BY cs.points DESC 
LIMIT 1;
```

### Q872 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time = '0:01:33' (wrong format) instead of gold's LIKE '1:33%' pattern

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT d.driver_code 
FROM drivers d 
JOIN qualifying q ON d.driver_id = q.driver_id 
WHERE q.race_id = 45 AND q.qualifying_3_time = '0:01:33';
```

### Q877 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the results.time IS NOT NULL filter entirely, including DNF/non-finishing drivers gold excludes

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.date_of_birth
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
WHERE r.race_id = 872
ORDER BY d.date_of_birth DESC
LIMIT 1;
```

### Q879 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** computes MAX(fastest_lap_speed) without CAST to REAL, so the comparison is a string/lexicographic max instead of numeric max, unlike gold's explicit CAST(...AS REAL)

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.nationality
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
WHERE r.fastest_lap_speed = (SELECT MAX(fastest_lap_speed) FROM results);
```

### Q881 (moderate, aggregate) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** introduces an unneeded per-driver GROUP BY where gold computes one global aggregate; also selects driver names gold's output never includes

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT 
    d.first_name, 
    d.last_name, 
    COUNT(r.result_id) * 100.0 / (SELECT COUNT(*) FROM races WHERE date = '1983-07-16') AS completion_rate
FROM 
    drivers d
JOIN 
    results r ON d.driver_id = r.driver_id
JOIN 
    races ra ON r.race_id = ra.race_id
WHERE 
    ra.date = '1983-07-16'
GROUP BY 
    d.driver_id;
```

### Q884 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the month-matching condition entirely, collapsing to just the earliest race in the minimum year instead of gold's races matching both the year and month of the very first race

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT name 
FROM races 
WHERE year = (SELECT MIN(year) FROM races) 
ORDER BY date ASC 
LIMIT 1;
```

### Q894 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects lt.time (a formatted string) instead of gold's lt.milliseconds in the output

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT lt.time AS lap_time, d.first_name || ' ' || d.last_name AS driver, r.name AS race
FROM lapTimes lt
JOIN drivers d ON lt.driver_id = d.driver_id
JOIN races r ON lt.race_id = r.race_id
ORDER BY lt.milliseconds ASC
LIMIT 1;
```

### Q896 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** replaces driverStandings.position<>1 rate calculation with results + a nonsensical R.round=1 condition

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN D.first_name = 'Lewis' AND D.last_name = 'Hamilton' AND R.round = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM drivers D 
JOIN results RES ON D.driver_id = RES.driver_id 
JOIN races R ON RES.race_id = R.race_id 
WHERE R.year >= 2010;
```

### Q897 (moderate, aggregate) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** drops the GROUP BY forename/surname/nationality + ORDER BY COUNT(wins) DESC ranking, instead filtering to the row(s) with the overall MAX wins value via a subquery

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.nationality, MAX(ds.points) AS max_points
FROM drivers d
JOIN driverStandings ds ON d.driver_id = ds.driver_id
WHERE ds.wins = (SELECT MAX(wins) FROM driverStandings);
```

### Q898 (simple, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** column order differs (name-columns before age vs gold's age-first), likely causing a positional evaluation mismatch

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name, strftime('%Y', 'now') - strftime('%Y', date_of_birth) AS age
FROM drivers
WHERE nationality = 'Japanese'
ORDER BY age ASC
LIMIT 1;
```

### Q902 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** replaces driverStandings (cumulative championship standing) with results.grid_position (starting grid position)

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT r.name 
FROM races r 
JOIN results res ON r.race_id = res.race_id 
JOIN drivers d ON res.driver_id = d.driver_id 
WHERE d.first_name = 'Alex' AND d.last_name = 'Yoong' AND res.grid_position < 20;
```

### Q904 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results.fastest_lap_time (a per-race time string) for lapTimes.milliseconds (a per-lap numeric time)

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT r.name AS race_name, r.year AS race_year
FROM races r
JOIN results res ON r.race_id = res.race_id
JOIN drivers d ON res.driver_id = d.driver_id
WHERE d.first_name = 'Michael' AND d.last_name = 'Schumacher'
ORDER BY res.fastest_lap_time ASC
LIMIT 1;
```

### Q915 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** subquery references date_of_birth directly on `results` (no join to drivers in that scope); overall query structure bears no resemblance to gold's simple oldest-driver lookup

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT country 
FROM drivers 
JOIN circuits ON drivers.driver_id = (SELECT driver_id FROM results WHERE race_id IN (SELECT race_id FROM races WHERE circuit_id = circuits.circuit_id) ORDER BY date_of_birth ASC LIMIT 1)
```

### Q930 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by results.position (finishing position) instead of filtering on results.rank=0 (fastest-lap rank flag), also collapsing gold's multi-row IN-subquery into a single ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT r.name
FROM races r
JOIN results res ON r.race_id = res.race_id
JOIN drivers d ON res.driver_id = d.driver_id
WHERE d.first_name = 'Lewis' AND d.last_name = 'Hamilton'
ORDER BY res.position ASC
LIMIT 1;
```

### Q937 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** garbled race name 'AustChineseralian Grand Prix' instead of gold's 'Chinese Grand Prix'

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT r.time 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
WHERE ra.year = 2008 AND ra.name = 'AustChineseralian Grand Prix' AND r.position = 2;
```

### Q940 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the results.time IS NOT NULL filter, counting all entrants (including DNFs) instead of just drivers with a completed time

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT driver_id) 
FROM results 
WHERE race_id IN (
    SELECT race_id 
    FROM races 
    WHERE year = 2008 AND name = 'Chinese Grand Prix'
);
```

### Q944 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** identifies the last-place driver via position = COUNT(*) instead of gold's positionOrder = MAX(positionOrder); position can have gaps/NULLs for non-classified finishers

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT 
    (first_place_time - last_place_time) / last_place_time * 100 AS percentage_faster
FROM (
    SELECT 
        MIN(CASE WHEN position = 1 THEN milliseconds END) AS first_place_time,
        MAX(CASE WHEN position = (SELECT COUNT(*) FROM results WHERE race_id = r.race_id) THEN milliseconds END) AS last_place_time
    FROM 
        results r
    JOIN 
        races ra ON r.race_id = ra.race_id
    WHERE 
        ra.year = 1988 AND ra.name = 'Australian Grand Prix'
);
```

### Q950 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorResults for constructorStandings

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

### Q955 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes driverStandings.position=1 (championship leader after the race) for results.position=1 (race winner); also averages races.time instead of results.milliseconds

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT 
    s.year, 
    AVG(r.time) AS avg_champion_time
FROM 
    seasons s
JOIN 
    races r ON s.year = r.year
JOIN 
    driverStandings ds ON r.race_id = ds.race_id
WHERE 
    s.year < 1975 AND ds.position = 1
GROUP BY 
    s.year;
```

### Q959 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** driverStandings.year doesn't exist; year lives on races, which isn't joined; also substitutes driverStandings.position=1 for gold's time-format filter

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

### Q962 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** references alias `DR.driver_id` which was never declared in FROM/JOIN (drivers is aliased `D`, not `DR`)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN D.date_of_birth < '1985-01-01' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT R.race_id, DR.driver_id) 
FROM races R 
JOIN results RES ON R.race_id = RES.race_id 
JOIN drivers D ON RES.driver_id = D.driver_id 
WHERE R.year BETWEEN 2000 AND 2005 AND RES.laps = 50;
```

### Q963 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** compares lt.time (a 'M:SS.mmm' text string) via string `<` against '02:00.00' instead of gold's numeric seconds conversion - string comparison is lexicographic and doesn't match numeric ordering

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT d.driver_id) 
FROM drivers d 
JOIN laptimes lt ON d.driver_id = lt.driver_id 
WHERE d.nationality = 'French' AND lt.time < '02:00.00';
```

### Q967 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses invented nationality value 'Netherlandic' instead of 'Dutch' (also applies the filter before the ORDER BY/LIMIT 3 instead of after)

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

### Q972 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT, otherwise equivalent to gold

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
WHERE d.date_of_birth LIKE '1971%' AND r.fastest_lap_time IS NOT NULL;
```

### Q977 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses inclusive BETWEEN 50 AND 100 instead of gold's exclusive raceId>50 AND raceId<100; drops the 'time IS NOT NULL' requirement; assumes status_id=2 corresponds to 'Disqualified' via a subquery lookup

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
WHERE race_id BETWEEN 50 AND 100 
AND status_id = (SELECT status_id FROM status WHERE status = 'Disqualified');
```

### Q978 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT, otherwise identical to gold

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE country = 'Austria'
```

### Q981 (moderate, retrieval) — **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** subquery selects MIN(date_of_birth) (oldest driver) instead of gold's youngest-driver selection; also lacks the outer ORDER BY date ASC LIMIT 1

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

### Q989 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** filters on results.position=1 instead of gold's time LIKE '_:%:__.___' pattern match - different column, different condition

**Gold SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT r.time 
FROM races r 
JOIN results res ON r.race_id = res.race_id 
WHERE r.name = 'Canadian Grand Prix' AND r.year = 2008 AND res.position = 1;
```

### Q990 (challenging, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorStandings for results; also uses position=1 instead of gold's time-format pattern filter

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

### Q994 (challenging, aggregate) — **JOIN errors** (extra table)

**Outcome:** `wrong_answer` · **Reason:** adds an unnecessary constructorStandings join, which could silently drop constructor-race rows lacking a matching standings entry

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    c.name AS constructor_name, 
    c.nationality AS constructor_nationality, 
    SUM(cr.points) AS total_points
FROM 
    constructorStandings crs
JOIN 
    constructorResults cr ON crs.constructor_id = cr.constructor_id AND crs.race_id = cr.race_id
JOIN 
    constructors c ON crs.constructor_id = c.constructor_id
JOIN 
    races r ON crs.race_id = r.race_id
WHERE 
    r.name = 'Monaco Grand Prix' 
    AND r.year BETWEEN 1980 AND 2010
GROUP BY 
    c.constructor_id
ORDER BY 
    total_points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** references q.round (qualifying has no round column) when round lives on the already-joined races table; also substitutes q.position=1 for gold's q3 IS NOT NULL + fastest-time ranking logic

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
WHERE r.year = 2008 AND c.name = 'Marina Bay Street Circuit' AND q.round = 3 AND q.position = 1;
```

### Q1014 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes lapTimes (with a broken race_id=circuit_id join condition) for gold's races+results+circuits chain, and selects lap NUMBER instead of any time-based measure

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(lap) AS min_lap
FROM lapTimes
JOIN circuits ON lapTimes.race_id = circuits.circuit_id
WHERE circuits.country = 'Italy';
```

---

## student_club (24 failures)

### Q1317 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an unnecessary/likely-invalid major_id IN (SELECT... major_name='Student_Club') condition via subquery, which gold doesn't have at all

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM member m 
JOIN attendance a ON m.member_id = a.member_id 
JOIN event e ON a.event_id = e.event_id 
WHERE m.major_id IN (SELECT major_id FROM major WHERE major_name = 'Student_Club') 
AND e.event_name = 'Women''s Soccer' 
AND m.t_shirt_size = 'Medium';
```

### Q1322 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='meeting' (lowercase) doesn't match the stored value 'Meeting'

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM event 
WHERE event_id IN (
    SELECT event_id 
    FROM attendance 
    GROUP BY event_id 
    HAVING COUNT(member_id) > 10
) 
AND type = 'meeting';
```

### Q1331 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** omits the member join entirely and misapplies 'Vice President' to income.source instead of member.position; also incorrectly SUMs the amount where gold just selects individual row(s)

**Gold SQL:**

```sql
SELECT T2.amount FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Vice President'
```

**Predicted SQL:**

```sql
SELECT SUM(amount) 
FROM income 
WHERE income_source = 'Vice President';
```

### Q1334 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra, invalid m.position='Student_Club' condition gold doesn't have

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name 
FROM member m 
JOIN zip_code z ON m.zip_code = z.zip_code 
WHERE z.state = 'Illinois' AND m.position = 'Student_Club';
```

### Q1338 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses exact equality event_date='2019-10-08' instead of gold's LIKE '2019-10-08%' pattern; also selects an extra expense_id column

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT e.expense_id, e.is_approved 
FROM expense e 
JOIN budget b ON e.budget_id = b.budget_id 
JOIN event ev ON b.event_id = ev.event_id 
WHERE ev.event_name = 'October Meeting' AND ev.event_date = '2019-10-08';
```

### Q1340 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra, seemingly-invalid budget.event_status='Student_Club' condition to both halves of the subtraction

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT SUM(amount_spent) 
     FROM budget 
     WHERE event_id IN (SELECT event_id FROM event WHERE event_date BETWEEN '2019-01-01' AND '2019-12-31') 
       AND event_status = 'Student_Club') -
    (SELECT SUM(amount_spent) 
     FROM budget 
     WHERE event_id IN (SELECT event_id FROM event WHERE event_date BETWEEN '2020-01-01' AND '2020-12-31') 
       AND event_status = 'Student_Club') AS difference;
```

### Q1344 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes event (with its own notes/event_date/type columns) for income (source/date_received) - different real table despite both having a 'notes' column

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE event_date = '2019-09-14' AND type = 'fundraising';
```

### Q1357 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** first_name/last_name live on member, which predicted never joins; also 'dues' case differs from stored 'Dues'

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT date_received 
FROM income 
WHERE first_name = 'Connor' AND last_name = 'Hilton' AND income_source = 'dues';
```

### Q1359 (challenging, aggregate) — **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** computes COUNT(*) of budget rows exceeding a threshold subquery instead of gold's direct ratio SUM(kickoff amount)/SUM(october amount)

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM budget b1 
JOIN event e1 ON b1.event_id = e1.event_id 
WHERE b1.category = 'Advertisement' AND e1.event_name = 'Yearly Kickoff' 
AND b1.amount > (
    SELECT b2.amount 
    FROM budget b2 
    JOIN event e2 ON b2.event_id = e2.event_id 
    WHERE b2.category = 'Advertisement' AND e2.event_name = 'October Meeting'
);
```

### Q1376 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's tie-preserving GROUP BY/HAVING nested MAX-ratio subquery to a plain ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT e.event_name 
FROM event e 
JOIN budget b ON e.event_id = b.event_id 
WHERE e.status = 'closed' 
ORDER BY (b.amount_spent / b.amount) DESC 
LIMIT 1;
```

### Q1380 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** category='food' (lowercase) doesn't match the stored value 'Food'

**Gold SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL:**

```sql
SELECT SUM(amount_spent) 
FROM budget 
WHERE category = 'food';
```

### Q1387 (moderate, retrieval) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** budget has no member_id column; the correct link is budget→expense (link_to_budget)→member (link_to_member), but predicted joins budget directly to member, skipping expense

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name 
FROM member m 
JOIN budget b ON m.member_id = b.member_id 
JOIN event e ON b.event_id = e.event_id 
WHERE e.event_name = 'Yearly Kickoff';
```

### Q1390 (moderate, aggregate) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** joins event directly to expense via `e.event_id = ex.budget_id` (an ID-space mismatch), omitting the budget table that correctly bridges event→budget→expense

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN e.event_name = 'Yearly Kickoff' THEN ex.cost ELSE 0 END) * 100.0 / SUM(ex.cost)) AS percentage
FROM 
    event e
JOIN 
    expense ex ON e.event_id = ex.budget_id;
```

### Q1392 (simple, retrieval) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** introduces GROUP BY income_source + SUM(amount) ranking instead of gold's simple ORDER BY source DESC LIMIT 1

**Gold SQL:**

```sql
SELECT source FROM income WHERE date_received BETWEEN '2019-09-01' and '2019-09-30' ORDER BY source DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT income_source, SUM(amount) AS total_amount
FROM income
WHERE date_received BETWEEN '2019-09-01' AND '2019-09-30'
GROUP BY income_source
ORDER BY total_amount DESC
LIMIT 1;
```

### Q1394 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra, invalid member.position='Student_Club' condition gold doesn't have

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

### Q1398 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** category='advertisement' (lowercase) doesn't match the stored value 'Advertisement'

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.event_name 
FROM event e 
JOIN budget b ON e.event_id = b.event_id 
WHERE b.category = 'advertisement' 
ORDER BY b.amount_spent DESC 
LIMIT 1;
```

### Q1403 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** recomputes 'remaining' via SUM(expense.cost) - budget.amount instead of using budget.remaining directly; drops the remaining<0 filter and sorts DESC instead of ASC

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

### Q1404 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** references e.category (expense has no category column) when category actually lives on the already-joined budget table

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
SELECT e.category, SUM(e.cost) AS total_approved_cost
FROM expense e
JOIN budget b ON e.budget_id = b.budget_id
JOIN event ev ON b.event_id = ev.event_id
WHERE ev.event_name = 'October Meeting' AND e.is_approved = 1
GROUP BY e.category;
```

### Q1422 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** selects budget.category (via an unnecessary budget join) instead of gold's event.type - budget is never referenced by gold at all

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

### Q1427 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='guest speaker' (case) doesn't match the stored value 'Guest Speaker'; also missing DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT b.category 
FROM budget b 
JOIN event e ON b.event_id = e.event_id 
WHERE e.location = 'MU 215' AND e.type = 'guest speaker' AND b.amount_spent = 0;
```

### Q1432 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops member.position='Member' entirely and substitutes an unrelated income.income_source='Student_Club' condition

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN i.amount = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM income i 
JOIN member m ON i.member_id = m.member_id 
WHERE m.t_shirt_size = 'Medium' AND i.income_source = 'Student_Club';
```

### Q1435 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='game'/status='closed' (case) don't match stored 'Game'/'Closed'; also missing DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT event_name 
FROM event 
WHERE type = 'game' 
AND status = 'closed' 
AND event_date BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1457 (challenging, aggregate) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** outer query lacks DISTINCT; also drops the budget join within the AVG subquery entirely

**Gold SQL:**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, m.phone
FROM member m
JOIN expense e ON m.member_id = e.member_id
WHERE e.cost > (SELECT AVG(cost) FROM expense);
```

### Q1460 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** splits the single exact description 'Water, Veggie tray, supplies' into a 3-value lowercased IN clause instead of matching the full combined string exactly

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, e.cost 
FROM member m 
JOIN expense e ON m.member_id = e.member_id 
WHERE e.expense_description IN ('water', 'veggie tray', 'supplies');
```

---

## superhero (25 failures)

### Q723 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue' (case) doesn't match gold's stored 'Blue'

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

### Q724 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue'/'blond' (case) don't match gold's stored 'Blue'/'Blond'

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

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the height_cm IS NOT NULL AND height_cm != 0 filter entirely; also selects an extra height_cm column

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT 
    superhero.superhero_name, 
    superhero.height_cm
FROM 
    superhero
JOIN 
    publisher ON superhero.publisher_id = publisher.id
WHERE 
    publisher.publisher_name = 'Marvel Comics'
ORDER BY 
    superhero.height_cm DESC;
```

### Q728 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** missing RANK() OVER (ORDER BY COUNT(...) DESC) window function

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.colour, COUNT(*) as count
FROM superhero s
JOIN colour c ON s.eye_colour_id = c.id
JOIN publisher p ON s.publisher_id = p.id
WHERE p.publisher_name = 'Marvel Comics'
GROUP BY c.colour
ORDER BY count DESC;
```

### Q732 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** s.speed does not exist anywhere in this schema - Speed is a value in hero_attribute/attribute, not a column

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN hero_attribute AS T3 ON T1.id = T3.hero_id INNER JOIN attribute AS T4 ON T3.attribute_id = T4.id WHERE T4.attribute_name = 'Speed' ORDER BY T3.attribute_value LIMIT 1
```

**Predicted SQL:**

```sql
SELECT p.publisher_name 
FROM publisher p 
JOIN superhero s ON p.id = s.publisher_id 
WHERE s.speed IS NOT NULL 
ORDER BY s.speed ASC 
LIMIT 1;
```

### Q733 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='gold' (case) doesn't match gold's stored 'Gold'

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN colour ON superhero.eye_colour_id = colour.id 
JOIN publisher ON superhero.publisher_id = publisher.id 
WHERE colour.colour = 'gold' AND publisher.publisher_name = 'Marvel Comics';
```

### Q736 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attribute_name='intelligence' (lowercase) doesn't match the stored value 'Intelligence', causing the subquery to return no rows

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE id = (SELECT hero_id FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'intelligence') ORDER BY attribute_value ASC LIMIT 1);
```

### Q743 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses alignment='Self-Centric' instead of gold's 'Bad', and computes the percentage over ALL superheroes instead of restricting the population (WHERE alignment='Bad') as gold does

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN a.alignment = 'Self-Centric' THEN 1 END) * 100.0 / COUNT(*)) AS percentage_self_centric,
    COUNT(CASE WHEN a.alignment = 'Self-Centric' AND p.publisher_name = 'Marvel Comics' THEN 1 END) AS marvel_self_centric_count
FROM 
    superhero s
JOIN 
    alignment a ON s.alignment_id = a.id
LEFT JOIN 
    publisher p ON s.publisher_id = p.id;
```

### Q744 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** publisher_name IN ('DC','Marvel') instead of the real stored values 'DC Comics'/'Marvel Comics', so no rows match at all

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
    p.publisher_name IN ('DC', 'Marvel')
GROUP BY 
    p.publisher_name
ORDER BY 
    superhero_count DESC
LIMIT 1;
```

### Q750 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the weight_kg > 0 filter entirely

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(weight_kg) 
FROM superhero 
JOIN gender ON superhero.gender_id = gender.id 
WHERE gender.gender = 'Female';
```

### Q753 (moderate, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** substitutes eye_colour_id IS NULL for gold's JOIN colour + colour='No Colour' - 'No Colour' is a specific categorical value, not the same as a NULL/missing eye_colour_id

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE height_cm BETWEEN 170 AND 190 
AND eye_colour_id IS NULL;
```

### Q758 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT, otherwise identical to gold

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT c.colour 
FROM superhero s 
JOIN colour c ON s.hair_colour_id = c.id 
JOIN race r ON s.race_id = r.id 
WHERE s.height_cm = 185 AND r.race = 'Human';
```

### Q766 (moderate, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's WITH max_strength CTE (finding all heroes tied for max Strength) with ORDER BY attribute_value DESC LIMIT 1, dropping ties

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT s.full_name
FROM superhero s
JOIN hero_attribute ha ON s.id = ha.hero_id
JOIN attribute a ON ha.attribute_id = a.id
WHERE a.attribute_name = 'Strength'
ORDER BY ha.attribute_value DESC
LIMIT 1;
```

### Q772 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** references h.hair_colour_id (colour table has no such column) when hair_colour_id actually lives on the already-joined superhero table (aliased sp)

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    c.colour AS eye_colour, 
    h.hair_colour_id AS hair_colour, 
    s.colour AS skin_colour 
FROM 
    superhero sp 
JOIN 
    gender g ON sp.gender_id = g.id 
JOIN 
    colour c ON sp.eye_colour_id = c.id 
JOIN 
    colour h ON sp.hair_colour_id = h.id 
JOIN 
    colour s ON sp.skin_colour_id = s.id 
JOIN 
    publisher p ON sp.publisher_id = p.id 
WHERE 
    g.gender = 'Female' 
    AND p.publisher_name = 'Dark Horse Comics';
```

### Q775 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses eye_colour_id instead of gold's skin_colour_id - a different real column entirely

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN T1.eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    superhero AS T1 
JOIN 
    gender AS T2 ON T1.gender_id = T2.id 
WHERE 
    T2.gender = 'Female';
```

### Q782 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='black' (case) doesn't match gold's stored 'Black'

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

### Q788 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** inverts which condition is the population restriction - filters WHERE publisher='Marvel Comics' and computes %Female within that, instead of gold's restricting to Female and computing %Marvel within Female; also uses INNER JOIN instead of gold's LEFT JOIN

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN g.gender = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero s 
JOIN gender g ON s.gender_id = g.id 
JOIN publisher p ON s.publisher_id = p.id 
WHERE p.publisher_name = 'Marvel Comics';
```

### Q790 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on superhero_name = 'Emil Blonsky'/'Charles Chandler' instead of gold's full_name - these are civilian names, not superhero alias names

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT (SELECT weight_kg FROM superhero WHERE superhero_name = 'Emil Blonsky') - 
       (SELECT weight_kg FROM superhero WHERE superhero_name = 'Charles Chandler') AS weight_difference;
```

### Q791 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the height_cm > 0 filter entirely, including zero/placeholder heights in the average

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### Q794 (moderate, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's tie-preserving '= (SELECT MAX(...))' equality subquery to ORDER BY attribute_value DESC LIMIT 1, dropping ties

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE id = (SELECT hero_id FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'Speed') ORDER BY attribute_value DESC LIMIT 1);
```

### Q797 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue'/'brown' (case) don't match gold's stored 'Blue'/'Brown'

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name 
FROM superhero s 
JOIN colour e ON s.eye_colour_id = e.id 
JOIN colour h ON s.hair_colour_id = h.id 
WHERE e.colour = 'blue' AND h.colour = 'brown';
```

### Q800 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue' (case) doesn't match gold's stored 'Blue'

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.colour = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero AS T1 
JOIN colour AS T2 ON T1.eye_colour_id = T2.id;
```

### Q819 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** substitutes 'eye_colour_id IS NULL' for gold's 'eye_colour_id = 1' (a specific real colour id, not equivalent to NULL); also drops the 'OR weight_kg = 0' half of gold's weight filter

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') AND weight_kg IS NULL) -
    (SELECT COUNT(*) FROM superhero WHERE eye_colour_id IS NULL AND weight_kg IS NULL) AS difference;
```

### Q822 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='green'/alignment='bad' (case) don't match gold's stored 'Green'/'Bad'

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN colour ON superhero.skin_colour_id = colour.id 
JOIN alignment ON superhero.alignment_id = alignment.id 
WHERE colour.colour = 'green' AND alignment.alignment = 'bad';
```

### Q829 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** publisher_name='DC' instead of the real stored value 'DC Comics', so the DC subquery returns no rows

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
SELECT 
    (SELECT COUNT(*) FROM superhero WHERE publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'DC')) -
    (SELECT COUNT(*) FROM superhero WHERE publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Marvel Comics')) AS difference;
```

---

## thrombosis_prediction (49 failures)

### Q1149 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses 'Inpatient'/'Outpatient'/'Male' instead of the actual stored codes '+'/'-'/'M', causing zero matches; also introduces a GROUP BY admission_type gold doesn't have

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    admission_type, 
    COUNT(*) AS count, 
    (COUNT(*) * 100.0 / SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) - COUNT(*) * 100.0 / SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END)) AS deviation_percentage
FROM 
    Patient
WHERE 
    sex = 'Male'
GROUP BY 
    admission_type;
```

### Q1150 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' instead of the stored single-letter code 'F'

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'female' AND strftime('%Y', birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient;
```

### Q1152 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type='Inpatient'/'Outpatient' instead of the stored codes '+'/'-'

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END) AS inpatient_to_outpatient_ratio
FROM 
    Patient
WHERE 
    diagnosis = 'SLE';
```

### Q1155 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** lactate_dehydrogenase>175 instead of gold's threshold >500 - a wrong/invented value

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.lactate_dehydrogenase > 175;
```

### Q1156 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on thrombosis_degree>0 instead of gold's russell_viper_venom_time='+' - a completely different Examination column

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Examination E ON P.ID = E.ID
WHERE E.thrombosis_degree > 0;
```

### Q1157 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree='severe' (a string) instead of the real numeric value 2

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.diagnosis 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE E.thrombosis_degree = 'severe';
```

### Q1162 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses sex='female' and admission_type='门诊' (Chinese text) instead of the stored codes 'F' and '-'

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE sex = 'female' 
AND strftime('%Y', first_hospital_visit_date) = '1997' 
AND admission_type = '门诊';
```

### Q1164 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses thrombosis_degree=(SELECT MAX(thrombosis_degree) FROM Examination) instead of the literal value 1; also sex='女' (Chinese) instead of 'F'

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

### Q1166 (simple, retrieval) — **Nesting problem** (wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** drops gold's UNION with the NOT EXISTS edge-case branch entirely

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT E.symptoms, P.diagnosis 
FROM Examination E 
JOIN Patient P ON E.ID = P.ID 
WHERE P.birthday = (SELECT MAX(birthday) FROM Patient) 
LIMIT 1;
```

### Q1168 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes Patient.first_record_date (via MAX, patient-level) for gold's Laboratory.Date (individual lab record date); also computes age relative to 'now' instead of gold's Patient."First Date" field

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MAX(P.first_record_date) AS last_laboratory_date,
    strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age_at_first_record
FROM 
    Patient P
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    P.diagnosis = 'SJS'
ORDER BY 
    P.birthday ASC
LIMIT 1;
```

### Q1169 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's sex-specific UA threshold logic (M:<=8.0, F:<=6.5) with a generic 'uric_acid > AVG' filter and simple male/female counts; also uses 'male'/'female' instead of 'M'/'F'

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN P.sex = 'male' THEN 1 ELSE 0 END) / 
    SUM(CASE WHEN P.sex = 'female' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM 
    Patient P
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    L.uric_acid > (SELECT AVG(uric_acid) FROM Laboratory);
```

### Q1171 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** age difference compared to <0 instead of gold's <18 - a wrong threshold value

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE E.examination_date BETWEEN '1990-01-01' AND '1993-12-31' 
AND strftime('%Y', E.examination_date) - strftime('%Y', P.birthday) < 0;
```

### Q1175 (moderate, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** SELECT returns raw birthday instead of computing age like gold does; also adds a possibly row-multiplying Examination join

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.sex, P.birthday, P.diagnosis
FROM Patient P
JOIN Examination E ON P.ID = E.ID
JOIN Laboratory L ON P.ID = L.ID
ORDER BY L.hemoglobin DESC
LIMIT 1;
```

### Q1179 (moderate, retrieval) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** selects three IgG/IgM/IgA columns instead of just the requested aCL IgM column

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT e.anticardiolipin_igg, e.anticardiolipin_igm, e.anticardiolipin_iga
FROM Examination e
JOIN Patient p ON e.ID = p.ID
WHERE p.diagnosis = 'SLE' AND p.first_record_date = '1994-02-19' AND e.examination_date = '1993-11-12';
```

### Q1185 (challenging, aggregate) — **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** computes (MAX-MIN)/COUNT(DISTINCT Date) instead of gold's SUM(Nov T-CHO)-SUM(Dec T-CHO))/SUM(Nov T-CHO) - a different aggregate approach entirely

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(L.total_cholesterol) - MIN(L.total_cholesterol)) / COUNT(DISTINCT L.Date) AS decrease_rate
FROM 
    Patient P
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    P.birthday = '1959-02-18'
    AND L.Date BETWEEN '1981-11-01' AND '1981-12-31';
```

### Q1187 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on Examination.examination_date instead of gold's Laboratory.Date - a different real date column; also adds unnecessary Patient/Examination joins

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

### Q1189 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** subquery computes AVG(anticardiolipin_igm)*1.2 over ALL Examination rows instead of restricting to Thrombosis=2 AND ANA Pattern='S' as gold's subquery does

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(*)
FROM Examination e
JOIN Patient p ON e.ID = p.ID
WHERE e.thrombosis_degree = 2
  AND e.antinuclear_antibody_pattern = 'S'
  AND e.anticardiolipin_igm > (SELECT AVG(anticardiolipin_igm) * 1.2 FROM Examination);
```

### Q1192 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses admission_type='门诊' (Chinese text) instead of '-'; total_bilirubin BETWEEN 5.1 AND 20.0 instead of gold's < 2.0

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE P.admission_type = '门诊'
AND L.Date BETWEEN '1991-10-01' AND '1991-10-31'
AND L.total_bilirubin BETWEEN 5.1 AND 20.0;
```

### Q1195 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' instead of the stored single-letter code 'F'

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(L.albumin) 
FROM Laboratory L 
JOIN Patient P ON L.ID = P.ID 
WHERE P.sex = 'female' AND L.platelet_count > 400 AND P.diagnosis = 'SLE';
```

### Q1198 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' instead of the stored single-letter code 'F'

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE sex = 'female' AND diagnosis = 'APS';
```

### Q1201 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** CASE WHEN sex='女' (Chinese text) instead of 'F'

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = '女' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient 
WHERE strftime('%Y', birthday) = '1980' AND diagnosis = 'RA';
```

### Q1205 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's sex-specific UA threshold logic (F: >6.5, M: >8.0) with a single generic 'uric_acid BETWEEN 2.4 AND 7.0' check that doesn't reference Patient.SEX at all

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN uric_acid BETWEEN 2.4 AND 7.0 THEN 'true' ELSE 'false' END AS is_normal FROM Laboratory WHERE ID = 57266
```

### Q1208 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' instead of 'M'; alanine_aminotransferase>40 instead of gold's >=60

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'male' AND L.alanine_aminotransferase > 40;
```

### Q1209 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold >40 instead of gold's >60

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

### Q1220 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** urea_nitrogen=15 instead of gold's exact value 29

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.urea_nitrogen = 15;
```

### Q1225 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's single T-BIL>=2.0 threshold with a totally different two-sided '< 0.3 OR > 1.2' range; also uses COUNT(*) instead of GROUP_CONCAT(DISTINCT ID)

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

### Q1227 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** no such function: YEAR (non-SQLite function)

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(YEAR(CURRENT_DATE) - YEAR(birthday)) AS average_age
FROM Patient
WHERE sex = 'male' AND ID IN (
    SELECT ID
    FROM Laboratory
    WHERE total_cholesterol > (SELECT AVG(total_cholesterol) FROM Laboratory)
);
```

### Q1229 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold >150 instead of gold's >=200

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

### Q1231 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' instead of 'M'; threshold >100 instead of gold's >=250

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'male' 
AND strftime('%Y', P.birthday) BETWEEN '1936' AND '1956' 
AND L.creatinine_phosphokinase > 100;
```

### Q1232 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's simple GLU>=180 threshold with a two-sided '<70 OR >110' abnormal-range check (also missing parentheses causes an operator-precedence bug); total_cholesterol BETWEEN 150-200 instead of gold's <250

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.blood_glucose < 70 OR L.blood_glucose > 110
AND L.total_cholesterol BETWEEN 150 AND 200;
```

### Q1235 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** compares red_blood_cell_count against a computed AVG(...) subquery instead of gold's fixed literal threshold 3.5

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.birthday) AS age, P.diagnosis
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.red_blood_cell_count < (SELECT AVG(red_blood_cell_count) FROM Laboratory);
```

### Q1238 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** hemoglobin BETWEEN 13.5-17.5 instead of gold's >10 AND <17

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.diagnosis = 'SLE' AND L.hemoglobin BETWEEN 13.5 AND 17.5 
ORDER BY P.birthday ASC 
LIMIT 1;
```

### Q1239 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** hematocrit BETWEEN 45-50 instead of gold's >=52 - a non-overlapping wrong threshold

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.hematocrit > 45 AND L.hematocrit < 50
GROUP BY P.ID
HAVING COUNT(L.ID) >= 2;
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** platelet_count thresholds 150/450 instead of gold's 100/400

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(CASE WHEN L.platelet_count < 150 THEN 1 END) AS lower_than_normal,
    COUNT(CASE WHEN L.platelet_count > 450 THEN 1 END) AS higher_than_normal
FROM 
    Laboratory L
JOIN 
    Patient P ON L.ID = P.ID
WHERE 
    L.platelet_count < 150 OR L.platelet_count > 450;
```

### Q1242 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** platelet_count BETWEEN 150000-450000 instead of gold's 100-400 - assumes a different unit scale than actually stored

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
JOIN Examination E ON P.ID = E.ID
WHERE strftime('%Y', L.Date) = '1984'
AND strftime('%Y', 'now') - strftime('%Y', P.birthday) < 50
AND L.platelet_count BETWEEN 150000 AND 450000;
```

### Q1243 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restructures gold's nested-CASE percentage-within-PT>=14-subset calculation into a flat WHERE-based percentage over the whole age>55 population; also uses PT>13.5 instead of gold's >=14

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN P.sex = 'female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage_female_with_abnormal_pt
FROM 
    Patient P
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    strftime('%Y', 'now') - strftime('%Y', P.birthday) > 55
    AND L.prothrombin_time > 13.5; -- Assuming normal PT is <= 13.5 seconds
```

### Q1247 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' instead of 'M'; white_blood_cell_count BETWEEN 4000-11000 (wrong unit scale) instead of 3.5-9.0; fibrinogen>400 instead of gold's >=450

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'male' 
AND L.white_blood_cell_count BETWEEN 4000 AND 11000 
AND (L.fibrinogen < 150 OR L.fibrinogen > 400);
```

### Q1251 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_g>11.9 instead of gold's >=2000

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
JOIN Laboratory ON Patient.ID = Laboratory.ID 
WHERE Laboratory.immunoglobulin_g > 11.9;
```

### Q1252 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses immunoglobulin_g='normal' (a nonexistent categorical value) instead of gold's numeric BETWEEN 900-2000 range

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
JOIN Examination E ON P.ID = E.ID 
WHERE L.immunoglobulin_g = 'normal' AND E.symptoms IS NOT NULL;
```

### Q1254 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_a='normal' instead of gold's numeric BETWEEN 80-500 range

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.immunoglobulin_a = 'normal' 
AND P.first_hospital_visit_date > '1990-01-01';
```

### Q1255 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_m>100 instead of gold's (<=40 OR >=400); also drops the DISTINCT-ID dedup subquery

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.diagnosis, COUNT(*) AS count
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.immunoglobulin_m > 100
GROUP BY P.diagnosis
ORDER BY count DESC
LIMIT 1;
```

### Q1256 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's 'CRP="+" AND first_record_date IS NULL' with 'no Laboratory row has non-null CRP at all' - an entirely different, unrelated condition

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE ID NOT IN (SELECT ID FROM Laboratory WHERE c_reactive_protein IS NOT NULL);
```

### Q1257 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** creatinine>1.2 instead of gold's >=1.5

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.creatinine > 1.2 AND P.birthday > DATE('now', '-70 years');
```

### Q1265 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses 'normal' instead of 'negative'/'0' for RNP; 'admitted' instead of '+' for Admission

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

### Q1267 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's WITH CTE structure (HAVING MAX(COALESCE(Thrombosis,0))=0 across ALL of a patient's exam records) in favor of a flat JOIN with thrombosis_degree IS NULL; also uses anti_sm='normal' instead of 'negative'/'0'

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
FROM Patient 
JOIN Examination ON Patient.ID = Examination.ID 
JOIN Laboratory ON Patient.ID = Laboratory.ID 
WHERE Laboratory.anti_sm = 'normal' AND Examination.thrombosis_degree IS NULL;
```

### Q1270 (challenging, aggregate) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** anti_scl70 (SC170) lives on Laboratory, which predicted never joins (only Patient+Examination); also restructures the NOT EXISTS Symptoms check and uses sex='female' instead of 'F'

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
FROM Patient p 
JOIN Examination e ON p.ID = e.ID 
WHERE p.sex = 'female' 
AND e.symptoms IS NULL 
AND e.anti_scl70 = 'normal';
```

### Q1275 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** uses 'normal' instead of 'negative'/'0' for both centromere and SSB; 'male' instead of 'M'

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

### Q1281 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces GOT>=60 with an OR of AST/ALT>40 (wrong threshold, extra unrelated column); also uses MIN(birthday) (oldest patient) instead of finding the youngest

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(P.birthday) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.aspartate_aminotransferase > 40 OR L.alanine_aminotransferase > 40;
```

### Q1302 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes thrombosis_degree>0 for gold's (KCT='+' OR RVVT='+' OR LAC='+') coagulation-test check - entirely different columns

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
JOIN Laboratory ON Patient.ID = Laboratory.ID 
JOIN Examination ON Patient.ID = Examination.ID 
WHERE Laboratory.creatinine_phosphokinase BETWEEN 10 AND 200 
AND Examination.thrombosis_degree > 0;
```

---

## toxicology (38 failures)

### Q197 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restructures gold's molecule-level oxygen-count/single-bond-molecule CTEs into an atom-bond-connected join that only counts oxygen atoms directly involved in a single bond; also uses 'O'/'single' instead of 'o'/'-'

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(oxygen_count) 
FROM (
    SELECT COUNT(*) AS oxygen_count 
    FROM molecule m
    JOIN atom a ON m.molecule_id = a.molecule_id
    JOIN bond b ON m.molecule_id = b.molecule_id
    JOIN connected c ON a.atom_id = c.atom_id AND b.bond_id = c.bond_id
    WHERE a.element = 'O' AND b.bond_type = 'single'
    GROUP BY m.molecule_id
)
```

### Q198 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(bond_id)) nested aggregate misuse

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(b.bond_id)) 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id 
WHERE b.bond_type = 'single' AND m.label = 'carcinogenic' 
GROUP BY m.molecule_id;
```

### Q200 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects molecule.label instead of gold's molecule_id; also uses 'triple'/'%carcinogenic%' instead of the stored codes '#'/'+'

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label
FROM molecule m
JOIN bond b ON m.molecule_id = b.molecule_id
WHERE b.bond_type = 'triple' AND m.label LIKE '%carcinogenic%';
```

### Q201 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='double' instead of gold's '='

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom a 
JOIN bond b ON a.molecule_id = b.molecule_id 
WHERE b.bond_type = 'double';
```

### Q206 (challenging, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes molecule.label='TR004_8_9' for gold's connected.bond_id='TR004_8_9' - connected is dropped entirely

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

### Q207 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='double' instead of gold's '=' - structure otherwise matches gold exactly

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN connected c ON a.atom_id = c.atom_id 
JOIN bond b ON c.bond_id = b.bond_id 
WHERE b.bond_type = 'double';
```

### Q208 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='H' instead of gold's 'h' - structure otherwise matches gold exactly

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT m.label 
FROM molecule m 
JOIN atom a ON m.molecule_id = a.molecule_id 
WHERE a.element = 'H' 
GROUP BY m.label 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q212 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's GROUP BY element HAVING COUNT(*) = (SELECT MIN(cnt)...) tie-preserving structure to ORDER BY COUNT(*) ASC LIMIT 1

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

### Q213 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** treats 'TR004_8'/'TR004_20' as values to look up via atom.element instead of using connected.atom_id/atom_id2 directly; also drops the symmetric OR condition

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT bond_type 
FROM bond 
WHERE molecule_id = (SELECT molecule_id FROM atom WHERE element = 'TR004_8') 
AND bond_id IN (SELECT bond_id FROM connected WHERE atom_id = (SELECT atom_id FROM atom WHERE element = 'TR004_8') AND atom_id2 = (SELECT atom_id FROM atom WHERE element = 'TR004_20'))
```

### Q215 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** both iodine_count and sulfur_count use the identical COUNT(*) expression instead of gold's element-specific COUNT(DISTINCT CASE...); also uses 'I'/'S'/'single' instead of 'i'/'s'/'-'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(*) AS iodine_count, 
    COUNT(*) AS sulfur_count 
FROM 
    atom 
JOIN 
    molecule ON atom.molecule_id = molecule.molecule_id 
JOIN 
    bond ON molecule.molecule_id = bond.molecule_id 
JOIN 
    connected ON atom.atom_id = connected.atom_id 
WHERE 
    (atom.element = 'I' OR atom.element = 'S') 
    AND bond.bond_type = 'single';
```

### Q218 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** computes the percentage over individual atom rows instead of gold's DISTINCT molecule_id-level check of whether a molecule contains any fluorine atom; also 'carcinogenic'/'F' instead of '+'/'f'

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN element != 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'carcinogenic';
```

### Q219 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** inverts which condition is the WHERE-filter vs the CASE-measured condition - filters WHERE label='carcinogenic' and counts triple-bond rows, instead of gold's WHERE bond_type='#' restricting to triple-bond molecules

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

### Q220 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters molecule.label='TR000' (via an unnecessary join) instead of gold's atom.molecule_id='TR000' directly

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT DISTINCT element 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR000' 
ORDER BY element ASC 
LIMIT 3;
```

### Q226 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters molecule.label='TR008' instead of gold's bond.molecule_id='TR008'; also 'double' instead of '='

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond_type = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage_double_bonds
FROM bond
JOIN molecule ON bond.molecule_id = molecule.molecule_id
WHERE molecule.label = 'TR008';
```

### Q227 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label='carcinogenic' instead of gold's '+'

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN label = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage
FROM molecule;
```

### Q228 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters molecule.label='TR206' instead of gold's atom.molecule_id='TR206'; also element='H' instead of 'h'

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN a.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS hydrogen_percentage
FROM 
    atom a
JOIN 
    molecule m ON a.molecule_id = m.molecule_id
WHERE 
    m.label = 'TR206';
```

### Q230 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters molecule.label='TR060' instead of gold's molecule_id='TR060'

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT a.element, m.label 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE m.label = 'TR060';
```

### Q231 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters molecule.label='TR010' instead of gold's bond.molecule_id='TR010'

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT bond_type 
FROM bond 
JOIN molecule ON bond.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR010' 
GROUP BY bond_type 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q232 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects molecule.label instead of gold's molecule_id; also 'single' instead of '-', and NOT LIKE '%carcinogenic%' instead of label='-'

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT m.label 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id 
WHERE b.bond_type = 'single' 
AND m.label NOT LIKE '%carcinogenic%' 
ORDER BY m.label ASC 
LIMIT 3;
```

### Q234 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** splits the compound atom_id 'TR009_12' into molecule.label='TR009' + numeric connected.atom_id=12, instead of directly matching connected.atom_id='TR009_12' as a string

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM bond 
JOIN molecule ON bond.molecule_id = molecule.molecule_id 
JOIN connected ON bond.bond_id = connected.bond_id 
WHERE molecule.label = 'TR009' AND (connected.atom_id = 12 OR connected.atom_id2 = 12);
```

### Q236 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters molecule.label='TR001_6_9' instead of gold's connected.bond_id='TR001_6_9'

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT b.bond_type, c.atom_id, c.atom_id2 
FROM bond b 
JOIN connected c ON b.bond_id = c.bond_id 
JOIN molecule m ON b.molecule_id = m.molecule_id 
WHERE m.label = 'TR001_6_9';
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** uses atom_id=19 (a bare integer exact match) instead of gold's SUBSTR(atom_id,-2)='19' (a string suffix match on the compound identifier)

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM connected 
WHERE atom_id = 19;
```

### Q240 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters molecule.label='TR004' instead of gold's atom.molecule_id='TR004'

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE m.label = 'TR004';
```

### Q242 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects molecule.label instead of gold's molecule_id; also treats atom_id as numeric BETWEEN instead of gold's SUBSTR string-suffix BETWEEN, and drops the label='+' filter

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label 
FROM molecule m 
JOIN atom a ON m.molecule_id = a.molecule_id 
WHERE a.atom_id BETWEEN 21 AND 25;
```

### Q243 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** joins connected via c.molecule_id (connected has no molecule_id column) when molecule_id lives on the already-joined bond table - should have joined via bond_id instead; also uses full element names instead of 'p'/'n'

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT b.bond_id, b.bond_type
FROM bond b
JOIN connected c ON b.molecule_id = c.molecule_id
JOIN atom a1 ON c.atom_id = a1.atom_id
JOIN atom a2 ON c.atom_id2 = a2.atom_id
WHERE a1.element = 'phosphorus' AND a2.element = 'nitrogen'
```

### Q244 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's WITH sub CTE + tie-preserving cnt=(SELECT MAX(cnt)...) with ORDER BY COUNT(*) DESC LIMIT 1, dropping ties; also 'double' instead of '='

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
SELECT m.label 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id 
WHERE b.bond_type = 'double' 
GROUP BY m.molecule_id 
ORDER BY COUNT(b.bond_id) DESC 
LIMIT 1;
```

### Q245 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='iodine' instead of the stored abbreviated code 'i'

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) 
FROM (
    SELECT COUNT(*) AS bond_count 
    FROM atom 
    JOIN connected ON atom.atom_id = connected.atom_id 
    WHERE atom.element = 'iodine' 
    GROUP BY atom.atom_id
)
```

### Q247 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra 'atom_id NOT IN (SELECT atom_id2 FROM connected)' condition gold doesn't have

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element 
FROM atom 
WHERE atom_id NOT IN (SELECT atom_id FROM connected) 
AND atom_id NOT IN (SELECT atom_id2 FROM connected);
```

### Q248 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes molecule.label='TR041' for bond.molecule_id='TR041' (molecule_id already lives on the joined bond table); also 'triple' instead of '#'

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT c.atom_id 
FROM connected c 
JOIN bond b ON c.bond_id = b.bond_id 
JOIN molecule m ON b.molecule_id = m.molecule_id 
WHERE b.bond_type = 'triple' AND m.label = 'TR041';
```

### Q249 (challenging, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes molecule.label='TR144_8_19' (via molecule join) for gold's connected.bond_id='TR144_8_19' - connected is dropped entirely

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT atom.element 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR144_8_19';
```

### Q253 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='triple' instead of gold's '#' - structure otherwise matches gold exactly

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN connected c ON a.atom_id = c.atom_id 
JOIN bond b ON c.bond_id = b.bond_id 
WHERE b.bond_type = 'triple';
```

### Q255 (moderate, aggregate) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** entirely omits the molecule join and the label='+' numerator condition, instead computing the overall percentage of bond_type='single' among ALL bonds

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS proportion
FROM bond;
```

### Q260 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restructures gold's molecule-level 'contains a P/Br atom somewhere' existence check into a per-atom filter; also uses 'phosphorus'/'bromine'/'triple' instead of 'p'/'br'/'#'

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
JOIN bond ON molecule.molecule_id = bond.molecule_id 
WHERE bond.bond_type = 'triple' AND (atom.element = 'phosphorus' OR atom.element = 'bromine');
```

### Q263 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='single' and element='chlorine' - both wrong/invented values causing zero matches; also restructures the molecule-scoping into a duplicating direct atom-bond join

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN a.element = 'chlorine' THEN 1 END) * 100.0 / COUNT(a.atom_id)) AS chlorine_percentage
FROM 
    atom a
JOIN 
    bond b ON a.molecule_id = b.molecule_id
WHERE 
    b.bond_type = 'single';
```

### Q273 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label LIKE '%carcinogenic%' and element='chlorine' instead of gold's '+' and 'cl'

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'chlorine' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE m.label LIKE '%carcinogenic%'
```

### Q281 (challenging, retrieval) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** groups by molecule_id instead of gold's element, replacing the per-element COUNT(*) output with an arbitrary single row via LIMIT 3,1; also drops the SUBSTR atom_id filter

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT a.element 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE m.label = 'carcinogenic' 
GROUP BY a.molecule_id 
ORDER BY a.atom_id 
LIMIT 3, 1;
```

### Q282 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='H' (uppercase) instead of the stored lowercase code 'h'

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN element = 'H' THEN 1 END) * 1.0 / COUNT(*)) AS hydrogen_ratio, 
    m.label 
FROM 
    atom a 
JOIN 
    molecule m ON a.molecule_id = m.molecule_id 
WHERE 
    m.molecule_id = 'TR006';
```

### Q327 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects molecule.label instead of gold's molecule_id; also restructures the label='-' filter into NOT LIKE '%carcinogenic%'

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT m.label 
FROM molecule m 
JOIN atom a ON m.molecule_id = a.molecule_id 
WHERE m.label NOT LIKE '%carcinogenic%' 
GROUP BY m.molecule_id 
HAVING COUNT(a.atom_id) > 5;
```

---

