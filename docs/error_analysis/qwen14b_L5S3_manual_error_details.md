# Qwen2.5-Coder-14B · L5·S3 — hand-classified failures (n=281)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. L5 uses the same 3NF physical schema as L3 (gold SQL is identical to `qwen14b_L3S3_*` for the same question), so gold/predicted differences reflect what changed in the model's *predicted* SQL when given L5's richer prompt metadata, not a different database. Predicted SQL uses S3 (descriptive snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. Grouped by database, sorted by question id.

| Category | Legend |
|---|---|
| Invalid SQL | |
| Schema linking | |
| JOIN errors | |
| GROUP BY errors | |
| Nesting problem | |
| Predicate error | |
| Other | |

---

## california_schools (28 failures)

### Q5 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Virtual = 'Yes' vs gold's 'F'; also missing rtype='S' filter

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
SELECT COUNT(*)
FROM satscores
JOIN schools ON satscores.county_district_school_code = schools.county_district_school_code
WHERE satscores.average_score_math > 400 AND schools.Virtual = 'Yes';
```

### Q11 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** condition uses only enrollment_k12, dropping gold's '+ Enrollment (Ages 5-17)' term

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

**Outcome:** `wrong_answer` · **Reason:** divides by enrollment_grade_12 instead of gold's NumTstTakr; also missing rtype='S' and NumTstTakr>0 filters

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

### Q17 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing CharterNum IS NOT NULL and rtype='S' filters

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
    s.charter_number, 
    ss.average_score_writing, 
    RANK() OVER (ORDER BY ss.average_score_writing DESC) AS rank
FROM 
    satscores ss
JOIN 
    schools s ON ss.county_district_school_code = s.county_district_school_code
WHERE 
    ss.average_score_writing > 499;
```

### Q23 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** wraps the enrollment difference in ABS(), which gold doesn't have

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT s.School, s.Street, s.City, s.Zip 
FROM schools s 
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code 
WHERE ABS(f.enrollment_k12 - f.enrollment_ages_5_17) > 30;
```

### Q24 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** school_name belongs to the already-joined frpm, misattributed to the schools alias

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.school_name 
FROM schools s 
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
WHERE f.percent_eligible_free_k12 > 0.1 AND ss.number_scores_1500_or_above > 0;
```

### Q25 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** County substituted for gold's District; also drops the GROUP BY/HAVING entirely

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

### Q26 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing School Type = 'High Schools (Public)' filter

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT 
    s.School AS school_name,
    s.Street AS street_address,
    s.City AS city,
    s.Zip AS zip_code,
    s.State AS state
FROM 
    schools s
JOIN 
    frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE 
    s.County = 'Monterey' 
    AND f.free_or_reduced_price_meal_count_ages_5_17 > 800;
```

### Q27 (moderate, retrieval) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** gold LEFT JOINs satscores; predicted uses a plain JOIN

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT 
    s.School, 
    ss.average_score_writing, 
    s.Phone
FROM 
    schools s
JOIN 
    satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE 
    s.open_date > '1991-12-31' OR s.closed_date < '2000-01-01';
```

### Q28 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** funding_type = 'Locally Funded' (case) vs gold's 'Locally funded'

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

### Q32 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `error` · **Reason:** subquery filters free_or_reduced_price_meal_count_k12 on schools, but that column lives on frpm

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
    county_district_school_code IN (
        SELECT 
            county_district_school_code
        FROM 
            schools
        WHERE 
            school_ownership_code = '66'
        ORDER BY 
            free_or_reduced_price_meal_count_k12 DESC
        LIMIT 5
    )
ORDER BY 
    free_or_reduced_price_meal_count_k12 DESC;
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

### Q37 (moderate, retrieval) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** ranking subquery uses frpm instead of gold's satscores

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
SELECT Street, City, State, Zip 
FROM schools 
WHERE county_district_school_code = (
    SELECT county_district_school_code 
    FROM frpm 
    ORDER BY percent_eligible_free_or_reduced_price_meal_k12 ASC 
    LIMIT 1
);
```

### Q40 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing AvgScrRead IS NOT NULL and rtype='S' filters

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.Phone 
FROM schools s 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
WHERE s.District = 'Fresno Unified' 
ORDER BY ss.average_score_reading ASC 
LIMIT 1;
```

### Q41 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's RANK() OVER PARTITION BY (top-5 per county) replaced by a single MAX-per-county IN-subquery; also Virtual=1 (wrong type) vs gold's 'F'

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
SELECT s.School, s.County, ss.average_score_reading
FROM schools s
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE s.Virtual = 1
AND (s.County, ss.average_score_reading) IN (
    SELECT County, MAX(average_score_reading)
    FROM satscores
    JOIN schools ON satscores.county_district_school_code = schools.county_district_school_code
    WHERE schools.Virtual = 1
    GROUP BY County
)
ORDER BY ss.average_score_reading DESC
LIMIT 5;
```

### Q46 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** educational_option_name='Special' substituted for gold's DOC=31; also adds an unneeded GROUP BY State

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.State, MAX(f.enrollment_k12) AS max_enrollment
FROM schools s
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE s.educational_option_name = 'Special'
GROUP BY s.State
ORDER BY max_enrollment DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*)) -- nested aggregate misuse

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) AS avg_monthly_openings
FROM (
    SELECT strftime('%Y-%m', open_date) AS month
    FROM schools
    WHERE County = 'Alameda' AND District = 'Elementary School District' AND strftime('%Y', open_date) = '1980'
    GROUP BY month
);
```

### Q48 (moderate, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** frpm substituted for gold's schools

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

**Outcome:** `wrong_answer` · **Reason:** missing rtype='S' and AvgScrMath IS NOT NULL filters

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
FROM schools s 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
ORDER BY ss.average_score_math DESC 
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** frpm.is_charter_school substituted for gold's schools.Charter

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
JOIN schools ON frpm.county_district_school_code = schools.county_district_school_code 
WHERE schools.County = 'Los Angeles' 
AND frpm.is_charter_school = 0 
AND frpm.percent_eligible_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** schools.School='State Special School' substituted for gold's EdOpsCode='SSS'

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
JOIN schools ON frpm.county_district_school_code = schools.county_district_school_code 
WHERE frpm.academic_year = '2014-2015' 
AND schools.School = 'State Special School' 
AND schools.City = 'Fremont';
```

### Q77 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** grade_span_offered substituted for gold's grade_span_served

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
    AND s.grade_span_offered = 'K-9';
```

### Q79 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** county_name (an frpm-only alias) referenced directly on schools, which has no such column; Virtual='Yes' also wrong

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT county_name, COUNT(*) AS num_schools
FROM schools
WHERE county_name IN ('San Diego', 'Santa Barbara') AND Virtual = 'Yes'
GROUP BY county_name
ORDER BY num_schools DESC
LIMIT 1;
```

### Q82 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** ORDER BY Longitude DESC instead of gold's ORDER BY ABS(longitude) DESC

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT grade_span_offered FROM schools ORDER BY Longitude DESC LIMIT 1
```

### Q83 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** educational_option_name substituted for gold's NSLP Provision Status

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT 
    City, 
    COUNT(*) AS Number_of_Schools
FROM 
    schools
WHERE 
    grade_span_offered = 'K-8' AND 
    educational_option_name = 'Multiple Provision Types'
GROUP BY 
    City;
```

### Q85 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds two extra OR'd name-field conditions gold doesn't have

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT frpm.percent_eligible_free_k12, frpm.district_code 
FROM frpm 
JOIN schools ON frpm.county_district_school_code = schools.county_district_school_code 
WHERE schools.admin_first_name_1 = 'Alusine' OR schools.admin_first_name_2 = 'Alusine' OR schools.admin_first_name_3 = 'Alusine';
```

### Q87 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** educational_option_name substituted for gold's DOC/SOC codes; City value also wrong

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT 
    admin_email_1 AS email1, 
    admin_email_2 AS email2 
FROM 
    schools 
WHERE 
    County = 'San Bernardino' 
    AND City = 'San Bernardino City Unified' 
    AND open_date BETWEEN '2009-01-01' AND '2010-12-31' 
    AND educational_option_name IN ('Intermediate/Middle School', 'Unified School');
```

---

## debit_card_specializing (24 failures)

### Q1472 (moderate, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** no GROUP BY/SUM at all; picks a single raw row instead of the per-customer annual total gold computes

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.customer_id
FROM customers c
JOIN yearmonth y ON c.customer_id = y.customer_id
WHERE y.date LIKE '2012%' AND c.segment = 'LAM'
ORDER BY y.consumption ASC
LIMIT 1;
```

### Q1473 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) applied to a YYYYMM text column returns NULL, and AVG is taken over raw rows instead of gold's per-customer-then-averaged subquery

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

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', y.date) applied to a YYYYMM text column returns NULL for every row

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
    yearmonth y
JOIN 
    customers c ON y.customer_id = c.customer_id
WHERE 
    strftime('%Y', y.date) = '2012';
