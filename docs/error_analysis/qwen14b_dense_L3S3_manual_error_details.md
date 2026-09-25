# Qwen2.5-Coder-14B (dense) - L3-S3 - hand-classified failures (n=234)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. This covers the **dense** few-shot method (`dense_fs3` prompt variant) at structural level L3 (native 3NF) / semantic level S3. Predicted SQL uses S3 (descriptive snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. Many labels below were additionally verified empirically by executing both gold and predicted SQL (or close hand-translations) directly against the dev SQLite databases, not just inferred from reading the query text. L3 is native 3NF, so Fan-out never applies here. Grouped by database, sorted by question id.

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

## california_schools (27 failures)

### Q5 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops rtype='S' filter (satscores likely also has district-level rtype='D' rows inflating COUNT(*)); Virtual filtered as 'Yes' (not a real domain value; should be 'F'); also omits DISTINCT

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
FROM satscores AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.average_score_math > 400 AND T2.Virtual = 'Yes'
```

### Q11 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** omits the schools join needed for the 'School is not NULL' filter; also drops the Enrollment(Ages 5-17) addition term, comparing only Enrollment(K-12) to 500

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT county_district_school_code FROM frpm WHERE enrollment_k12 > 500
```

### Q12 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** WHERE ratio divides by enrollment_grade_12 instead of number_test_takers; SELECT swaps to the precomputed percent column and drops rtype/enrollment filters

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
SELECT MAX(T2.percent_eligible_free_ages_5_17) 
FROM satscores AS T1 
INNER JOIN frpm AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.number_scores_1500_or_above / T1.enrollment_grade_12 > 0.3
```

### Q17 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops CharterNum IS NOT NULL and rtype='S' filters; join, columns, and window function otherwise match gold

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
    RANK() OVER (ORDER BY T1.average_score_writing DESC) as rank 
FROM 
    satscores AS T1 
INNER JOIN 
    schools AS T2 
ON 
    T1.county_district_school_code = T2.county_district_school_code 
WHERE 
    T1.average_score_writing > 499
```

### Q23 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** adds ABS() around the enrollment difference gold doesn't have; also drops the School IS NOT NULL filter

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT T2.School, T2.Street 
FROM frpm AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE ABS(T1.enrollment_k12 - T1.enrollment_ages_5_17) > 30
```

### Q24 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** missing rtype='S' filter; percent_eligible_free_k12 is a legitimate stand-in for the raw ratio (verified: stored as the same unscaled fraction as gold's manual computation)

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT s.school_name 
FROM frpm f 
JOIN satscores s ON f.county_district_school_code = s.county_district_school_code 
WHERE f.percent_eligible_free_k12 > 0.1 AND s.number_scores_1500_or_above > 0
```

### Q25 (moderate, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` - **Reason:** gold's per-group HAVING AVG(AvgScrMath)>400 (GROUP BY sname,FundingType) collapsed to a flat per-row WHERE filter with no GROUP BY; also filters City='Riverside' instead of District LIKE 'Riverside%'

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
SELECT T2.School, T2.funding_type FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.City = 'Riverside' AND T1.average_score_math > 400
```

### Q26 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** grade_span_offered substituted for school_type in the 'High Schools (Public)' filter; county and FRPM-count-Ages-5-17 comparison are otherwise correct

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT T2.School, T2.Street, T2.City, T2.Zip, T2.State 
FROM frpm AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.county_name = 'Monterey' 
AND T1.free_or_reduced_price_meal_count_ages_5_17 > 800 
AND T2.grade_span_offered LIKE '%12%'
```

### Q27 (moderate, retrieval) -- **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` - **Reason:** INNER JOIN drops schools with no matching satscores row that gold's LEFT JOIN preserves; also selects an extra phone_extension column not in gold

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT T2.School, T1.average_score_writing, T2.Phone, T2.phone_extension 
FROM satscores AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.open_date > '1991-12-31' OR T2.closed_date < '2000-01-01'
```

### Q31 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** omits the schools join needed for the 'school is not null' filter

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT `percent_eligible_free_k12` 
FROM frpm 
ORDER BY `enrollment_k12` DESC 
LIMIT 9, 2
```

### Q32 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** SELECT and ORDER BY use the Ages-5-17 FRPM count/percent columns instead of the required K-12 variants; also adds an extra school_name column

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT 
    T1.school_name, 
    T1.percent_eligible_free_or_reduced_price_meal_ages_5_17 
FROM 
    frpm AS T1 
JOIN 
    schools AS T2 
ON 
    T1.county_district_school_code = T2.county_district_school_code 
WHERE 
    T2.school_ownership_code = 66 
ORDER BY 
    T1.free_or_reduced_price_meal_count_ages_5_17 DESC 
LIMIT 5;
```

### Q36 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** missing rtype='S' filter

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
INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
ORDER BY T1.number_scores_1500_or_above DESC 
LIMIT 1
```

### Q37 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes frpm's percent_eligible_free_or_reduced_price_meal_k12 ordering for gold's satscores NumGE1500/NumTstTakr MIN-ratio subquery

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
FROM frpm AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
ORDER BY T1.percent_eligible_free_or_reduced_price_meal_k12 ASC 
LIMIT 1
```

### Q39 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters mailing_city='Fresno' instead of County='Fresno' -- a different real column; date-range conversion of the year filter is otherwise equivalent

**Gold SQL:**

```sql
SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'
```

**Predicted SQL:**

```sql
SELECT AVG(T1.number_test_takers) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.mailing_city = 'Fresno' AND T2.open_date BETWEEN '1980-01-01' AND '1980-12-31'
```

### Q41 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** replaces gold's RANK() OVER (PARTITION BY county ORDER BY AvgScrRead DESC) window function with a GROUP BY/ORDER BY/LIMIT approximation that only returns the single overall top-5 rows, not top-5-per-county; also Virtual='Y' instead of 'F'

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
SELECT T2.School, T2.County 
FROM satscores AS T1 
INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.Virtual = 'Y' 
GROUP BY T2.County, T2.School 
ORDER BY AVG(T1.average_score_reading) DESC 
LIMIT 5
```

### Q46 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters educational_option_code='SPECON' instead of district_ownership_code=31 -- a different real column; also introduces an unneeded GROUP BY State/SUM aggregation, selecting State instead of School

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.State, SUM(T1.enrollment_k12) AS total_enrollment 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.educational_option_code = 'SPECON' 
GROUP BY T2.State 
ORDER BY total_enrollment DESC 
LIMIT 1
```

### Q47 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` - **Reason:** AVG(COUNT(*)) nested aggregate misuse

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) 
FROM (
    SELECT open_date, COUNT(*) 
    FROM schools 
    WHERE strftime('%Y', open_date) = '1980' 
      AND County = 'Alameda' 
      AND District = 'Elementary School District' 
    GROUP BY strftime('%m', open_date)
)
```

### Q48 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` - **Reason:** queries frpm (district_type/status_type/County) instead of schools -- errors on status_type since frpm has no such column, only schools does; also collapses gold's two independent COUNT(*) subqueries into one CASE-based ratio using district_type text values instead of DOC codes

**Gold SQL:**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN district_type = 'Unified School District' THEN 1 ELSE 0 END) AS REAL) / SUM(CASE WHEN district_type = 'Elementary School District' THEN 1 ELSE 0 END) 
FROM frpm 
WHERE status_type = 'Merged' AND County = 'Orange'
```

### Q50 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops rtype='S' and AvgScrMath IS NOT NULL filters

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
SELECT T2.mailing_street, T2.School 
FROM satscores AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
ORDER BY T1.average_score_math DESC 
LIMIT 6, 1
```

### Q62 (challenging, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** uses precomputed percent_eligible_free_k12 (verified stored as an unscaled 0-1 fraction) without gold's *100 scaling on the Free Meal Count/Enrollment ratio

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

### Q72 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters County='Fremont' instead of City='Fremont' (Fremont is a city, not a valid County value); also uses educational_option_name with a near-miss literal instead of EdOpsCode='SSS'

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT SUM(T1.enrollment_ages_5_17) 
FROM frpm AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.academic_year = '2014-2015' 
AND T2.County = 'Fremont' 
AND T2.educational_option_name = 'State Special School'
```

### Q77 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** grade_span_offered used instead of grade_span_served for the GSserved='K-9' filter; SELECT also omits gold's *100 scaling on the eligibility ratio (verified: the precomputed percent field is an unscaled fraction)

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT T2.School, T1.percent_eligible_free_ages_5_17 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.County = 'Los Angeles' AND T2.grade_span_offered = 'KG-09'
```

### Q79 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** Virtual='Yes' is an invented value; the real domain values for this column are 'F'/'N'/'P', not Yes/No

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
LIMIT 1
```

### Q82 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** missing ABS() around longitude, reversing which extreme (east vs west) is picked; also adds an unnecessary join to frpm

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.grade_span_offered FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code ORDER BY T2.Longitude DESC LIMIT 1
```

### Q83 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` - **Reason:** grade_span_offered belongs to schools (T2) but is referenced via the frpm alias T1 -- an alias mix-up on an already-joined table, causing the error; also substitutes educational_option_type for NSLP Provision Status

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT T2.City, COUNT(*) 
FROM frpm AS T1 
INNER JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.grade_span_offered = 'Kindergarten to 8th' 
AND T1.educational_option_type = 'Multiple Provision Types' 
GROUP BY T2.City
```

### Q85 (moderate, retrieval) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** selects the precomputed percent_eligible_free_k12 field (verified stored as an unscaled 0-1 fraction) instead of gold's explicit *100-scaled ratio -- a scaling mismatch, not a different real column; the WHERE filter (admin_first_name_1='Alusine') matches gold exactly

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT f.percent_eligible_free_k12, f.district_code 
FROM frpm f 
JOIN schools s ON f.county_district_school_code = s.county_district_school_code 
WHERE s.admin_first_name_1 = 'Alusine'
```

### Q87 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** replaces SOC=62 (school_ownership_code) with an instruction_level_name OR condition; also drops the DOC=54 filter entirely

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT admin_email_1, admin_email_2 
FROM schools 
WHERE County = 'San Bernardino' 
AND City = 'San Bernardino' 
AND open_date BETWEEN '2009-01-01' AND '2010-12-31' 
AND instruction_level_name IN ('Intermediate/Middle School', 'Unified School')
```

---

## debit_card_specializing (13 failures)

### Q1473 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** AVG(consumption) computed directly over monthly rows instead of gold's per-customer SUM(Consumption) subquery /12 -- missing the required derived-table aggregation step

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consumption) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T1.segment = 'SME' AND SUBSTRING(T2.date, 1, 4) = '2013'
```

### Q1476 (challenging, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** verified numerically equivalent to gold (402524570.170002 vs 402524570.169991, a floating-point summation-order artifact under 1e-5 relative error) -- IIF vs CASE and BETWEEN 201201-201212 vs SUBSTR(Date,1,4)='2012' are both confirmed non-bugs; the tiny residual mismatch is a harness floating-point precision artifact, not a real SQL error

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT (SUM(CASE WHEN T1.currency = 'CZK' THEN T2.consumption ELSE 0 END) - SUM(CASE WHEN T1.currency = 'EUR' THEN T2.consumption ELSE 0 END)) AS difference FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T2.date BETWEEN 201201 AND 201212
```

### Q1480 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** strftime('%Y', date) misapplied to yearmonth's 'YYYYMM' text format returns NULL for all rows (verified), so the WHERE filter matches zero rows; the also-wrong GROUP BY date and MAX-instead-of-SUM are moot

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT date 
FROM yearmonth 
WHERE customer_id IN (
    SELECT customer_id 
    FROM customers 
    WHERE segment = 'SME'
) 
AND date BETWEEN 201301 AND 201312 
GROUP BY date 
ORDER BY SUM(consumption) DESC 
LIMIT 1
```

### Q1481 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` - **Reason:** predicted SQL is truncated mid-query and includes a literal ```sql fence, causing a syntax error; also abandons gold's segment-comparison CTEs for an unrelated per-customer extremes computation

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
```sql
SELECT 
    (SELECT AVG(consumption) 
     FROM customers AS c1 
     INNER JOIN yearmonth AS ym1 
     ON c1.customer_id = ym1.customer_id 
     WHERE ym1.date BETWEEN '201301' AND '201312' 
       AND c1.currency = 'CZK' 
       AND c1.segment = 'SME' 
     ORDER BY SUM(ym1.consumption) ASC 
     LIMIT 1) - 
    (SELECT AVG(consumption) 
     FROM customers AS c2 
     INNER JOIN yearmonth AS ym2 
     ON c2.customer_id = ym2.customer_id 
     WHERE ym2.date BETWEEN '201301' AND '201312' 
       AND c2.currency = 'CZK' 
       AND c2.segment = 'LAM' 
     ORDER BY SUM(ym2.consumption) ASC 
     LIMIT 1) AS diff_sme_lam,

    (SELECT AVG(consumption) 
     FROM customers AS c3 
     INNER JOIN yearmonth AS ym3 
     ON c3.customer_id = ym3.customer_id 
     WHERE ym3.date BETWEEN '201301' AND '201312' 
       AND c3.currency = 'CZK' 
       AND c3.segment = 'LAM' 
     ORDER BY SUM(ym3.consumption) ASC 
     LIMIT 1) - 
    (SELECT AVG(consumption) 
     FROM customers AS c4 
     INNER JOIN yearmonth AS ym4 
     ON c4.customer_id = ym4.customer_id 
     WHERE ym4.date BETWEEN '201301' AND '201312' 
       AND c4.currency = 'CZK' 
       AND c4.segment = 'KAM' 
     ORDER BY SUM(ym4.consumption) ASC 
     LIMIT 1) AS diff_lam_kam,

    (SELECT AVG(consumption) 
     FROM customers AS c5 
     INNER JOIN yearmonth AS ym5 
     ON c5.customer_id = ym5.customer_id 
     WHERE ym5.date BETWEEN '201301' AND '201312' 
       AND c5.currency
```

