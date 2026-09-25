# Qwen2.5-Coder-32B · L3·S3 — hand-classified failures (n=280)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. Predicted SQL uses S3 (descriptive snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. This is the largest (32B) model in the study, so failures skew toward subtler predicate/value bugs rather than gross structural or schema-linking errors. Many judgment calls (tie-preserving HAVING/MAX patterns vs ORDER BY/LIMIT collapse, missing DISTINCT causing duplicate rows, date-format/unit-scale mismatches) were verified by actually executing both the predicted and gold SQL against the real database rather than reasoning from the SQL text alone. Grouped by database, sorted by question id.

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

**Outcome:** `wrong_answer` · **Reason:** Virtual = 'Yes' vs gold's 'F'; also missing rtype='S' filter.

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
FROM satscores s 
JOIN schools sch ON s.county_district_school_code = sch.county_district_school_code 
WHERE s.average_score_math > 400 AND sch.Virtual = 'Yes'
```

### Q11 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `+ Enrollment (Ages 5-17)` term entirely, filtering on enrollment_k12 alone instead of the combined sum > 500.

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

### Q12 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's `NumGE1500/NumTstTakr > 0.3` ratio with an unrelated `number_test_takers/enrollment_grade_12 > 0.3` ratio; also drops the rtype='S', NumTstTakr>0, and Enrollment(5-17)>0 filters.

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
SELECT MAX(frpm.percent_eligible_free_ages_5_17) 
FROM frpm 
JOIN satscores ON frpm.county_district_school_code = satscores.county_district_school_code 
WHERE (satscores.number_test_takers / satscores.enrollment_grade_12) > 0.3
```

### Q17 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `CharterNum IS NOT NULL` and `rtype='S'` filters (the RANK() OVER window function itself matches gold correctly).

**Gold SQL:**

```sql
SELECT CharterNum, AvgScrWrite, 
RANK() OVER (ORDER BY AvgScrWrite DESC) AS WritingScoreRank 
FROM schools AS T1  INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds 
WHERE T2.AvgScrWrite > 499 AND CharterNum is not null AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT s.charter_number, ss.average_score_writing, RANK() OVER (ORDER BY ss.average_score_writing DESC) as rank
FROM satscores ss
JOIN schools s ON ss.county_district_school_code = s.county_district_school_code
WHERE ss.average_score_writing > 499
```

### Q23 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** SELECT returns 3 extra columns (City, Zip, State) beyond gold's School+Street, changing the result-set shape.

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT s.School, s.Street, s.City, s.Zip, s.State 
FROM frpm f 
JOIN schools s ON f.county_district_school_code = s.county_district_school_code 
WHERE f.enrollment_k12 - f.enrollment_ages_5_17 > 30
```

### Q24 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `rtype='S'` filter; also adds an unneeded DISTINCT.

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
WHERE f.percent_eligible_free_k12 > 0.1 AND s.number_scores_1500_or_above > 0
```

### Q25 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters County='Riverside' instead of gold's District LIKE 'Riverside%' (two different real columns); also drops the GROUP BY/HAVING AVG(...)>400 aggregation and the rtype='S' filter.

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
JOIN satscores sat ON s.county_district_school_code = sat.county_district_school_code 
WHERE s.County = 'Riverside' AND sat.average_score_math > 400
```

### Q26 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters the percentage column percent_eligible_free_or_reduced_price_meal_ages_5_17 > 800 instead of the absolute FRPM Count (Ages 5-17) > 800 (percentages never exceed 1, so this is always false); also instruction_level_name substituted for School Type.

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT s.School, s.Street, s.City, s.Zip, s.State 
FROM schools s 
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code 
WHERE f.county_name = 'Monterey' AND f.percent_eligible_free_or_reduced_price_meal_ages_5_17 > 800 AND s.instruction_level_name LIKE '%High%'
```

### Q27 (moderate, retrieval) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** INNER JOIN substituted for gold's LEFT JOIN (verified: 749 rows vs 8574 with LEFT JOIN), dropping schools with no matching satscores row.

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT s.School, ss.average_score_writing, s.Phone 
FROM schools s 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
WHERE s.open_date > '1991-12-31' OR s.closed_date < '2000-01-01'
```

### Q28 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** funding_type = 'Local' used instead of the real value 'Locally funded' (in both the outer WHERE and the subquery WHERE).

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT s.School, s.district_ownership_type 
FROM schools s 
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code 
WHERE s.funding_type = 'Local' AND (f.enrollment_k12 - f.enrollment_ages_5_17) > (
    SELECT AVG(f.enrollment_k12 - f.enrollment_ages_5_17) 
    FROM schools s 
    JOIN frpm f ON s.county_district_school_code = f.county_district_school_code 
    WHERE s.funding_type = 'Local'
)
```

### Q31 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses the stored percent_eligible_free_k12 column instead of recomputing FreeMealCount/Enrollment live as gold does (verified a tiny floating-point precision mismatch between the stored and live-computed values).

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT percent_eligible_free_k12 FROM frpm ORDER BY enrollment_k12 DESC LIMIT 9, 2
```

### Q32 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses the stored percent_eligible_free_or_reduced_price_meal_k12 column instead of gold's live CAST(FRPM Count AS REAL)/Enrollment computation (verified same precision-mismatch pattern as Q31).

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT T1.percent_eligible_free_or_reduced_price_meal_k12 
FROM frpm AS T1 
JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.school_ownership_code = 66 
ORDER BY T1.free_or_reduced_price_meal_count_k12 DESC 
LIMIT 5
```

### Q36 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the rtype='S' filter (could select a non-school-level record); also the SELECT list is truncated to 2 of the 6 requested admin name columns.

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
SELECT T2.admin_first_name_1, T2.admin_last_name_1 
FROM satscores AS T1 
JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
ORDER BY T1.number_scores_1500_or_above DESC 
LIMIT 1
```

### Q37 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving `= (SELECT MIN(ratio) ...)` comparison (which can return multiple tied schools) is collapsed to `ORDER BY ratio ASC LIMIT 1`; also drops the NumTstTakr>0/NOT NULL/rtype='S' filters inside the subquery.

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
SELECT Street, City, State, Zip FROM schools WHERE county_district_school_code = (SELECT county_district_school_code FROM satscores ORDER BY (number_scores_1500_or_above / number_test_takers) ASC LIMIT 1)
```

### Q40 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the rtype='S' and AvgScrRead IS NOT NULL filters, which can change which row is the ORDER BY minimum.

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T1.district_name = 'Fresno Unified' ORDER BY T1.average_score_reading ASC LIMIT 1
```

### Q41 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold's RANK() OVER (PARTITION BY county ...) per-county top-5 window function is missing entirely, replaced by a single global ORDER BY ... LIMIT 5; also Virtual='Yes' vs gold's 'F'.

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
WHERE s.Virtual = 'Yes'
GROUP BY s.School, s.County, ss.average_score_reading
ORDER BY s.County, ss.average_score_reading DESC
LIMIT 5
```

### Q46 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** "State" (real, on schools) is referenced on a single-table frpm query with no join present.

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT State, SUM(enrollment_k12) AS total_enrollment
FROM frpm
WHERE educational_option_type = 'Special'
GROUP BY State
ORDER BY total_enrollment DESC
LIMIT 1
```

### Q47 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** AVG(COUNT(*)) is a nested-aggregate misuse, which SQLite rejects outright.

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(COUNT(*)) FROM (SELECT DATE(open_date, 'start of month') AS month_start, COUNT(*) AS schools_opened FROM schools WHERE County = 'Alameda' AND district_ownership_type = 'Elementary School District' AND STRFTIME('%Y', open_date) = '1980' GROUP BY month_start)
```

### Q48 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** frpm is substituted for gold's schools; DOC=54/DOC=52 numeric ownership codes are replaced with unrelated district_type string filters, and StatusType='Merged' is dropped entirely.

**Gold SQL:**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN district_type = 'Unified School District' THEN 1 ELSE 0 END) AS REAL) / SUM(CASE WHEN district_type = 'Elementary School District' THEN 1 ELSE 0 END) AS ratio FROM frpm WHERE county_name = 'Orange County' AND district_type IN ('Unified School District', 'Elementary School District')
```

### Q50 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the rtype='S' and AvgScrMath IS NOT NULL filters, changing which row lands at the LIMIT 6,1 offset.

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
SELECT T2.mailing_street, T2.School FROM satscores AS T1 JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code ORDER BY T1.average_score_math DESC LIMIT 6, 1
```

### Q62 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses the stored ratio-scale percent_eligible_free_k12 (0-1) directly against the 0.18 threshold instead of recomputing the 0-100 percentage FreeMealCount*100/Enrollment as gold does — a scale mismatch that changes which rows qualify.

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM frpm WHERE county_name = 'Los Angeles' AND is_charter_school = 0 AND percent_eligible_free_k12 < 0.18
```

### Q72 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** school_name LIKE '%State Special School%' used instead of the real EdOpsCode='SSS' filter (a different real column entirely); also academic_year exact-match '2014-2015' instead of gold's BETWEEN 2014 AND 2015 range.

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
AND frpm.school_name LIKE '%State Special School%' 
AND schools.City = 'Fremont'
```

### Q77 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters grade_span_offered instead of gold's GSserved (grade_span_served) — two different real columns; SELECT also uses the stored ratio-scale percent column instead of recomputing the 0-100 percentage.

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT s.School, f.percent_eligible_free_ages_5_17 
FROM schools s 
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code 
WHERE s.County = 'Los Angeles' AND s.grade_span_offered LIKE '%K-9%'
```

### Q79 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Virtual = 1 (integer) used instead of the real text code 'F'.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT County, COUNT(*) AS num_schools FROM schools WHERE County IN ('San Diego', 'Santa Barbara') AND Virtual = 1 GROUP BY County ORDER BY num_schools DESC LIMIT 1
```

### Q82 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Missing the ABS() wrapper on longitude, so ORDER BY picks the most positive (not most extreme-magnitude/westernmost) longitude.

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT grade_span_offered FROM schools ORDER BY Longitude DESC LIMIT 1
```

### Q83 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** educational_option_name (on schools) substituted for NSLP Provision Status (on frpm) — two different real columns on different tables; drops the join to frpm entirely as a result.

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT City, COUNT(*) AS Number_of_Schools
FROM schools
WHERE grade_span_offered = 'K-8' AND educational_option_name LIKE '%Multiple Provision Types%'
GROUP BY City
```

### Q85 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds extra `OR admin_first_name_2='Alusine' OR admin_first_name_3='Alusine'` conditions beyond gold's single AdmFName1 filter.

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT T1.percent_eligible_free_k12, T1.district_code 
FROM frpm AS T1 
JOIN schools AS T2 
ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.admin_first_name_1 = 'Alusine' OR T2.admin_first_name_2 = 'Alusine' OR T2.admin_first_name_3 = 'Alusine'
```

### Q87 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** DOC=54/SOC=62 numeric ownership codes replaced with unrelated instruction_level_name/educational_option_name text filters; City value also drifted to a district-style name instead of the plain city name.

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT admin_email_1, admin_email_2 
FROM schools 
WHERE County = 'San Bernardino' 
AND City = 'San Bernardino City Unified' 
AND open_date BETWEEN '2009-01-01' AND '2010-12-31' 
AND instruction_level_name = 'Intermediate/Middle School' 
AND educational_option_name = 'Unified School'
```

---

## debit_card_specializing (22 failures)

### Q1472 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** "currency" is real (customers.Currency) but referenced unqualified on a single-table yearmonth query with no join present; also the value 'LAM' assigned to it is a segment code, not a currency.

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT customer_id FROM yearmonth WHERE date LIKE '2012%' AND currency = 'LAM' ORDER BY consumption ASC LIMIT 1
```

### Q1473 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Averages raw per-row monthly consumption directly instead of first aggregating per-customer annual totals in a derived table/subquery as gold does (also drops the /12).

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE segment = 'SME') AND strftime('%Y', date) = '2013'
```

### Q1476 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) is applied to yearmonth's compact 'YYYYMM' text column; it fails to parse so the WHERE never matches (verified: NULL vs a real non-null result using gold's SUBSTR approach).

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN c.currency = 'CZK' THEN y.consumption ELSE 0 END) - SUM(CASE WHEN c.currency = 'EUR' THEN y.consumption ELSE 0 END) AS consumption_difference
FROM customers c
JOIN yearmonth y ON c.customer_id = y.customer_id
WHERE strftime('%Y', y.date) = '2012'
```

### Q1479 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** GROUP BY/SELECT use strftime('%Y', date) on the compact 'YYYYMM' column, which fails to parse and collapses all rows into one bogus group instead of grouping by real year.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT strftime('%Y', T2.date) AS year, SUM(T2.consumption) AS total_consumption
FROM customers AS T1
JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id
WHERE T1.currency = 'CZK'
GROUP BY year
ORDER BY total_consumption DESC
LIMIT 1
```