```

### Q1479 (moderate, aggregate) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** GROUP BY the full date value instead of gold's SUBSTR(Date,1,4) year

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT date 
FROM yearmonth 
JOIN customers ON yearmonth.customer_id = customers.customer_id 
WHERE customers.currency = 'CZK' 
GROUP BY date 
ORDER BY SUM(consumption) DESC 
LIMIT 1;
```

### Q1480 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) applied to a YYYYMM text column returns NULL; also groups by full date instead of gold's month substring

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT y.date AS peak_month
FROM yearmonth y
JOIN customers c ON y.customer_id = c.customer_id
WHERE c.segment = 'SME' AND strftime('%Y', y.date) = '2013'
GROUP BY y.date
ORDER BY SUM(y.consumption) DESC
LIMIT 1;
```

### Q1481 (challenging, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's 4-CTE per-customer-average/min-selection structure replaced by a flat SUM(CASE) difference

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN c.segment = 'SME' THEN y.consumption ELSE 0 END) - SUM(CASE WHEN c.segment = 'LAM' THEN y.consumption ELSE 0 END)) AS diff_sme_lam,
    (SUM(CASE WHEN c.segment = 'LAM' THEN y.consumption ELSE 0 END) - SUM(CASE WHEN c.segment = 'KAM' THEN y.consumption ELSE 0 END)) AS diff_lam_kam,
    (SUM(CASE WHEN c.segment = 'KAM' THEN y.consumption ELSE 0 END) - SUM(CASE WHEN c.segment = 'SME' THEN y.consumption ELSE 0 END)) AS diff_kam_sme
FROM 
    yearmonth y
JOIN 
    customers c ON y.customer_id = c.customer_id
WHERE 
    y.date LIKE '2013%' AND c.currency = 'CZK';
```

### Q1482 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', y.date) applied to a YYYYMM text column returns NULL

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
    c.currency = 'EUR'
GROUP BY 
    c.segment;
```

### Q1483 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** date BETWEEN '2013-08-01' AND '2013-11-30' (ISO format) vs gold's YYYYMM text bounds '201308'/'201311'

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(consumption) 
FROM yearmonth 
WHERE customer_id = 6 AND date BETWEEN '2013-08-01' AND '2013-11-30';
```

### Q1484 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country full names ('Czech Republic'/'Slovakia') vs gold's codes ('CZE'/'SVK'); segment case also wrong

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN country = 'Czech Republic' THEN 1 ELSE 0 END) - SUM(CASE WHEN country = 'Slovakia' THEN 1 ELSE 0 END) AS difference FROM gasstations WHERE segment = 'discount'
```

### Q1486 (simple, aggregate) — **JOIN errors** (extra table)

**Outcome:** `wrong_answer` · **Reason:** unnecessary join to transactions_1k not in gold, inflating the per-customer counts via duplicate rows

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

**Outcome:** `wrong_answer` · **Reason:** gold LEFT JOINs yearmonth (denominator includes customers with no records); predicted uses a plain JOIN; also missing DISTINCT

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

**Outcome:** `wrong_answer` · **Reason:** date LIKE '2012-02-%' (dashed ISO format) vs gold's YYYYMM text '201202' -- pattern never matches

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM yearmonth 
WHERE date LIKE '2012-02-%';
```

### Q1498 (simple, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** no GROUP BY at all; MAX(consumption) instead of gold's SUM(...) GROUP BY month then take the top

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) FROM yearmonth WHERE date LIKE '2012%'
```

### Q1505 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** currency = 'euro' vs gold's 'EUR'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT y.customer_id) 
FROM yearmonth y 
JOIN customers c ON y.customer_id = c.customer_id 
WHERE c.currency = 'euro' AND y.consumption > 1000;
```

### Q1506 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** country = 'Czech Republic' vs gold's 'CZE'

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

**Outcome:** `wrong_answer` · **Reason:** country = 'Czech Republic' vs gold's 'CZE'

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

### Q1514 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** missing join to gasstations

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT c.currency 
FROM customers c 
JOIN transactions_1k t ON c.customer_id = t.customer_id 
WHERE t.date = '2012-08-24' AND t.time = '16:25:00';
```

### Q1524 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects currency and filters amount instead of gold's country/Price on the already-needed gasstations table

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT c.currency 
FROM customers c 
JOIN transactions_1k t ON c.customer_id = t.customer_id 
WHERE t.date = '2012-08-24' AND t.amount = 548.4;
```

### Q1525 (simple, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** yearmonth substituted for gold's transactions_1k; yearmonth has no daily-granularity Date

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN c.currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(c.customer_id) 
FROM customers c 
JOIN yearmonth y ON c.customer_id = y.customer_id 
WHERE y.date = '2012-08-25';
```

### Q1526 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** amount substituted for gold's price in the weighted total

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
JOIN 
    transactions_1k t ON y2012.customer_id = t.customer_id
WHERE 
    y2012.date = '2012-08-25' 
    AND y2013.date = '2013-08-25' 
    AND t.amount = 634.8;
```

### Q1528 (simple, aggregate) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** joins customers/yearmonth/gasstations via a nonsensical chain_id path instead of gold's single-table gasstations query

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN c.segment = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(c.customer_id)) AS premium_percentage
FROM 
    customers c
JOIN 
    yearmonth y ON c.customer_id = y.customer_id
JOIN 
    gasstations g ON y.customer_id = g.chain_id
WHERE 
    g.country = 'SVK';
```

### Q1529 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** SUM(amount) misses the *Price multiplication in gold's SUM(Amount*Price)

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_spent, 
       SUM(CASE WHEN date LIKE '2012-08-%' THEN amount ELSE 0 END) AS august_2012_spent
FROM transactions_1k
WHERE customer_id = 38508;
```

### Q1531 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** AVG(price) misses the weighting by amount in gold's SUM(Price*Amount)/SUM(Amount)

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

**Outcome:** `wrong_answer` · **Reason:** drops the /Amount division from gold's Price/Amount > 29.00 filter

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

## european_football_2 (35 failures)

### Q1025 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season = '2016' (truncated) vs gold's '2015/2016'

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

### Q1028 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** gold's tie-preserving HAVING = (SELECT MAX(...)) collapsed to ORDER BY ... LIMIT 1

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T3.team_long_name 
FROM Match AS T1 
JOIN League AS T2 ON T1.league_id = T2.id 
JOIN Team AS T3 ON T1.away_team_api_id = T3.team_api_id 
WHERE T2.name = 'Scotland Premier League' AND T1.season = '2010' AND T1.away_team_goals > T1.home_team_goals 
GROUP BY T3.team_long_name 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1030 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season = '2016' (truncated) vs gold's '2015/2016'

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

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on the age computation

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

**Outcome:** `wrong_answer` · **Reason:** gold's tie-preserving HAVING collapsed to ORDER BY ... LIMIT 1

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

### Q1035 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN 50 AND 60 (inclusive) vs gold's exclusive > 50 AND < 60; also missing DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT team_fifa_api_id FROM Team_Attributes WHERE buildup_play_speed BETWEEN 50 AND 60
```

### Q1036 (challenging, aggregate) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on team_long_name

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

**Outcome:** `wrong_answer` · **Reason:** row-level SUM/COUNT(*) instead of gold's COUNT(DISTINCT player)

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

### Q1058 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** references T2.finishing where T2 is Player, not Player_Attributes; also structurally conflates both branches of gold's comparison into one OR condition

**Gold SQL:**

```sql
SELECT A FROM (SELECT AVG(finishing) result, 'highest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MAX(height) FROM Player) UNION SELECT AVG(finishing) result, 'shortest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MIN(height) FROM Player)) tmp ORDER BY result DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CASE WHEN AVG(T1.finishing) > AVG(T2.finishing) THEN 'highest' ELSE 'shortest' END AS result
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T2.height = (SELECT MAX(height) FROM Player)
   OR T2.height = (SELECT MIN(height) FROM Player)
```

### Q1068 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date BETWEEN '2010' AND '2015' compares raw date strings instead of gold's strftime('%Y', date) year extraction

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
JOIN Player ON Player_Attributes.player_api_id = Player.player_api_id 
WHERE Player.height > 170 AND Player_Attributes.date BETWEEN '2010' AND '2015';
```

### Q1076 (challenging, aggregate) — **Nesting problem** (wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** adds a UNION ALL of two separate per-player AVG queries instead of gold's single conditional-difference query

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL:**

```sql
SELECT AVG(T1.ball_control) AS avg_ball_control_abdou_diallo FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Abdou Diallo' GROUP BY T2.player_name UNION ALL SELECT AVG(T1.ball_control) AS avg_ball_control_aaron_appindangoye FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Aaron Appindangoye' GROUP BY T2.player_name
```

### Q1080 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attacking_work_rate = 'High' vs gold's 'low'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player_Attributes WHERE preferred_foot = 'Left' AND attacking_work_rate = 'High';
```

### Q1084 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra attacking_work_rate='High' condition gold doesn't have

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT p.player_api_id) 
FROM Player p 
JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id 
WHERE strftime('%Y', p.birthday) < '1986' 
AND pa.attacking_work_rate = 'High' 
AND pa.defensive_work_rate = 'High';
```