### Q1482 (challenging, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** restructures gold's single-row three-column (SME/LAM/KAM) conditional-sum output into a GROUP BY T1.segment aggregation producing 3 separate rows -- a GROUP BY presence/shape mismatch not present in gold; underlying SUBSTRING-based year filtering is equivalent to gold's SUBSTR (verified SUBSTRING works in this SQLite build)

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    T1.segment, 
    ((SUM(CASE WHEN SUBSTRING(T2.date, 1, 4) = '2013' THEN T2.consumption ELSE 0 END) - 
      SUM(CASE WHEN SUBSTRING(T2.date, 1, 4) = '2012' THEN T2.consumption ELSE 0 END)) * 100.0 / 
     SUM(CASE WHEN SUBSTRING(T2.date, 1, 4) = '2012' THEN T2.consumption ELSE 0 END)) AS percentage_change
FROM 
    customers AS T1 
INNER JOIN 
    yearmonth AS T2 
ON 
    T1.customer_id = T2.customer_id 
WHERE 
    T1.currency = 'EUR' 
GROUP BY 
    T1.segment;
```

### Q1490 (moderate, aggregate) -- **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` - **Reason:** uses INNER JOIN where gold's LEFT JOIN preserves customers with no yearmonth rows; also drops the COUNT(DISTINCT...) per-customer dedup

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(consumption > 46.73, 1, 0)) AS REAL) * 100 / COUNT(*) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T1.segment = 'LAM'
```

### Q1498 (simple, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** missing GROUP BY entirely (gold groups by month); also uses MAX instead of SUM, returning the single largest individual reading instead of the peak month's total

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) AS HighestMonthlyConsumption FROM yearmonth WHERE date LIKE '2012%'
```

### Q1514 (simple, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** predicted omits DISTINCT and the (redundant, non-filtering) gasstations join that gold itself never references any column of; if multiple transactions share this exact date/time, duplicate currency values would appear

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT T2.currency FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.customer_id = T2.customer_id WHERE T1.date = '2012-08-24' AND T1.time = '16:25:00'
```

### Q1525 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** joins yearmonth instead of transactions_1k -- yearmonth's Date field is 'YYYYMM' format and never matches the literal '2012-08-25', so the query returns zero/NULL; also drops the COUNT(DISTINCT...) dedup

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(T2.currency = 'EUR') AS FLOAT) * 100 / COUNT(T2.customer_id) 
FROM yearmonth AS T1 
INNER JOIN customers AS T2 
ON T1.customer_id = T2.customer_id 
WHERE T1.date = '2012-08-25'
```

### Q1526 (challenging, aggregate) -- **Other** (extra SELECT column)

**Outcome:** `wrong_answer` - **Reason:** verified numerically identical to gold (-5.81524267467235 exactly) -- the nested-subquery-to-join/GROUP BY rewrite is a faithful equivalent; the only defect is an extra CustomerID column added to the SELECT list that gold doesn't have, causing an output-shape/column-count mismatch

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT 
    T1.customer_id, 
    (SUM(CASE WHEN T2.date BETWEEN '201201' AND '201212' THEN T2.consumption ELSE 0 END) - 
     SUM(CASE WHEN T2.date BETWEEN '201301' AND '201312' THEN T2.consumption ELSE 0 END)) / 
    SUM(CASE WHEN T2.date BETWEEN '201201' AND '201212' THEN T2.consumption ELSE 0 END) AS consumption_decrease_rate
FROM 
    transactions_1k AS T1 
INNER JOIN 
    yearmonth AS T2 
ON 
    T1.customer_id = T2.customer_id 
WHERE 
    T1.date = '2012-08-25' 
    AND T1.price = 634.8 
GROUP BY 
    T1.customer_id
```

### Q1529 (moderate, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** SUM(amount) omits the *Price multiplication gold's Amount*Price expression includes -- a missing scaling factor, not the raw quantity alone; the LIKE date-pattern filter is equivalent aside from an extra hyphen

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_spent, 
       SUM(CASE WHEN date LIKE '2012-08-%' THEN amount ELSE 0 END) AS august_spent 
FROM transactions_1k 
WHERE customer_id = 38508;
```

### Q1531 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** replaces gold's nested subquery (selecting the customer with the single highest total SUM(Amount*Price) spend) with an ORDER BY SUM(price) DESC LIMIT 1 approximation over a per-customer GROUP BY -- ranks by total price sum instead of total amount*price spend, a different customer-selection criterion; also computes AVG(price) instead of gold's amount-weighted SUM(Price*Amount)/SUM(Amount)

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT T3.customer_id, AVG(T1.price) AS avg_price_per_item, T3.currency 
FROM transactions_1k AS T1 
INNER JOIN customers AS T3 ON T1.customer_id = T3.customer_id 
GROUP BY T3.customer_id 
ORDER BY SUM(T1.price) DESC 
LIMIT 1
```

### Q1533 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares raw Price > 29.00 instead of gold's per-unit ratio Price/Amount > 29.00 -- drops the division by Amount entirely

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT T1.consumption 
FROM yearmonth AS T1 
INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id 
WHERE T2.product_id = 5 AND T2.price > 29.00 AND T1.date = '201208'
```

---

## european_football_2 (28 failures)

### Q1025 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** season filtered as '2016' instead of the real 'YYYY/YYYY' format '2015/2016' (verified: matches zero rows); SUM(home)+SUM(away) split is mathematically identical to gold's SUM(home+away)

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT t1.name 
FROM League AS t1 
INNER JOIN Match AS t2 ON t1.id = t2.league_id 
WHERE t2.season = '2016' 
GROUP BY t1.name 
ORDER BY SUM(t2.home_team_goals) + SUM(t2.away_team_goals) DESC 
LIMIT 1
```

### Q1028 (challenging, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's HAVING COUNT(*)=(SELECT MAX(win_count)...) tie-preserving construct into ORDER BY COUNT(*) DESC LIMIT 1, losing ties; also season filtered as '2010' instead of '2009/2010'

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT t3.team_long_name 
FROM League AS t1 
INNER JOIN Match AS t2 ON t1.id = t2.league_id 
INNER JOIN Team AS t3 ON t2.away_team_api_id = t3.team_api_id 
WHERE t2.season = '2010' AND t1.name = 'Scotland Premier League' AND t2.away_team_goals > t2.home_team_goals 
GROUP BY t3.team_api_id 
ORDER BY COUNT(*) DESC 
LIMIT 1
```

### Q1029 (moderate, retrieval) -- **Other** (extra SELECT column)

**Outcome:** `wrong_answer` - **Reason:** adds an extra team_long_name column to the SELECT list that gold doesn't have -- join/order/limit otherwise match gold exactly

**Gold SQL:**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT t1.team_long_name, t2.buildup_play_speed 
FROM Team AS t1 
INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id 
ORDER BY t2.buildup_play_speed DESC 
LIMIT 4
```

### Q1031 (challenging, retrieval) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** wraps the per-row age expression in AVG(), collapsing gold's DISTINCT list of individual ages into a single averaged scalar; also drops the month/day exact-age CASE correction

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
SELECT AVG(strftime('%Y', CURRENT_TIMESTAMP) - strftime('%Y', T1.birthday)) 
FROM Player AS T1 
JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.sprint_speed >= 97 AND T2.date BETWEEN '2013-01-01' AND '2015-12-31'
```

### Q1032 (moderate, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's tie-preserving HAVING COUNT(m.id)=(SELECT MAX(match_count)...) into ORDER BY match_count DESC LIMIT 1, losing ties

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT t1.name, COUNT(t2.id) AS match_count 
FROM League AS t1 
INNER JOIN Match AS t2 ON t1.id = t2.league_id 
GROUP BY t1.name 
ORDER BY match_count DESC 
LIMIT 1
```

### Q1035 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** uses inclusive BETWEEN 50 AND 60 instead of gold's exclusive buildUpPlaySpeed > 50 AND < 60 -- verified 155 rows have the value exactly 50 or 60, which would be wrongly included; also drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT team_fifa_api_id FROM Team_Attributes WHERE buildup_play_speed BETWEEN 50 AND 60
```

### Q1037 (challenging, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** counts raw joined Player_Attributes rows via SUM(CASE...)/COUNT(t1.id) instead of gold's COUNT(DISTINCT...) -- a player with multiple attribute snapshots gets counted once per snapshot instead of once

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t2.preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(t1.id) 
FROM Player AS t1 
INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id 
WHERE STRFTIME('%Y', t1.birthday) BETWEEN '1987' AND '1992'
```

### Q1080 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** attacking_work_rate filtered as 'high' instead of gold's 'low'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT t1.id) 
FROM Player AS t1 
INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id 
WHERE t2.preferred_foot = 'left' AND t2.attacking_work_rate = 'high'
```

### Q1084 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** adds an extra, ungrounded attacking_work_rate='low' condition not present in gold; also drops DISTINCT (COUNT(t1.id) vs COUNT(DISTINCT player_name))

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(t1.id) 
FROM Player AS t1 
INNER JOIN Player_Attributes AS t2 
ON t1.player_api_id = t2.player_api_id 
WHERE STRFTIME('%Y', t1.birthday) < '1986' 
AND t2.attacking_work_rate = 'low' 
AND t2.defensive_work_rate = 'high'
```

### Q1088 (moderate, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** omits DISTINCT on player_name; verified empirically two different players share a name, so the un-deduplicated subquery approach returns 1109 rows vs gold's 1105 distinct names

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id IN (SELECT player_api_id FROM Player_Attributes WHERE volleys > 70 AND dribbling > 70)
```

### Q1091 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** adds an extra, wrongly-formatted season='2009' condition (verified: matches zero rows) not present in gold, which filters purely by SUBSTR(date,1,7)='2009-04'

**Gold SQL:**

```sql
SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND SUBSTR(t2."date", 1, 7) = '2009-04'
```

**Predicted SQL:**

```sql
SELECT COUNT(t2.id) 
FROM League AS t1 
INNER JOIN Match AS t2 
ON t1.id = t2.league_id 
WHERE t1.name = 'Belgium Jupiler League' 
AND t2.season = '2009' 
AND SUBSTR(t2.`date`, 6, 2) = '04'
```

### Q1092 (simple, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's tie-preserving HAVING COUNT=(SELECT MAX(match_count)...) into ORDER BY COUNT(t2.id) DESC LIMIT 1, losing ties

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT t1.name 
FROM League AS t1 
INNER JOIN Match AS t2 
ON t1.id = t2.league_id 
WHERE t2.season = '2008/2009' 
GROUP BY t1.name 
ORDER BY COUNT(t2.id) DESC 
LIMIT 1
```

### Q1094 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's two CTEs (each selecting the most recent overall_rating via ORDER BY date DESC LIMIT 1); instead cross-joins every historical Player_Attributes row for both players with no date-based selection

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT ((t1.overall_rating - t2.overall_rating) * 100.0 / t2.overall_rating) AS percentage_increase 
FROM Player_Attributes AS t1 
INNER JOIN Player AS t3 ON t1.player_api_id = t3.player_api_id 
INNER JOIN Player_Attributes AS t2 
INNER JOIN Player AS t4 ON t2.player_api_id = t4.player_api_id 
WHERE t3.player_name = 'Ariel Borysiuk' AND t4.player_name = 'Paulin Puel'
```

### Q1102 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares date to a bare 'YYYY-MM-DD' literal instead of gold's SUBSTR(date,1,10) truncation; verified Player_Attributes.date carries a ' 00:00:00' time suffix, so the exact-equality filter matches zero rows

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT t1.player_name 
FROM Player AS t1 
INNER JOIN Player_Attributes AS t2 
ON t1.player_api_id = t2.player_api_id 
WHERE t2.overall_rating = 77 AND t2.date = '2016-06-23' 
ORDER BY t1.birthday ASC 
LIMIT 1
```

### Q1103 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares date to a bare 'YYYY-MM-DD' literal instead of gold's SUBSTR(date,1,10) truncation; verified this matches zero rows given the stored datetime suffix

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Aaron Mooy' AND t2.date = '2016-02-04'
```

### Q1107 (moderate, retrieval) -- **Other** (missing ORDER BY tie-breaker)