### Q1480 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** GROUP BY on month is dropped entirely; picks a single highest-consumption row (and returns the raw full date) instead of aggregating consumption per month across SME customers.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT date FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE segment = 'SME') AND date LIKE '2013%' ORDER BY consumption DESC LIMIT 1
```

### Q1481 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** "segment" is real (customers) but referenced directly inside a yearmonth-scoped subquery with no join to customers present there.

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE currency = 'CZK') AND date LIKE '2013%' AND segment = 'SME') - 
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE currency = 'CZK') AND date LIKE '2013%' AND segment = 'LAM') AS SME_LAM_diff,
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE currency = 'CZK') AND date LIKE '2013%' AND segment = 'LAM') - 
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE currency = 'CZK') AND date LIKE '2013%' AND segment = 'KAM') AS LAM_KAM_diff,
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE currency = 'CZK') AND date LIKE '2013%' AND segment = 'KAM') - 
    (SELECT AVG(consumption) FROM yearmonth WHERE customer_id IN (SELECT customer_id FROM customers WHERE currency = 'CZK') AND date LIKE '2013%' AND segment = 'SME') AS KAM_SME_diff
```

### Q1482 (challenging, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Join condition `y.date = t.date` compares yearmonth's compact 'YYYYMM' dates to transactions_1k's 'YYYY-MM-DD' dates; verified the incompatible-format key yields zero rows vs gold's 3-value tuple; also an unneeded extra join to transactions_1k.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    c.segment, 
    ((SUM(CASE WHEN strftime('%Y', y.date) = '2013' THEN y.consumption ELSE 0 END) - 
      SUM(CASE WHEN strftime('%Y', y.date) = '2012' THEN y.consumption ELSE 0 END)) * 100.0 / 
     SUM(CASE WHEN strftime('%Y', y.date) = '2012' THEN y.consumption ELSE 0 END)) AS percentage_change
FROM 
    customers c
JOIN 
    transactions_1k t ON c.customer_id = t.customer_id
JOIN 
    yearmonth y ON c.customer_id = y.customer_id AND y.date = t.date
WHERE 
    c.currency = 'EUR' AND c.segment IN ('SME', 'LAM', 'KAM')
GROUP BY 
    c.segment
```

### Q1483 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN bounds given in hyphenated 'YYYY-MM' format ('2013-08'/'2013-11') don't match yearmonth's compact 'YYYYMM' storage (verified: NULL vs gold's 1224.96).

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(consumption) FROM yearmonth WHERE customer_id = 6 AND date BETWEEN '2013-08' AND '2013-11'
```

### Q1484 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic'/'Slovakia' and lowercase 'discount' used instead of the real codes 'CZE'/'SVK'/'Discount'.

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT (SELECT COUNT(*) FROM gasstations WHERE country = 'Czech Republic' AND segment = 'discount') - (SELECT COUNT(*) FROM gasstations WHERE country = 'Slovakia' AND segment = 'discount') AS difference
```

### Q1490 (moderate, aggregate) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** INNER JOIN substituted for gold's LEFT JOIN, dropping 47 LAM customers with zero yearmonth rows from the denominator (verified); also missing DISTINCT on the customer counts.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.consumption > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T1.segment = 'LAM'
```

### Q1493 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** `date LIKE '2012-02%'` doesn't match the compact 'YYYYMM' storage format (verified: NULL vs gold-equivalent 66.6).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(customer_id) FROM yearmonth WHERE date LIKE '2012-02%'
```

### Q1498 (simple, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** GROUP BY on month is dropped entirely; MAX(consumption) returns a single top row's value instead of SUM aggregated per month.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) FROM yearmonth WHERE date LIKE '2012%'
```

### Q1505 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'euro' used instead of the real currency code 'EUR'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.customer_id) 
FROM customers c 
JOIN yearmonth y ON c.customer_id = y.customer_id 
WHERE c.currency = 'euro' AND y.consumption > 1000
```

### Q1506 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic' used instead of the real code 'CZE'.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT p.description 
FROM transactions_1k t 
JOIN gasstations g ON t.gas_station_id = g.gas_station_id 
JOIN products p ON t.product_id = p.product_id 
WHERE g.country = 'Czech Republic'
```

### Q1509 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'Czech Republic' used instead of the real code 'CZE'.

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
SELECT COUNT(*) FROM transactions_1k AS t JOIN gasstations AS g ON t.gas_station_id = g.gas_station_id WHERE g.country = 'Czech Republic' AND t.date > '2012-01-01'
```

### Q1514 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT causes 3 duplicate rows instead of gold's 1 (verified); the dropped gasstations join is harmless/vestigial.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT c.currency FROM customers c JOIN transactions_1k t ON c.customer_id = t.customer_id WHERE t.date = '2012-08-24' AND t.time = '16:25:00'
```

### Q1524 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Selects customers.currency (the customer's own currency) instead of gasstations.Country; also filters transactions_1k.amount=548.4 instead of Price=548.4.

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT c.currency FROM customers c JOIN transactions_1k t ON c.customer_id = t.customer_id WHERE t.date = '2012-08-24' AND t.amount = 548.4
```

### Q1526 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters transactions_1k.amount=634.8 to locate the target customer instead of gold's Price=634.8 (both real columns on the same table, wrong one chosen).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT (y2012.consumption - y2013.consumption) / y2012.consumption AS decrease_rate
FROM yearmonth y2012
JOIN yearmonth y2013 ON y2012.customer_id = y2013.customer_id
JOIN transactions_1k t ON y2012.customer_id = t.customer_id
WHERE t.date = '2012-08-25' AND t.amount = 634.8 AND y2012.date LIKE '2012%' AND y2013.date LIKE '2013%'
```

### Q1528 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** "segment" is real (gasstations, already joined as T1) but referenced via the wrong alias T2 (transactions_1k).

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.segment = 'premium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM gasstations AS T1 JOIN transactions_1k AS T2 ON T1.gas_station_id = T2.gas_station_id WHERE T1.country = 'SVK'
```

### Q1529 (moderate, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing *Price scaling factor; sums raw Amount instead of Amount*Price for both total_spent and august_2012_spent.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_spent, SUM(CASE WHEN date LIKE '2012-08%' THEN amount ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE customer_id = '38508'
```

### Q1531 (moderate, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Uses AVG(price) (unweighted) instead of the amount-weighted SUM(price*amount)/SUM(amount); the top-spender subquery also orders by SUM(amount) alone instead of SUM(amount*price).

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT c.customer_id, AVG(t.price) AS avg_price_per_item, c.currency
FROM customers c
JOIN transactions_1k t ON c.customer_id = t.customer_id
WHERE c.customer_id = (
    SELECT customer_id
    FROM transactions_1k
    GROUP BY customer_id
    ORDER BY SUM(amount) DESC
    LIMIT 1
)
GROUP BY c.customer_id, c.currency
```

### Q1533 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Filters Price>29.00 instead of the unit-price ratio Price/Amount>29.00; also the date filter uses a hyphenated LIKE pattern that doesn't match the compact YYYYMM format.

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT y.consumption 
FROM transactions_1k t 
JOIN yearmonth y ON t.customer_id = y.customer_id 
WHERE t.product_id = 5 AND t.price > 29.00 AND y.date LIKE '2012-08%'
```

---

## european_football_2 (33 failures)

### Q1025 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2016' vs the real stored format '2015/2016'.

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
LIMIT 1
```

### Q1028 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving `HAVING COUNT(*) = (SELECT MAX(win_count)...)` pattern is collapsed to `ORDER BY wins DESC LIMIT 1`; also a wrong season ('2010/2011' vs '2009/2010') and an incorrect League.name/Country split ('Premier League' + Country='Scotland' instead of the single real value 'Scotland Premier League').

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T2.team_long_name, COUNT(*) as wins
FROM Match AS M
JOIN Team AS T2 ON M.away_team_api_id = T2.team_api_id
JOIN League AS L ON M.league_id = L.id
JOIN Country AS C ON L.country_id = C.id
WHERE C.name = 'Scotland' AND L.name = 'Premier League' AND M.season = '2010/2011' AND M.away_team_goals > M.home_team_goals
GROUP BY T2.team_long_name
ORDER BY wins DESC
LIMIT 1
```

### Q1029 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds an extra team_long_name column beyond gold's single-column buildUpPlaySpeed output.

**Gold SQL:**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT T.team_long_name, TA.buildup_play_speed 
FROM Team AS T 
JOIN Team_Attributes AS TA ON T.team_api_id = TA.team_api_id 
ORDER BY TA.buildup_play_speed DESC 
LIMIT 4
```

### Q1030 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2016' vs the real stored format '2015/2016'.

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
LIMIT 1
```

### Q1031 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `CASE WHEN strftime('%m-%d','now') < strftime('%m-%d', birthday) THEN 1 ELSE 0 END` adjustment entirely, causing an off-by-one age error for players whose birthday hasn't yet occurred this year.

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
SELECT (strftime('%Y', 'now') - strftime('%Y', P.birthday)) AS age
FROM Player P
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id
WHERE PA.sprint_speed >= 97 AND PA.date BETWEEN '2013-01-01' AND '2015-12-31'
```

### Q1032 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving `HAVING COUNT(m.id) = (SELECT MAX(match_count)...)` pattern is collapsed to `ORDER BY match_count DESC LIMIT 1`.

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(M.id) AS match_count FROM League L JOIN Match M ON L.id = M.league_id GROUP BY L.id ORDER BY match_count DESC LIMIT 1
```

### Q1035 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT can produce duplicate team_fifa_api_id rows across multiple qualifying dates.

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT team_fifa_api_id FROM Team_Attributes WHERE buildup_play_speed > 50 AND buildup_play_speed < 60
```

### Q1036 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT (verified: pred returns 129 rows vs gold's 128 distinct rows — one duplicate team from having multiple qualifying Team_Attributes rows in 2012).

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T1.team_long_name FROM Team AS T1 JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id WHERE T2.date LIKE '2012%' AND T2.buildup_play_passing > (SELECT AVG(buildup_play_passing) FROM Team_Attributes WHERE date LIKE '2012%')
```

### Q1037 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT/per-player counting causes the ratio to be computed per Player_Attributes row instead of per distinct player (a player with multiple attribute snapshots is counted multiple times in both numerator and denominator).

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.birthday BETWEEN '1987-01-01' AND '1992-12-31'
```

### Q1040 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** GROUP BY omits player_api_id (grouping by player_name alone risks silently merging two different players who happen to share a name).

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
SELECT P.player_name 
FROM Player P 
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id 
WHERE P.height > 180 
GROUP BY P.player_name 
ORDER BY AVG(PA.heading_accuracy) DESC 
LIMIT 10
```

### Q1076 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** AVG(CASE WHEN player=X THEN value ELSE 0 END) dilutes the per-player average with zero-contributions from every other player's rows, instead of gold's SUM(CASE...)/COUNT(CASE...ELSE NULL) pattern that correctly restricts to that player's own rows.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL:**

```sql
SELECT AVG(CASE WHEN T2.player_name = 'Abdou Diallo' THEN T1.ball_control ELSE 0 END) - AVG(CASE WHEN T2.player_name = 'Aaron Appindangoye' THEN T1.ball_control ELSE 0 END) AS ball_control_difference FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
```

### Q1080 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attacking_work_rate LIKE '%high%' used instead of gold's ='low' — the opposite value.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate LIKE '%high%'
```

### Q1084 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces defensive_work_rate='high' with a much looser NOT LIKE '%low%' (which also admits 'medium'/other values); adds two entirely fabricated extra filters (preferred_foot IN ('left','right') and attacking_work_rate LIKE '%high%') not present in gold at all.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.player_api_id) 
FROM Player P 
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id 
WHERE strftime('%Y', P.birthday) < '1986' 
AND PA.preferred_foot IN ('left', 'right') 
AND PA.defensive_work_rate NOT LIKE '%low%' 
AND PA.attacking_work_rate LIKE '%high%'
```

### Q1088 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** "volley" (singular) doesn't exist anywhere in the schema; the real column is "volleys" (plural).

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT P.player_name FROM Player P JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id WHERE PA.volley > 70 AND PA.dribbling > 70
```

### Q1092 (simple, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving HAVING=MAX pattern is collapsed to ORDER BY COUNT(...) DESC LIMIT 1.

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
ORDER BY COUNT(M.id) DESC 
LIMIT 1
```