### Q1088 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on player_name

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT P.player_name 
FROM Player P 
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id 
WHERE PA.volleys > 70 AND PA.dribbling > 70;
```

### Q1092 (simple, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** gold's tie-preserving HAVING collapsed to ORDER BY ... LIMIT 1

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

### Q1094 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** player_name for the second player referenced via a Player_Attributes alias instead of joining Player

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT ((A.overall_rating - B.overall_rating) * 100.0 / B.overall_rating) AS percentage_difference
FROM Player_Attributes A
JOIN Player C ON A.player_api_id = C.player_api_id
JOIN Player_Attributes B ON B.player_api_id = C.player_api_id
WHERE C.player_name = 'Ariel Borysiuk' AND B.player_name = 'Paulin Puel';
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** exact date match instead of gold's prefix/format-aware comparison

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.player_name
FROM Player P
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id
WHERE PA.overall_rating = 77 AND PA.date = '2016/6/23'
ORDER BY P.birthday ASC
LIMIT 1;
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** same date exact-match issue as Q1102

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT T1.overall_rating FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Aaron Mooy' AND T1.date = '2016/2/4'
```

### Q1105 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** same date exact-match issue

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.attacking_work_rate FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Francesco Migliore' AND T1.date = '2015/5/1'
```

### Q1107 (moderate, retrieval) — **JOIN errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** joined on player_api_id where gold explicitly needs player_fifa_api_id

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

**Outcome:** `wrong_answer` · **Reason:** same date exact-match issue

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT T2.buildup_play_passing_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 
ON T1.team_api_id = T2.team_api_id 
WHERE T1.team_long_name = 'FC Lorient' AND T2.date = '2010/2/22';
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** same date exact-match issue

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
WHERE T1.team_long_name = 'Hannover 96' AND T2.date = '2015/9/10';
```

### Q1114 (challenging, aggregate) — **JOIN errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** joined on player_api_id where gold explicitly needs player_fifa_api_id

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

### Q1115 (challenging, aggregate) — **JOIN errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** joined on player_api_id where gold explicitly needs player_fifa_api_id

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT ((a1.overall_rating - a2.overall_rating) * 100.0 / a2.overall_rating) AS percentage_difference
FROM Player_Attributes a1
JOIN Player p1 ON a1.player_api_id = p1.player_api_id
JOIN Player_Attributes a2 ON a2.player_api_id = p1.player_api_id
JOIN Player p2 ON a2.player_api_id = p2.player_api_id
WHERE p1.player_name = 'Landon Donovan' AND p2.player_name = 'Jordan Bowery' AND a1.date = '2013/7/12' AND a2.date = '2013/7/12';
```

### Q1122 (simple, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** strength substituted for gold's overall_rating

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1124 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds a bizarre EXISTS-based extra condition gold doesn't have

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.player_name
FROM Player p
JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id
WHERE pa.attacking_work_rate = 'High'
AND EXISTS (
    SELECT 1
    FROM Player_Attributes pa2
    WHERE pa2.player_api_id != pa.player_api_id
    AND pa2.attacking_work_rate = 'High'
);
```

### Q1130 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on player_name

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T.team_short_name 
FROM Team_Attributes AS TA 
JOIN Team AS T ON TA.team_api_id = T.team_api_id 
WHERE TA.chance_creation_passing_class = 'Safe';
```

### Q1135 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** preferred_foot = 'Right' (case) vs gold's 'right'

**Gold SQL:**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'Right' ORDER BY potential ASC LIMIT 4
```

### Q1136 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra attacking_work_rate='High' condition gold doesn't have

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

**Outcome:** `wrong_answer` · **Reason:** 'Belgian' vs gold's 'Belgium'

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

### Q1141 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra IN-list restriction gold doesn't have

**Gold SQL:**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL:**

```sql
SELECT DISTINCT ta.buildup_play_speed_class 
FROM Team_Attributes ta 
JOIN Team t ON ta.team_api_id = t.team_api_id 
WHERE t.team_long_name = 'KSV Cercle Brugge' 
AND ta.buildup_play_speed_class IN ('slow', 'balanced', 'fast');
```

### Q1144 (simple, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's nested max-weight subquery (tie-preserving) replaced by ORDER BY ... LIMIT 1

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT T1.finishing, T1.curve FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id ORDER BY T2.weight DESC LIMIT 1
```

### Q1145 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season = '2015-2016' (hyphen) vs gold's '2015/2016' (slash)

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

**Outcome:** `wrong_answer` · **Reason:** strength substituted for gold's overall_rating

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1148 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** strength > 70 substituted for gold's overall_rating > 70

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN height < 180 AND strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Player JOIN Player_Attributes ON Player.player_api_id = Player_Attributes.player_api_id
```

---

## financial (22 failures)

### Q89 (moderate, aggregate) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** trans.type='VYDAJ' substituted for gold's account.frequency filter; region case also wrong

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
WHERE d.region = 'East Bohemia' AND t.type = 'VYDAJ';
```

### Q93 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** region = 'North Bohemia' (case) vs gold's 'north Bohemia'

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(*)
FROM client
JOIN district ON client.district_id = district.district_id
WHERE client.gender = 'M'
AND district.region = 'North Bohemia'
AND district.average_salary > 8000;
```

### Q95 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** ORDER BY birth_date ASC (oldest) instead of gold's DESC (youngest) -- direction reversed

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
JOIN district di ON c.district_id = di.district_id
ORDER BY c.birth_date ASC, di.average_salary DESC
LIMIT 1;
```

### Q98 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency = 'weekly' (translated) vs gold's untranslated 'POPLATEK TYDNE'

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

### Q99 (moderate, retrieval) — **Other** (missing LIMIT)

**Outcome:** `wrong_answer` · **Reason:** drops gold's LIMIT 1, returning all grouped rows instead of the single top one

**Gold SQL:**

```sql
SELECT T1.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T2.date) = '1993' AND T1.duration > 12 ORDER BY T1.amount DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id, MAX(l.amount) AS max_amount
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE l.duration_months > 12 AND strftime('%Y', a.date) = '1993'
GROUP BY a.account_id
ORDER BY max_amount DESC;
```

### Q112 (simple, retrieval) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** missing joins to account and district (predicted only reaches client+disp)

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
WHERE c.gender = 'F' AND c.birth_date = '1976-01-29';
```

### Q115 (challenging, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** gold's GROUP BY A4 (number_inhabitants) dropped entirely; region case also wrong

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
    district d ON c.district_id = d.district_id
WHERE 
    d.region = 'South Bohemia'
ORDER BY 
    d.number_inhabitants DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** MAX/MIN over a date range substituted for gold's exact-two-date conditional sums; also adds an unneeded GROUP BY client_id

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
    l.date = '1993-07-05' AND
    t.date BETWEEN '1993-03-22' AND '1998-12-27'
GROUP BY 
    c.client_id;
```

### Q118 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status = 'A' vs gold's 'C'

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

**Outcome:** `wrong_answer` · **Reason:** status='A' (vs gold's 'D'); drops the /A12*100 normalization; adds an invented amount>0 filter

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

### Q129 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type = 'withdrawal' (translated) vs gold's untranslated 'VYDAJ'

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT d.district_name
FROM trans t
JOIN account a ON t.account_id = a.account_id
JOIN district d ON a.district_id = d.district_id
WHERE t.type = 'withdrawal' AND t.date BETWEEN '1996-01-01' AND '1996-01-31'
ORDER BY t.amount DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency = 'Monthly' (translated) vs gold's untranslated 'POPLATEK MESICNE'

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT a.account_id) 
FROM account a 
JOIN loan l ON a.account_id = l.account_id 
WHERE a.statement_frequency = 'Monthly' 
AND l.amount >= 250000 
AND l.date BETWEEN '1995-01-01' AND '1997-12-31';
```

### Q137 (moderate, aggregate) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** missing join to loan entirely (status IN ('C','D') can't be evaluated); district_name value also invented

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM account 
JOIN district ON account.district_id = district.district_id 
WHERE district.district_name = 'Branch location 1';
```

### Q145 (moderate, aggregate) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** references card.account_id directly, which requires an unjoined path through disp; type='credit' also an invented value

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT t.account_id
FROM trans t
JOIN card c ON t.account_id = c.account_id
WHERE t.type = 'credit' AND t.amount < (SELECT AVG(amount) FROM trans WHERE strftime('%Y', date) = '1998') AND strftime('%Y', t.date) = '1998';
```

### Q149 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency/average_salary projected instead of gold's disp.type; a loan-NULL check substituted for type<>'OWNER'

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
LEFT JOIN loan l ON a.account_id = l.account_id
WHERE l.loan_id IS NULL AND d.average_salary BETWEEN 8000 AND 9000;
```

### Q152 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** number_inhabitants filtered where gold filters number_crimes_1995 (A15)

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(d.number_crimes_1995) 
FROM district d 
JOIN account a ON d.district_id = a.district_id 
WHERE d.number_inhabitants > 4000 AND strftime('%Y', a.date) >= '1997'
```

### Q159 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** trans.type substituted for gold's trans.operation -- two different real columns confused

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