**Outcome:** `wrong_answer` - **Reason:** drops gold's secondary ORDER BY date ASC tie-breaker after crossing DESC; verified empirically the top crossing value is tied, giving a different date (2013-03-28 vs gold's 2013-02-15) without it

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT t2.date FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC LIMIT 1
```

### Q1113 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters team_short_name='Hannover 96' instead of team_long_name -- verified team_short_name is actually 'HAN', so this matches zero rows

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT t2.defence_aggression_class FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_short_name = 'Hannover 96' AND SUBSTR(t2.`date`, 1, 10) = '2015-09-10'
```

### Q1114 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** BETWEEN compares the full datetime string directly against date-only bounds instead of gold's SUBSTR(date,1,10) truncation -- verified this excludes the player's most recent record (exactly on the upper-bound date), giving 32 rows/75.28 avg instead of gold's 33 rows/75.39

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(t2.overall_rating) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Marko Arnautovic' AND t2.date BETWEEN '2007-02-22' AND '2016-04-21'
```

### Q1115 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** both derived-table subqueries filter date='2013-07-12' by exact equality instead of gold's SUBSTR(date,1,10) truncation -- verified this matches zero rows given the stored datetime suffix

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT ((t2_overall_rating - t1_overall_rating) * 100.0 / t1_overall_rating) AS percentage_difference
FROM (
    SELECT t2.overall_rating AS t1_overall_rating
    FROM Player AS t1
    INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
    WHERE t1.player_name = 'Landon Donovan' AND t2.date = '2013-07-12'
) AS subquery1,
(
    SELECT t2.overall_rating AS t2_overall_rating
    FROM Player AS t1
    INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
    WHERE t1.player_name = 'Jordan Bowery' AND t2.date = '2013-07-12'
) AS subquery2
```

### Q1122 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** orders by strength instead of overall_rating -- a completely different real column; also loses gold's tie-preserving MAX-equality subquery for a plain ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id ORDER BY t2.strength DESC LIMIT 1
```

### Q1136 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters potential=MAX(potential) instead of crossing=MAX(crossing) -- a different real column entirely

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) 
FROM Player_Attributes 
WHERE potential = (SELECT MAX(potential) FROM Player_Attributes) 
AND preferred_foot = 'left'
```

### Q1139 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares date to a bare 'YYYY-MM-DD' literal instead of gold's LIKE '...%' prefix match -- verified Match.date carries a time suffix, so the exact-equality filter matches zero rows

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT t2.home_team_goals, t2.away_team_goals 
FROM League AS t1 
INNER JOIN Match AS t2 ON t1.id = t2.league_id 
WHERE t1.name = 'Belgium Jupiler League' 
AND t2.date = '2008-09-24'
```

### Q1141 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters team_short_name='KSV Cercle Brugge' instead of team_long_name -- verified team_short_name is actually 'CEB'; the added buildup_play_speed_class IN (...) condition lists all three possible enum values so it doesn't actually restrict anything

**Gold SQL:**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL:**

```sql
SELECT DISTINCT t2.buildup_play_speed_class 
FROM Team AS t1 
INNER JOIN Team_Attributes AS t2 
ON t1.team_api_id = t2.team_api_id 
WHERE t1.team_short_name = 'KSV Cercle Brugge' 
AND t2.buildup_play_speed_class IN ('Slow', 'Balanced', 'Fast')
```

### Q1144 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's tie-preserving weight=MAX(weight) subquery into ORDER BY weight DESC LIMIT 1 -- verified two players tie for max weight, so gold returns 2 rows and predicted only 1

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT t2.finishing, t2.curve FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id ORDER BY t1.weight DESC LIMIT 1
```

### Q1145 (simple, aggregate) -- **Other** (extra SELECT column)

**Outcome:** `wrong_answer` - **Reason:** adds an extra COUNT(t2.id) column to the SELECT list that gold doesn't have

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT t1.name, COUNT(t2.id) AS game_count 
FROM League AS t1 
INNER JOIN Match AS t2 ON t1.id = t2.league_id 
WHERE t2.season = '2015/2016' 
GROUP BY t1.name 
ORDER BY game_count DESC 
LIMIT 4
```

### Q1146 (moderate, retrieval) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** introduces a GROUP BY team_api_id/SUM(away_team_goals) aggregation gold doesn't have -- gold wants the away team of the single match with the highest away_team_goal value, not the team with the highest goal total across all matches

**Gold SQL:**

```sql
SELECT t2.team_long_name FROM Match AS t1 INNER JOIN Team AS t2 ON t1.away_team_api_id = t2.team_api_id ORDER BY t1.away_team_goal DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT t1.team_long_name 
FROM Team AS t1 
INNER JOIN Match AS t2 
ON t1.team_api_id = t2.away_team_api_id 
GROUP BY t1.team_api_id 
ORDER BY SUM(t2.away_team_goals) DESC 
LIMIT 1
```

### Q1147 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** orders by strength instead of overall_rating -- a completely different real column; also loses gold's tie-preserving MAX-equality subquery for ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id ORDER BY t2.strength DESC LIMIT 1
```

### Q1148 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** substitutes strength for overall_rating in the CASE condition; also drops the base WHERE height<180 filter that scopes gold's denominator population, and drops DISTINCT

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN t1.height < 180 AND t2.strength > 70 THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(t1.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

---

## financial (20 failures)

### Q89 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** 'after transaction' is an invented English translation; the real stored value is 'POPLATEK PO OBRATU'

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.account_id) 
FROM account AS T1 
INNER JOIN district AS T2 ON T1.district_id = T2.district_id 
WHERE T1.statement_frequency = 'after transaction' AND T2.region = 'east Bohemia'
```

### Q93 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** 'North Bohemia' (capital N) case-mismatches the real stored value 'north Bohemia' -- verified: matches zero rows under case-sensitive comparison

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.client_id) 
FROM client AS T1 
INNER JOIN district AS T2 ON T1.district_id = T2.district_id 
WHERE T1.gender = 'M' AND T2.region = 'North Bohemia' AND T2.average_salary > 8000
```

### Q94 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** district linked via client.district_id (through disp/client) instead of directly via account.district_id -- an extra, wrong join path; also drops gold's two subqueries (the earliest-born-female client lookup, and the district-wide MAX(A11)-MIN(A11) global spread), instead computing MAX/MIN(average_salary) as a bare aggregate over the filtered join, collapsing all rows into one arbitrary result

**Gold SQL:**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.account_id, MAX(T2.average_salary) - MIN(T2.average_salary) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.client_id = T3.client_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC LIMIT 1
```

### Q95 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** district linked via client.district_id instead of via account.district_id -- the account table needed for the correct district linkage is never joined; also sorts birth_date ASC instead of gold's DESC (reversed direction), picking the oldest client instead of the youngest

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT T2.account_id FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN district AS T3 ON T1.district_id = T3.district_id ORDER BY T1.birth_date ASC, T3.average_salary DESC LIMIT 1
```

### Q115 (challenging, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** drops gold's GROUP BY T2.A4 (number_inhabitants) entirely -- the percentage aggregate collapses ALL south Bohemia clients into one result instead of being scoped, via GROUP BY, to clients in the single highest-population district; ORDER BY/LIMIT after an ungrouped aggregate is a no-op

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(T2.gender = 'M') AS REAL) * 100 / COUNT(T2.client_id) 
FROM district AS T1 
INNER JOIN client AS T2 ON T1.district_id = T2.district_id 
WHERE T1.region = 'south Bohemia' 
ORDER BY T1.number_inhabitants DESC 
LIMIT 1
```

### Q116 (challenging, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** computes the same balance-difference ratio as gold but omits the *100 scaling factor -- verified numerically: predicted's value (4.3045...) is exactly gold's value (430.45...) divided by 100

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT (T3.balance_after_transaction - T4.balance_after_transaction) / T4.balance_after_transaction AS increase_rate
FROM loan AS T1
INNER JOIN account AS T2 ON T1.account_id = T2.account_id
INNER JOIN trans AS T3 ON T2.account_id = T3.account_id
INNER JOIN trans AS T4 ON T2.account_id = T4.account_id
WHERE T1.date = '1993-07-05'
AND T3.date = '1998-12-27'
AND T4.date = '1993-03-22'
```

### Q118 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** status='A' (contract finished, no problems) instead of gold's status='C' (running contract, OK) -- a different, wrong loan-status code

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT (COUNT(CASE WHEN T3.status = 'A' THEN 1 END) * 100.0 / COUNT(*)) AS percentage 
FROM account AS T1 
INNER JOIN loan AS T3 ON T1.account_id = T3.account_id 
WHERE T3.amount < 100000
```

### Q125 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** district linked via disp/client.district_id instead of directly via account.district_id -- two extra tables inserted into the join chain; also computes a raw unemployment-rate difference instead of gold's %-change form (A13-A12)/A12*100, and filters status='A' instead of 'D' with an unrelated amount>0 condition replacing the A12/A13 not-null checks

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT T2.unemployment_rate_1996 - T2.unemployment_rate_1995 AS unemployment_rate_increment
FROM loan AS T1
INNER JOIN account AS T3 ON T1.account_id = T3.account_id
INNER JOIN disp AS T4 ON T3.account_id = T4.account_id
INNER JOIN client AS T5 ON T4.client_id = T5.client_id
INNER JOIN district AS T2 ON T5.district_id = T2.district_id
WHERE T1.status = 'A' AND T1.amount > 0
```

### Q129 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters transaction_operation='VYBER' instead of type='VYDAJ' -- verified these are two different real columns (VYBER is a specific operation, a subset of VYDAJ-type transactions); also adds a DISTINCT not in gold that could collapse genuinely-duplicate top-10 district names

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.district_name 
FROM district AS T1 
INNER JOIN account AS T2 ON T1.district_id = T2.district_id 
INNER JOIN trans AS T3 ON T2.account_id = T3.account_id 
WHERE T3.transaction_operation = 'VYBER' 
AND T3.date BETWEEN '1996-01-01' AND '1996-01-31' 
ORDER BY T3.amount DESC 
LIMIT 10
```

### Q137 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters region=1 instead of district_id=1 -- verified region (a text column of city/region names) never equals the integer 1, matching zero rows; also loosens status='C' OR 'D' to status!='A', which additionally admits status='B'

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(T2.account_id) 
FROM district AS T1 
INNER JOIN account AS T2 ON T1.district_id = T2.district_id 
INNER JOIN loan AS T3 ON T2.account_id = T3.account_id 
WHERE T1.region = 1 AND T3.status != 'A'
```

### Q138 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's subquery finding the district with the 2nd-highest A15 (number_crimes_1995) value; instead applies ORDER BY .../LIMIT 1 OFFSET 1 directly on the outer COUNT() aggregate query -- verified this returns zero rows entirely, since a GROUP BY-less aggregate collapses to one row that OFFSET 1 then skips

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A15 = (SELECT T3.A15 FROM district AS T3 ORDER BY T3.A15 DESC LIMIT 1, 1)
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.client_id) 
FROM client AS T1 
INNER JOIN district AS T2 ON T1.district_id = T2.district_id 
WHERE T1.gender = 'M' 
ORDER BY T2.number_crimes_1995 DESC 
LIMIT 1 OFFSET 1
```

### Q145 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects client_id instead of gold's account_id -- a different entity/granularity entirely (a client can have multiple accounts via disp); also drops the operation='VYBER KARTOU' filter entirely

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.client_id 
FROM client AS T1 
INNER JOIN disp AS T2 ON T1.client_id = T2.client_id 
INNER JOIN account AS T3 ON T2.account_id = T3.account_id 
INNER JOIN trans AS T4 ON T3.account_id = T4.account_id 
WHERE STRFTIME('%Y', T4.date) = '1998' 
AND T4.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

### Q149 (challenging, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** replaces gold's simple type<>'OWNER' condition with an unrelated NOT IN (SELECT type FROM disp/account/loan) subquery gold doesn't have; also uses an inclusive BETWEEN 8000-9000 range instead of gold's exclusive lower bound (>8000)

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
FROM disp AS T1 
INNER JOIN account AS T2 ON T1.account_id = T2.account_id 
INNER JOIN district AS T3 ON T2.district_id = T3.district_id 
WHERE T3.average_salary BETWEEN 8000 AND 9000 
AND T1.type NOT IN (SELECT T1.type FROM disp AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN loan AS T3 ON T2.account_id = T3.account_id)
```

### Q152 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters number_inhabitants>4000 instead of gold's number_crimes_1995>4000 -- a different real column entirely (though the AVG() itself correctly targets number_crimes_1995); also converts gold's DISTINCT-district IN-subquery into a JOIN which could duplicate districts with multiple qualifying accounts

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