### Q1094 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Gold's per-player "most recent rating" CTEs (ORDER BY date DESC LIMIT 1) are missing entirely, replaced by an all-time MAX(CASE...) that ignores the date dimension and instead finds each player's highest-ever rating.

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT ((MAX(CASE WHEN T2.player_name = 'Ariel Borysiuk' THEN T1.overall_rating ELSE 0 END) - MAX(CASE WHEN T2.player_name = 'Paulin Puel' THEN T1.overall_rating ELSE 0 END)) * 100.0 / MAX(CASE WHEN T2.player_name = 'Paulin Puel' THEN T1.overall_rating ELSE 0 END)) AS percentage_difference FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact match date='2016-06-23' fails against the time-suffixed date column (verified: stored as 'YYYY-MM-DD 00:00:00'; exact match gives 0 rows vs SUBSTR's 52).

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.player_name FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.overall_rating = 77 AND T1.date = '2016-06-23' ORDER BY T2.birthday ASC LIMIT 1
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact match date='2016-02-04' fails against the time-suffixed date column (same 'YYYY-MM-DD 00:00:00' storage issue as Q1102).

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT T1.overall_rating FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Aaron Mooy' AND T1.date = '2016-02-04'
```

### Q1105 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact match date='2015-05-01' fails against the time-suffixed date column instead of gold's LIKE '2015-05-01%' pattern.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.attacking_work_rate FROM Player_Attributes AS T1 JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Francesco Migliore' AND T1.date = '2015-05-01'
```

### Q1107 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing the secondary `ORDER BY date ASC` tie-break; if multiple rows share the max crossing value, gold picks the earliest by date while pred has no tie-break at all.

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT date FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Kevin Constant') ORDER BY crossing DESC LIMIT 1
```

### Q1110 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact match date='2010-02-22' fails against the time-suffixed date column instead of gold's LIKE '2010-02-22%' pattern.

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT T1.buildup_play_passing_class FROM Team_Attributes AS T1 JOIN Team AS T2 ON T1.team_api_id = T2.team_api_id WHERE T2.team_long_name = 'FC Lorient' AND T1.date = '2010-02-22'
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact match date='2015-09-10' fails against the time-suffixed date column instead of gold's LIKE '2015-09-10%' pattern.

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT T2.defence_aggression_class FROM Team AS T1 JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id WHERE T1.team_long_name = 'Hannover 96' AND T2.date = '2015-09-10'
```

### Q1114 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN uses bare date strings against the time-suffixed date column, which can incorrectly exclude the boundary date's rows (e.g. '2016-04-21 00:00:00' > '2016-04-21' lexically).

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(overall_rating) FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Marko Arnautovic') AND date BETWEEN '2007-02-22' AND '2016-04-21'
```

### Q1115 (challenging, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** The self-join condition requires ld.player_api_id = jb.player_api_id (both sides the same player), which is impossible to satisfy for two different named players (Landon Donovan vs Jordan Bowery), so the query returns nothing; also an exact-date-vs-time-suffix mismatch.

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT ((ld.overall_rating - jb.overall_rating) * 100.0 / jb.overall_rating) AS percentage_difference
FROM Player_Attributes ld
JOIN Player_Attributes jb ON ld.player_api_id = jb.player_api_id AND ld.date = jb.date
JOIN Player pld ON ld.player_api_id = pld.player_api_id
JOIN Player pjb ON jb.player_api_id = pjb.player_api_id
WHERE ld.date = '2013-07-12' AND pld.player_name = 'Landon Donovan' AND pjb.player_name = 'Jordan Bowery'
```

### Q1122 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Orders by strength instead of gold's overall_rating — two different real attributes.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1130 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT can produce duplicate team_short_name rows across multiple qualifying dates.

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T1.team_short_name FROM Team AS T1 JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id WHERE T2.chance_creation_passing_class = 'Safe'
```

### Q1133 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Threshold '1999-12-31' used instead of gold's intended >1990 birth-year threshold — an unrelated, much later cutoff year.

**Gold SQL:**

```sql
SELECT COUNT(id) FROM Player WHERE STRFTIME('%Y', birthday) > '1990' AND player_name LIKE 'Aaron%'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player WHERE player_name LIKE 'Aaron%' AND birthday > '1999-12-31'
```

### Q1136 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses potential instead of gold's crossing attribute throughout; also narrows the MAX subquery with extra filters not in gold and adds a fabricated attacking_work_rate != 'Low' condition.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player_Attributes WHERE potential = (SELECT MAX(potential) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate != 'Low') AND preferred_foot = 'left' AND attacking_work_rate != 'Low'
```

### Q1139 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** League name 'Belgian Jupiler League' vs the real stored value 'Belgium Jupiler League'; also an exact-date-vs-time-suffix mismatch.

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT home_team_goals, away_team_goals FROM Match WHERE date = '2008-09-24' AND league_id = (SELECT id FROM League WHERE name = 'Belgian Jupiler League')
```

### Q1145 (simple, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds an extra num_games count column beyond gold's single name column, changing the result-set shape.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(M.id) as num_games
FROM League L
JOIN Match M ON L.id = M.league_id
WHERE M.season = '2015/2016'
GROUP BY L.id
ORDER BY num_games DESC
LIMIT 4
```

### Q1146 (moderate, retrieval) — **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds an unwarranted GROUP BY away_team_api_id + SUM(away_team_goals) aggregation where gold wants a single-match raw maximum (no grouping at all) — a fundamentally different question (career total vs one match's away score).

**Gold SQL:**

```sql
SELECT t2.team_long_name FROM Match AS t1 INNER JOIN Team AS t2 ON t1.away_team_api_id = t2.team_api_id ORDER BY t1.away_team_goal DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.team_long_name FROM Match AS M JOIN Team AS T2 ON M.away_team_api_id = T2.team_api_id GROUP BY M.away_team_api_id ORDER BY SUM(M.away_team_goals) DESC LIMIT 1
```

### Q1147 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Orders by strength instead of gold's overall_rating — two different real attributes.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE player_api_id = (SELECT player_api_id FROM Player_Attributes ORDER BY strength DESC LIMIT 1)
```

### Q1148 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses T2.strength instead of gold's T2.overall_rating; also drops the height < 180 WHERE filter entirely, changing the denominator scope from "short players" to "all players".

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.height < 180 AND T2.strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Player AS T1 JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id
```

---

## financial (22 failures)

### Q89 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the statement_frequency='POPLATEK PO OBRATU' filter entirely, replacing it with an unrelated `t.date > a.date` condition via an unnecessary join to trans.

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
WHERE d.region = 'East Bohemia' AND t.date > a.date
```

### Q92 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold's inclusive BETWEEN 6000 AND 10000 is replaced with exclusive `> 6000 AND < 10000` bounds.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T2.district_id)  FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' AND T2.A11 BETWEEN 6000 AND 10000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT d.district_id) 
FROM district d 
JOIN client c ON d.district_id = c.district_id 
WHERE c.gender = 'F' 
GROUP BY d.district_id 
HAVING AVG(d.average_salary) > 6000 AND AVG(d.average_salary) < 10000
```

### Q93 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** district_name LIKE '%North Bohemia%' used instead of the real region = 'north Bohemia' (two different real columns — district_name holds town names, not region names).

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT c.client_id) 
FROM client c 
JOIN district d ON c.district_id = d.district_id 
WHERE c.gender = 'M' AND d.district_name LIKE '%North Bohemia%' AND d.average_salary > 8000
```

### Q94 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** The alias `d` is reused for both `disp` and `district` in the same FROM clause, corrupting the join chain so account_id (which should route through the shadowed disp alias) is never actually reachable.

**Gold SQL:**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT c.account_id, MAX(d.average_salary) - MIN(d.average_salary) 
FROM client c 
JOIN disp d ON c.client_id = d.client_id 
JOIN district d ON c.district_id = d.district_id 
WHERE c.gender = 'F' 
ORDER BY c.birth_date ASC 
LIMIT 1
```

### Q98 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency = 'WEEKLY' (translated English) used instead of the real stored Czech value 'POPLATEK TYDNE'; also an extra status='A' filter not in gold.

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE l.status = 'A' AND STRFTIME('%Y', l.date) = '1997' AND a.statement_frequency = 'WEEKLY'
ORDER BY l.amount ASC
LIMIT 1
```

### Q99 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an extra status='A' filter not present in gold, which can change which loan is the top ORDER BY match.

**Gold SQL:**

```sql
SELECT T1.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T2.date) = '1993' AND T1.duration > 12 ORDER BY T1.amount DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE l.duration_months > 12 AND l.status = 'A' AND strftime('%Y', a.date) = '1993'
ORDER BY l.amount DESC
LIMIT 1
```

### Q115 (challenging, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `error` · **Reason:** Join condition `disp.district_id` is fabricated — disp has no district_id column; the correct path routes through client instead.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T3.client_id) 
FROM district AS T1 
JOIN disp AS T2 ON T1.district_id = T2.district_id 
JOIN client AS T3 ON T2.client_id = T3.client_id 
WHERE T1.region = 'South Bohemia' 
GROUP BY T1.district_id 
ORDER BY T1.number_inhabitants DESC 
LIMIT 1
```

### Q116 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's SUM(IIF(date=X, balance, 0)) conditional aggregation with an unaggregated self-join of trans to itself, which can yield multiple/wrong rows instead of one aggregated ratio if either date has more than one transaction.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT (t2.balance_after_transaction - t1.balance_after_transaction) / t1.balance_after_transaction * 100 AS increase_rate
FROM trans t1
JOIN trans t2 ON t1.account_id = t2.account_id
JOIN loan l ON t1.account_id = l.account_id
WHERE l.date = '1993-07-05'
AND t1.date = '1993-03-22'
AND t2.date = '1998-12-27'
```

### Q118 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='A' used instead of gold's status='C'.

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM loan WHERE amount < 100000
```

### Q125 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status IN ('A','C') used instead of gold's status='D'; also amount>0 substituted for the A12/A13 not-null/positivity checks.

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT (d.unemployment_rate_1996 - d.unemployment_rate_1995) / d.unemployment_rate_1995 * 100 AS unemployment_rate_increment
FROM loan l
JOIN disp dp ON l.account_id = dp.account_id
JOIN client c ON dp.client_id = c.client_id
JOIN district d ON c.district_id = d.district_id
WHERE l.status IN ('A', 'C') AND l.amount > 0
```

### Q129 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='PRIJEM' (deposit) used instead of gold's type='VYDAJ' (withdrawal) — two different real transaction-type codes.

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
WHERE t.type = 'PRIJEM' AND t.date LIKE '1996-01-%' 
ORDER BY t.amount DESC 
LIMIT 10
```

### Q136 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency='monthly' used instead of the real Czech value 'POPLATEK MESICNE'; also an extra status='A' filter not in gold.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT l.account_id) 
FROM loan l 
JOIN account a ON l.account_id = a.account_id 
WHERE l.amount >= 250000 
AND l.date BETWEEN '1995-01-01' AND '1997-12-31' 
AND l.status = 'A' 
AND a.statement_frequency = 'monthly'
```

### Q137 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='running' is an invented value not matching the real status codes; collapses gold's status='C' OR status='D' into this one wrong value.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM account WHERE account_id IN (SELECT account_id FROM loan WHERE status = 'running') AND district_id = 1
```

### Q145 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Returns client_id instead of gold's account_id; also filters trans.type='PRIJEM' instead of the real trans.operation='VYBER KARTOU' (two different real columns on trans).

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT T1.client_id FROM client AS T1 JOIN disp AS T2 ON T1.client_id = T2.client_id JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'PRIJEM' AND T3.amount < (SELECT AVG(amount) FROM trans WHERE type = 'PRIJEM') AND strftime('%Y', T3.date) = '1998'
```

### Q149 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** disp (needed for the type column gold selects) is missing entirely; substitutes an unrelated `NOT IN (SELECT account_id FROM loan)` condition and district instead.

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
SELECT DISTINCT a.type 
FROM account a 
JOIN district d ON a.district_id = d.district_id 
WHERE a.account_id NOT IN (SELECT account_id FROM loan) 
AND d.average_salary > 8000 AND d.average_salary <= 9000
```

### Q152 (moderate, aggregate) — **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds a GROUP BY district_id where gold has no grouping at all (a single overall AVG across all qualifying districts), producing one row per district instead of one overall value.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(d.number_crimes_1995) 
FROM district d 
JOIN account a ON d.district_id = a.district_id 
WHERE d.number_crimes_1995 > 4000 AND strftime('%Y', a.date) >= '1997' 
GROUP BY d.district_id
```

### Q159 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** client_id (real, on client/disp) is referenced on a single-table trans query with no join present.

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT * FROM trans WHERE client_id = 3356 AND type = 'withdrawal' AND transaction_operation = 'cash'
```