**Outcome:** `wrong_answer` · **Reason:** missing disp.type='OWNER' filter

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END) AS total_loans_1996,
    SUM(CASE WHEN strftime('%Y', l.date) = '1997' THEN l.amount ELSE 0 END) AS total_loans_1997,
    ((SUM(CASE WHEN strftime('%Y', l.date) = '1997' THEN l.amount ELSE 0 END) - SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END)) * 100.0 / SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END)) AS growth_rate
FROM 
    loan l
JOIN 
    disp d ON l.account_id = d.account_id
JOIN 
    client c ON d.client_id = c.client_id
WHERE 
    c.gender = 'M';
```

### Q173 (challenging, aggregate) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** trans substituted for gold's "order" table

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
    account.account_id = 3 AND trans.amount < 0
GROUP BY 
    statement_frequency;
```

### Q186 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency = 'weekly' (translated) vs gold's untranslated 'POPLATEK TYDNE'

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.statement_frequency = 'weekly' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM account AS T1 JOIN disp AS T2 ON T1.account_id = T2.account_id JOIN client AS T3 ON T2.client_id = T3.client_id WHERE T3.gender = 'M'
```

### Q192 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='A' vs gold's IN('C','D'); statement_frequency='monthly' translated/wrong term

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(loan.amount) 
FROM loan 
JOIN account ON loan.account_id = account.account_id 
WHERE loan.status = 'A' AND account.statement_frequency = 'monthly';
```

### Q194 (moderate, retrieval) — **JOIN errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins loan on client_id = account_id, a nonsensical key mismatch; card.type value also wrong

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.client_id, strftime('%Y', 'now') - strftime('%Y', c.birth_date) AS age
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN card ca ON d.disposition_id = ca.disposition_id
JOIN loan l ON c.client_id = l.account_id
WHERE ca.type = 'high level' AND l.status = 'A';
```

---

## formula_1 (43 failures)

### Q846 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** results substituted for gold's qualifying; position>10 filter unrelated to gold's ORDER BY q1

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT T1.driver_ref_name FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T2.race_id = 20 AND T2.position > 10
```

### Q847 (simple, retrieval) — **Other** (tie-handling)

**Outcome:** `wrong_answer` · **Reason:** drops gold's NULLS LAST tie-break on q2

**Gold SQL:**

```sql
SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 ORDER BY T1.q2 ASC NULLS LAST LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.last_name FROM drivers d JOIN qualifying q ON d.driver_id = q.driver_id WHERE q.race_id = 19 ORDER BY q.qualifying_2_time LIMIT 1
```

### Q850 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on name

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT name FROM races WHERE circuit_id IN (SELECT circuit_id FROM circuits WHERE country = 'Germany')
```

### Q854 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** circuits.name used directly instead of gold's races.name (join to races missing)

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Australian Grand Prix'
```

### Q857 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** same circuits.name vs races.name pattern as Q854

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Abu Dhabi Grand Prix'
```

### Q859 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** number substituted for gold's race_id filter

**Gold SQL:**

```sql
SELECT T1.q1 FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 354 AND T2.forename = 'Bruno' AND T2.surname = 'Senna'
```

**Predicted SQL:**

```sql
SELECT T2.qualifying_1_time FROM drivers AS T1 INNER JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T1.first_name = 'Bruno' AND T1.last_name = 'Senna' AND T2.number = 354
```

### Q861 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** qualify_id used instead of gold's race_id; exact time match instead of LIKE pattern

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT T1.number FROM drivers AS T1 INNER JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T2.qualify_id = 903 AND T2.qualifying_3_time = '0:01:54'
```

### Q865 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** position IS NOT NULL substituted for gold's time IS NOT NULL

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name FROM drivers WHERE driver_id IN (SELECT driver_id FROM results WHERE race_id = 592 AND position IS NOT NULL) ORDER BY date_of_birth ASC LIMIT 1
```

### Q866 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** exact time match '0:01:27' instead of gold's LIKE '1:27%' pattern

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.url 
FROM drivers d 
JOIN laptimes lt ON d.driver_id = lt.driver_id 
WHERE lt.race_id = 161 AND lt.time = '0:01:27'
```

### Q868 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** circuits.name used directly instead of gold's races.name

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE name = 'Malaysian Grand Prix'
```

### Q869 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** constructorStandings substituted for gold's constructorResults

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

### Q872 (simple, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** qualify_3_time doesn't exist anywhere (real column is qualifying_3_time)

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT d.driver_code 
FROM drivers d 
JOIN qualifying q ON d.driver_id = q.driver_id 
WHERE q.qualify_3_time = '0:01:33' AND q.race_id = 45;
```

### Q877 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing time IS NOT NULL filter

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
LIMIT 1
```

### Q879 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds a fastest_lap_speed IS NOT NULL filter but drops gold's CAST(...AS REAL), risking lexicographic sort

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.nationality 
FROM drivers d 
JOIN results r ON d.driver_id = r.driver_id 
WHERE r.fastest_lap_speed IS NOT NULL 
ORDER BY r.fastest_lap_speed DESC 
LIMIT 1;
```

### Q880 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters results.number=853 instead of gold's race_id=853/854; MAX/MIN substituted for the two-race CASE comparison

**Gold SQL:**

```sql
SELECT ((MAX(CASE WHEN r.`raceId` = 853 THEN CAST(r.`fastestLapSpeed` AS REAL) END) -
         MAX(CASE WHEN r.`raceId` = 854 THEN CAST(r.`fastestLapSpeed` AS REAL) END)) * 100.0) /
       MAX(CASE WHEN r.`raceId` = 854 THEN CAST(r.`fastestLapSpeed` AS REAL) END) AS percent_faster
FROM `drivers` d
JOIN `results`  r ON d.`driverId` = r.`driverId`
WHERE d.`forename` = 'Paul'
  AND d.`surname`  = 'di Resta';
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(fastest_lap_speed) - MIN(fastest_lap_speed)) * 100.0 / MAX(fastest_lap_speed) AS percentage_faster
FROM 
    results
JOIN 
    drivers ON results.driver_id = drivers.driver_id
WHERE 
    drivers.first_name = 'Paul' AND drivers.last_name = 'di Resta' AND results.number = 853;
```

### Q881 (moderate, aggregate) — **GROUP BY errors** (missing_or_extra_groupby)

**Outcome:** `wrong_answer` · **Reason:** adds GROUP BY driver_id that gold's single overall-percentage query doesn't have

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT 
    d.first_name, 
    d.last_name, 
    COUNT(r.result_id) * 100.0 / COUNT(DISTINCT r.race_id) AS completion_rate
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

### Q884 (moderate, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's year+month subquery match replaced by a simpler MIN(date) equality, missing ties within the same month

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT name FROM races WHERE date = (SELECT MIN(date) FROM races)
```

### Q894 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects the time string instead of gold's milliseconds numeric value

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.time, T2.first_name, T2.last_name, T1.name 
FROM races AS T1 
JOIN drivers AS T2 ON T3.driver_id = T2.driver_id 
JOIN laptimes AS T3 ON T1.race_id = T3.race_id 
ORDER BY T3.milliseconds ASC 
LIMIT 1
```

### Q896 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** circuit_id != 1 substituted for gold's position <> 1; driver filtered by name instead of joined surname condition

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN D.first_name = 'Lewis' AND D.last_name = 'Hamilton' AND C.circuit_id != 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM results R 
JOIN drivers D ON R.driver_id = D.driver_id 
JOIN races RA ON R.race_id = RA.race_id 
JOIN circuits C ON RA.circuit_id = C.circuit_id 
WHERE RA.year >= 2010;
```

### Q897 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** wins = MAX(wins) substituted for gold's GROUP BY-then-ORDER-BY-COUNT(wins) logic -- restructured metric

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

**Outcome:** `wrong_answer` · **Reason:** drops the computed age expression, projecting raw date_of_birth instead of gold's age subtraction

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name, date_of_birth FROM drivers WHERE nationality = 'Japanese' ORDER BY date_of_birth DESC LIMIT 1
```

### Q902 (simple, retrieval) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** results/grid_position substituted for gold's driverStandings/position

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT r.name FROM races r JOIN results res ON r.race_id = res.race_id JOIN drivers d ON res.driver_id = d.driver_id WHERE d.first_name = 'Alex' AND d.last_name = 'Yoong' AND res.grid_position < 20
```

### Q904 (moderate, retrieval) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** results substituted for gold's lapTimes

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT r.name, r.year 
FROM races r 
JOIN results res ON r.race_id = res.race_id 
JOIN drivers d ON res.driver_id = d.driver_id 
WHERE d.first_name = 'Michael' AND d.last_name = 'Schumacher' 
ORDER BY res.fastest_lap_time ASC 
LIMIT 1;
```