### Q159 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters type='VYBER' and transaction_operation='PRIJEM' -- these values are swapped relative to the real domains (VYBER is an operation value, PRIJEM is a type value; verified type='VYBER' matches zero rows), neither matching gold's operation='VYBER'; additionally selects only transaction_id instead of gold's full T4.* row

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT T3.transaction_id FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T1.client_id = 3356 AND T3.type = 'VYBER' AND T3.transaction_operation = 'PRIJEM'
```

### Q169 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops the disp.type='OWNER' filter entirely, including male DISPONENTs' loans too; also reverses the subtraction order (1996-1997 instead of gold's 1997-1996), flipping the sign, and omits the *100 scaling factor

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T1.year = 1996 THEN T1.amount ELSE 0 END) - SUM(CASE WHEN T1.year = 1997 THEN T1.amount ELSE 0 END)) / 
    SUM(CASE WHEN T1.year = 1996 THEN T1.amount ELSE 0 END) AS growth_rate
FROM 
    (SELECT 
        strftime('%Y', T4.date) AS year, 
        T4.amount 
     FROM 
        client AS T1 
     INNER JOIN 
        disp AS T2 ON T1.client_id = T2.client_id 
     INNER JOIN 
        account AS T3 ON T2.account_id = T3.account_id 
     INNER JOIN 
        loan AS T4 ON T3.account_id = T4.account_id 
     WHERE 
        T1.gender = 'M') AS T1
```

### Q173 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes the trans table (with an invented/nonexistent operation value 'DEBIT') for gold's "order" table with its account_id/k_symbol/SUM(amount) grouped subquery -- entirely different real-world concept (standing orders vs realized transactions); also computes a DEBIT count instead of retrieving k_symbol for the matching total_amount

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT T1.statement_frequency, SUM(CASE WHEN T3.amount = 3539 THEN 1 ELSE 0 END) AS debit_count FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T1.account_id = T3.account_id WHERE T1.account_id = 3 AND T3.transaction_operation = 'DEBIT'
```

### Q189 (moderate, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` - **Reason:** references T2.account (T2=account table, no such column -- only account_id exists there); the model almost certainly truncated 'account_id' to 'account' rather than genuinely intending trans.account (an unrelated recipient-account-number column on a table never referenced anywhere else in the query)

**Gold SQL:**

```sql
SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id  WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.account FROM client AS T1 INNER JOIN disp AS T3 ON T1.client_id = T3.client_id INNER JOIN account AS T2 ON T3.account_id = T2.account_id INNER JOIN district AS T4 ON T1.district_id = T4.district_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T4.average_salary ASC LIMIT 1
```

### Q192 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** status='A' instead of gold's status IN ('C','D'); also frequency='POPLATEK MESICNE' (monthly issuance) instead of gold's 'POPLATEK PO OBRATU' -- two different, wrong domain values

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(T3.amount) 
FROM account AS T1 
INNER JOIN loan AS T3 ON T1.account_id = T3.account_id 
WHERE T3.status = 'A' AND T1.statement_frequency = 'POPLATEK MESICNE'
```

### Q194 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** card type filtered as 'high_level' instead of the real stored value 'gold' -- verified: matches zero rows; also adds an unwanted month/day birthday correction to the age computation that gold's simpler year-difference doesn't include

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT T2.client_id, strftime('%Y', 'now') - strftime('%Y', T2.birth_date) - (strftime('%m-%d', 'now') < strftime('%m-%d', T2.birth_date)) AS age 
FROM disp AS T1 
INNER JOIN client AS T2 ON T1.client_id = T2.client_id 
INNER JOIN card AS T3 ON T1.disposition_id = T3.disposition_id 
WHERE T3.type = 'high_level' AND T1.type = 'OWNER'
```

---

## formula_1 (36 failures)

### Q846 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops gold's ORDER BY q1 DESC LIMIT 5 (top-5 qualifying times) entirely, replacing it with an unrelated WHERE position>10 filter -- a different question altogether

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT T2.driver_ref_name FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id = 20 AND T1.position > 10
```

### Q857 (simple, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified 9 races were held at this circuit (Abu Dhabi GP across different years) -- without DISTINCT the same lat/lng is returned 9 times instead of gold's single deduplicated row

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.latitude, T1.longitude FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuit_id = T1.circuit_id WHERE T2.name = 'Abu Dhabi Grand Prix'
```

### Q861 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects qualifying.number (T1) instead of gold's drivers.number (T2) -- both tables have a column literally named 'number' but they hold different values (verified empirically: results differ, {3,5} vs {3,1}); the added DISTINCT is harmless

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driver_id = T1.driver_id WHERE T1.race_id = 903 AND T1.qualifying_3_time LIKE '1:54%'
```

### Q866 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares time to an exact '0:01:27' (wrong format: H:MM:SS) via '=' instead of gold's LIKE '1:27%' prefix match against the real 'M:SS.mmm' format -- verified matches zero rows; also drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT T2.first_name, T2.last_name, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driver_id = T1.driver_id WHERE T1.race_id = 161 AND T1.time = '0:01:27'
```

### Q868 (simple, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified 19 races were held at this circuit (Malaysian GP across different years) -- without DISTINCT the same lat/lng is returned 19 times instead of gold's single deduplicated row

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.latitude, T1.longitude FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuit_id = T1.circuit_id WHERE T2.name = 'Malaysian Grand Prix'
```

### Q869 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes constructorStandings (cumulative championship standings) for gold's constructorResults (race-specific points) -- a different real table/concept

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.url 
FROM constructors AS T1 
INNER JOIN constructorStandings AS T2 ON T1.constructor_id = T2.constructor_id 
WHERE T2.race_id = 9 
ORDER BY T2.points DESC 
LIMIT 1
```

### Q877 (moderate, retrieval) -- **Other** (extra SELECT column)

**Outcome:** `wrong_answer` - **Reason:** adds an extra date_of_birth column to the SELECT list that gold doesn't have; filter/join/order/limit otherwise match gold exactly

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.first_name, T2.last_name, T2.date_of_birth 
FROM results AS T1 
INNER JOIN drivers AS T2 ON T2.driver_id = T1.driver_id 
WHERE T1.race_id = 872 AND T1.time IS NOT NULL 
ORDER BY T2.date_of_birth DESC 
LIMIT 1
```

### Q879 (moderate, retrieval) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** sorts by fastestLapSpeed directly (stored as TEXT) instead of gold's CAST(...AS REAL) -- lexicographic instead of numeric sort, verified to flip the top result (Italian vs gold's Brazilian); also adds a redundant IS NOT NULL filter not in gold

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driver_id = T1.driver_id WHERE T2.fastest_lap_speed IS NOT NULL ORDER BY T2.fastest_lap_speed DESC LIMIT 1
```

### Q880 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** confuses driver car number with raceId -- filters T2.number=853 and derives T3.race_id via a nonsensical subquery based on results.number=853, rather than gold's direct literal raceId values 853/854; entirely misidentifies which columns correspond to the specific races being compared

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
    (T2.fastest_lap_speed - T3.fastest_lap_speed) / T3.fastest_lap_speed * 100 AS percentage_faster
FROM 
    drivers AS T1
INNER JOIN 
    results AS T2 ON T1.driver_id = T2.driver_id
INNER JOIN 
    results AS T3 ON T1.driver_id = T3.driver_id
WHERE 
    T1.first_name = 'Paul' 
    AND T1.last_name = 'di Resta' 
    AND T2.number = 853 
    AND T3.race_id = (SELECT MIN(race_id) FROM results WHERE race_id > (SELECT race_id FROM results WHERE number = 853))
```

### Q884 (moderate, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's year+month subquery matching (which returns all races in the same year AND month as the earliest race -- verified 3 races: British GP, Monaco GP, Indianapolis 500) into an exact date=MIN(date) equality, which only returns the single earliest-dated race

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT name FROM races WHERE date = (SELECT MIN(date) FROM races)
```