### Q169 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the disp.type='OWNER' filter entirely, allowing non-owner (disponent) associations on the same account to inflate/double-count loans.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT (SUM(CASE WHEN l.date BETWEEN '1997-01-01' AND '1997-12-31' THEN l.amount ELSE 0 END) - SUM(CASE WHEN l.date BETWEEN '1996-01-01' AND '1996-12-31' THEN l.amount ELSE 0 END)) * 100.0 / SUM(CASE WHEN l.date BETWEEN '1996-01-01' AND '1996-12-31' THEN l.amount ELSE 0 END) AS growth_rate
FROM loan l
JOIN disp d ON l.account_id = d.account_id
JOIN client c ON d.client_id = c.client_id
WHERE c.gender = 'M'
```

### Q173 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** amount/type (real, on order/trans/loan) referenced on a single-table account query with no join present.

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT statement_frequency, SUM(amount) AS total_debit FROM account WHERE account_id = 3 AND type = 'debit' GROUP BY statement_frequency HAVING SUM(amount) = 3539
```

### Q186 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency='weekly' used instead of the real Czech value 'POPLATEK TYDNE'.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM client AS T1 JOIN disp AS T2 ON T1.client_id = T2.client_id JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.statement_frequency = 'weekly'
```

### Q192 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Both status='running' and statement_frequency='after each transaction' are invented/translated values that don't match the real stored codes ('C'/'D' and 'POPLATEK PO OBRATU').

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(loan.amount) 
FROM loan 
JOIN account ON loan.account_id = account.account_id 
WHERE loan.status = 'running' AND account.statement_frequency = 'after each transaction'
```

### Q194 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** card.type='high level' used instead of the real value 'gold' (verified: real card types are gold/classic/junior); also an extra unwarranted "must have a loan" subquery filter not present in gold.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.client_id, (strftime('%Y', 'now') - strftime('%Y', c.birth_date)) AS age
FROM client c
JOIN disp d ON c.client_id = d.client_id
JOIN card ca ON d.disposition_id = ca.disposition_id
WHERE ca.type = 'high level' AND d.type = 'owner' AND c.client_id IN (
    SELECT DISTINCT client_id
    FROM disp
    WHERE account_id IN (
        SELECT account_id
        FROM loan
    )
)
```

---

## formula_1 (41 failures)

### Q846 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes results + a DNF-status filter for gold's qualifying table ordered by q1 time — a completely different concept (finishing status vs qualifying pace ranking).

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT T1.driver_ref_name FROM drivers AS T1 JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T2.race_id = 20 AND T2.status_id = (SELECT status_id FROM status WHERE status = 'Did not finish')
```

### Q847 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the NULLS LAST clause, so a driver with a NULL qualifying_2_time incorrectly sorts first in ASC order and gets picked.

**Gold SQL:**

```sql
SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 ORDER BY T1.q2 ASC NULLS LAST LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.last_name FROM drivers AS T1 JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T2.race_id = 19 ORDER BY T2.qualifying_2_time ASC LIMIT 1
```

### Q850 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT can produce duplicate race-name rows when the same race name recurs across multiple years at German circuits.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT T2.name FROM circuits AS T1 JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T1.country = 'Germany'
```

### Q857 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters circuits.name = 'Abu Dhabi Grand Prix' instead of properly joining to races and filtering races.name (circuit name and race name are different real columns/concepts; the join to races is dropped entirely).

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE name = 'Abu Dhabi Grand Prix'
```

### Q861 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes results for gold's drivers (same 2-for-2 table swap), returning qualifying's own session-specific number instead of the driver's permanent number; also the time literal '0:01:54' doesn't match gold's LIKE '1:54%' pattern format.

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT T1.number FROM qualifying AS T1 JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id = 903 AND T1.qualifying_3_time = '0:01:54'
```

### Q865 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces time IS NOT NULL (any finisher) with position = '1' (only the race winner) — a much narrower and semantically different condition.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name FROM drivers d JOIN results r ON d.driver_id = r.driver_id WHERE r.race_id = 592 AND r.position = '1' ORDER BY d.date_of_birth ASC LIMIT 1
```

### Q866 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact match time='0:01:27' used instead of gold's LIKE '1:27%' pattern (lapTimes.time is stored as 'M:SS.mmm' text, not '0:HH:MM').

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.url 
FROM drivers d 
JOIN laptimes l ON d.driver_id = l.driver_id 
WHERE l.race_id = 161 AND l.time = '0:01:27'
```

### Q868 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT (matches gold's join structure exactly otherwise).

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.latitude, T1.longitude FROM circuits AS T1 JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.name = 'Malaysian Grand Prix'
```

### Q872 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact match qualifying_3_time='0:01:33' used instead of gold's LIKE '1:33%' pattern.

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT T1.driver_code FROM drivers AS T1 JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T2.race_id = 45 AND T2.qualifying_3_time = '0:01:33'
```

### Q877 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces time IS NOT NULL with position='1' (only the race winner) instead of gold's "any finisher" criterion.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name FROM drivers d JOIN results r ON d.driver_id = r.driver_id WHERE r.race_id = 872 AND r.position = '1' ORDER BY d.date_of_birth DESC LIMIT 1
```

### Q879 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Missing CAST(... AS REAL) on the text-typed fastest_lap_speed column causes a lexicographic string sort instead of numeric (verified: wrong top row 'Italian' returned instead of the correct 'Brazilian').

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 JOIN results AS T2 ON T1.driver_id = T2.driver_id ORDER BY T2.fastest_lap_speed DESC LIMIT 1
```

### Q880 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Compares the named driver's speed against all OTHER drivers within a single race (driver_id != X) instead of gold's comparison of the SAME driver's speed across two DIFFERENT races (race_id=853 vs 854); also missing CAST.

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
SELECT (MAX(CASE WHEN T1.driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Paul' AND last_name = 'di Resta') THEN T1.fastest_lap_speed ELSE NULL END) - MAX(CASE WHEN T1.driver_id != (SELECT driver_id FROM drivers WHERE first_name = 'Paul' AND last_name = 'di Resta') THEN T1.fastest_lap_speed ELSE NULL END)) * 100 / MAX(CASE WHEN T1.driver_id != (SELECT driver_id FROM drivers WHERE first_name = 'Paul' AND last_name = 'di Resta') THEN T1.fastest_lap_speed ELSE NULL END) AS percent_faster
FROM results AS T1
JOIN races AS T2 ON T1.race_id = T2.race_id
WHERE T2.race_id = 853
```

### Q881 (moderate, aggregate) — **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Adds an unwarranted GROUP BY driver_id, producing one row per driver with a degenerate per-driver ratio instead of gold's single overall percentage.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, COUNT(r.status_id) / (SELECT COUNT(*) FROM results WHERE race_id = (SELECT race_id FROM races WHERE date = '1983-07-16')) AS completion_rate
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
JOIN races ra ON r.race_id = ra.race_id
WHERE ra.date = '1983-07-16'
GROUP BY d.driver_id;
```

### Q884 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Exact date = MIN(date) match (1 row) used instead of gold's year+month match (verified: pred returns 1 race vs gold's 3, since the earliest F1 season held multiple races in the same month).

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT name FROM races WHERE date = (SELECT MIN(date) FROM races)
```

### Q894 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Uses an ungrouped MIN(time) mixed with unaggregated driver/race columns (which then come from an arbitrary row, not necessarily the fastest) instead of gold's ORDER BY milliseconds ASC LIMIT 1; also uses the text time column instead of the numeric milliseconds.

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(T1.time) AS best_lap_time, T2.first_name || ' ' || T2.last_name AS driver, T3.name AS race FROM laptimes AS T1 JOIN drivers AS T2 ON T1.driver_id = T2.driver_id JOIN races AS T3 ON T1.race_id = T3.race_id
```

### Q896 (challenging, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Join condition r.result_id = ds.driver_standings_id compares two unrelated primary keys with no real foreign-key relationship.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN ds.position = 1 THEN 0 ELSE 1 END) AS REAL) * 100 / COUNT(*) 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
JOIN drivers d ON r.driver_id = d.driver_id 
JOIN driverstandings ds ON r.result_id = ds.driver_standings_id 
WHERE d.first_name = 'Lewis' AND d.last_name = 'Hamilton' AND ra.year >= 2010
```

### Q898 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Hardcodes the year 2023 instead of using STRFTIME('%Y', CURRENT_TIMESTAMP) (the actual current year at query time), giving a wrong age.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name, 2023 - strftime('%Y', date_of_birth) AS age FROM drivers WHERE nationality = 'Japanese' ORDER BY age ASC LIMIT 1
```

### Q902 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes results.grid_position (starting grid position) for gold's driverStandings.position (championship standings position) — different concepts entirely.

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT T2.name FROM results AS T1 JOIN races AS T2 ON T1.race_id = T2.race_id JOIN drivers AS T3 ON T1.driver_id = T3.driver_id WHERE T3.first_name = 'Alex' AND T3.last_name = 'Yoong' AND T1.grid_position < 20
```

### Q904 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes results.fastest_lap_time (a per-race summary, text, uncast) for gold's lapTimes.milliseconds (the actual per-lap numeric time records).

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT r.name, r.year 
FROM results res 
JOIN races r ON res.race_id = r.race_id 
JOIN drivers d ON res.driver_id = d.driver_id 
WHERE d.first_name = 'Michael' AND d.last_name = 'Schumacher' 
ORDER BY res.fastest_lap_time ASC 
LIMIT 1
```

### Q909 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Substitutes a fabricated country IN (list of European countries) condition for gold's actual filter races.name = 'European Grand Prix' — a wholesale wrong condition.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T1.country = 'Germany' THEN T2.circuitID END) AS REAL) * 100 / COUNT(T2.circuitId) FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'European Grand Prix'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.country = 'Germany' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM circuits AS T1 JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T1.country IN ('Austria', 'Belgium', 'France', 'Germany', 'Hungary', 'Italy', 'Monaco', 'Netherlands', 'Spain', 'United Kingdom')
```

### Q915 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the dob IS NOT NULL filter, so a driver with a NULL date_of_birth could be incorrectly selected first (NULLs sort before real dates in ASC order).

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT nationality FROM drivers ORDER BY date_of_birth ASC LIMIT 1
```

### Q928 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters circuits.name = 'Canadian Grand Prix' instead of races.name (again conflating circuit name with race name); also uses position_order instead of gold's position — two different real columns.

**Gold SQL:**

```sql
SELECT d.forename, d.surname, d.driverRef FROM drivers AS d JOIN results AS r ON d.driverId = r.driverId JOIN races AS ra ON r.raceId = ra.raceId WHERE ra.name = 'Canadian Grand Prix' AND ra.year = 2007 AND r.position = 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.driver_ref_name 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
JOIN drivers d ON r.driver_id = d.driver_id 
JOIN circuits c ON ra.circuit_id = c.circuit_id 
WHERE ra.year = 2007 AND c.name = 'Canadian Grand Prix' AND r.position_order = 1
```

### Q930 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses position_order (via ORDER BY/LIMIT 1, picking one race) instead of gold's actual filter condition results.rank = 0 (a different real column with a specific meaning), changing both which column matters and how many races could match.

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT r.name 
FROM results res 
JOIN races r ON res.race_id = r.race_id 
JOIN drivers d ON res.driver_id = d.driver_id 
WHERE d.first_name = 'Lewis' AND d.last_name = 'Hamilton' 
ORDER BY res.position_order ASC 
LIMIT 1
```

### Q937 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Race name 'Australian Grand Prix' used instead of gold's 'Chinese Grand Prix'; also position_order instead of position.

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT T1.time FROM results AS T1 JOIN races AS T2 ON T1.race_id = T2.race_id WHERE T2.year = 2008 AND T2.name = 'Australian Grand Prix' AND T1.position_order = 2
```

### Q944 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Computes (MIN(milliseconds) - MAX(milliseconds)) instead of gold's (last_driver_time - champion_time) ordering, flipping the sign of the result (verified: -1.165 vs the correct +1.165).

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT ((MIN(T1.milliseconds) - MAX(T1.milliseconds)) * 100.0 / MAX(T1.milliseconds)) AS percentage_difference
FROM results AS T1
JOIN races AS T2 ON T1.race_id = T2.race_id
WHERE T2.year = 1988 AND T2.name = 'Australian Grand Prix'
```

### Q950 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes constructorResults (per-race points) for gold's constructorStandings (cumulative championship standings) — two different real tables.

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT T2.name FROM constructorResults AS T1 JOIN constructors AS T2 ON T1.constructor_id = T2.constructor_id WHERE T1.race_id = 291 AND T1.points = 0
```

### Q954 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** The CASE-WHEN checks nationality = 'Japanese' (which should be a WHERE filter) instead of gold's time IS NOT NULL completion criterion, computing "% of entries driven by Japanese drivers" instead of gold's "% of Japanese drivers' races that were completed".

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.nationality = 'Japanese' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM drivers AS T1 
JOIN results AS T2 ON T1.driver_id = T2.driver_id 
JOIN races AS T3 ON T2.race_id = T3.race_id 
WHERE T3.year BETWEEN 2007 AND 2009
```