### Q915 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** circuits.country substituted for gold's drivers.nationality

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.country FROM circuits AS T1 INNER JOIN races AS T2 ON T1.circuit_id = T2.circuit_id INNER JOIN results AS T3 ON T2.race_id = T3.race_id INNER JOIN drivers AS T4 ON T3.driver_id = T4.driver_id ORDER BY T4.date_of_birth ASC LIMIT 1
```

### Q930 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** ORDER BY position ASC LIMIT 1 substituted for gold's rank = 0 filter

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT r.name FROM races r JOIN results res ON r.race_id = res.race_id JOIN drivers d ON res.driver_id = d.driver_id WHERE d.first_name = 'Lewis' AND d.last_name = 'Hamilton' ORDER BY res.position ASC LIMIT 1
```

### Q937 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'AustChineseralian Grand Prix' -- garbled literal vs gold's 'Chinese Grand Prix'

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

**Outcome:** `wrong_answer` · **Reason:** missing time IS NOT NULL filter

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

### Q944 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing time IS NOT NULL filter on the champion/last-driver time comparison

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT ((MAX(results.milliseconds) - MIN(results.milliseconds)) * 100.0 / MIN(results.milliseconds)) AS percentage_faster
FROM results
JOIN races ON results.race_id = races.race_id
WHERE races.year = 1988 AND races.name = 'Australian Grand Prix';
```

### Q950 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** constructorResults substituted for gold's constructorStandings

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

### Q955 (challenging, aggregate) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** single races table substituted for gold's results/races join -- no winning-time column available

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT year, AVG(TIME) AS avg_time_seconds FROM races WHERE year < 1975 GROUP BY year
```

### Q959 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** MAX(fastest_lap_number)/position=1 substituted for gold's time LIKE pattern filter

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT MAX(results.fastest_lap_number) 
FROM results 
JOIN races ON results.race_id = races.race_id 
WHERE races.year = 2009 AND results.position = 1
```

### Q962 (challenging, aggregate) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** COUNT(DISTINCT race_id, driver_id) -- multi-column DISTINCT COUNT is invalid SQLite syntax

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN D.date_of_birth < '1985-01-01' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT R.race_id, D.driver_id) 
FROM races R 
JOIN results RES ON R.race_id = RES.race_id 
JOIN drivers D ON RES.driver_id = D.driver_id 
WHERE R.year BETWEEN 2000 AND 2005 AND RES.laps >= 50;
```

### Q967 (simple, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's top-3-youngest subquery-then-count structure dropped entirely; also nationality = 'Netherlandic' (wrong value)

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM drivers WHERE nationality = 'Netherlandic' ORDER BY date_of_birth DESC LIMIT 3
```

### Q972 (moderate, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on driver_id/driver_code

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

**Outcome:** `wrong_answer` · **Reason:** drops the time IS NOT NULL conditional-SUM measure entirely, substituting a plain COUNT(*); date range also inclusive vs gold's exclusive bounds

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM results WHERE race_id BETWEEN 50 AND 100 AND status_id = (SELECT status_id FROM status WHERE status = 'Disqualified')
```

### Q978 (simple, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on location/lat/lng

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE country = 'Austria'
```

### Q981 (moderate, retrieval) — **Other** (wrong aggregate function/scaling)

**Outcome:** `wrong_answer` · **Reason:** wraps year in MIN() without a GROUP BY, so the other projected columns (name/date/time) come from an arbitrary row instead of gold's ORDER BY date ASC LIMIT 1

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

### Q988 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** AVG(milliseconds) substituted for gold's AVG(duration)

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, AVG(p.milliseconds) AS avg_pit_stop_duration
FROM drivers d
JOIN pitStops p ON d.driver_id = p.driver_id
WHERE d.nationality = 'German' AND d.date_of_birth BETWEEN '1980-01-01' AND '1985-12-31'
GROUP BY d.driver_id
ORDER BY avg_pit_stop_duration ASC
LIMIT 3;
```

### Q989 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's time LIKE pattern filter, substituting an unrelated ORDER BY position LIMIT 1

**Gold SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T2.time FROM races AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id WHERE T1.name = 'Canadian Grand Prix' AND T1.year = 2008 ORDER BY T2.position LIMIT 1
```

### Q990 (challenging, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** constructorStandings substituted for gold's results

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

### Q994 (challenging, aggregate) — **Other** (SELECT-list shape)

**Outcome:** `wrong_answer` · **Reason:** aggregate column projected first in predicted vs last in gold's tuple order

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
    constructors c
JOIN 
    constructorResults cr ON c.constructor_id = cr.constructor_id
JOIN 
    races r ON cr.race_id = r.race_id
WHERE 
    r.name = 'Monaco Grand Prix' 
    AND r.year BETWEEN 1980 AND 2010
GROUP BY 
    c.constructor_id
ORDER BY 
    total_points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** position=1 substituted for gold's computed-fastest-q3-time ordering; adds an invented round=3 filter

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
WHERE r.year = 2008 AND c.name = 'Marina Bay Street Circuit' AND q.position = 1 AND r.round = 3;
```

### Q1014 (challenging, aggregate) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** lapTimes.lap (lap number) substituted for gold's results.FastestLapTime string-parsed comparison

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(lap) FROM lapTimes WHERE race_id IN (SELECT race_id FROM races WHERE circuit_id IN (SELECT circuit_id FROM circuits WHERE country = 'Italy'))
```

---

## student_club (24 failures)

### Q1322 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type = 'meeting' (case) vs gold's 'Meeting'

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

### Q1334 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** state = 'IL' (abbreviation) vs gold's 'Illinois'

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name 
FROM member m 
JOIN zip_code z ON m.zip_code = z.zip_code 
WHERE z.state = 'IL';
```

### Q1338 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** exact date match '2019-10-08' instead of gold's LIKE prefix pattern (time-suffix issue)

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

### Q1339 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** restricts to a specific year (2023) that gold's month-only match (any year) doesn't have

**Gold SQL:**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL:**

```sql
SELECT AVG(cost) 
FROM expense 
JOIN member ON expense.member_id = member.member_id 
WHERE member.first_name = 'Elijah' AND member.last_name = 'Allen' 
AND strftime('%Y-%m', expense.expense_date) IN ('2023-09', '2023-10');
```

### Q1340 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds an extra invented status='Student_Club' condition

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN strftime('%Y', event_date) = '2019' THEN amount_spent ELSE 0 END) - 
    SUM(CASE WHEN strftime('%Y', event_date) = '2020' THEN amount_spent ELSE 0 END) AS difference
FROM 
    budget
JOIN 
    event ON budget.event_id = event.event_id
WHERE 
    event.status = 'Student_Club';
```

### Q1344 (simple, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** event substituted for gold's income; also wrong date format

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE event_name = 'fundraising' AND event_date = '2019/9/14'
```

### Q1350 (moderate, retrieval) — **Schema linking** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** joins event and selects its status instead of using budget.event_status directly; date format also wrong

**Gold SQL:**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT e.status 
FROM event e 
JOIN budget b ON e.event_id = b.event_id 
JOIN expense ex ON b.budget_id = ex.budget_id 
WHERE ex.expense_description = 'Post Cards, Posters' AND ex.expense_date = '2019/8/20';
```

### Q1357 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** income_source = 'dues' (case) vs gold's 'Dues'

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT date_received 
FROM income 
WHERE member_id = (SELECT member_id FROM member WHERE first_name = 'Connor' AND last_name = 'Hilton') 
AND income_source = 'dues';
```

### Q1359 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** computes a subtraction instead of gold's ratio (division); missing type='Meeting' filter

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN e.event_name = 'Yearly Kickoff' THEN b.amount ELSE 0 END) - 
    SUM(CASE WHEN e.event_name = 'October Meeting' THEN b.amount ELSE 0 END) AS difference
FROM 
    budget b
JOIN 
    event e ON b.event_id = e.event_id
WHERE 
    b.category = 'Advertisement';
```

### Q1376 (moderate, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's nested MAX-ratio subquery with tie-preserving HAVING replaced by ORDER BY ... LIMIT 1; status case also wrong

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

**Outcome:** `wrong_answer` · **Reason:** category = 'food' (case) vs gold's 'Food'

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

### Q1387 (moderate, retrieval) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** member joined directly to budget on event_id; missing the expense/event joins gold uses; category value also wrong

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name 
FROM member m 
JOIN budget b ON m.member_id = b.event_id 
WHERE b.category = 'Yearly Kickoff';
```

### Q1390 (moderate, aggregate) — **JOIN errors** (missing table)

**Outcome:** `error` · **Reason:** expense joined directly to event_id, which requires the unjoined budget table as an intermediate step

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
    expense ex ON e.event_id = ex.event_id;
```

### Q1398 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** category = 'advertisement' (case) vs gold's 'Advertisement'

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT event_name 
FROM event 
WHERE event_id = (
    SELECT event_id 
    FROM budget 
    WHERE category = 'advertisement' 
    ORDER BY amount_spent DESC 
    LIMIT 1
);
```

### Q1403 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** recomputes overspend via SUM(cost) - amount instead of using the existing remaining column; status case also wrong

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

**Outcome:** `error` · **Reason:** category belongs to the already-joined budget, misattributed to the expense alias

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
WHERE ev.event_name = 'October Meeting' AND e.is_approved = 'yes'
GROUP BY e.category;
```

### Q1409 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** expense_date = '8/20/2019' (US format) vs gold's ISO '2019-08-20'

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) AS total_expense
FROM expense
WHERE expense_date = '8/20/2019';
```