### Q894 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects/orders by lapTimes.time (TEXT) instead of gold's milliseconds (numeric) -- verified this returns a completely different top result (a 10+ minute outlier lap due to lexicographic string sort) instead of gold's genuine fastest lap

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.time, T2.first_name, T2.last_name, T3.name 
FROM lapTimes AS T1 
INNER JOIN drivers AS T2 ON T2.driver_id = T1.driver_id 
INNER JOIN races AS T3 ON T3.race_id = T1.race_id 
ORDER BY T1.time ASC 
LIMIT 1
```

### Q895 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** joins lapTimes only on driver_id, omitting race_id -- averages over ALL of Hamilton's career lap times instead of scoping to the 2009 Malaysian Grand Prix; also manually re-derives the time from the formatted time string instead of using the milliseconds column directly

**Gold SQL:**

```sql
SELECT AVG(T2.milliseconds) FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.year = 2009 AND T1.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT AVG(CAST(SUBSTR(T3.time, 1, INSTR(T3.time, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(T3.time, INSTR(T3.time, ':') + 1) AS REAL)) FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id INNER JOIN lapTimes AS T3 ON T3.driver_id = T1.driver_id INNER JOIN races AS T4 ON T4.race_id = T2.race_id WHERE T1.first_name = 'Lewis' AND T1.last_name = 'Hamilton' AND T4.name = 'Malaysian Grand Prix' AND T4.year = 2009
```

### Q896 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** computes % of races where round=1 (season-opening races) instead of gold's % where driverStandings.position<>1 (non-race-wins by standings position) -- substitutes races.round and the results table for driverStandings.position entirely, a completely different real column/table and concept

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.round = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM drivers AS T1 
INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id 
INNER JOIN races AS T3 ON T2.race_id = T3.race_id 
WHERE T1.first_name = 'Lewis' AND T1.last_name = 'Hamilton' AND T3.year >= 2010
```

### Q898 (simple, retrieval) -- **Other** (dropped SELECT computation)

**Outcome:** `wrong_answer` - **Reason:** drops the STRFTIME year-difference age calculation entirely, selecting raw date_of_birth instead of the computed age; WHERE/ORDER BY/LIMIT otherwise match gold

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name, date_of_birth FROM drivers WHERE nationality = 'Japanese' ORDER BY date_of_birth DESC LIMIT 1
```

### Q902 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes the results table (grid_position, starting grid position) for gold's driverStandings table (championship standings position) -- different real-world concepts entirely

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

### Q904 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes results.fastestLapTime (a per-race summary stat, and a TEXT time string) for gold's lapTimes.milliseconds (the raw per-lap numeric timing data) -- a different real table/column/granularity

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.name, T2.year 
FROM results AS T1 
INNER JOIN races AS T2 ON T1.race_id = T2.race_id 
INNER JOIN drivers AS T3 ON T1.driver_id = T3.driver_id 
WHERE T3.first_name = 'Michael' AND T3.last_name = 'Schumacher' 
ORDER BY T1.fastest_lap_time ASC 
LIMIT 1
```

### Q915 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** joins drivers to circuits via a fabricated/nonexistent driver_id=circuit_id relationship (no real FK connects these tables) instead of gold's simple single-table query on drivers; consequently selects circuits.country instead of drivers.nationality

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.country FROM drivers AS T1 INNER JOIN circuits AS T2 ON T1.driver_id = T2.circuit_id ORDER BY T1.date_of_birth ASC LIMIT 1
```

### Q930 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** orders by position (race finishing position) instead of filtering on rank=0 (a specific classification/rank sentinel value) -- different real columns with different meanings; also collapses gold's IN-subquery (which could match multiple races) into a single ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT T1.name 
FROM races AS T1 
INNER JOIN results AS T2 ON T2.race_id = T1.race_id 
INNER JOIN drivers AS T3 ON T3.driver_id = T2.driver_id 
WHERE T3.first_name = 'Lewis' AND T3.last_name = 'Hamilton' 
ORDER BY T2.position ASC 
LIMIT 1
```

### Q937 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** race name garbled to 'AustChineseralian Grand Prix' -- verified: matches zero rows

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT T2.time 
FROM races AS T1 
INNER JOIN results AS T2 ON T2.race_id = T1.race_id 
WHERE T1.name = 'AustChineseralian Grand Prix' AND T1.year = 2008 AND T2.position = 2
```

### Q944 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's CTE chain (identifying the specific champion via positionOrder=1 and the last-place driver via MAX(positionOrder)) in favor of a flat MAX/MIN(milliseconds) aggregate -- verified numerically to give a different result (1.179 vs gold's 1.165), since MIN/MAX doesn't reliably correspond to the position-order-specific rows; also filters position IS NOT NULL instead of gold's time IS NOT NULL

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT 
    ((MAX(T2.milliseconds) - MIN(T2.milliseconds)) * 100.0 / MIN(T2.milliseconds)) AS percentage_faster
FROM 
    races AS T1
INNER JOIN 
    results AS T2 ON T1.race_id = T2.race_id
WHERE 
    T1.name = 'Australian Grand Prix' 
    AND T1.year = 1988
    AND T2.position IS NOT NULL;
```

### Q950 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes constructorResults for gold's constructorStandings -- a different real table/concept

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT T2.name FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructor_id = T1.constructor_id WHERE T1.race_id = 291 AND T1.points = 0
```

### Q951 (simple, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** uses COUNT(*) instead of gold's COUNT(DISTINCT constructorId) within the per-group HAVING structure -- verified this changes the per-group value from gold's 1 to predicted's 2, even though the query structure otherwise matches

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM constructors AS T1 INNER JOIN constructorResults AS T2 ON T1.constructor_id = T2.constructor_id WHERE T1.nationality = 'Japanese' AND T2.points = 0 GROUP BY T1.constructor_id HAVING COUNT(T2.race_id) = 2
```

### Q954 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** swaps which condition is the WHERE-scoping filter and which is the CASE-measured condition relative to gold -- computes % of all 2007-2009 classified drivers who are Japanese instead of gold's % of Japanese drivers' 2007-2009 entries that were classified (time IS NOT NULL)

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.nationality = 'Japanese' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM results AS T1 
INNER JOIN races AS T2 ON T1.race_id = T2.race_id 
INNER JOIN drivers AS T3 ON T1.driver_id = T3.driver_id 
WHERE T2.year BETWEEN 2007 AND 2009 AND T1.time IS NOT NULL
```

### Q955 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` - **Reason:** substitutes driverStandings for gold's results -- driverStandings doesn't have a milliseconds column at all (that lives on results), causing the 'no such column' error; driverStandings.position (cumulative standings) is also a different concept from results.position (race finish position)

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT T2.year, AVG(T2.milliseconds) / 1000 AS avg_time_seconds 
FROM driverStandings AS T1 
INNER JOIN races AS T2 ON T1.race_id = T2.race_id 
WHERE T1.position = 1 AND T2.year < 1975 
GROUP BY T2.year
```

### Q962 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares laps=50 (exact equality) instead of gold's laps>50; also drops DISTINCT entirely in both numerator and denominator, so drivers with multiple qualifying race entries get counted multiple times

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(IIF(T3.date_of_birth < '1985-01-01' AND T2.laps = 50, 1, 0)) AS REAL) * 100 / COUNT(T2.driver_id) 
FROM races AS T1 
INNER JOIN results AS T2 ON T2.race_id = T1.race_id 
INNER JOIN drivers AS T3 ON T3.driver_id = T2.driver_id 
WHERE T1.year BETWEEN 2000 AND 2005
```

### Q963 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares the raw lap-time TEXT string lexicographically to '02:00.00' instead of gold's manually-parsed numeric seconds < 120 -- verified this drops from gold's 9 matching drivers to 0, since single-digit-minute lap strings like '1:44.225' compare as lexicographically larger than '02:00.00'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T2.driver_id) 
FROM lapTimes AS T1 
INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.nationality = 'French' AND T1.time < '02:00.00'
```

### Q967 (simple, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's derived-table subquery (which first selects the 3 youngest drivers by JULIANDAY(dob) DESC, then counts how many are Dutch) -- instead filters WHERE nationality first (as 'Netherlandic', an invented value; verified even corrected to 'Dutch' the COUNT(*) aggregate without GROUP BY collapses to a global total of 17, ignoring ORDER BY/LIMIT entirely, vs gold's 1)

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM drivers WHERE nationality = 'Netherlandic' ORDER BY date_of_birth DESC LIMIT 3
```

### Q972 (moderate, retrieval) -- **Other** (unwarranted ORDER BY/LIMIT)

**Outcome:** `wrong_answer` - **Reason:** adds an unwarranted ORDER BY fastest_lap_time ASC LIMIT 1 that narrows gold's full DISTINCT list (verified 4 qualifying driver/code pairs) down to a single row; WHERE conditions and columns otherwise correctly match gold

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT T1.driver_id, T1.driver_code 
FROM drivers AS T1 
INNER JOIN results AS T2 ON T2.driver_id = T1.driver_id 
WHERE strftime('%Y', T1.date_of_birth) = '1971' AND T2.fastest_lap_time IS NOT NULL 
ORDER BY T2.fastest_lap_time ASC 
LIMIT 1
```

### Q977 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** filters status_id IN (3..100) instead of gold's status_id=2 -- a completely different filtering criterion; also uses an inclusive race_id BETWEEN 50-100 instead of gold's exclusive >50 AND <100, and drops the time IS NOT NULL conditional count (uses plain COUNT(*) instead of SUM(IIF(time IS NOT NULL,1,0)))

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
WHERE race_id BETWEEN 50 AND 100 AND status_id IN (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100)
```

### Q978 (simple, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified circuits in Austria include an exact duplicate row (Spielburg appears twice) -- without DISTINCT this duplicate is returned instead of gold's deduplicated set

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE country = 'Austria'
```

### Q981 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` - **Reason:** references T3.name (T3=drivers, which has no 'name' column) instead of T1.name (T1=races, already joined) -- an alias mix-up on an already-joined table, causing the error; also mixes an aggregate MIN(year) with non-aggregate columns without GROUP BY

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(T1.year), T3.name, T3.date, T3.time 
FROM races AS T1 
INNER JOIN qualifying AS T2 ON T1.race_id = T2.race_id 
INNER JOIN drivers AS T3 ON T2.driver_id = T3.driver_id 
WHERE T3.date_of_birth = (SELECT MAX(date_of_birth) FROM drivers)
```

### Q988 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects driver_id and an extra avg_duration column instead of gold's forename, surname -- a different column choice entirely for the requested driver identification; GROUP BY grain (driver_id vs forename/surname) is otherwise equivalent since both uniquely identify the driver

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT T2.driver_id, AVG(T1.duration) AS avg_duration 
FROM pitStops AS T1 
INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id 
WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.date_of_birth) BETWEEN '1980' AND '1985' 
GROUP BY T2.driver_id 
ORDER BY avg_duration ASC 
LIMIT 3
```

### Q994 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes constructorStandings (cumulative championship standings) for gold's constructorResults (race-specific points) -- a different real table/concept; also selects raw T2.points instead of wrapping in SUM(), an ungrouped column reference alongside the GROUP BY

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.points, T1.name, T1.nationality 
FROM constructors AS T1 
INNER JOIN constructorStandings AS T2 ON T2.constructor_id = T1.constructor_id 
INNER JOIN races AS T3 ON T3.race_id = T2.race_id 
WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 
GROUP BY T1.constructor_id 
ORDER BY SUM(T2.points) DESC 
LIMIT 1
```

### Q1001 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** adds an ungrounded races.round=3 condition not present in gold -- verified the actual round for the 2008 Singapore GP is 15, so this filters out all rows entirely, returning empty instead of gold's Felipe Massa; also substitutes qualifying.position=1 for gold's manually-parsed-q3-time ORDER BY ASC LIMIT 1

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.first_name, T3.last_name 
FROM races AS T1 
INNER JOIN qualifying AS T2 ON T1.race_id = T2.race_id 
INNER JOIN drivers AS T3 ON T3.driver_id = T2.driver_id 
WHERE T1.circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Marina Bay Street Circuit') 
AND T1.year = 2008 
AND T1.round = 3 
AND T2.position = 1
```

### Q1002 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` - **Reason:** references T2.first_name/last_name/nationality (T2=results, no such columns) instead of T3.first_name/last_name/nationality (T3=drivers, already joined) -- an alias mix-up on an already-joined table, causing the error; also substitutes results for driverStandings as the third joined table

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, T3.name FROM drivers AS T1 INNER JOIN driverStandings AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T2.raceId = T3.raceId ORDER BY JULIANDAY(T1.dob) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.first_name, T2.last_name, T2.nationality, T1.name 
FROM races AS T1 
INNER JOIN results AS T2 ON T1.race_id = T2.race_id 
INNER JOIN drivers AS T3 ON T2.driver_id = T3.driver_id 
ORDER BY T3.date_of_birth DESC 
LIMIT 1
```

### Q1011 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** uses MIN(time) (TEXT lap-time string) instead of gold's MIN(milliseconds) (numeric) inside the per-driver derived table -- verified this returns a completely different set of 'fastest' drivers due to lexicographic vs numeric sort corruption

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name 
FROM drivers AS T1 
INNER JOIN (
    SELECT driver_id, MIN(time) AS min_time 
    FROM lapTimes 
    GROUP BY driver_id
) AS T2 
ON T1.driver_id = T2.driver_id 
ORDER BY T2.min_time 
LIMIT 20
```

---

## student_club (19 failures)

### Q1322 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's outer COUNT(*) FROM (subquery) wrapper -- verified this returns one row per qualifying event (23,25,30,27) instead of gold's single count (4) of how many events qualify

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

### Q1323 (moderate, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** groups by event_name instead of gold's event_id -- verified two DIFFERENT 'Football game' events (14 and 12 attendees each, neither >20 individually) get merged under the shared name and their counts summed to 26>20, spuriously including 'Football game' in the result that gold correctly excludes

**Gold SQL:**

```sql
SELECT DISTINCT E.`event_name`
FROM `Event` AS E
JOIN `Attendance` AS A ON E.`event_id` = A.`link_to_event`
WHERE E.`type` <> 'Fundraiser'
GROUP BY E.`event_id`
HAVING COUNT(*) > 20;
```

**Predicted SQL:**

```sql
SELECT T1.event_name 
FROM event AS T1 
INNER JOIN attendance AS T2 ON T1.event_id = T2.event_id 
WHERE T1.type != 'Fundraiser' 
GROUP BY T1.event_name 
HAVING COUNT(T2.member_id) > 20
```

### Q1338 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters on expense_date='2019-10-08' instead of gold's event_date LIKE '2019-10-08%' -- the EVENT's date and its associated EXPENSE's date are different real columns/values entirely

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT T3.is_approved 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.event_id 
INNER JOIN expense AS T3 ON T2.budget_id = T3.budget_id 
WHERE T1.event_name = 'October Meeting' AND T3.expense_date = '2019-10-08'
```

### Q1339 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** adds a fabricated year=2023 constraint not in gold (via strftime('%Y-%m',...) IN ('2023-09','2023-10')) -- verified all data is from 2019, so this matches zero rows; gold's SUBSTR(date,6,2) IN ('09','10') correctly ignores year entirely

**Gold SQL:**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL:**

```sql
SELECT AVG(T3.cost) 
FROM member AS T1 
INNER JOIN expense AS T3 ON T1.member_id = T3.member_id 
WHERE T1.first_name = 'Elijah' AND T1.last_name = 'Allen' 
AND strftime('%Y-%m', T3.expense_date) IN ('2023-09', '2023-10')
```

### Q1344 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes the event table for gold's income table -- both happen to have 'notes'/date columns, but they're different real-world entities (fundraising income record vs a club event); also type='fundraising' (lowercase) likely wouldn't match the real value's case

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE event_date = '2019-09-14' AND type = 'fundraising'
```

### Q1350 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects event.status via an unnecessarily-added event join instead of gold's budget.event_status -- two different columns on different tables; also splits the single literal 'Post Cards, Posters' (one string with an embedded comma) into two separate IN() values

**Gold SQL:**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT T1.status 
FROM event AS T1 
JOIN budget AS T2 ON T1.event_id = T2.event_id 
JOIN expense AS T3 ON T2.budget_id = T3.budget_id 
WHERE T3.expense_description IN ('Post Cards', 'Posters') 
AND T3.expense_date = '2019-08-20'
```

### Q1351 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` - **Reason:** references T2.major_name where T2=member (no such column) instead of T1.major_name where T1=major (already joined) -- an alias mix-up on an already-joined table, causing the error

**Gold SQL:**

```sql
SELECT T2.major_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.first_name = 'Brent' AND T1.last_name = 'Thomason'
```

**Predicted SQL:**

```sql
SELECT T2.major_name FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.major_id WHERE T2.first_name = 'Brent' AND T2.last_name = 'Thomason'
```

### Q1359 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** replaces gold's flat CAST/SUM ratio calculation with an unrelated derived-table/self-join subquery counting budget-item pairs where Yearly Kickoff spending exceeds October Meeting spending -- an entirely different computation and result type (count vs ratio) that gold's flat query structure doesn't require at all

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM (
    SELECT T1.amount_spent - T3.amount_spent AS diff 
    FROM budget AS T1 
    INNER JOIN event AS T2 ON T1.event_id = T2.event_id 
    INNER JOIN budget AS T3 ON T3.event_id = (
        SELECT event_id 
        FROM event 
        WHERE event_name = 'October Meeting'
    )
    WHERE T2.event_name = 'Yearly Kickoff' 
    AND T1.category = 'Advertisement' 
    AND T3.category = 'Advertisement'
) 
WHERE diff > 0
```

### Q1376 (moderate, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's tie-preserving HAVING ratio=MAX(ratio) subquery structure into ORDER BY .../LIMIT 1 -- verified gold actually returns 3 tied top-ratio events, not 1; additionally filters status='closed' (lowercase), which doesn't match the real stored value 'Closed' at all, currently returning zero rows outright

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.event_id WHERE T1.status = 'closed' ORDER BY (T2.amount - T2.amount_remaining) / T2.amount DESC LIMIT 1
```

### Q1387 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops the position='Treasurer' filter entirely -- returns all members with expenses tied to the Yearly Kickoff budget instead of just the Treasurer

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT T4.first_name, T4.last_name 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.event_id 
INNER JOIN expense AS T3 ON T2.budget_id = T3.budget_id 
INNER JOIN member AS T4 ON T3.member_id = T4.member_id 
WHERE T1.event_name = 'Yearly Kickoff'
```

### Q1389 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** joins expense directly to event via expense.budget_id = event.event_id -- a bogus join since expense.budget_id doesn't reference event.event_id at all (verified: zero matching rows); the budget table, which it actually references, is entirely omitted; also aggregates SUM(cost) per event via an added GROUP BY, instead of gold's single cheapest raw expense row (no aggregation)

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.event_name FROM expense AS T1 INNER JOIN event AS T2 ON T1.budget_id = T2.event_id GROUP BY T2.event_id ORDER BY SUM(T1.cost) ASC, T2.event_name ASC LIMIT 1
```

### Q1403 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** filters status='closed' (lowercase) instead of the real stored value 'Closed' -- matches zero rows entirely; the ORDER BY direction, once the case is fixed, is arithmetically equivalent to gold's ORDER BY remaining ASC (since amount_spent-amount = -remaining)

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.event_name 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.event_id 
WHERE T1.status = 'closed' 
ORDER BY T2.amount_spent - T2.amount DESC 
LIMIT 1
```

### Q1411 (simple, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified the member has multiple expense records with duplicate descriptions (e.g. 'Posters' x3, 'Water, chips, cookies' x3) -- adding DISTINCT collapses these 12 rows to 7 unique values, which the evaluator penalizes against gold's non-deduplicated 12-row multiset

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.expense_description FROM member AS T1 INNER JOIN expense AS T3 ON T1.member_id = T3.member_id WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

### Q1422 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects budget.category (via an unnecessary added join) instead of gold's event.type -- a completely different real-world attribute on a different table; could also return one row per budget item for events with multiple budget line items, whereas gold's single-table query returns exactly one row per event

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.event_id WHERE T1.location = 'MU 215'
```

### Q1427 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** type='guest speaker' (lowercase) instead of the real stored value 'Guest Speaker' -- verified: matches zero rows; also drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT T2.category 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.event_id 
WHERE T1.location = 'MU 215' AND T1.type = 'guest speaker' AND T2.amount_spent = 0
```

### Q1432 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** swaps which condition is the WHERE-scoping filter (amount=50) and which is the CASE-measured condition (t_shirt_size='Medium') relative to gold -- computes % of $50 donations where size=Medium instead of gold's % of Medium-sized members' donations that equal $50; also drops the position='Member' filter entirely

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT (SUM(CASE WHEN T1.t_shirt_size = 'Medium' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage 
FROM member AS T1 
JOIN income AS T2 ON T1.member_id = T2.member_id 
WHERE T2.amount = 50
```

### Q1435 (moderate, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified two separate 'Football game' events both qualify -- without DISTINCT the event_name is returned twice (once per event_id) instead of gold's single deduplicated row

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT event_name 
FROM event 
WHERE type = 'Game' 
AND status = 'Closed' 
AND event_date BETWEEN '2019-03-15' AND '2020-03-20'
```

### Q1457 (challenging, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified missing DISTINCT inflates the result from gold's 3 rows to 11 -- members with multiple above-average expenses get repeated

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

### Q1460 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** splits gold's single literal 'Water, Veggie tray, supplies' (one compound description with embedded commas) into three separate IN() values ('Water','Veggie Tray','Supplies') -- misreading a single value as a list; also adds an extra expense_description column to the SELECT list

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name, T3.expense_description, T3.cost 
FROM member AS T1 
INNER JOIN expense AS T3 ON T1.member_id = T3.member_id 
WHERE T3.expense_description IN ('Water', 'Veggie Tray', 'Supplies')
```

---

## superhero (21 failures)

### Q726 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops the height_cm IS NOT NULL AND height_cm != 0 filters entirely -- includes heroes with zero/unknown height that gold explicitly excludes, and changes their ORDER BY position

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' ORDER BY superhero.height_cm DESC
```

### Q728 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops the RANK() OVER (ORDER BY COUNT(*) DESC) window-function column entirely -- gold's output has 3 columns (colour, count, rank) per row, predicted only 2

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

### Q736 (moderate, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's tie-preserving MIN-equality subquery into ORDER BY attribute_value ASC LIMIT 1 -- verified 3 heroes tie for minimum intelligence, so gold returns 3 rows and predicted only 1

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Intelligence' ORDER BY T2.attribute_value ASC LIMIT 1
```

### Q738 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` - **Reason:** attribute_name is never reachable -- the attribute table (which holds it) is never joined at all (only superhero+hero_attribute are joined); requires adding the missing join, not just an alias fix

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_attribute AS T2 INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Durability' AND T2.attribute_value < 50 AND T1.id = T2.hero_id)
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T2.attribute_name = 'Durability' AND T2.attribute_value < 50
```

### Q743 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** moves the alignment condition from WHERE (gold scopes the entire computation to alignment='Bad') into a CASE inside COUNT(), and additionally uses the wrong value 'Neutral' instead of 'Bad' -- computes % of all heroes that are Neutral instead of gold's % that are Bad (scoped via WHERE), and similarly miscounts the Marvel-specific count

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(COUNT(CASE WHEN T2.alignment = 'Neutral' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) AS neutral_percentage,
    COUNT(CASE WHEN T2.alignment = 'Neutral' AND T3.publisher_name = 'Marvel Comics' THEN T1.id ELSE NULL END) AS neutral_marvel_count
FROM 
    superhero AS T1
INNER JOIN 
    alignment AS T2 ON T1.alignment_id = T2.id
INNER JOIN 
    publisher AS T3 ON T1.publisher_id = T3.id
```

### Q744 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's derived-table SUM(CASE) structure and outer CASE-based 'which publisher has more' column entirely -- verified Marvel=387 > DC=224 -- outputs only a single raw DC-Marvel difference (-163, wrong sign for this query's marvel-first convention) instead of gold's two columns ('Marvel Comics', 163)

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
    (SELECT COUNT(*) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T2.publisher_name = 'DC Comics') -
    (SELECT COUNT(*) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T2.publisher_name = 'Marvel Comics') AS difference
```

### Q745 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** looks for a superhero named 'Star Trek' instead of a publisher named 'Star Trek' -- substitutes the superhero table for gold's publisher table entirely

**Gold SQL:**

```sql
SELECT id FROM publisher WHERE publisher_name = 'Star Trek'
```

**Predicted SQL:**

```sql
SELECT T1.publisher_id FROM superhero AS T1 WHERE T1.superhero_name = 'Star Trek'
```

### Q750 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops the weight_kg > 0 filter entirely -- includes heroes with weight_kg=0 (unspecified weight) in the average, skewing it

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero WHERE gender_id = (SELECT id FROM gender WHERE gender = 'Female')
```

### Q753 (moderate, retrieval) -- **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` - **Reason:** misinterprets 'No Colour' as an absent/NULL eye_colour_id (via LEFT JOIN ... colour IS NULL) rather than gold's real, explicit 'No Colour' row in the colour dimension table (id=1, referenced by 169 heroes) -- verified zero heroes actually have a NULL eye_colour_id, so predicted returns zero rows vs gold's 14

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 LEFT JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour IS NULL
```

### Q758 (moderate, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified multiple Human heroes at height 185 share hair colours (e.g. Brown x4, Black x3) -- without DISTINCT these repeat instead of gold's deduplicated set

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT T3.colour 
FROM superhero AS T1 
INNER JOIN race AS T2 ON T1.race_id = T2.id 
INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id 
WHERE T2.race = 'Human' AND T1.height_cm = 185
```

### Q766 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` - **Reason:** attribute_name is never reachable -- the attribute table is never joined at all; also collapses gold's tie-preserving CTE (max_strength) into ORDER BY DESC LIMIT 1

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT T1.full_name 
FROM superhero AS T1 
INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id 
WHERE T2.attribute_name = 'Strength' 
ORDER BY T2.attribute_value DESC 
LIMIT 1
```

### Q769 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** substitutes the hero_power/superpower tables (a boolean has-power relationship) for gold's hero_attribute/attribute tables (a numeric stat) -- completely different real tables/concepts; also restructures into an unrelated GROUP BY/COUNT(*) approach

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name 
FROM superhero AS T1 
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id 
INNER JOIN hero_power AS T3 ON T1.id = T3.hero_id 
INNER JOIN superpower AS T4 ON T3.power_id = T4.id 
WHERE T2.publisher_name = 'Dark Horse Comics' AND T4.power_name = 'Durability' 
GROUP BY T1.id 
ORDER BY COUNT(*) DESC 
LIMIT 1
```

### Q772 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects the resolved colour NAMES (via additional joins to colour) instead of gold's raw eye_colour_id/hair_colour_id/skin_colour_id integer FK values -- different real columns with different value types, would never match exactly even though they represent the same concept

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

### Q775 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** joins colour via eye_colour_id instead of gold's skin_colour_id -- two different real FK columns on superhero, both referencing colour, but conceptually different attributes

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) 
FROM superhero AS T1 
INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id 
INNER JOIN gender AS T3 ON T1.gender_id = T3.id 
WHERE T3.gender = 'Female'
```

### Q786 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` - **Reason:** attribute_name is never reachable -- the attribute table (which holds it) is never joined at all, in either the outer query or the inner MAX subquery

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
FROM superhero AS T1 
INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id 
WHERE T2.attribute_name = 'Strength' 
AND T2.attribute_value = (SELECT MAX(attribute_value) FROM hero_attribute WHERE attribute_name = 'Strength')
```

### Q788 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** moves the publisher_name='Marvel Comics' condition from CASE (gold: numerator-only condition) into WHERE (a scoping filter) -- inverts the entire computation into '% of Marvel heroes that are female' instead of gold's '% of female heroes that are Marvel'; also uses INNER JOIN instead of gold's LEFT JOIN to publisher, dropping heroes without any publisher from the denominator

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) 
FROM superhero AS T1 
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id 
INNER JOIN gender AS T3 ON T1.gender_id = T3.id 
WHERE T2.publisher_name = 'Marvel Comics'
```

### Q791 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops the height_cm > 0 filter entirely -- includes heroes with zero/unspecified height in the average

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### Q794 (moderate, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's tie-preserving MAX-equality subquery into ORDER BY attribute_value DESC LIMIT 1 -- verified 40 heroes tie for maximum Speed, so gold returns 40 rows and predicted only 1

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT T3.superhero_name 
FROM hero_attribute AS T1 
INNER JOIN attribute AS T2 ON T1.attribute_id = T2.id 
INNER JOIN superhero AS T3 ON T1.hero_id = T3.id 
WHERE T2.attribute_name = 'Speed' 
ORDER BY T1.attribute_value DESC 
LIMIT 1
```

### Q796 (moderate, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** joins attribute using T1.id = T3.hero_id (a condition that doesn't reference attribute.id at all) instead of the correct attribute.id = hero_attribute.attribute_id key -- verified this produces a full 6x6 cross product (36 rows) instead of gold's 6 correctly-paired attribute_name/attribute_value rows for the hero

**Gold SQL:**

```sql
SELECT T3.attribute_name, T2.attribute_value FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT T2.attribute_name, T3.attribute_value 
FROM superhero AS T1 
INNER JOIN attribute AS T2 ON T1.id = T3.hero_id 
INNER JOIN hero_attribute AS T3 ON T1.id = T3.hero_id 
WHERE T1.superhero_name = '3-D Man'
```

### Q819 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** second term treats colour.id=1 ('No Colour', a real value) as eye_colour_id IS NULL instead of = 1 -- verified zero heroes actually have a NULL eye_colour_id, so this term always evaluates to 0, making the result equal to just the Blue-eyed count instead of gold's Blue-minus-No-Colour difference

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT COUNT(*) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T2.colour = 'Blue' AND (T1.weight_kg IS NULL OR T1.weight_kg = 0)) -
    (SELECT COUNT(*) FROM superhero WHERE eye_colour_id IS NULL AND (weight_kg IS NULL OR weight_kg = 0))
```

### Q829 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's outer CASE (which publisher has more heroes) column entirely -- the raw DC-Marvel difference value (-163) is numerically correct for this query's dc-first convention, but the missing publisher-name column alone makes the output shape wrong

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
    (SELECT COUNT(*) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T2.publisher_name = 'DC Comics') -
    (SELECT COUNT(*) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T2.publisher_name = 'Marvel Comics') AS difference
```

---

## thrombosis_prediction (42 failures)

### Q1149 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** drops gold's CTE and CASE-based 'in-patient'/'outpatient' label column entirely; computes an unrelated (in-out)/(in+out)*100 deviation formula instead of gold's in_count*100/out_count ratio

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    (CAST(SUM(CASE WHEN admission_type = '+' THEN 1 ELSE 0 END) AS REAL) - CAST(SUM(CASE WHEN admission_type = '-' THEN 1 ELSE 0 END) AS REAL)) / 
    (CAST(SUM(CASE WHEN admission_type = '+' THEN 1 ELSE 0 END) AS REAL) + CAST(SUM(CASE WHEN admission_type = '-' THEN 1 ELSE 0 END) AS REAL)) * 100 AS deviation_percentage
FROM 
    Patient
WHERE 
    sex = 'M'
```

### Q1150 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** swaps which condition is the WHERE-scoping filter (sex='F') and which is the CASE-measured condition (birth year>1930) relative to gold -- computes % of post-1930-born patients who are female instead of gold's % of female patients born after 1930

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE STRFTIME('%Y', birthday) > '1930'
```

### Q1152 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** 'Inpatient'/'Outpatient' are invented English translations; the real stored Admission values are '+'/'-' symbols (verified)

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T1.admission_type = 'Inpatient' THEN 1 ELSE 0 END) / 
    SUM(CASE WHEN T1.admission_type = 'Outpatient' THEN 1 ELSE 0 END) AS ratio
FROM 
    Patient AS T1
WHERE 
    T1.diagnosis = 'SLE'
```

### Q1155 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** narrows to LDH between 600-800 (adding an upper bound not in gold, and raising the lower bound from 500 to 600) instead of gold's simple LDH>500

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID, T1.sex, T1.birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.lactate_dehydrogenase > 600 AND T2.lactate_dehydrogenase < 800
```

### Q1156 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters kaolin_clotting_time (KCT) instead of gold's russell_viper_venom_time (RVVT) -- two different lab test columns

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT T1.ID, strftime('%Y', 'now') - strftime('%Y', T1.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', T1.birthday)) AS age 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T2.kaolin_clotting_time = '+'
```

### Q1157 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** thrombosis_degree='severe' (a text label) instead of gold's numeric Thrombosis=2 -- verified the real domain is integers 0-3, not text labels

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID, T1.sex, T1.diagnosis 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T2.thrombosis_degree = 'severe'
```

### Q1162 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** uses first_hospital_visit_date ('First Date') instead of gold's first_record_date ('Description') -- different real columns; also flips admission_type to '+' instead of '-', and adds an unrelated Examination join/date condition not in gold

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'F' 
AND STRFTIME('%Y', T1.first_hospital_visit_date) = '1997' 
AND T2.examination_date > T1.first_hospital_visit_date 
AND T1.admission_type = '+'
```

### Q1164 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** sex='女' (Chinese character, verified matches zero rows) instead of gold's 'F'; also thrombosis_degree=3 instead of gold's 1 -- both wrong values

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
SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = '女' AND T2.thrombosis_degree = 3 AND strftime('%Y', T2.examination_date) = '1997'
```

### Q1166 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** the MAX(birthday) subquery omits gold's join restriction to patients who have an Examination record, potentially selecting the wrong (patient-only) birthday and returning an empty join (verified); also drops gold's UNION/NOT EXISTS fallback branch that handles patients whose Examination rows all have NULL symptoms

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT T1.symptoms, T1.diagnosis 
FROM Examination AS T1 
INNER JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T2.birthday = (SELECT MAX(birthday) FROM Patient)
```

### Q1168 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects MAX(Patient.first_hospital_visit_date) instead of gold's Laboratory.Date -- a different real column entirely on a different table; wrapping it in MAX() without GROUP BY also collapses the entire query to one aggregate value across ALL SJS patients, ignoring the ORDER BY/LIMIT 1 (oldest-patient) scoping entirely

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(T2.first_hospital_visit_date), STRFTIME('%Y', T2.first_hospital_visit_date) - STRFTIME('%Y', T2.birthday) 
FROM Laboratory AS T1 
INNER JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T2.diagnosis = 'SJS' 
ORDER BY T2.birthday ASC 
LIMIT 1
```

### Q1169 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** moves sex into the CASE/ratio computation and the UA threshold into a single WHERE filter (>6.5), inverting gold's structure entirely -- gold computes (males with UA<=8.0) / (females with UA<=6.5) using separate thresholds per sex; predicted computes (males)/(females) among all patients with UA>6.5 uniformly

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN T1.sex = 'M' THEN 1 ELSE 0 END) AS REAL) / SUM(CASE WHEN T1.sex = 'F' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM 
    Patient AS T1
INNER JOIN 
    Laboratory AS T2 ON T1.ID = T2.ID
WHERE 
    T2.uric_acid > 6.5
```

### Q1171 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** age threshold changed to <0 instead of gold's <18 -- an essentially impossible condition (examination before birth)

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE STRFTIME('%Y', T2.examination_date) BETWEEN '1990' AND '1993' 
AND STRFTIME('%Y', T2.examination_date) - STRFTIME('%Y', T1.birthday) < 0
```

### Q1175 (moderate, retrieval) -- **Other** (wrong SELECT-expression formula)

**Outcome:** `wrong_answer` - **Reason:** computes age as of the current date (strftime('now') - birthday) instead of gold's age at the time of the specific HGB-max lab test (STRFTIME(Date) - STRFTIME(Birthday)) -- a different, time-varying value; ORDER BY hemoglobin DESC LIMIT 1 otherwise matches gold's HGB DESC LIMIT 1 correctly

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.age, T1.diagnosis 
FROM (
    SELECT P.ID, P.sex, P.birthday, P.diagnosis, L.hemoglobin, 
           strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
    FROM Patient P 
    INNER JOIN Laboratory L ON P.ID = L.ID
) AS T1
ORDER BY T1.hemoglobin DESC 
LIMIT 1
```

### Q1179 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects anticardiolipin_igg instead of gold's anticardiolipin_igm -- a different lab test entirely; also looks up the patient ID via Examination.diagnosis/examination_date instead of gold's Patient.Diagnosis/Description(first_record_date) -- Examination does have its own separate 'Diagnosis' column, but it's the wrong table/column pairing for this patient-identification step

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT T2.anticardiolipin_igg 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.ID = ( 
    SELECT ID 
    FROM Examination 
    WHERE `examination_date` = '1994-02-19' AND diagnosis = 'SLE' 
) 
AND T2.`examination_date` = '1993-11-12'
```

### Q1185 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** assumes lab records fall exactly on '1981-11-01'/'1981-12-01' instead of using gold's LIKE '1981-11-%'/'1981-12-%' month-wide matching with SUM aggregation -- verified the patient's actual lab dates are 1981-11-16 and 1981-12-21, so the exact-date self-join matches zero rows entirely

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (T2.total_cholesterol - T3.total_cholesterol) / T3.total_cholesterol AS decrease_rate
FROM 
    Patient AS T1
INNER JOIN 
    Laboratory AS T2 ON T1.ID = T2.ID
INNER JOIN 
    Laboratory AS T3 ON T1.ID = T3.ID
WHERE 
    T1.birthday = '1959-02-18' 
    AND T2.Date = '1981-12-01' 
    AND T3.Date = '1981-11-01'
```

### Q1187 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** filters aspartate_aminotransferase (GOT) > 30 instead of gold's alanine_aminotransferase (GPT) > 30 -- two different real lab-test columns; also adds an unnecessary join to Patient that doesn't change the result

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.Date BETWEEN '1987-07-06' AND '1996-01-31' 
AND T2.aspartate_aminotransferase > 30 
AND T2.albumin < 4
```

### Q1189 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** the AVG(anticardiolipin_igm)*1.2 subquery threshold drops gold's Thrombosis=2 AND ANA_Pattern='S' scoping -- computes the average across ALL Examination rows instead of just the same filtered subset gold uses

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Examination 
WHERE thrombosis_degree = 2 
  AND antinuclear_antibody_pattern = 'S' 
  AND anticardiolipin_igm > (SELECT AVG(anticardiolipin_igm) * 1.2 FROM Examination)
```

### Q1192 (challenging, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** admission_type='门诊随访' (Chinese text, verified matches zero rows) instead of gold's '-'; also total_bilirubin restricted to 0.3-1.2 instead of gold's simple <2.0

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID, T1.sex, T1.birthday 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.admission_type = '门诊随访' 
AND T2.Date BETWEEN '1991-10-01' AND '1991-10-31' 
AND T2.total_bilirubin BETWEEN 0.3 AND 1.2
```

### Q1195 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** sex='female' instead of gold's 'F' -- the real domain values are 'F'/'M', not English words; verified matches zero rows

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(T2.albumin) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'female' AND T2.platelet_count > 400 AND T1.diagnosis = 'SLE'
```

### Q1205 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops the sex-conditional logic entirely (gold: F&UA>6.5 OR M&UA>8.0) -- instead checks a flat UA BETWEEN 6.5-8.0 range regardless of sex, a fundamentally different condition

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN T2.uric_acid BETWEEN 6.5 AND 8.0 THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

### Q1208 (moderate, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** adds an EXISTS-correlated subquery requiring an earlier qualifying Laboratory record for the same patient -- a condition entirely absent from gold, which just requires any GPT>=60 record; also lowers the threshold to 40 instead of gold's 60

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
AND T2.alanine_aminotransferase > 40 
AND EXISTS (
    SELECT 1 
    FROM Laboratory AS T3 
    WHERE T3.ID = T1.ID 
    AND T3.alanine_aminotransferase > 40 
    AND T3.Date < T2.Date
)
```

### Q1209 (moderate, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified missing DISTINCT causes repeated diagnosis values (e.g. 'MRA' x9) since many patients with GPT>60 share the same diagnosis

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT T1.diagnosis 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.alanine_aminotransferase > 60 
ORDER BY T1.birthday ASC
```

### Q1220 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** urea_nitrogen=13 instead of gold's UN=29 -- a different, wrong threshold value

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.urea_nitrogen = 13
```

### Q1225 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** adds an ungrounded 'OR total_bilirubin < 1.2' branch not in gold (also changing >=2.0 to >2.0), fundamentally altering which rows qualify; additionally uses COUNT(ID) instead of gold's GROUP_CONCAT(DISTINCT ID), a completely different type of output (a count number vs a concatenated ID list)

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT T1.sex, COUNT(T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.`total_bilirubin` < 1.2 OR T2.`total_bilirubin` > 2.0 
GROUP BY T1.sex
```

### Q1227 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** sex='male' instead of gold's 'M' -- verified matches zero rows; also the AVG() formula omits the 'current year minus' subtraction, averaging raw birth years instead of ages, and drops the DISTINCT-per-patient dedup subquery

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(STRFTIME('%Y', T1.birthday)) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.sex = 'male' AND T2.total_cholesterol > 250
```

### Q1229 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** triglyceride>300 instead of gold's TG>=200 -- a different, wrong threshold; also drops DISTINCT

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.triglyceride > 300 
AND STRFTIME('%Y', 'now') - STRFTIME('%Y', T1.birthday) > 50
```

### Q1232 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** uses blood_glucose > 180 instead of gold's >= 180 -- verified 4 lab records have GLU exactly 180 that would be wrongly excluded; total_cholesterol<250 filter is otherwise correct

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID, T1.sex, strftime('%Y', 'now') - strftime('%Y', T1.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', T1.birthday)) AS age 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.blood_glucose > 180 AND T2.total_cholesterol < 250
```

### Q1235 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** red_blood_cell_count<4.0 instead of gold's RBC<3.5 -- a different, wrong threshold value

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.ID, T1.diagnosis, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.birthday) AS age 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.red_blood_cell_count < 4.0
```

### Q1238 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** hemoglobin BETWEEN 13.5-17.5 instead of gold's HGB>10 AND <17 -- both bounds shifted to a different range entirely

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

### Q1239 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** hematocrit>45 instead of gold's HCT>=52 -- a substantially different, wrong threshold, even though the overall 'at least 2 qualifying records' GROUP BY/HAVING approach is structurally equivalent to gold's subquery-based version

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT T1.ID, strftime('%Y', 'now') - strftime('%Y', T1.birthday) AS age 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.hematocrit > 45 
GROUP BY T1.ID 
HAVING COUNT(T2.ID) >= 2
```

### Q1241 (challenging, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** uses SUM(CASE...) over raw joined Laboratory rows instead of gold's two independent COUNT(DISTINCT ID) subqueries -- a patient with multiple qualifying low/high PLT records gets counted multiple times

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T2.platelet_count < 100 THEN 1 ELSE 0 END) AS lower_than_normal,
    SUM(CASE WHEN T2.platelet_count > 400 THEN 1 ELSE 0 END) AS higher_than_normal
FROM 
    Patient AS T1 
INNER JOIN 
    Laboratory AS T2 
ON 
    T1.ID = T2.ID
WHERE 
    T2.platelet_count < 100 OR T2.platelet_count > 400;
```

### Q1242 (challenging, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** drops DISTINCT -- patients with multiple qualifying 1984 Laboratory records in the PLT range would be counted/returned repeatedly instead of once

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2.Date) = '1984' AND strftime('%Y', 'now') - strftime('%Y', T1.birthday) < 50 AND T2.platelet_count BETWEEN 100 AND 400
```

### Q1243 (challenging, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** uses SUM(CASE...)/COUNT(*) over raw Laboratory rows instead of gold's COUNT(DISTINCT CASE...)/COUNT(DISTINCT CASE...) -- a patient with multiple qualifying PT>=14 lab records gets counted once per record instead of once total; moving the PT>=14 condition into WHERE is otherwise a structurally equivalent scoping

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.sex = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE strftime('%Y', 'now') - strftime('%Y', T1.birthday) > 55 AND T2.prothrombin_time >= 14
```

### Q1251 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** uses > 2000 instead of gold's >= 2000 -- verified 2 records have IGG exactly 2000 that would be wrongly excluded; also counts raw Laboratory rows instead of gold's COUNT(DISTINCT ID)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Laboratory WHERE immunoglobulin_g > 2000
```

### Q1255 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` - **Reason:** queries Examination alone, never joining Laboratory -- immunoglobulin_m only exists on Laboratory, causing the error; also uses wrong threshold values (11/300 instead of gold's 40/400)

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT diagnosis FROM Examination WHERE immunoglobulin_m < 11 OR immunoglobulin_m > 300 GROUP BY diagnosis ORDER BY COUNT(diagnosis) DESC LIMIT 1
```

### Q1256 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** compares c_reactive_protein > 3 (a numeric threshold) instead of gold's exact CRP = '+' match -- a different operator/structure entirely, not just a different value

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.c_reactive_protein > 3 AND T1.first_record_date IS NULL
```

### Q1257 (challenging, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified missing DISTINCT inflates the result from gold's 4 to 30 -- patients with multiple CRE>=1.5 records get counted repeatedly

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.creatinine >= 1.5 AND T1.birthday > DATE('now', '-70 years')
```

### Q1265 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** anti_ribonuclear_protein='-' (verified: not a real domain value, matches zero rows) instead of gold's IN ('negative','0'); also replaces Admission='+' with a much broader IS NOT NULL check

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.anti_ribonuclear_protein = '-' AND T1.admission_type IS NOT NULL
```

### Q1267 (moderate, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` - **Reason:** drops gold's CTE with HAVING MAX(COALESCE(Thrombosis,0))=0 (requiring ALL of a patient's Examination records show no thrombosis) -- instead uses a flat WHERE thrombosis_degree=0, which only requires at least one record to show no thrombosis, a fundamentally different any-vs-all semantics; also drops the SM='negative' alternative (only checks =0)

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
SELECT COUNT(DISTINCT T1.ID) 
FROM Examination AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.anti_sm = 0 AND T1.thrombosis_degree = 0
```

### Q1270 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** sex='female' instead of gold's 'F' -- verified matches zero rows; also substitutes a simple Patient.diagnosis IS NOT NULL check for gold's NOT EXISTS(Examination WHERE Symptoms IS NOT NULL) -- a completely different condition

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
SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.anti_scl70 IN ('negative', '0') 
AND T1.sex = 'female' 
AND T1.diagnosis IS NOT NULL
```

### Q1275 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` - **Reason:** drops the '0' alternative for both anti_centromere and anti_ssb (uses ='negative' instead of gold's IN ('negative','0')) -- verified 11 and 58 records respectively use '0' instead of 'negative', which would be wrongly excluded

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.anti_centromere = 'negative' 
AND T2.anti_ssb = 'negative' 
AND T1.sex = 'M'
```

### Q1281 (moderate, retrieval) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** computes MIN(birthday) -- the OLDEST patient -- instead of gold's ORDER BY Birthday DESC LIMIT 1, which selects the YOUNGEST patient; an inverted direction/aggregate choice

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(T1.birthday) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.aspartate_aminotransferase >= 60
```

---

## toxicology (28 failures)

### Q197 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** filters element='O' (uppercase) instead of the real lowercase 'o' -- verified matches zero rows; also the atom-bond join by molecule_id alone (not a specific bond) would multiply oxygen-atom counts by each molecule's bond count if the value bug weren't already blocking everything

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(T1.oxygen_count) 
FROM (
    SELECT COUNT(*) AS oxygen_count 
    FROM atom AS T1 
    INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id 
    WHERE T2.bond_type = '-' AND T1.element = 'O' 
    GROUP BY T1.molecule_id
) AS T1
```

### Q198 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` - **Reason:** AVG(COUNT(bond_id)) nested aggregate misuse; label != '-' is verified equivalent to gold's label = '+' since label only has 2 values

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(T2.bond_id)) 
FROM molecule AS T1 
INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T1.label != '-' AND T2.bond_type = '-' 
GROUP BY T1.molecule_id
```

### Q201 (moderate, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** drops DISTINCT from both COUNT() calls -- verified the atom-bond join (by molecule_id) fans out per matching '=' bond, changing the result from 38.7% to 41.3%

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.atom_id) 
FROM atom AS T1 
INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.bond_type = '='
```

### Q207 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** skips the connected table entirely, joining atom directly to bond via molecule_id -- verified this matches almost every element (17) instead of gold's specific 5 elements actually participating in a double bond

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element 
FROM atom AS T1 
INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.bond_type = '='
```

### Q212 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's HAVING COUNT(*)=(SELECT MIN(cnt)...) tie-preserving structure into ORDER BY/LIMIT 1; also counts DISTINCT molecule_id per element instead of gold's raw atom-row COUNT(*), a different metric (atoms-of-this-element vs molecules-containing-this-element)

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
SELECT T.element FROM ( 
    SELECT T2.element, COUNT(DISTINCT T2.molecule_id) 
    FROM molecule AS T1 
    INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id 
    WHERE T1.label = '-' 
    GROUP BY T2.element 
    ORDER BY COUNT(DISTINCT T2.molecule_id) 
    LIMIT 1 
) t
```

### Q215 (challenging, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** drops DISTINCT from both COUNT(CASE...) calls and replaces gold's IN-subquery with an actual JOIN to bond -- a molecule with multiple '-' bonds fans out each atom row once per matching bond

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(CASE WHEN T1.element = 'i' THEN T1.atom_id END) AS iodine_count,
    COUNT(CASE WHEN T1.element = 's' THEN T1.atom_id END) AS sulfur_count
FROM 
    atom AS T1
INNER JOIN 
    molecule AS T2 ON T1.molecule_id = T2.molecule_id
INNER JOIN 
    bond AS T3 ON T2.molecule_id = T3.molecule_id
WHERE 
    T3.bond_type = '-'
```

### Q218 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** compares element != 'F' (uppercase) instead of the real lowercase 'f' -- since 'F' never matches any real value, this condition is trivially true for every row, making the computed percentage always ~100% regardless of actual fluorine content; also computes a per-atom-row percentage instead of gold's per-molecule (COUNT DISTINCT) percentage

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.element != 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM molecule AS T1 
INNER JOIN atom AS T3 ON T1.molecule_id = T3.molecule_id 
WHERE T1.label = '+'
```

### Q219 (challenging, aggregate) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** numerator SUM(CASE...) is not deduplicated (unlike the denominator's COUNT(DISTINCT)) -- verified this gives 100.0 instead of gold's 66.67 due to fan-out from molecules with multiple '#' bonds

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.label = '+' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT T1.molecule_id) FROM molecule AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '#'
```

### Q226 (moderate, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** omits gold's ROUND(...,5) precision wrapper -- the raw unrounded ratio value won't match the evaluator's exact string comparison

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

### Q227 (simple, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** omits gold's ROUND(...,3) precision wrapper; SUM(CASE...,1,0) vs COUNT(CASE...) is mathematically equivalent

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T.label = '+' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T.molecule_id) FROM molecule AS T
```