### Q955 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** Alias mixup: milliseconds belongs to the already-joined results (aliased res), but referenced instead via races (aliased r); also an unnecessary join to seasons.

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT s.year, AVG(r.milliseconds / 1000.0) AS avg_time_seconds
FROM seasons s
JOIN races r ON s.year = r.year
JOIN results res ON r.race_id = res.race_id
WHERE s.year < 1975 AND res.position = 1
GROUP BY s.year
```

### Q962 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses laps = 50 (exact equality) instead of gold's laps > 50 (greater-than threshold) — a restructured/wrong operator.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN d.date_of_birth < '1985-01-01' AND r.laps = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT r.driver_id) 
FROM results r 
JOIN drivers d ON r.driver_id = d.driver_id 
WHERE r.race_id IN (SELECT race_id FROM races WHERE year BETWEEN 2000 AND 2005)
```

### Q963 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's SUBSTR-based numeric time-parsing (converting 'M:SS.mmm' to total seconds) with a naive string comparison time < '02:00.00', which doesn't correctly order lap times and uses a mismatched format.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT d.driver_id) 
FROM drivers d 
JOIN laptimes l ON d.driver_id = l.driver_id 
WHERE d.nationality = 'French' AND l.time < '02:00.00'
```

### Q967 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** nationality = 'Netherlands' used instead of the real code 'Dutch' (as gold itself uses); the top-3 date selection logic also differs subtly from gold's row-based LIMIT 3.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM drivers WHERE nationality = 'Netherlands' AND date_of_birth IN (SELECT date_of_birth FROM drivers ORDER BY date_of_birth DESC LIMIT 3)
```

### Q972 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds an unwarranted ORDER BY fastest_lap_time ASC LIMIT 1 that gold doesn't have, truncating the result set to 1 row instead of returning all matching distinct driver/code pairs born in 1971.

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.driver_id, d.driver_code 
FROM drivers d 
JOIN results r ON d.driver_id = r.driver_id 
WHERE d.date_of_birth LIKE '1971%' 
AND r.fastest_lap_time IS NOT NULL 
ORDER BY r.fastest_lap_time ASC 
LIMIT 1
```

### Q977 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Inclusive BETWEEN 50 AND 100 used instead of gold's exclusive > 50 AND < 100 bounds, incorrectly including raceId=50 and raceId=100.

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM results WHERE race_id BETWEEN 50 AND 100 AND status_id = (SELECT status_id FROM status WHERE status = 'Disqualified')
```

### Q978 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT causes a duplicate circuit-location row (verified: 3 rows vs gold's 2 distinct Austrian circuit locations).

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE country = 'Austria'
```

### Q981 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Returns qualifying.qualifying_1_time instead of gold's races.time (the race's own scheduled start time) — two entirely different real columns.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.year, r.name, r.date, q.qualifying_1_time 
FROM qualifying q 
JOIN races r ON q.race_id = r.race_id 
JOIN seasons s ON r.year = s.year 
JOIN drivers d ON q.driver_id = d.driver_id 
WHERE d.date_of_birth = (SELECT MAX(date_of_birth) FROM drivers) 
ORDER BY r.date ASC 
LIMIT 1
```

### Q988 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Adds an extra avg_pit_stop_duration column beyond gold's two name columns (verified the underlying driver identification/ranking logic itself was correct, but the result-set shape differs).

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, AVG(p.duration) as avg_pit_stop_duration
FROM drivers d
JOIN pitstops p ON d.driver_id = p.driver_id
WHERE d.nationality = 'German' AND d.date_of_birth BETWEEN '1980-01-01' AND '1985-12-31'
GROUP BY d.driver_id
ORDER BY avg_pit_stop_duration ASC
LIMIT 3
```

### Q990 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes constructorStandings (filtered by position=1) for gold's results (filtered by a specific time LIKE gap-time pattern) — a fundamentally different table/concept.

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T2.constructor_ref_name, T2.url FROM constructorstandings AS T1 JOIN constructors AS T2 ON T1.constructor_id = T2.constructor_id JOIN races AS T3 ON T1.race_id = T3.race_id WHERE T3.year = 2009 AND T3.name = 'Singapore Grand Prix' AND T1.position = 1
```

### Q994 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes constructorStandings for gold's constructorResults; also drops the GROUP BY name + SUM(points) aggregation entirely, picking a single race's raw points via ORDER BY/LIMIT 1 instead of a summed total across all qualifying years.

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT cs.points, c.name, c.nationality 
FROM constructorstandings cs 
JOIN constructors c ON cs.constructor_id = c.constructor_id 
JOIN races r ON cs.race_id = r.race_id 
WHERE r.name = 'Monaco Grand Prix' AND r.year BETWEEN 1980 AND 2010 
ORDER BY cs.points DESC 
LIMIT 1
```

### Q1001 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds a fabricated round = 3 filter, misinterpreting "Q3" (the third qualifying knockout session) as "round 3" of the season calendar — an entirely wrong condition not present in gold.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name || ' ' || d.last_name AS full_name
FROM drivers d
JOIN qualifying q ON d.driver_id = q.driver_id
JOIN races r ON q.race_id = r.race_id
JOIN circuits c ON r.circuit_id = c.circuit_id
WHERE r.year = 2008 AND c.name = 'Marina Bay Street Circuit' AND q.position = 1 AND r.round = 3
```

### Q1011 (challenging, aggregate) — **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Drops the GROUP BY driverId (finding each driver's personal-best MIN(milliseconds)) entirely, instead ordering raw individual lap records directly, which can repeat the same driver multiple times in the top 20.

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name 
FROM drivers d 
JOIN laptimes l ON d.driver_id = l.driver_id 
ORDER BY l.milliseconds ASC 
LIMIT 20
```

### Q1014 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Substitutes lapTimes.milliseconds (raw individual lap records) for gold's results.FastestLapTime (a per-race best-lap summary field that gold specifically parses from text).

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(milliseconds) AS lap_record FROM lapTimes WHERE race_id IN (SELECT race_id FROM races WHERE circuit_id IN (SELECT circuit_id FROM circuits WHERE country = 'Italy'))
```

---

## student_club (23 failures)

### Q1317 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an extra fabricated filter `position = 'Student_Club'` (not a real position value; 'Student_Club' is actually a major_name) not present in gold.

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM member m JOIN attendance a ON m.member_id = a.member_id JOIN event e ON a.event_id = e.event_id WHERE e.event_name = 'Women''s Soccer' AND m.t_shirt_size = 'Medium' AND m.position = 'Student_Club'
```

### Q1322 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** `type = 'meeting'` (lowercase) vs the real stored value 'Meeting' (verified: 0 rows vs gold-equivalent 4).

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM event WHERE event_id IN (SELECT event_id FROM attendance GROUP BY event_id HAVING COUNT(member_id) > 10) AND type = 'meeting'
```

### Q1334 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Adds an extra fabricated filter `position = 'Student_Club'` (not a real position value) not present in gold.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name FROM member m JOIN zip_code z ON m.zip_code = z.zip_code WHERE z.state = 'Illinois' AND m.position = 'Student_Club'
```

### Q1338 (moderate, retrieval) — **JOIN errors** (Wrong column)

**Outcome:** `error` · **Reason:** expense has no event_id column; the join condition `e.event_id = ev.event_id` is fabricated (correct path routes through budget instead).

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT CASE WHEN e.is_approved = 1 THEN 'true' ELSE 'false' END AS approved FROM expense e JOIN event ev ON e.event_id = ev.event_id WHERE ev.event_name = 'October Meeting' AND ev.event_date = '2019-10-08'
```

### Q1340 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** event_date (real, on event) is referenced on a single-table budget subquery with no join present; also a bogus `event_status = 'Student_Club'` value.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT (SELECT SUM(amount_spent) FROM budget WHERE event_status = 'Student_Club' AND strftime('%Y', event_date) = '2020') - (SELECT SUM(amount_spent) FROM budget WHERE event_status = 'Student_Club' AND strftime('%Y', event_date) = '2019') AS difference
```

### Q1344 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** event is substituted for gold's income (both happen to have a "notes" column, but the question is about income records).

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE event_date = '2019-09-14' AND type = 'fundraising'
```

### Q1357 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** first_name/last_name (real, on member) are referenced on a single-table income query with no join present.

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT date_received FROM income WHERE first_name = 'Connor' AND last_name = 'Hilton'
```

### Q1359 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** Introduces a comparison subquery and restructures gold's ratio-of-sums into a COUNT of a boolean threshold check; also drops the type='Meeting' filter.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' AND T2.category = 'Advertisement' AND T2.amount > (SELECT T2.amount FROM event AS T1 JOIN budget AS T2 ON T1.event_id = T2.event_id WHERE T1.event_name = 'October Meeting' AND T2.category = 'Advertisement') THEN 1 ELSE 0 END) AS count FROM event AS T1 JOIN budget AS T2 ON T1.event_id = T2.event_id
```

### Q1376 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving `HAVING ... = (SELECT MAX(ratio) ...)` pattern is collapsed to a plain `ORDER BY ... LIMIT 1` (verified: still wrong even after fixing the compounding status-case bug, since it only returns 1 of gold's 3 tied events).

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
LIMIT 1
```

### Q1380 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** `category = 'food'` (lowercase) vs the real stored value 'Food'.

**Gold SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL:**

```sql
SELECT SUM(amount_spent) FROM budget WHERE category = 'food'
```

### Q1387 (moderate, retrieval) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Join condition `member.member_id = budget.budget_id` compares two unrelated primary keys; the correct path routes through expense instead.

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 JOIN budget AS T2 ON T1.member_id = T2.budget_id JOIN event AS T3 ON T2.event_id = T3.event_id WHERE T3.event_name = 'Yearly Kickoff'
```

### Q1389 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** event_id/event_name (real, on event) are referenced directly on a single-table expense subquery with no join to route through budget.

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT event_name FROM event WHERE event_id = (SELECT event_id FROM expense GROUP BY event_id ORDER BY SUM(cost) ASC, event_name ASC LIMIT 1)
```

### Q1398 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** `category = 'advertisement'` (lowercase) vs the real stored value 'Advertisement'.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.event_name FROM event e JOIN budget b ON e.event_id = b.event_id WHERE b.category = 'advertisement' ORDER BY b.amount_spent DESC LIMIT 1
```

### Q1399 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** `last_name = 'McLean'` vs the actual stored spelling 'Mclean' (verified via direct lookup).

**Gold SQL:**

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean' AND T3.event_name = 'Women''s Soccer'
```

**Predicted SQL:**

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END AS attended FROM member JOIN attendance ON member.member_id = attendance.member_id JOIN event ON attendance.event_id = event.event_id WHERE member.first_name = 'Maya' AND member.last_name = 'McLean' AND event.event_name = 'Women''s Soccer'
```

### Q1401 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters budget.category='Posters' instead of expense.expense_description='Posters' (verified: 'Posters' isn't a real category value for that event's budget rows, so the query returns NULL).

**Gold SQL:**

```sql
SELECT T3.cost FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'September Speaker' AND T3.expense_description = 'Posters'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE budget_id IN (SELECT budget_id FROM budget WHERE event_id = (SELECT event_id FROM event WHERE event_name = 'September Speaker') AND category = 'Posters')
```

### Q1403 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `amount_remaining < 0` filter entirely; replaces the ORDER BY on the real amount_remaining column with a manually recomputed, differently-signed expression; also a status case mismatch.

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.event_name 
FROM event e 
JOIN budget b ON e.event_id = b.event_id 
WHERE e.status = 'closed' 
ORDER BY (b.amount_spent - b.amount) DESC 
LIMIT 1
```

### Q1404 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** `is_approved = 1` (integer) used instead of the real stored TEXT value 'true' (verified: expense.is_approved stores the strings 'true'/NULL, not 0/1).

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
SELECT b.category, SUM(e.cost) AS total_value
FROM expense e
JOIN budget b ON e.budget_id = b.budget_id
JOIN event ev ON b.event_id = ev.event_id
WHERE ev.event_name = 'October Meeting' AND e.is_approved = 1
GROUP BY b.category
```