### Q1422 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** budget.category substituted for gold's event.type

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT category 
FROM budget 
WHERE event_id IN (
    SELECT event_id 
    FROM event 
    WHERE location = 'MU 215'
);
```

### Q1427 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type = 'guest speaker' (case) vs gold's 'Guest Speaker'

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

**Outcome:** `wrong_answer` · **Reason:** missing position='Member' filter; adds an extra invented income_source='Student_Club' condition

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

**Outcome:** `wrong_answer` · **Reason:** type/status case mismatches ('game'/'closed' vs 'Game'/'Closed')

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

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT (join to budget also dropped, but harmless since gold's own subquery doesn't filter on it either)

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

### Q1460 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 3-item IN-list of lowercase words substituted for gold's single combined description string

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

### Q1464 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** date_received = '9/9/2019' (US format) vs gold's ISO '2019-09-09'

**Gold SQL:**

```sql
SELECT M.`first_name`, M.`last_name`, I.`amount`
FROM `Income` I
JOIN `Member` M ON M.`member_id` = I.`link_to_member`
WHERE I.`date_received` = '2019-09-09';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, i.amount
FROM income i
JOIN member m ON i.member_id = m.member_id
WHERE i.date_received = '9/9/2019';
```

---

## superhero (24 failures)

### Q724 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour values 'blue'/'blond' (case) vs gold's 'Blue'/'Blond'

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') 
AND hair_colour_id = (SELECT id FROM colour WHERE colour = 'blond');
```

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing height_cm IS NOT NULL AND != 0 filters

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT superhero_name, height_cm 
FROM superhero 
JOIN publisher ON superhero.publisher_id = publisher.id 
WHERE publisher_name = 'Marvel Comics' 
ORDER BY height_cm DESC;
```

### Q728 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's RANK() OVER window function replaced by plain GROUP BY/ORDER BY with no window function

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.colour, COUNT(*) AS count
FROM superhero s
JOIN colour c ON s.eye_colour_id = c.id
JOIN publisher p ON s.publisher_id = p.id
WHERE p.publisher_name = 'Marvel Comics'
GROUP BY c.colour
ORDER BY count DESC;
```

### Q732 (moderate, retrieval) — **Invalid SQL** (wrong column)

**Outcome:** `error` · **Reason:** s.speed doesn't exist anywhere -- Speed is a value in the EAV attribute table, not a superhero column

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

**Outcome:** `wrong_answer` · **Reason:** colour = 'gold' (case) vs gold's 'Gold'

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

**Outcome:** `wrong_answer` · **Reason:** attribute_name = 'intelligence' (case) vs gold's 'Intelligence'

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE id = (
    SELECT hero_id 
    FROM hero_attribute 
    WHERE attribute_id = (
        SELECT id 
        FROM attribute 
        WHERE attribute_name = 'intelligence'
    ) 
    ORDER BY attribute_value ASC 
    LIMIT 1
);
```

### Q743 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alignment = 'Self-Centric' vs the real value 'Bad'

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN a.alignment = 'Self-Centric' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) AS percentage_self_centric,
    SUM(CASE WHEN a.alignment = 'Self-Centric' AND p.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) AS count_marvel_self_centric
FROM 
    superhero s
JOIN 
    alignment a ON s.alignment_id = a.id
JOIN 
    publisher p ON s.publisher_id = p.id;
```

### Q744 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** publisher_name IN ('DC','Marvel') (abbreviated) vs gold's 'DC Comics'/'Marvel Comics'; also drops the difference computation

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

**Outcome:** `wrong_answer` · **Reason:** missing weight_kg > 0 filter

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero WHERE gender_id = (SELECT id FROM gender WHERE gender = 'Female')
```

### Q753 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** assumes NULL eye_colour_id represents 'No Colour' instead of joining the real colour='No Colour' row

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

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on colour

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

**Outcome:** `wrong_answer` · **Reason:** gold's tie-preserving max_strength CTE replaced by ORDER BY ... LIMIT 1

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

**Outcome:** `wrong_answer` · **Reason:** joins colour 3x to project resolved colour names instead of gold's raw eye/hair/skin_colour_id values

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    c1.colour AS eye_colour, 
    c2.colour AS hair_colour, 
    c3.colour AS skin_colour 
FROM 
    superhero s 
JOIN 
    colour c1 ON s.eye_colour_id = c1.id 
JOIN 
    colour c2 ON s.hair_colour_id = c2.id 
JOIN 
    colour c3 ON s.skin_colour_id = c3.id 
JOIN 
    gender g ON s.gender_id = g.id 
JOIN 
    publisher p ON s.publisher_id = p.id 
WHERE 
    g.gender = 'Female' AND 
    p.publisher_name = 'Dark Horse Comics';
```

### Q775 (challenging, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** eye_colour_id substituted for gold's skin_colour_id

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN c.colour = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    superhero s 
JOIN 
    gender g ON s.gender_id = g.id 
JOIN 
    colour c ON s.eye_colour_id = c.id 
WHERE 
    g.gender = 'Female';
```

### Q782 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour = 'black' (case) vs gold's 'Black'

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'black') 
AND hair_colour_id = (SELECT id FROM colour WHERE colour = 'black');
```

### Q786 (moderate, aggregate) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's tie-preserving MAX-equality subquery replaced by ORDER BY ... LIMIT 1, losing ties

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT ha.`hero_id`)
FROM `hero_attribute` AS ha
JOIN `attribute` AS a ON ha.`attribute_id` = a.`id`
WHERE a.`attribute_name` = 'Strength'
  AND ha.`attribute_value` = (
        SELECT MAX(ha2.`attribute_value`)
        FROM `hero_attribute` ha2
        JOIN `attribute` a2 ON ha2.`attribute_id` = a2.`id`
        WHERE a2.`attribute_name` = 'Strength'
      );
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
WHERE id IN (
    SELECT hero_id 
    FROM hero_attribute 
    WHERE attribute_id = (
        SELECT id 
        FROM attribute 
        WHERE attribute_name = 'Strength'
    ) 
    ORDER BY attribute_value DESC 
    LIMIT 1
);
```

### Q788 (challenging, aggregate) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** gold LEFT JOINs publisher (denominator = all Female); predicted uses INNER JOIN and filters publisher in WHERE, restricting both numerator and denominator to Marvel

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

**Outcome:** `wrong_answer` · **Reason:** superhero_name substituted for gold's full_name

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT (SELECT weight_kg FROM superhero WHERE superhero_name = 'Emil Blonsky') - (SELECT weight_kg FROM superhero WHERE superhero_name = 'Charles Chandler') AS weight_difference
```

### Q791 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** missing height_cm > 0 filter

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### Q794 (moderate, retrieval) — **Nesting problem** (wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold's tie-preserving MAX-equality subquery replaced by ORDER BY ... LIMIT 1, losing ties

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE id = (SELECT hero_id FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'Speed') ORDER BY attribute_value DESC LIMIT 1)
```

### Q797 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour values 'blue'/'brown' (case) vs gold's 'Blue'/'Brown'

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name 
FROM superhero s 
JOIN colour c1 ON s.eye_colour_id = c1.id 
JOIN colour c2 ON s.hair_colour_id = c2.id 
WHERE c1.colour = 'blue' AND c2.colour = 'brown';
```

### Q800 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour = 'blue' (case) vs gold's 'Blue'

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN c.colour = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM superhero s 
JOIN colour c ON s.eye_colour_id = c.id;
```

### Q819 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** assumes eye_colour_id IS NULL means id=1's colour instead of matching it directly; drops the 'weight_kg = 0 OR' half of gold's condition

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') THEN 1 ELSE 0 END) - 
    SUM(CASE WHEN eye_colour_id IS NULL THEN 1 ELSE 0 END) AS difference
FROM 
    superhero
WHERE 
    weight_kg IS NULL;
```

### Q829 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** publisher_name = 'DC' (abbreviated) vs gold's 'DC Comics'

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

## thrombosis_prediction (47 failures)

### Q1149 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male' vs gold's 'M'; also restructures the in/out ratio into a per-admission-type percentage-of-total

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    admission_type, 
    COUNT(*) AS count, 
    CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM Patient WHERE sex = 'male') AS percentage
FROM 
    Patient
WHERE 
    sex = 'male'
GROUP BY 
    admission_type;
```

### Q1150 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'female' vs gold's 'F'

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient 
WHERE strftime('%Y', birthday) > '1930';
```

### Q1152 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type = 'Inpatient'/'Outpatient' (assumed translated values) vs gold's '+'/'-' codes

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) * 1.0 / 
    SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END) AS inpatient_to_outpatient_ratio
FROM 
    Patient
WHERE 
    diagnosis = 'SLE';
```

### Q1155 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 175 vs gold's 500

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

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree > 0 substituted for gold's RVVT = '+'

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

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree = 'severe' (assumed translated string) vs gold's numeric code 2

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

**Outcome:** `wrong_answer` · **Reason:** sex/admission_type both wrong translated values vs gold's 'F'/'-'

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
AND admission_type = 'outpatient';
```