### Q228 (moderate, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** omits gold's ROUND(...,4) precision wrapper; the added redundant join to molecule doesn't change the filtered atom set

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'h' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR206'
```

### Q230 (challenging, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified multiple atoms share the same element within this molecule (e.g. 'c' and 'h' repeat many times) -- without DISTINCT these repeat instead of gold's deduplicated (element,label) pairs

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

### Q232 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** selects label instead of gold's molecule_id -- since label is already constrained to '-' by the WHERE filter, this returns three rows of the constant '-' instead of three distinct molecule IDs; ORDER BY label is similarly a no-op instead of gold's ORDER BY molecule_id

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT T2.label FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '-' AND T1.bond_type = '-' ORDER BY T2.label ASC LIMIT 3
```

### Q234 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** atom_id=12 (a bare integer) instead of gold's string-formatted 'TR009_12' -- verified matches zero rows; also omits the OR atom_id2= check entirely

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected AS T1 
JOIN bond AS T2 ON T1.bond_id = T2.bond_id 
WHERE T1.atom_id = 12 AND T2.molecule_id = 'TR009'
```

### Q236 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** joins connected twice on the same bond_id condition (T2 for atom_id, T3 for atom_id2) instead of once -- verified this produces a 2x2=4-row cross product (including two spurious self-paired rows) instead of gold's clean 2-row result from a single join

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT T.bond_type, T2.atom_id, T3.atom_id2 
FROM bond AS T 
JOIN connected AS T2 ON T.bond_id = T2.bond_id 
JOIN connected AS T3 ON T.bond_id = T3.bond_id 
WHERE T.bond_id = 'TR001_6_9'
```