### Q1410 (simple, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Concatenates first_name/last_name into a single "full_name" string instead of returning them as two separate columns like gold, changing the result-set shape (verified the underlying join/filter logic itself matches gold exactly).

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name, SUM(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.member_id = 'rec4BLdZHS2Blfp4v'
```

**Predicted SQL:**

```sql
SELECT m.first_name || ' ' || m.last_name AS full_name, SUM(e.cost) AS total_cost
FROM member m
JOIN expense e ON m.member_id = e.member_id
WHERE m.member_id = 'rec4BLdZHS2Blfp4v'
GROUP BY m.member_id;
```

### Q1422 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Returns budget.category instead of gold's event.type (both real columns, but category answers a different question), via an unnecessary extra join to budget.

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.category FROM budget b JOIN event e ON b.event_id = e.event_id WHERE e.location = 'MU 215'
```

### Q1427 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** `type = 'guest speaker'` (lowercase) vs the real stored value 'Guest Speaker'.

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.category 
FROM budget b 
JOIN event e ON b.event_id = e.event_id 
WHERE e.location = 'MU 215' AND e.type = 'guest speaker' AND b.amount_spent = 0
```

### Q1432 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `position = 'Member'` filter and adds a fabricated `income_source = 'Student_Club'` value (not a real income_source); also inverts which condition lives in the CASE-WHEN numerator vs the WHERE filter.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT (SUM(CASE WHEN T1.t_shirt_size = 'Medium' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS percentage FROM member AS T1 JOIN income AS T2 ON T1.member_id = T2.member_id WHERE T2.amount = 50 AND T2.income_source = 'Student_Club'
```

### Q1435 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** `type='game'`/`status='closed'` (lowercase) vs the real stored values 'Game'/'Closed' (verified: empty result vs gold's 2 rows).

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT event_name FROM event WHERE type = 'game' AND status = 'closed' AND event_date BETWEEN '2019-03-15' AND '2020-03-20'
```

### Q1460 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Splits gold's single exact-match description string 'Water, Veggie tray, supplies' into an IN-list of 3 unrelated lowercase substrings ('water','veggie tray','supplies').

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, e.cost 
FROM member m 
JOIN expense e ON m.member_id = e.member_id 
WHERE e.expense_description IN ('water', 'veggie tray', 'supplies')
```

---

## superhero (29 failures)

### Q723 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue' vs the real stored value 'Blue'.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT s.id) FROM superhero s JOIN colour c ON s.eye_colour_id = c.id JOIN hero_power hp ON s.id = hp.hero_id JOIN superpower p ON hp.power_id = p.id WHERE c.colour = 'blue' AND p.power_name = 'Agility'
```

### Q724 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue'/hair='blond' vs the real stored values 'Blue'/'Blond'.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') AND hair_colour_id = (SELECT id FROM colour WHERE colour = 'blond')
```

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `height_cm IS NOT NULL AND height_cm != 0` filter entirely, including invalid placeholder heights in the ranking.

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Marvel Comics') ORDER BY height_cm DESC
```

### Q728 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** The RANK() OVER (ORDER BY COUNT(...) DESC) window function is missing entirely, replaced by a plain GROUP BY + ORDER BY.

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.colour, COUNT(*) as count FROM superhero s JOIN colour c ON s.eye_colour_id = c.id JOIN publisher p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' GROUP BY c.colour ORDER BY count DESC
```

### Q733 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='gold' vs the real stored value 'Gold'.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM superhero s JOIN colour c ON s.eye_colour_id = c.id JOIN publisher p ON s.publisher_id = p.id WHERE c.colour = 'gold' AND p.publisher_name = 'Marvel Comics'
```

### Q736 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving `= (SELECT MIN(...))` comparison is collapsed to `ORDER BY ... LIMIT 1` (verified: still returns only 1 of gold's 3 tied heroes even after fixing the compounding case-mismatch bug); also 'intelligence' vs real 'Intelligence'.

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE id = (SELECT hero_id FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'intelligence') ORDER BY attribute_value ASC LIMIT 1)
```

### Q738 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attribute_name='durability' vs the real stored value 'Durability' (the EXISTS-vs-JOIN restructuring itself is functionally equivalent).

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_attribute AS T2 INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Durability' AND T2.attribute_value < 50 AND T1.id = T2.hero_id)
```

**Predicted SQL:**

```sql
SELECT s.superhero_name FROM superhero s JOIN hero_attribute ha ON s.id = ha.hero_id JOIN attribute a ON ha.attribute_id = a.id WHERE a.attribute_name = 'durability' AND ha.attribute_value < 50
```

### Q739 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** power_name='death touch' vs the real stored value 'Death Touch'.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Death Touch'
```

**Predicted SQL:**

```sql
SELECT s.superhero_name FROM superhero s JOIN hero_power hp ON s.id = hp.hero_id JOIN superpower p ON hp.power_id = p.id WHERE p.power_name = 'death touch'
```

### Q743 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alignment='Selfish' is an invented value not in the real set (Good/Bad/Neutral/N/A); gold's actual value is 'Bad'.

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.alignment = 'Selfish' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T2.id), SUM(CASE WHEN T1.alignment = 'Selfish' AND T3.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM alignment AS T1 JOIN superhero AS T2 ON T1.id = T2.alignment_id JOIN publisher AS T3 ON T2.publisher_id = T3.id
```

### Q744 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'DC' used instead of the real value 'DC Comics'; also the required publisher_with_more_superheroes name column is omitted from the SELECT list entirely.

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
SELECT (SUM(CASE WHEN T.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) - SUM(CASE WHEN T.publisher_name = 'DC' THEN 1 ELSE 0 END)) AS difference FROM superhero AS S JOIN publisher AS T ON S.publisher_id = T.id
```

### Q750 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `weight_kg > 0` filter entirely, including invalid placeholder weights in the average.

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero WHERE gender_id = (SELECT id FROM gender WHERE gender = 'Female')
```

### Q753 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** `eye_colour_id IS NULL` used instead of joining to colour and filtering on the real lookup value 'No Colour' (a genuine row in the colour table, not a NULL FK).

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE height_cm BETWEEN 170 AND 190 AND eye_colour_id IS NULL
```

### Q758 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Missing DISTINCT causes duplicate hair-colour rows for heroes sharing the same height/race/colour.

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT T2.colour FROM superhero AS T1 JOIN colour AS T2 ON T1.hair_colour_id = T2.id WHERE T1.height_cm = 185 AND T1.race_id = (SELECT id FROM race WHERE race = 'Human')
```

### Q766 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attribute_name='strength' vs the real stored value 'Strength' (the tie-preserving MAX-subquery pattern is otherwise correctly preserved, unlike Q736).

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT T1.full_name FROM superhero AS T1 JOIN hero_attribute AS T2 ON T1.id = T2.hero_id JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'strength' AND T2.attribute_value = (SELECT MAX(attribute_value) FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'strength'))
```

### Q769 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Orders by a COUNT of matching Durability hero_attribute rows (0 or 1) instead of the actual Durability attribute value, so it doesn't find the highest-durability hero at all.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Dark Horse Comics') ORDER BY (SELECT COUNT(*) FROM hero_attribute WHERE hero_id = superhero.id AND attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'Durability')) DESC LIMIT 1
```

### Q772 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT returns joined colour NAMES (c1.colour, c2.colour, c3.colour) instead of gold's raw eye/hair/skin_colour_id FK integers.

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT c1.colour AS eye_colour, c2.colour AS hair_colour, c3.colour AS skin_colour
FROM superhero s
JOIN gender g ON s.gender_id = g.id
JOIN colour c1 ON s.eye_colour_id = c1.id
JOIN colour c2 ON s.hair_colour_id = c2.id
JOIN colour c3 ON s.skin_colour_id = c3.id
JOIN publisher p ON s.publisher_id = p.id
WHERE g.gender = 'Female' AND p.publisher_name = 'Dark Horse Comics'
```

### Q775 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Joins colour via eye_colour_id instead of gold's skin_colour_id — two different real FK columns on superhero.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'Female' AND T3.colour = 'Blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM gender AS T1 JOIN superhero AS T2 ON T1.id = T2.gender_id JOIN colour AS T3 ON T3.id = T2.eye_colour_id
```

### Q781 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='amber' vs the real stored value 'Amber'.

**Gold SQL:**

```sql
SELECT T1.height_cm FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T2.colour = 'Amber'
```

**Predicted SQL:**

```sql
SELECT height_cm FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'amber')
```

### Q782 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='black' vs the real stored value 'Black' (the join-condition restructuring itself is functionally equivalent to gold's).

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'black') AND hair_colour_id = (SELECT id FROM colour WHERE colour = 'black')
```

### Q786 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** attribute_name='strength' vs the real stored value 'Strength' (the correlated MAX subquery is otherwise a valid, equivalent restructuring of gold's).

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
SELECT COUNT(DISTINCT ha.hero_id) 
FROM hero_attribute ha 
JOIN attribute a ON ha.attribute_id = a.id 
WHERE a.attribute_name = 'strength' AND ha.attribute_value = (
    SELECT MAX(attribute_value) 
    FROM hero_attribute 
    WHERE attribute_id = a.id
)
```

### Q788 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Gold's `publisher='Marvel Comics'` condition lives inside the numerator's CASE-WHEN (with an unconditional Female-only denominator via LEFT JOIN); pred moves it into a hard WHERE filter instead, inverting which ratio is computed (%Marvel-among-Female vs %Female-among-Marvel).

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM gender AS T1 JOIN superhero AS T2 ON T1.id = T2.gender_id JOIN publisher AS T3 ON T2.publisher_id = T3.id WHERE T3.publisher_name = 'Marvel Comics'
```

### Q791 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Drops the `height_cm > 0` filter entirely, including invalid placeholder heights in the average.

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### Q794 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Substitutes hero_power+superpower (a boolean powers list) for gold's hero_attribute+attribute (numeric stats), confusing "has the Speed power" with "has a Speed stat value" (and hero_power has no attribute_value column at all).

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE id = (SELECT hero_id FROM hero_power WHERE power_id = (SELECT id FROM superpower WHERE power_name = 'Speed') ORDER BY attribute_value DESC LIMIT 1)
```

### Q797 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue'/'brown' vs the real stored values 'Blue'/'Brown'.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') AND hair_colour_id = (SELECT id FROM colour WHERE colour = 'brown')
```

### Q800 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour='blue' vs the real stored value 'Blue'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.colour = 'blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM superhero AS T1 JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

### Q819 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** `eye_colour_id IS NULL` incorrectly stands in for a specific real colour id (colour.id=1); also drops the `weight_kg = 0 OR` half of gold's OR condition, keeping only the IS NULL half; and lowercase 'blue'.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT (SELECT COUNT(*) FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue') AND weight_kg IS NULL) - (SELECT COUNT(*) FROM superhero WHERE eye_colour_id IS NULL AND weight_kg IS NULL) AS difference
```

### Q822 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alignment='villain' is an invented value not in the real set (Good/Bad/Neutral/N/A); gold's actual value is 'Bad'; also colour='green' lowercase mismatch.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM superhero JOIN colour ON superhero.skin_colour_id = colour.id JOIN alignment ON superhero.alignment_id = alignment.id WHERE colour.colour = 'green' AND alignment.alignment = 'villain'
```

### Q825 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** T3.gender (superhero) referenced instead of the already-joined T4.gender (gender table) — an alias mixup.

**Gold SQL:**

```sql
SELECT T4.gender FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.power_name = 'Phoenix Force'
```

**Predicted SQL:**

```sql
SELECT T3.gender FROM hero_power AS T1 JOIN superpower AS T2 ON T1.power_id = T2.id JOIN superhero AS T3 ON T1.hero_id = T3.id JOIN gender AS T4 ON T3.gender_id = T4.id WHERE T2.power_name = 'Phoenix Force'
```

### Q829 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** 'DC' used instead of the real value 'DC Comics'; also omits the required publisher_with_more_superheroes name column from the SELECT list.

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
SELECT (SUM(CASE WHEN T2.publisher_name = 'DC' THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END)) AS difference FROM superhero AS T1 JOIN publisher AS T2 ON T1.publisher_id = T2.id
```

---

## thrombosis_prediction (46 failures)

### Q1149 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' and admission_type='inpatient'/'outpatient' used instead of the real codes 'M' and '+'/'-'; the aggregate formula itself also differs from gold's in/out ratio approach.

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN admission_type = 'inpatient' THEN 1 ELSE 0 END) - SUM(CASE WHEN admission_type = 'outpatient' THEN 1 ELSE 0 END)) * 100.0 / COUNT(*) AS deviation_percentage
FROM 
    Patient
WHERE 
    sex = 'male'
```

### Q1150 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' used instead of the real code 'F'.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'female' AND birthday > '1930-12-31' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient
```

### Q1152 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type='Inpatient'/'Outpatient' used instead of the real codes '+'/'-'.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) AS REAL) / SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END) AS inpatient_to_outpatient_ratio FROM Patient WHERE diagnosis = 'SLE'
```

### Q1155 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Threshold lactate_dehydrogenase > 250 used instead of gold's actual threshold of 500.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.lactate_dehydrogenase > 250
```

### Q1156 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses thrombosis_degree > 0 instead of gold's russell_viper_venom_time = '+' — two entirely different real columns (RVVT vs thrombosis degree).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT P.ID, (strftime('%Y', 'now') - strftime('%Y', P.birthday)) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Examination E ON P.ID = E.ID
WHERE E.thrombosis_degree > 0
```

### Q1157 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree = 'severe' used instead of the real integer value 2 (thrombosis_degree is stored as an integer scale 0-3, not a text severity label).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.diagnosis FROM Patient P JOIN Examination E ON P.ID = E.ID WHERE E.thrombosis_degree = 'severe'
```

### Q1162 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses first_hospital_visit_date (Patient."First Date") instead of gold's Description column (mapped to first_record_date) — two different real columns; also sex/admission_type values are mistranslated.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE sex = 'female' AND first_hospital_visit_date LIKE '1997%' AND admission_type = 'outpatient'
```