### Q1164 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex value in Chinese ('女') vs gold's 'F'; MAX(thrombosis_degree) subquery substituted for gold's fixed Thrombosis = 1

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
AND E.thrombosis_degree = (SELECT MAX(thrombosis_degree) FROM Examination WHERE strftime('%Y', examination_date) = '1997') 
AND strftime('%Y', E.examination_date) = '1997';
```

### Q1166 (simple, retrieval) — **Nesting problem** (wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** gold's UNION (handling the no-symptoms edge case) dropped entirely; also MIN(birthday) (oldest) substituted for gold's MAX(Birthday) (youngest) -- direction reversed

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT E.symptoms, P.diagnosis 
FROM Examination E 
JOIN Patient P ON E.ID = P.ID 
WHERE P.birthday = (SELECT MIN(birthday) FROM Patient);
```

### Q1168 (challenging, retrieval) — **Other** (wrong aggregate function/scaling)

**Outcome:** `wrong_answer` · **Reason:** MAX(Date) mixed with non-aggregated Patient columns with no GROUP BY, returning an arbitrary row for age/diagnosis

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    MAX(L.Date) AS last_laboratory_date,
    strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age_at_first_hospital_visit
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

### Q1169 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male'/'female' vs gold's 'M'/'F'; single UA>7.0 threshold substituted for gold's gender-specific 8.0/6.5 thresholds

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
    L.uric_acid > 7.0;
```

### Q1171 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold < 0 vs gold's < 18

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

**Outcome:** `wrong_answer` · **Reason:** projects raw sex/birthday/diagnosis instead of gold's computed age + diagnosis

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
WHERE L.hemoglobin = (SELECT MAX(hemoglobin) FROM Laboratory)
```

### Q1179 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** birthday = '1994-02-19' substituted for gold's Description filter; extra igg column also selected

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT E.anticardiolipin_igg, E.anticardiolipin_igm
FROM Examination E
JOIN Patient P ON E.ID = P.ID
WHERE P.diagnosis = 'SLE' AND P.birthday = '1994-02-19' AND E.examination_date = '1993-11-12';
```

### Q1185 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** self-join with MAX/MIN over date ranges substituted for gold's single-pass conditional sums by specific month

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (MAX(L1.total_cholesterol) - MIN(L2.total_cholesterol)) / MAX(L1.total_cholesterol) AS decrease_rate
FROM 
    Laboratory L1
JOIN 
    Laboratory L2 ON L1.ID = L2.ID
JOIN 
    Patient P ON L1.ID = P.ID
WHERE 
    P.birthday = '1959-02-18'
    AND L1.Date BETWEEN '1981-11-01' AND '1981-11-30'
    AND L2.Date BETWEEN '1981-12-01' AND '1981-12-31';
```

### Q1187 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** examination_date substituted for gold's Laboratory.Date; aspartate_aminotransferase (GOT/AST) substituted for gold's GPT (ALT)

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

**Outcome:** `wrong_answer` · **Reason:** predicted's AVG subquery drops gold's WHERE filters (Thrombosis=2 AND ANA Pattern='S'), averaging over all examinations instead

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE E.thrombosis_degree = 2 
AND E.antinuclear_antibody_pattern = 'S' 
AND E.anticardiolipin_igm > (SELECT AVG(anticardiolipin_igm) * 1.2 FROM Examination);
```

### Q1192 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type in Chinese ('门诊') vs gold's '-'; total_bilirubin BETWEEN 5 AND 20 vs gold's < 2.0

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, P.sex, P.birthday, P.first_record_date, P.first_hospital_visit_date, P.admission_type, P.diagnosis
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE P.admission_type = '门诊' AND L.Date BETWEEN '1991-10-01' AND '1991-10-31' AND L.total_bilirubin BETWEEN 5 AND 20;
```

### Q1195 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'female' vs gold's 'F'

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

**Outcome:** `wrong_answer` · **Reason:** sex = 'female' vs gold's 'F'

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

**Outcome:** `wrong_answer` · **Reason:** sex value in Chinese ('女') vs gold's 'F'

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

**Outcome:** `wrong_answer` · **Reason:** single BETWEEN 2.4-7.0 range substituted for gold's gender-specific F>6.5/M>8.0 conditional logic

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN uric_acid BETWEEN 2.4 AND 7.0 THEN 'true' ELSE 'false' END AS uric_acid_normal FROM Laboratory WHERE ID = 57266
```

### Q1208 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male' vs gold's 'M'; threshold 40 vs gold's 60

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

### Q1209 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** aspartate_aminotransferase (GOT/AST) substituted for gold's GPT (ALT); threshold 40 vs gold's 60

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.diagnosis 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.aspartate_aminotransferase > 40 
ORDER BY P.birthday ASC;
```

### Q1220 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 40 vs gold's exact value 29

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.urea_nitrogen = 40;
```

### Q1225 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** total_bilirubin < 0.3 OR > 1.2 substituted for gold's >= 2.0; COUNT(*) substituted for gold's GROUP_CONCAT(DISTINCT ID)

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

### Q1227 (moderate, aggregate) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** YEAR() is not a SQLite function

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
    WHERE total_cholesterol > 200
);
```

### Q1229 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 150 vs gold's >= 200

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
      strftime('%Y', 'now') - strftime('%Y', P.birthday) - 
      (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) > 50;
```

### Q1231 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male' vs gold's 'M'; threshold 130 vs gold's 250

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
AND P.birthday BETWEEN '1936-01-01' AND '1956-12-31' 
AND L.creatinine_phosphokinase > 130;
```

### Q1232 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** blood_glucose < 70 OR > 110 substituted for gold's single >= 180 condition; AND/OR operator-precedence bug further scrambles the logic

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

**Outcome:** `wrong_answer` · **Reason:** dynamic AVG(...) subquery threshold substituted for gold's fixed literal < 3.5

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

### Q1238 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** hemoglobin = 'normal' (categorical) substituted for gold's numeric BETWEEN 10 AND 17

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.diagnosis = 'SLE' AND L.hemoglobin = 'normal' 
ORDER BY P.birthday ASC 
LIMIT 1;
```

### Q1239 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** hematocrit BETWEEN 45 AND 55 vs gold's >= 52 (single-sided)

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.hematocrit > 45 AND L.hematocrit < 55
GROUP BY P.ID
HAVING COUNT(L.ID) >= 2;
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thresholds 150/450 vs gold's 100/400

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(CASE WHEN T2.platelet_count < 150 THEN 1 END) AS lower_than_normal,
    COUNT(CASE WHEN T2.platelet_count > 450 THEN 1 END) AS higher_than_normal
FROM 
    Patient AS T1
JOIN 
    Laboratory AS T2 ON T1.ID = T2.ID;
```

### Q1242 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold scale 150000-450000 vs gold's 100-400 -- unit mismatch

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, P.sex, P.birthday, L.Date, L.platelet_count
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE strftime('%Y', L.Date) = '1984'
AND strftime('%Y', 'now') - strftime('%Y', P.birthday) < 50
AND L.platelet_count BETWEEN 150000 AND 450000;
```

### Q1243 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 13.5 vs gold's 14

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
    AND L.prothrombin_time > 13.5;  -- Assuming normal PT is <= 13.5
```

### Q1247 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male' vs gold's 'M'; WBC/fibrinogen thresholds wrong; AND/OR operator-precedence bug further scrambles the logic

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
AND L.white_blood_cell_count BETWEEN 4.0 AND 11.0 
AND L.fibrinogen < 200 OR L.fibrinogen > 400;
```

### Q1251 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 150 vs gold's 2000 -- unit mismatch

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT ID) 
FROM Laboratory 
WHERE immunoglobulin_g > 150;
```

### Q1252 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_g = 'normal' (categorical) substituted for gold's numeric BETWEEN 900 AND 2000

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

### Q1254 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_a = 'normal' (categorical) substituted for gold's numeric BETWEEN 80 AND 500

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.immunoglobulin_a = 'normal' AND P.first_hospital_visit_date > '1990-01-01';
```

### Q1256 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** NOT IN subquery (patients without abnormal CRP) substituted for gold's positive AND-combination (CRP='+' AND Description IS NULL) -- inverted logic

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
WHERE ID NOT IN (
    SELECT DISTINCT ID 
    FROM Laboratory 
    WHERE c_reactive_protein = 'abnormal'
);
```

### Q1257 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** threshold 1.2 vs gold's 1.5; birthday > '2015-01-01' substituted for gold's age < 70 condition

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.creatinine > 1.2 AND P.birthday > '2015-01-01'
```

### Q1265 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type = 'admitted' vs gold's '+'

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

### Q1267 (moderate, aggregate) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** gold's LEFT JOIN+COALESCE (keeps patients with no exam record) replaced by an INNER JOIN, excluding them from the count

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
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
JOIN Examination E ON P.ID = E.ID 
WHERE L.anti_sm = 'normal' AND E.thrombosis_degree = 0;
```