### Q239 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** atom_id=19/atom_id2=19 (bare integers) instead of gold's SUBSTR(atom_id,-2)='19' suffix match on the full string ID -- verified matches zero rows

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected WHERE atom_id = 19 OR atom_id2 = 19
```

### Q242 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** atom_id BETWEEN 21 AND 25 (bare integers) instead of gold's SUBSTR(atom_id,-2) BETWEEN '21' AND '25' suffix match -- verified matches zero rows

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.atom_id BETWEEN 21 AND 25 AND T2.label = '+'
```

### Q244 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` - **Reason:** collapses gold's tie-preserving HAVING cnt=(SELECT MAX(cnt) FROM sub) CTE structure into GROUP BY/ORDER BY DESC LIMIT 1 -- verified 2 molecules tie for the maximum double-bond count, so gold returns 2 rows and predicted only 1

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
GROUP BY T2.molecule_id 
ORDER BY COUNT(T1.bond_type) DESC 
LIMIT 1
```

### Q245 (moderate, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** computes AVG(bond_id) -- a nonsensical average of bond identifier strings -- instead of gold's COUNT(bond_id)/COUNT(atom_id) ratio; a wrong aggregate function entirely

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(T2.bond_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

### Q247 (challenging, retrieval) -- **Other** (missing/redundant DISTINCT)

**Outcome:** `wrong_answer` - **Reason:** verified many duplicate element values (e.g. 'na' repeated many times) among unconnected atoms -- without DISTINCT these repeat instead of gold's deduplicated set

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE atom_id NOT IN (SELECT atom_id FROM connected)
```