### Q1164 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces the fixed condition Thrombosis = 1 with a dynamically-computed = (SELECT MAX(thrombosis_degree)...) — an entirely different, non-equivalent condition; also sex='Female' mistranslation.

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
SELECT COUNT(*) FROM Examination e JOIN Patient p ON e.ID = p.ID WHERE e.examination_date LIKE '1997%' AND e.thrombosis_degree = (SELECT MAX(thrombosis_degree) FROM Examination WHERE examination_date LIKE '1997%') AND p.sex = 'Female'
```

### Q1166 (simple, retrieval) — **Nesting problem** (Wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** Gold's UNION (handling the edge case where the eldest patient has no recorded symptoms) is missing entirely, replaced with a simple ORDER BY examination_date ASC LIMIT 1.

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
ORDER BY E.examination_date ASC 
LIMIT 1
```

### Q1169 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male'/'female' used instead of the real codes 'M'/'F'; additionally, the per-sex uric-acid thresholds (8.0 for M, 6.5 for F) are collapsed into a single unrelated > 7.0 filter.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN T1.sex = 'male' THEN 1 ELSE 0 END) * 1.0 / SUM(CASE WHEN T1.sex = 'female' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM Patient AS T1
JOIN Laboratory AS T2 ON T1.ID = T2.ID
WHERE T2.uric_acid > 7.0
```

### Q1175 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses Examination.diagnosis instead of gold's Patient.Diagnosis (two different real columns with the same name on different tables); also adds an unwarranted month-day adjustment to the age calculation that gold's simpler year-difference formula doesn't have.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT (strftime('%Y', L.Date) - strftime('%Y', P.birthday)) - (strftime('%m-%d', L.Date) < strftime('%m-%d', P.birthday)) AS age, E.diagnosis 
FROM Laboratory L 
JOIN Patient P ON L.ID = P.ID 
JOIN Examination E ON L.ID = E.ID 
ORDER BY L.hemoglobin DESC 
LIMIT 1
```

### Q1179 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses first_hospital_visit_date instead of gold's Description/first_record_date column; also the SELECT returns 2 extra unrequested columns (anticardiolipin_igg, anticardiolipin_iga) beyond gold's single anticardiolipin_igm target.

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT T1.anticardiolipin_igg, T1.anticardiolipin_igm, T1.anticardiolipin_iga 
FROM Examination AS T1 
JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T2.diagnosis = 'SLE' AND T2.first_hospital_visit_date = '1994-02-19' AND T1.examination_date = '1993-11-12'
```

### Q1185 (challenging, aggregate) — **Other**

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's SUM-based conditional aggregation with a raw self-join arithmetic (L1.total_cholesterol - L2.total_cholesterol)/L1.total_cholesterol, which can yield multiple mismatched rows instead of one aggregated value if the patient has multiple lab records in either month.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT (L1.total_cholesterol - L2.total_cholesterol) / L1.total_cholesterol AS decrease_rate
FROM Patient P
JOIN Laboratory L1 ON P.ID = L1.ID AND strftime('%Y-%m', L1.Date) = '1981-11'
JOIN Laboratory L2 ON P.ID = L2.ID AND strftime('%Y-%m', L2.Date) = '1981-12'
WHERE P.birthday = '1959-02-18'
```

### Q1187 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses aspartate_aminotransferase (GOT) instead of gold's alanine_aminotransferase (GPT) — two different real lab columns.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID FROM Patient P JOIN Laboratory L ON P.ID = L.ID WHERE L.Date BETWEEN '1987-07-06' AND '1996-01-31' AND L.aspartate_aminotransferase > 30 AND L.albumin < 4 ORDER BY P.ID
```

### Q1189 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** The averaging subquery drops the Thrombosis=2 AND ANA Pattern='S' filters that gold's subquery retains, computing the average across ALL exams instead of just the matching subset.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT E.ID) 
FROM Examination E 
JOIN Laboratory L ON E.ID = L.ID 
WHERE E.thrombosis_degree = 2 
AND E.antinuclear_antibody_pattern = 'S' 
AND E.anticardiolipin_igm > (SELECT AVG(anticardiolipin_igm) * 1.2 FROM Examination)
```

### Q1192 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** admission_type='outpatient' used instead of the real code '-'; also substitutes an invented "normal range" BETWEEN 0.2 AND 1.2 for gold's simple < 2.0 threshold.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE P.admission_type = 'outpatient'
AND strftime('%Y-%m', L.Date) = '1991-10'
AND L.total_bilirubin BETWEEN 0.2 AND 1.2
```

### Q1195 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' used instead of the real code 'F'.

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(L.albumin) 
FROM Laboratory L 
JOIN Patient P ON L.ID = P.ID 
WHERE P.sex = 'female' AND L.platelet_count > 400 AND P.diagnosis = 'SLE'
```

### Q1198 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' used instead of the real code 'F'.

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE sex = 'female' AND diagnosis = 'APS'
```

### Q1201 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='Female' used instead of the real code 'F'.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = 'Female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE birthday LIKE '1980%' AND diagnosis = 'RA'
```

### Q1205 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's sex-conditional threshold (F: >6.5, M: >8.0, requiring a join to Patient) with a single generic "normal range" BETWEEN 3.5 AND 7.2 that ignores the patient's sex entirely.

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN uric_acid BETWEEN 3.5 AND 7.2 THEN 'true' ELSE 'false' END AS is_uric_acid_normal FROM Laboratory WHERE ID = 57266
```

### Q1208 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' used instead of the real code 'M'; also threshold >40 used instead of gold's >=60.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'male' AND L.alanine_aminotransferase > 40
```

### Q1209 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Threshold alanine_aminotransferase > 40 used instead of gold's >= 60.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT P.diagnosis FROM Patient P JOIN Laboratory L ON P.ID = L.ID WHERE L.alanine_aminotransferase > 40 ORDER BY P.birthday ASC
```

### Q1220 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN 18 AND 20 used instead of gold's exact = 29 (an invented range that doesn't even overlap the real target value).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.urea_nitrogen BETWEEN 18 AND 20
```

### Q1225 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Substitutes an invented "abnormal range" < 1.2 OR > 1.9 for gold's simple >= 2.0 threshold.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT Patient.sex, COUNT(*) as count
FROM Patient
JOIN Laboratory ON Patient.ID = Laboratory.ID
WHERE Laboratory.total_bilirubin < 1.2 OR Laboratory.total_bilirubin > 1.9
GROUP BY Patient.sex
```

### Q1227 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'male' used instead of the real code 'M'; additionally the fixed T-CHO >= 250 threshold is replaced with a dynamically-computed > AVG(total_cholesterol) condition.

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(strftime('%Y', 'now') - strftime('%Y', P.birthday)) AS average_age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE P.sex = 'male' AND L.total_cholesterol > (SELECT AVG(total_cholesterol) FROM Laboratory)
```

### Q1229 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Threshold triglyceride > 150 used instead of gold's >= 200; also adds an unwarranted month-day adjustment to the age calculation gold's simpler formula doesn't have.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.triglyceride > 150 AND (strftime('%Y', 'now') - strftime('%Y', P.birthday)) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) > 50
```

### Q1231 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' used instead of the real code 'M'; also CPK threshold >195 used instead of gold's >=250.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Patient P JOIN Laboratory L ON P.ID = L.ID WHERE P.sex = 'male' AND P.birthday BETWEEN '1936-01-01' AND '1956-12-31' AND L.creatinine_phosphokinase > 195
```

### Q1232 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Substitutes invented "abnormal reference ranges" (glucose<65 OR >100, cholesterol BETWEEN 120 AND 200) for gold's simple fixed thresholds (glucose>=180, cholesterol<250).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex, strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.blood_glucose < 65 OR L.blood_glucose > 100
AND L.total_cholesterol >= 120 AND L.total_cholesterol <= 200
```

### Q1235 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Replaces gold's fixed RBC < 3.5 threshold with a dynamic < AVG(...) condition; also drops the Diagnosis column from the SELECT list entirely.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT P.ID, (strftime('%Y', 'now') - strftime('%Y', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.red_blood_cell_count < (SELECT AVG(red_blood_cell_count) FROM Laboratory)
```

### Q1238 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** hemoglobin BETWEEN 13.5 AND 17.5 used instead of gold's BETWEEN 10 AND 17 — an invented clinical reference range instead of the actual specified bounds.

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.ID, P.sex FROM Patient P JOIN Laboratory L ON P.ID = L.ID WHERE P.diagnosis = 'SLE' AND L.hemoglobin BETWEEN 13.5 AND 17.5 ORDER BY P.birthday ASC LIMIT 1
```

### Q1239 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Threshold hematocrit > 45 used instead of gold's >= 52.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT P.ID, (strftime('%Y', 'now') - strftime('%Y', P.birthday)) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.hematocrit > 45
GROUP BY P.ID
HAVING COUNT(*) >= 2
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Thresholds 150000/450000 assume a different unit scale than the real stored platelet_count values, which only range 5-5844 (verified); gold's actual thresholds are 100/400.

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN platelet_count < 150000 THEN 1 ELSE 0 END) AS lower_than_normal,
    SUM(CASE WHEN platelet_count > 450000 THEN 1 ELSE 0 END) AS higher_than_normal
FROM 
    Laboratory
```

### Q1242 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** platelet_count range 150000-450000 used instead of gold's actual-scale 100-400 (same unit-scale mismatch as Q1241).

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE strftime('%Y', L.Date) = '1984' 
AND (strftime('%Y', 'now') - strftime('%Y', P.birthday)) < 50 
AND L.platelet_count BETWEEN 150000 AND 450000
```

### Q1243 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' used instead of the real code 'F'; threshold >13.0 used instead of gold's >=14.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN P.sex = 'female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE (strftime('%Y', 'now') - strftime('%Y', P.birthday)) > 55 AND L.prothrombin_time > 13.0
```

### Q1247 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' used instead of the real code 'M'; WBC range 4.0-11.0 used instead of gold's 3.5-9.0; fibrinogen threshold 400 used instead of gold's 450.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE P.sex = 'male' AND L.white_blood_cell_count BETWEEN 4.0 AND 11.0 AND (L.fibrinogen < 150 OR L.fibrinogen > 400)
```

### Q1251 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Threshold immunoglobulin_g > 1600 used instead of gold's >= 2000.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.immunoglobulin_g > 1600
```

### Q1252 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_g < 160 used instead of gold's BETWEEN 900 AND 2000 — a completely different, non-overlapping condition.

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
WHERE L.immunoglobulin_g < 160 AND E.symptoms IS NOT NULL
```

### Q1254 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_a < 160 used instead of gold's BETWEEN 80 AND 500.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) FROM Patient P JOIN Laboratory L ON P.ID = L.ID WHERE L.immunoglobulin_a < 160 AND P.first_hospital_visit_date > '1990-01-01'
```

### Q1255 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** immunoglobulin_m > 150 used instead of gold's <= 40 OR >= 400 (a single threshold instead of the OR-range spanning both low and high abnormal values).

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.diagnosis, COUNT(*) as count FROM Patient P JOIN Laboratory L ON P.ID = L.ID WHERE L.immunoglobulin_m > 150 GROUP BY P.diagnosis ORDER BY count DESC LIMIT 1
```

### Q1256 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Substitutes "CRP is NULL/unrecorded" for gold's CRP = '+' (a positive qualitative marker) — an inverted/wrong condition; also drops the Description IS NULL filter entirely.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE ID NOT IN (SELECT ID FROM Laboratory WHERE c_reactive_protein IS NOT NULL)
```

### Q1257 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Threshold creatinine > 1.2 used instead of gold's >= 1.5.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) FROM Patient P JOIN Laboratory L ON P.ID = L.ID WHERE L.creatinine > 1.2 AND (strftime('%Y', 'now') - strftime('%Y', P.birthday)) < 70
```

### Q1265 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** Laboratory (needed for the RNP/anti_ribonuclear_protein column gold filters on) is missing entirely; substitutes Examination instead, which has no such column.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE E.anti_ribonuclear_protein = 'normal' AND P.admission_type IS NOT NULL
```

### Q1267 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_sm='normal' doesn't match the real coded values ('negative'/'0'/numeric codes, verified); also the thrombosis_degree IS NULL check on a per-row JOIN doesn't replicate gold's "MAX degree across all exams = 0" aggregation logic.

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
JOIN Examination E ON P.ID = E.ID 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.anti_sm = 'normal' AND E.thrombosis_degree IS NULL
```

### Q1270 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_scl70='normal' and sex='female' don't match the real coded values ('negative'/'0', 'F'); also the per-row symptoms IS NULL JOIN check doesn't replicate gold's NOT EXISTS (requiring no exam row at all has symptoms).

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
JOIN Examination E ON P.ID = E.ID 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.anti_scl70 = 'normal' AND P.sex = 'female' AND E.symptoms IS NULL
```