### Q1270 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'female' vs gold's 'F'

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
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
LEFT JOIN Examination E ON P.ID = E.ID 
WHERE L.anti_scl70 = 'normal' 
AND P.sex = 'female' 
AND (E.symptoms IS NULL OR E.symptoms = '');
```

### Q1275 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male' vs gold's 'M'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.anti_centromere = 'normal' AND L.anti_ssb = 'normal' AND P.sex = 'male';
```

### Q1281 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** MIN(birthday) substituted for gold's ORDER BY Birthday DESC LIMIT 1; aspartate/alanine aminotransferase OR'd together with wrong threshold, substituted for gold's GOT >= 60

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

---

## toxicology (34 failures)

### Q197 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type = 'single' vs gold's '-'

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(oxygen_count) 
FROM (
    SELECT COUNT(*) AS oxygen_count 
    FROM atom 
    JOIN bond ON atom.molecule_id = bond.molecule_id 
    JOIN connected ON atom.atom_id = connected.atom_id 
    WHERE atom.element = 'O' AND bond.bond_type = 'single' 
    GROUP BY atom.molecule_id
)
```

### Q198 (challenging, aggregate) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*)) -- nested aggregate misuse

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) 
FROM bond 
WHERE bond_type = 'single' 
GROUP BY molecule_id;
```

### Q200 (simple, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects m.label instead of gold's molecule_id; bond_type/label values also wrong

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

**Outcome:** `wrong_answer` · **Reason:** element case 'C' vs 'c'; bond_type 'double' vs gold's '='

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN a.element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    atom a 
JOIN 
    bond b ON a.molecule_id = b.molecule_id 
WHERE 
    b.bond_type = 'double';
```

### Q206 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `error` · **Reason:** b.label doesn't belong on bond (that identifier exists only on molecule, for an unrelated purpose); gold needs no bond join at all, just connected.bond_id

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN connected c ON a.atom_id = c.atom_id 
JOIN bond b ON c.bond_id = b.bond_id 
WHERE b.label = 'TR004_8_9';
```

### Q207 (challenging, retrieval) — **JOIN errors** (missing table)

**Outcome:** `wrong_answer` · **Reason:** joins atom directly to bond via molecule_id, missing gold's connected junction table

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN bond b ON a.molecule_id = b.molecule_id 
WHERE b.bond_type = 'double';
```

### Q208 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element = 'H' vs gold's 'h'

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

**Outcome:** `wrong_answer` · **Reason:** gold's tie-preserving HAVING = (SELECT MIN(cnt)...) dropped; replaced by an unrelated NOT IN filter with no HAVING

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
WHERE molecule_id NOT IN (
    SELECT molecule_id 
    FROM molecule 
    WHERE label LIKE '%carcinogenic%'
) 
GROUP BY element 
ORDER BY COUNT(*) ASC 
LIMIT 1;
```

### Q215 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case 'I'/'S' vs 'i'/'s'; bond_type 'single' vs gold's '-'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(*) AS iodine_count, 
    'Iodine' AS element_type
FROM 
    atom
JOIN 
    molecule ON atom.molecule_id = molecule.molecule_id
JOIN 
    bond ON molecule.molecule_id = bond.molecule_id
WHERE 
    atom.element = 'I' AND bond.bond_type = 'single'

UNION ALL

SELECT 
    COUNT(*) AS sulfur_count, 
    'Sulfur' AS element_type
FROM 
    atom
JOIN 
    molecule ON atom.molecule_id = molecule.molecule_id
JOIN 
    bond ON molecule.molecule_id = bond.molecule_id
WHERE 
    atom.element = 'S' AND bond.bond_type = 'single';
```

### Q218 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case 'F' vs 'f'; label = 'carcinogenic' vs gold's '+'

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN element != 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM atom 
WHERE molecule_id IN (SELECT molecule_id FROM molecule WHERE label = 'carcinogenic');
```

### Q219 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invented values 'triple'/'carcinogenic' vs gold's '#'/'+' 

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond.bond_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM bond 
JOIN molecule ON bond.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'carcinogenic';
```

### Q226 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type = 'double' vs gold's '='

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond_type = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond WHERE molecule_id = 'TR008'
```

### Q227 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label = 'carcinogenic' vs gold's '+'

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

**Outcome:** `wrong_answer` · **Reason:** filters m.label='TR206' where gold filters atom.molecule_id directly; element case also wrong

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR206'
```

### Q230 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters m.label='TR060' where gold filters molecule_id directly

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element, m.label 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE m.label = 'TR060';
```

### Q232 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects/filters m.label instead of gold's molecule_id; bond_type/label conditions also wrong

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id 
WHERE b.bond_type = 'single' 
AND m.label NOT LIKE '%carcinogenic%' 
ORDER BY m.label ASC 
LIMIT 3;
```

### Q234 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** atom_id = '12' (partial) vs gold's full composite 'TR009_12'; also drops the atom_id2 half of gold's OR condition

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM bond 
JOIN connected ON bond.bond_id = connected.bond_id 
JOIN atom ON connected.atom_id = atom.atom_id 
WHERE atom.atom_id = '12' AND bond.molecule_id = 'TR009';
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** exact match atom_id='19' substituted for gold's SUBSTR(atom_id,-2)='19' suffix match

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM connected 
WHERE atom_id = '19';
```

### Q240 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins molecule and filters label='TR004' instead of using atom.molecule_id directly

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT DISTINCT element 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR004';
```

### Q242 (moderate, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects m.label instead of gold's molecule_id; also drops the SUBSTR suffix match and the label='+' filter

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label 
FROM molecule m 
JOIN atom a ON m.molecule_id = a.molecule_id 
WHERE a.atom_id BETWEEN '21' AND '25';
```

### Q243 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invented values 'phosphorus'/'nitrogen' vs gold's 'p'/'n'

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT b.bond_id
FROM bond b
JOIN connected c ON b.bond_id = c.bond_id
JOIN atom a1 ON c.atom_id = a1.atom_id
JOIN atom a2 ON c.atom_id2 = a2.atom_id
WHERE a1.element = 'phosphorus' AND a2.element = 'nitrogen'
```

### Q244 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type = 'double' vs gold's '='; also loses ties via ORDER BY ... LIMIT 1

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

**Outcome:** `wrong_answer` · **Reason:** element = 'iodine' vs gold's 'i'

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
);
```

### Q247 (challenging, retrieval) — **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` · **Reason:** missing DISTINCT on element

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element 
FROM atom 
WHERE atom_id NOT IN (SELECT atom_id FROM connected);
```

### Q248 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type = 'triple' vs gold's '#'

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT atom_id 
FROM atom 
WHERE molecule_id = 'TR041' AND atom_id IN (
    SELECT atom_id 
    FROM connected 
    WHERE bond_id IN (
        SELECT bond_id 
        FROM bond 
        WHERE molecule_id = 'TR041' AND bond_type = 'triple'
    )
);
```

### Q249 (challenging, retrieval) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** atom.molecule_id substituted for gold's connected.bond_id

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE molecule_id = 'TR144_8_19';
```

### Q253 (challenging, retrieval) — **JOIN errors** (wrong table)

**Outcome:** `wrong_answer` · **Reason:** joins atom directly to bond via molecule_id, missing gold's connected junction table

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN bond b ON a.molecule_id = b.molecule_id 
WHERE b.bond_type = 'triple';
```

### Q255 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** bond_type = 'single' vs gold's '-'; also drops the join to molecule/label='+' entirely

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond
```

### Q260 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** invented values 'triple'/'phosphorus'/'bromine' vs gold's '#'/'p'/'br'

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
WHERE bond.bond_type = 'triple' AND atom.element IN ('phosphorus', 'bromine');
```

### Q263 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case 'Cl' vs 'cl'; bond_type 'single' vs gold's '-'

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN a.element = 'Cl' THEN 1 END) * 100.0 / COUNT(a.element)) AS chlorine_percentage
FROM 
    atom a
JOIN 
    bond b ON a.molecule_id = b.molecule_id
WHERE 
    b.bond_type = 'single';
```

### Q273 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element case 'Cl' vs 'cl'; label 'carcinogenic' vs gold's '+'

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN a.element = 'Cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM 
    atom a 
JOIN 
    molecule m ON a.molecule_id = m.molecule_id 
WHERE 
    m.label = 'carcinogenic';
```

### Q281 (challenging, retrieval) — **GROUP BY errors** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** GROUP BY molecule_id instead of gold's element; also missing the SUBSTR suffix filter and label='carcinogenic' wrong value

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
GROUP BY m.molecule_id 
ORDER BY COUNT(*) 
LIMIT 3, 1;
```

### Q282 (challenging, aggregate) — **Invalid SQL** (other execution error)

**Outcome:** `error` · **Reason:** ambiguous column name: molecule_id (exists on both joined tables, unqualified reference)

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN element = 'H' THEN 1 END) * 1.0 / COUNT(*)) AS hydrogen_ratio, 
    label 
FROM 
    atom 
JOIN 
    molecule ON atom.molecule_id = molecule.molecule_id 
WHERE 
    molecule_id = 'TR006';
```

### Q327 (moderate, aggregate) — **Schema linking** (wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects m.label instead of gold's molecule_id; label condition also wrong

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