### Q248 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` - **Reason:** references T1.molecule_id (T1=connected, no such column) instead of T2.molecule_id (T2=bond, already joined) -- an alias mix-up on an already-joined table, causing the error; also uses bond_type='triple' (an invented English word) instead of the real symbol '#'

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT T1.atom_id 
FROM connected AS T1 
JOIN bond AS T2 ON T1.bond_id = T2.bond_id 
WHERE T2.bond_type = 'triple' AND T1.molecule_id = 'TR041'
```

### Q253 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` - **Reason:** skips the connected table entirely, joining atom directly to bond via molecule_id -- same missing-table pattern as Q207, matching far more elements than gold's atoms actually participating in a triple bond

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.element FROM bond AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#'
```

### Q255 (moderate, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** omits gold's ROUND(...,5) precision wrapper; SUM(CASE...,1,0) vs COUNT(CASE...) is mathematically equivalent

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.label = '+' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

### Q260 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** element='P' OR element='Br' (uppercase) instead of the real lowercase 'p'/'br' -- verified matches zero rows; also restructures gold's two independent IN-subquery conditions (molecule-level existence checks) into a single row-level join filter, a narrower semantics

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM atom AS T1 
INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.bond_type = '#' AND (T1.element = 'P' OR T1.element = 'Br')
```

### Q263 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** bond_type='single' (an invented English word) instead of the real symbol '-' -- verified matches zero rows; also restructures gold's atom+IN-subquery-on-molecule approach into a fan-out-prone connected/bond/atom join

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.element = 'cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM connected AS T1 
INNER JOIN bond AS T2 ON T1.bond_id = T2.bond_id 
INNER JOIN atom AS T3 ON T1.atom_id = T3.atom_id 
WHERE T2.bond_type = 'single'
```

### Q273 (moderate, aggregate) -- **Other** (wrong aggregate function or scaling)

**Outcome:** `wrong_answer` - **Reason:** omits the CAST(...AS REAL), causing SQLite integer division to truncate the result -- verified gold's 3.14192849404117 becomes a truncated 3 in predicted

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(CASE WHEN T1.element = 'cl' THEN T1.atom_id ELSE NULL END) * 100 / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

### Q281 (challenging, retrieval) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` - **Reason:** groups by molecule_id instead of gold's element -- a completely different grouping entity/meaning; also drops the substr(atom_id,-2)='_4' filter entirely, and omits the COUNT(*) column, instead using an unrelated ORDER BY MIN(atom_id) LIMIT 3,1 trick to pick a single element

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT T1.element 
FROM atom AS T1 
INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.label = '+' 
GROUP BY T1.molecule_id 
ORDER BY MIN(T1.atom_id) 
LIMIT 3, 1
```

### Q282 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` - **Reason:** element='H' (uppercase) instead of the real lowercase 'h' -- verified matches zero rows (0 vs gold's 17), so the ratio numerator is always 0 regardless of actual hydrogen content

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT (COUNT(CASE WHEN T1.element = 'H' THEN T1.atom_id END) * 1.0 / COUNT(T1.atom_id)) AS ratio, T2.label 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T1.molecule_id = 'TR006'
```

---