### Q1275 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_centromere='normal'/anti_ssb='normal'/sex='male' don't match the real coded values ('negative'/'0', 'M').

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.anti_centromere = 'normal' AND L.anti_ssb = 'normal' AND P.sex = 'male'
```

### Q1281 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses MIN(birthday) (the oldest patient) instead of gold's ORDER BY birthday DESC LIMIT 1 (the youngest patient) — inverted logic; also wrong threshold (40 vs gold's 60) and an extra unwarranted OR condition on alanine_aminotransferase.

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(P.birthday) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.aspartate_aminotransferase > 40 OR L.alanine_aminotransferase > 40
```

---

## toxicology (36 failures)

### Q197 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='O' (should be lowercase 'o') and bond_type='single' (should be '-') — both real columns, wrong/invented literal representations of the actual cryptic codes.

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(oxygen_count) FROM (SELECT COUNT(*) AS oxygen_count FROM atom WHERE element = 'O' AND molecule_id IN (SELECT molecule_id FROM bond WHERE bond_type = 'single') GROUP BY molecule_id)
```

### Q198 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='single' vs real '-'; label='carcinogenic' vs real '+'.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(single_bonds) FROM (SELECT COUNT(b.bond_id) AS single_bonds FROM bond b JOIN molecule m ON b.molecule_id = m.molecule_id WHERE b.bond_type = 'single' AND m.label = 'carcinogenic' GROUP BY m.molecule_id)
```

### Q200 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT returns molecule.label ('+'/'-' only) instead of gold's molecule_id, collapsing the per-molecule listing into at most 2 rows; also bond_type/label values are invented English words instead of the real symbol codes.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label FROM molecule m JOIN bond b ON m.molecule_id = b.molecule_id WHERE b.bond_type = 'triple' AND m.label LIKE '%carcinogenic%'
```

### Q201 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Routes atom->connected->bond (restricting to atoms that are direct participants in a matching bond) instead of gold's direct atom->bond join on molecule_id (which counts ALL atoms in any molecule containing that bond type); also element/bond_type values are wrong case/word.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.atom_id) 
FROM atom AS T1 
JOIN connected AS T2 ON T1.atom_id = T2.atom_id 
JOIN bond AS T3 ON T2.bond_id = T3.bond_id 
WHERE T3.bond_type = 'double'
```

### Q206 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.label = 'TR004_8_9' (label only ever holds '+'/'-') instead of the real connected.bond_id = 'TR004_8_9'.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id JOIN bond AS T3 ON T2.bond_id = T3.bond_id JOIN molecule AS T4 ON T3.molecule_id = T4.molecule_id WHERE T4.label = 'TR004_8_9'
```

### Q207 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='double' vs the real symbol code '='.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = 'double'
```

### Q208 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='H' vs the real lowercase code 'h'.

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT m.label FROM molecule m JOIN atom a ON m.molecule_id = a.molecule_id WHERE a.element = 'H' GROUP BY m.label ORDER BY COUNT(*) DESC LIMIT 1
```

### Q212 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving `HAVING COUNT(*) = (SELECT MIN(cnt)...)` pattern (returns ALL tied elements) is collapsed to `ORDER BY COUNT(*) ASC LIMIT 1`; also uses an incorrect `NOT IN (label='carcinogenic')` filter instead of directly filtering label='-'.

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
SELECT element FROM atom WHERE molecule_id NOT IN (SELECT molecule_id FROM molecule WHERE label = 'carcinogenic') GROUP BY element ORDER BY COUNT(*) ASC LIMIT 1
```

### Q215 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Routes through connected (restricting to atoms directly participating in a matching bond) instead of gold's molecule-level `molecule_id IN (...)` inclusion (which counts ALL atoms in any molecule containing that bond type); also element/bond_type values are translated English words instead of the real codes.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN T1.element = 'iodine' THEN 1 ELSE 0 END) AS iodine_count, SUM(CASE WHEN T1.element = 'sulfur' THEN 1 ELSE 0 END) AS sulfur_count FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = 'single'
```

### Q218 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='fluorine' used instead of the real code 'f'; label='carcinogenic' instead of the real code '+'; the calculation also shifts from per-molecule to per-atom counting.

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element != 'fluorine' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'carcinogenic'
```

### Q219 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** The ratio direction is inverted (computes percent of triple bonds within carcinogenic-labeled molecules' bonds, instead of gold's percent of '+'-labeled molecules among those containing a triple bond); also wrong literal values ('carcinogenic'/'triple' instead of '+'/'#').

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'carcinogenic'
```

### Q220 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Treats 'TR000' as a label value via a subquery (molecule.label = 'TR000'), but label never holds ID-shaped strings; gold simply compares molecule_id = 'TR000' directly.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR000') ORDER BY element LIMIT 3
```

### Q226 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='double' vs real '='; also missing the ROUND(...,5) wrapper, causing more decimal places than gold's rounded value.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.bond_type = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM molecule AS T1 JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = 'TR008'
```

### Q227 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label='carcinogenic' vs real '+'; also missing the ROUND(...,3) wrapper.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN label = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM molecule
```

### Q228 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.label = 'TR206' instead of molecule_id = 'TR206' (label never holds ID-shaped strings); also element='H' vs real 'h'.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR206'
```

### Q230 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.label = 'TR060' instead of molecule_id = 'TR060'; also adds an unnecessary join to connected that can duplicate atom rows.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT T1.element, T3.label FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id JOIN molecule AS T3 ON T1.molecule_id = T3.molecule_id WHERE T3.label = 'TR060'
```

### Q231 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Uses molecule.label = 'TR010' instead of molecule_id = 'TR010' to identify the molecule (label never holds ID-shaped strings).

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT bond_type FROM bond WHERE molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR010') GROUP BY bond_type ORDER BY COUNT(*) DESC LIMIT 1
```

### Q232 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** molecule.carcinogenic doesn't exist anywhere in the schema (molecule only has molecule_id and label) — a genuinely hallucinated column.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT m.label FROM molecule m JOIN bond b ON m.molecule_id = b.molecule_id WHERE b.bond_type = 'single' AND m.carcinogenic = 0 ORDER BY m.label LIMIT 3
```

### Q234 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.label = 'TR009' instead of molecule_id = 'TR009'; also uses the plain integer 12 instead of the real compound atom_id string 'TR009_12', and drops DISTINCT.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected c JOIN bond b ON c.bond_id = b.bond_id JOIN molecule m ON b.molecule_id = m.molecule_id WHERE (c.atom_id = 12 OR c.atom_id2 = 12) AND m.label = 'TR009'
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Uses raw atom_id = 19 instead of gold's SUBSTR(atom_id, -2) = '19' trailing-number extraction (atom_id is a compound string like 'TR000_19', not a plain integer, so the equality never matches).

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected WHERE atom_id = 19 OR atom_id2 = 19
```

### Q240 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.label = 'TR004' instead of the real molecule_id = 'TR004' (gold uses molecule_id directly, no join to molecule needed at all).

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR004'
```

### Q242 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT returns molecule.label instead of gold's molecule_id; additionally, atom_id is compared as a plain integer BETWEEN 21 AND 25 instead of gold's SUBSTR(atom_id,-2) BETWEEN '21' AND '25' trailing-number extraction, and label='carcinogenic' is an invented value.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label FROM molecule m JOIN atom a ON m.molecule_id = a.molecule_id WHERE a.atom_id BETWEEN 21 AND 25 AND m.label = 'carcinogenic'
```

### Q243 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element = 'P'/'N' (uppercase) used instead of the real lowercase codes 'p'/'n'.

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
WHERE (a1.element = 'P' AND a2.element = 'N') OR (a1.element = 'N' AND a2.element = 'P')
```

### Q244 (moderate, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** Gold's tie-preserving `cnt = (SELECT MAX(cnt) FROM sub)` pattern (returns ALL molecules tied for the max double-bond count) is collapsed to `ORDER BY COUNT(*) DESC LIMIT 1`; also bond_type='double' vs real '='.

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
SELECT m.label FROM molecule m JOIN bond b ON m.molecule_id = b.molecule_id WHERE b.bond_type = 'double' GROUP BY m.molecule_id ORDER BY COUNT(b.bond_id) DESC LIMIT 1
```

### Q245 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='iodine' used instead of the real code 'i'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) FROM (SELECT COUNT(DISTINCT c.bond_id) AS bond_count FROM atom a JOIN connected c ON a.atom_id = c.atom_id WHERE a.element = 'iodine' GROUP BY a.atom_id)
```

### Q247 (challenging, retrieval) — **Nesting problem** (Wrong set operation)

**Outcome:** `wrong_answer` · **Reason:** Adds a `UNION SELECT atom_id2 FROM connected` that gold's reference subquery doesn't have (gold only checks the atom_id column, not atom_id2).

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE atom_id NOT IN (SELECT atom_id FROM connected UNION SELECT atom_id2 FROM connected)
```

### Q248 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.label = 'TR041' instead of molecule_id = 'TR041'; also bond_type='triple' vs the real code '#'.

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT c.atom_id FROM connected c JOIN bond b ON c.bond_id = b.bond_id JOIN molecule m ON b.molecule_id = m.molecule_id WHERE b.bond_type = 'triple' AND m.label = 'TR041'
```

### Q249 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** Filters molecule.label = 'TR144_8_19' (a bond_id-shaped value that label can never hold) instead of gold's connected.bond_id = 'TR144_8_19', and joins entirely the wrong tables (atom+molecule instead of connected+atom).

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'TR144_8_19'
```

### Q253 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='triple' vs the real code '#' (the join structure itself matches gold's, just reordered/realiased).

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = 'triple'
```

### Q255 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Filters atom.element='carcinogen' (an invented value that doesn't correspond to gold's molecule.label='+' concept at all, and isn't even a real element code) instead of properly joining to molecule.label; also bond_type='single' vs the real code '-'.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T1.bond_type = 'single' AND (T2.atom_id IN (SELECT atom_id FROM atom WHERE element = 'carcinogen') OR T2.atom_id2 IN (SELECT atom_id FROM atom WHERE element = 'carcinogen'))
```

### Q260 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='phosphorus'/'bromine' and bond_type='triple' are English translations that don't match the real codes 'p'/'br'/'#'; the query also incorrectly restricts to only p/br atoms that are direct bond participants, rather than counting ALL atoms in qualifying molecules as gold does.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT a.atom_id) 
FROM atom a 
JOIN connected c ON a.atom_id = c.atom_id 
JOIN bond b ON c.bond_id = b.bond_id 
WHERE b.bond_type = 'triple' AND (a.element = 'phosphorus' OR a.element = 'bromine')
```

### Q263 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Routes through connected+bond (restricting to atoms directly participating in a matching bond) instead of gold's molecule_id IN (subquery on bond.molecule_id) inclusion (counting ALL atoms in any molecule containing that bond type); also element='chlorine'/bond_type='single' are wrong translated values.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'chlorine' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN connected AS T2 ON T1.atom_id = T2.atom_id JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = 'single'
```

### Q273 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='chlorine' vs the real code 'cl'; label='carcinogenic' vs the real code '+' (the join structure atom->molecule itself matches gold's).

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'chlorine' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM atom AS T1 JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'carcinogenic'
```

### Q281 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** The correlated subquery's unqualified `molecule_id` reference is ambiguous between the outer atom and molecule aliases, which SQLite rejects outright as "ambiguous column name".

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT m.label, a.element 
FROM molecule m 
JOIN atom a ON m.molecule_id = a.molecule_id 
WHERE a.atom_id = (
    SELECT atom_id 
    FROM connected 
    WHERE molecule_id = m.molecule_id 
    GROUP BY atom_id 
    ORDER BY COUNT(atom_id2) DESC 
    LIMIT 1
) 
AND m.label LIKE '%carcinogenic%'
```

### Q282 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='Hydrogen' vs the real lowercase code 'h' (molecule_id='TR006' is used correctly here, matching gold).

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN element = 'Hydrogen' THEN 1 ELSE 0 END) AS REAL) / COUNT(atom_id) AS ratio, m.label 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE m.molecule_id = 'TR006'
```

### Q327 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** SELECT returns molecule.label instead of gold's molecule_id; also replaces the label='-' filter with an unrelated NOT IN (molecules containing element='C') condition, and uses uppercase 'C' instead of the real lowercase 'c'.

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT m.label FROM molecule m WHERE m.molecule_id NOT IN (SELECT DISTINCT m.molecule_id FROM molecule m JOIN atom a ON m.molecule_id = a.molecule_id WHERE a.element = 'C') AND (SELECT COUNT(*) FROM atom a WHERE a.molecule_id = m.molecule_id) > 5
```

---

