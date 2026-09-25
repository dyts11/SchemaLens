# Qwen2.5-Coder-0.5B · L3·S3 — hand-classified failures (n=383)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. Predicted SQL uses S3 (descriptive snake_case) column names throughout when correctly formed -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. This is the smallest (0.5B) model in the study, so a substantially higher share of failures are Invalid SQL or badly malformed/nonsensical queries than for larger models. Grouped by database, sorted by question id.

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

## california_schools (30 failures)

### Q5 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** school_name is the real S3 alias of frpm.'School Name', but predicted's FROM is schools alone (no join to frpm); also uses school_ownership_code='Virtual' as a substitute for the real Virtual column and misuses AVG() in WHERE

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
SELECT COUNT(*) FROM schools WHERE AVG(school_name) > 400 AND school_ownership_code = 'Virtual';
```

### Q11 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** predicted selects school_code (frpm.'School Code', a different real column) instead of the CDSCode alias (county_district_school_code); both school_code and enrollment_k12 are real only on frpm, but predicted's FROM is schools alone with no join

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT school_code FROM schools WHERE enrollment_k12 > 500;
```

### Q12 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** free_or_reduced_price_meal_count_ages_5_17 (frpm's 'FRPM Count (Ages 5-17)') is real but predicted's FROM is schools alone (no join at all); also references a wholly invented 'SAT_excellent_rate' column with no real counterpart anywhere

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
SELECT MAX(free_or_reduced_price_meal_count_ages_5_17) AS highest_eligible_free_rate
FROM schools
WHERE SAT_excellent_rate > 0.3 AND enrollment_ages_5_17 >= 5;
```

### Q17 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** single-table frpm query borrows charter_number (real on schools) and average_score_writing (real on satscores), neither joined; also compares school_name > 'Writing' and drops gold's RANK() OVER window-function structure entirely

**Gold SQL:**

```sql
SELECT CharterNum, AvgScrWrite, 
RANK() OVER (ORDER BY AvgScrWrite DESC) AS WritingScoreRank 
FROM schools AS T1  INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds 
WHERE T2.AvgScrWrite > 499 AND CharterNum is not null AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS total_count, AVG(school_name) AS avg_score, charter_number, AVG(average_score_writing) AS avg_score_writing, COUNT(*) AS total_rank
FROM frpm
WHERE school_name > 'Writing' AND average_score_writing > 499
GROUP BY charter_number;
```

### Q23 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'street_address' is not a real column or S3 alias anywhere (schools.Street's S3 name is unchanged 'Street', not 'street_address'); also misattributed to the frpm alias rather than schools

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT T1.school_name, T1.street_address
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.enrollment_k12 - T2.enrollment_ages_5_17 > 30;
```

### Q24 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** satscores replaced wholesale by schools (frpm common to both); school_name (a frpm alias) then gets misattributed to the swapped-in schools alias, and number_test_takers (satscores) becomes unreachable

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT T2.school_name FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T1.percent_eligible_free_k12 > 0.1 AND T1.number_test_takers >= 1500;
```

### Q25 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** school_name and county_name are both real on frpm (T2, already joined); predicted misattributes them to the schools alias (T1) instead -- alias mix-up; also misuses AVG() directly in WHERE instead of GROUP BY/HAVING

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
SELECT T1.school_name, T1.funding_type
FROM schools AS T1
JOIN frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.county_name = 'Riverside' AND AVG(T2.average_score_math) > 400;
```

### Q26 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'address' is not a real column or S3 alias anywhere in the schema (the closest real concepts are schools.Street/City/State/Zip individually, not a combined 'address' field)

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT T1.school_name, T1.address FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.state = 'CA' AND T1.free_or_reduced_price_meal_count_ages_5_17 > 800
```

### Q27 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** schools (source of OpenDate/ClosedDate) replaced wholesale by frpm; satscores is common to both, but frpm has no open_date/closed_date columns

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT T1.school_name, AVG(T2.average_score_writing) AS average_score_writing
FROM frpm AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.open_date > '1991-01-01' AND T1.closed_date < '2000-01-01'
GROUP BY T1.school_name;
```

### Q28 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** doc_type is real on schools/T2 (already joined); predicted references T1.doc_type where T1 is frpm -- alias mix-up

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT T1.school_name, T1.doc_type
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.funding_type = 'Local Funded'
GROUP BY T1.school_name, T1.doc_type
HAVING AVG(T1.enrollment_k12 - T1.free_meal_count_ages_5_17) > (SELECT AVG(T1.enrollment_k12) FROM frpm WHERE T1.funding_type = 'Local Funded')
```

### Q31 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** average_score_reading/average_score_math (satscores aliases) are real but predicted's outer query never joins satscores (FROM frpm alone); the 10th/11th-percentile FRPM ranking question is also completely misunderstood

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT AVG(average_score_reading) AS eligible_free_rate_10th, AVG(average_score_math) AS eligible_free_rate_11th
FROM frpm
WHERE county_district_school_code IN (
    SELECT county_district_school_code
    FROM schools
    WHERE school_name = '10th'
        OR school_name = '11th'
)
ORDER BY enrollment_k12 DESC
LIMIT 1;
```

### Q32 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** enrollment_ages_5_17 is real on frpm; used inside a subquery whose FROM is schools alone, with no join to frpm within that subquery's scope

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT AVG(free_or_reduced_price_meal_count_k12) AS eligible_free_or_reduced_price_meal_rate
FROM frpm
WHERE county_district_school_code IN (
    SELECT county_district_school_code
    FROM schools
    WHERE school_ownership_code = 66
    ORDER BY enrollment_ages_5_17 DESC
    LIMIT 5
)
GROUP BY county_district_school_code;
```

### Q36 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** satscores (source of enroll12/NumGE1500) replaced wholesale by frpm; schools is common to both, but neither schools nor frpm has an enrollment_grade_12/enroll12 column

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
SELECT T1.admin_first_name_1, T1.admin_last_name_1, T1.admin_email_1
FROM schools AS T1
JOIN frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.enrollment_grade_12 > 1500
ORDER BY T1.enrollment_grade_12 DESC
LIMIT 1;
```

### Q37 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** SQLite raises 'misuse of aggregate: MIN()' -- a construction bug (MIN() applied to a column, enrollment_ages_5_17, that only exists on frpm inside a subquery scoped to schools alone), not a plain missing-identifier error

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
SELECT T1.street, T1.city, T1.state, T1.zip
FROM schools AS T1
JOIN frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.enrollment_ages_5_17 < (SELECT MIN(enrollment_ages_5_17) FROM schools)
ORDER BY enrollment_ages_5_17 ASC LIMIT 1;
```

### Q39 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** number_test_takers (satscores) is real but predicted's FROM is schools alone, no join; also filters county_district_school_code='FRESNO' (the CDSCode identifier column) instead of the real County='Fresno' column

**Gold SQL:**

```sql
SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'
```

**Predicted SQL:**

```sql
SELECT AVG(number_test_takers) FROM schools WHERE County_district_school_code = 'FRESNO' AND open_date BETWEEN '1980-01-01' AND '1980-12-31'
```

### Q40 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** satscores (source of AvgScrRead ordering) replaced wholesale by frpm; schools is common to both, but Phone (which belongs to the schools alias, T2) is referenced via T1 (frpm)

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.phone FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.school_name = 'Fresno Unified' ORDER BY T1.average_score_reading ASC LIMIT 1
```

### Q41 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** satscores (source of AvgScrRead/rtype) replaced wholesale by frpm; schools is common to both, but the resulting aliases are also crossed (T1/frpm for average_score_reading, T2/schools for school_name); gold's CTE+RANK() OVER top-5-per-county window structure is dropped too

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
SELECT T2.school_name FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code ORDER BY T1.average_score_reading DESC LIMIT 5
```

### Q45 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'charter_school' does not exist as a real column or exact S3 alias anywhere (closest real aliases are is_charter_school/charter_school_number, neither matching); the query also drops the schools table (holding AdmFName1/AdmLName1) entirely, replacing it with frpm

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.AdmFName1 = 'Ricci' AND T2.AdmLName1 = 'Ulrich'
```

**Predicted SQL:**

```sql
SELECT T1.school_name, AVG(T2.average_score_writing) AS average_writing_score
FROM frpm AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.charter_school = 'Ricci Ulrich'
GROUP BY T1.school_name;
```

### Q46 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on status_type='Special School' instead of the intended district_ownership_code=31 (DOC); also restructures the query into a COUNT+GROUP BY aggregation instead of a direct top-1 lookup ordered by enrollment

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS total_enrollments
FROM frpm
WHERE county_district_school_code IN (
    SELECT county_district_school_code
    FROM schools
    WHERE status_type = 'Special School'
)
GROUP BY county_district_school_code
ORDER BY total_enrollments DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** number_scores_1500_or_above (satscores.NumGE1500) is real but predicted's FROM is schools alone with no join; also misuses county_district_school_code (CDSCode identifier) as if it held the county name, and calls the non-SQLite YEAR() function

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(number_scores_1500_or_above) AS monthly_average_opening_count
FROM schools
WHERE county_district_school_code = 'Alameda' AND YEAR(open_date) = 1980;
```

### Q48 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on status_type='Unified School District' instead of the intended district_ownership_code (DOC) 52/54 codes, and misuses county_district_school_code (CDSCode identifier) in place of County='Orange'; also restructures gold's two independent single-table subquery counts into one CASE/SUM ratio with an unnecessary frpm join

**Gold SQL:**

```sql
SELECT CAST((
SELECT COUNT(*) FROM schools 
WHERE County = 'Orange' AND DOC = '54' AND StatusType = 'Merged' AND school is not null) AS REAL) 
/ (SELECT COUNT(*) FROM schools WHERE DOC = '52' AND StatusType = 'Merged' AND school is not null) AS ratio;
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.county_district_school_code = 'Orange County' THEN 1 ELSE 0 END) AS REAL) / COUNT(T1.county_district_school_code) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.status_type = 'Unified School District'
```

### Q50 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted selects T1.Street instead of gold's MailStreet (both real columns on schools, different fields); also uses record_type='Math' instead of 'S' as the filter value and drops the OFFSET 6 (LIMIT 6,1) needed for the 7th-highest score

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
SELECT T1.Street FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.record_type = 'Math' ORDER BY T2.average_score_math DESC LIMIT 1
```

### Q62 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** schools (source of Charter=0) is missing entirely from predicted's single-table frpm query; the Charter filter is dropped along with it

**Gold SQL:**

```sql
SELECT COUNT(T2.School) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.Charter = 0 AND CAST(T1."Free Meal Count (K-12)" AS REAL) * 100 / T1."Enrollment (K-12)" < 0.18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM frpm WHERE county_name = 'Los Angeles' AND percent_eligible_free_k12 < 0.18;
```

### Q72 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted calls YEAR(), a non-SQLite function

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM frpm WHERE county_district_school_code IN (SELECT county_district_school_code FROM schools WHERE district_name = 'Fremont' AND YEAR(open_date) = 2014 AND YEAR(closed_date) = 2015) AND enrollment_ages_5_17 BETWEEN 5 AND 17;
```

### Q77 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'Percent_Eligible_FRPM' doesn't match any real column or S3 alias (frpm's real aliases are percent_eligible_free_or_reduced_price_meal_k12 / ..._ages_5_17); also on the wrong table (single-table schools query, frpm never joined) and uses a bogus Grade_Span_Served BETWEEN 5 AND 9 instead of GSserved='K-9'

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS eligible_schools, AVG(Percent_Eligible_FRPM) AS percentage_eligible
FROM schools
WHERE County = 'Los Angeles' AND Grade_Span_Served BETWEEN 5 AND 9;
```

### Q79 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** gold groups by County to compare San Diego vs. Santa Barbara counts (GROUP BY + ORDER BY COUNT); predicted has no GROUP BY at all, instead building a NOT IN subquery that doesn't perform the comparison, and drops the Virtual='F' filter entirely

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS school_count
FROM schools
WHERE county = 'San Diego' AND county_district_school_code NOT IN (
    SELECT county_district_school_code
    FROM schools
    WHERE county = 'Santa Barbara'
)
ORDER BY school_count DESC
LIMIT 1;
```

### Q82 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** gold orders by ABS(longitude) DESC (furthest from 0, i.e. most negative since CA longitudes are negative); predicted uses raw MAX(longitude) without the ABS() transformation, selecting a different (least-negative) row

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT grade_span_offered FROM schools WHERE longitude = (SELECT MAX(longitude) FROM schools);
```

### Q83 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** schools (source of City, GSoffered, GSserved) replaced wholesale by satscores; frpm is common to both, but City/grade_span_offered/grade_span_served are misattributed to frpm, which lacks them; also splits GSoffered='K-8' into two incorrect literal comparisons

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT 
    T1.city, 
    COUNT(T2.school_code) AS school_count
FROM 
    frpm AS T1
JOIN 
    satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T1.grade_span_offered = 'Kindergarten' AND T1.grade_span_served = '8th Grade'
GROUP BY 
    T1.city;
```

### Q85 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** district_code (frpm) and admin_first_name_1 (schools) have their table aliases crossed -- district_code is referenced via T2/schools and admin_first_name_1 via T1/frpm, exactly backwards from where each column actually lives

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT T2.district_code FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T1.admin_first_name_1 = 'Alusine'
```

### Q87 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'charter_school_type' doesn't match any real column or S3 alias (frpm's real Charter aliases are is_charter_school/charter_school_number/charter_funding_type); the query also substitutes several real-but-wrong-domain frpm charter columns for the intended schools.DOC/SOC filters and uses a wrong City value

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.admin_email_1, T1.admin_email_2
FROM schools AS T1
JOIN frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.County = 'San Bernardino' AND T1.City = 'City of San Bernardino City Unified'
  AND T2.charter_school_number BETWEEN 1 AND 12
  AND T2.charter_funding_type = 'Intermediate/Middle School' AND T2.charter_school_type = 'Unified School';
```

---

## debit_card_specializing (30 failures)

### Q1471 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** currency belongs to customers/T1 (already joined); predicted uses T2.currency (transactions_1k has no currency column) -- alias mix-up on an already-joined table

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.currency = 'CZK' THEN 1 ELSE 0 END) FROM customers AS T1 JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id;
```

### Q1472 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** customers (holding Segment='LAM') dropped wholesale and replaced by transactions_1k; predicted joins yearmonth+transactions_1k instead of gold's customers+yearmonth, losing the segment filter entirely

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.customer_id
FROM yearmonth AS T1
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id
WHERE T1.date LIKE '2012%'
GROUP BY T1.customer_id
ORDER BY SUM(T2.amount) ASC
LIMIT 1;
```

### Q1473 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** predicted references bare 'month' on yearmonth, which has no such column anywhere in the schema (only CustomerID/Date/Consumption)

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consumption) AS average_monthly_consumption
FROM yearmonth
WHERE YEAR(month) = 2013 AND segment = 'SME';
```

### Q1476 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** bare 'currency' used directly on transactions_1k (no JOIN in outer query); currency is real only on customers, which appears solely inside an unrelated ID-membership subquery, not joined to reach it

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS difference
FROM transactions_1k
WHERE customer_id IN (
    SELECT customer_id
    FROM customers
    WHERE segment = 'CZK'
)
AND date BETWEEN '2012-01-01' AND '2012-12-31'
AND currency = 'EUR';
```

### Q1479 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted calls YEAR(), a non-SQLite function

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT YEAR(yearmonth.date) AS year, SUM(transactions_1k.amount) AS total_consumption
FROM yearmonth
JOIN transactions_1k ON yearmonth.customer_id = transactions_1k.customer_id
JOIN gasstations ON transactions_1k.gas_station_id = gasstations.gas_station_id
JOIN products ON transactions_1k.product_id = products.product_id
WHERE products.currency = 'CZK'
GROUP BY YEAR(yearmonth.date)
ORDER BY total_consumption DESC
LIMIT 1;
```

### Q1480 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.yearmonth referenced as a column, but 'yearmonth' is a table name, not a column anywhere in the schema

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.date AS peak_month
FROM yearmonth AS T1
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id
WHERE T1.yearmonth = '2013' AND T1.segment = 'SME'
GROUP BY T1.date
ORDER BY SUM(T2.amount) DESC
LIMIT 1;
```

### Q1481 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** T2.consumption used but T2 is aliased to customers; consumption is real on yearmonth (T1), already joined -- alias mix-up on an already-joined table

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT AVG(T2.consumption) AS average_consumption
FROM yearmonth AS T1
JOIN customers AS T2 ON T1.customer_id = T2.customer_id
WHERE T1.date BETWEEN '2013-01-01' AND '2013-12-31'
GROUP BY T2.segment
HAVING SUM(T1.consumption) = (SELECT SUM(T2.consumption) FROM yearmonth AS T1 WHERE T1.date BETWEEN '2013-01-01' AND '2013-12-31' AND T1.segment IN ('SME', 'LAM', 'LAM', 'KAM'));
```

### Q1482 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** T1.segment referenced (T1 aliased to yearmonth) but Segment is only real on customers, which predicted never joins at all; predicted's join graph (yearmonth+transactions_1k) omits the customers table gold requires

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T2.date BETWEEN '2012-01-01' AND '2013-01-01' THEN T1.consumption * T2.price ELSE 0 END) AS total_consumption_eur
FROM 
    yearmonth AS T1
JOIN 
    transactions_1k AS T2 ON T1.customer_id = T2.customer_id
WHERE 
    T1.segment = 'SME' OR T1.segment = 'LAM' OR T1.segment = 'KAM'
GROUP BY 
    T1.customer_id;
```

### Q1483 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** predicted sources the monthly total from transactions_1k.amount instead of gold's yearmonth.Consumption -- same-role single-table substitution

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_consumption
FROM transactions_1k
WHERE customer_id = 6
  AND strftime('%Y-%m', date) BETWEEN '2013-08' AND '2013-11';
```

### Q1484 (simple, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only gasstations (no join at all); predicted invents a join to customers via a non-existent gasstations.customer_id key and misattributes country to customers instead of the already-present gasstations alias

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T2.chain_id) FROM customers AS T1 INNER JOIN gasstations AS T2 ON T1.customer_id = T2.customer_id WHERE T1.country = 'Czech Republic' AND T2.segment = 'Discount';
```

### Q1486 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** T2.currency used but T2 is aliased to transactions_1k; currency is real on customers (T1), already joined -- alias mix-up

**Gold SQL:**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN T2.currency = 'CZK' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN T2.currency = 'EUR' THEN T1.amount ELSE 0 END) AS difference
FROM customers AS T1
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id
WHERE T1.segment = 'SME';
```

### Q1490 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** predicted sources the >46.73 consumption threshold from transactions_1k.amount instead of gold's yearmonth.Consumption -- same-role table substitution (also INNER vs LEFT JOIN, secondary)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE T1.segment = 'LAM'
```

### Q1493 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** predicted sources the >528.3 consumption threshold from transactions_1k.amount instead of gold's yearmonth.Consumption -- same-role table substitution

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE strftime('%Y', T2.date) = '2012' AND strftime('%m', T2.date) = '02';
```

### Q1498 (simple, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted calls YEAR(), a non-SQLite function

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) FROM yearmonth WHERE YEAR(date) = 2012 AND month = 1;
```

### Q1500 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** T2.description used but T2 is aliased to transactions_1k; description is real on products (T1), already joined -- alias mix-up (also references a non-existent products.segment)

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T1.Date LIKE '2012-08-%'
```

**Predicted SQL:**

```sql
SELECT T2.description FROM products AS T1 INNER JOIN transactions_1k AS T2 ON T1.product_id = T2.product_id WHERE T2.date LIKE '2012-08%' AND T1.segment = 'August';
```

### Q1501 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** predicted joins customers+transactions_1k but never joins gasstations, which gold requires to reach Country; T2.country fails since transactions_1k has no country column

**Gold SQL:**

```sql
SELECT DISTINCT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date LIKE '2012-08-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.country FROM customers AS T1 JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE T2.date LIKE '2012-08%' AND T2.time LIKE '%August%'
```

### Q1505 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** single-table query on customers references bare 'consumption', which is real only on yearmonth and is never joined; filter also substitutes customers.segment='euro' for the intended currency='EUR'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(customer_id) FROM customers WHERE segment = 'euro' AND consumption > 1000;
```

### Q1506 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** T1.chain_id referenced (T1 aliased to transactions_1k, no such column) -- gasstations (which has chain_id/Country) is only used in an unrelated uncorrelated subquery, never actually joined to the outer query

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT T2.description FROM transactions_1k AS T1 INNER JOIN products AS T2 ON T1.product_id = T2.product_id WHERE T1.chain_id = (SELECT chain_id FROM gasstations WHERE country = 'Czech Republic') AND T1.segment = 'Gasoline';
```

### Q1507 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted selects a derived yearmonth.date value instead of gold's transactions_1k.Time; an unnecessary yearmonth join is added while the needed output column (Time) is dropped

**Gold SQL:**

```sql
SELECT DISTINCT T1.Time FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T2.ChainID = 11
```

**Predicted SQL:**

```sql
SELECT DISTINCT strftime('%Y-%m', t2.date) AS transaction_date
FROM transactions_1k t1
JOIN yearmonth t2 ON t1.customer_id = t2.customer_id
JOIN gasstations g ON t1.gas_station_id = g.gas_station_id
WHERE g.chain_id = 11;
```

### Q1509 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** single-table query on transactions_1k references bare 'country', which is real only on gasstations and is never joined

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
SELECT COUNT(transaction_id) FROM transactions_1k WHERE date >= '2012-01-01' AND country = 'Czech Republic'
```

### Q1514 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** T2.currency used but T2 is aliased to transactions_1k; currency is real on customers (T1), already joined -- alias mix-up

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT T2.currency FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE T2.date = '2012-08-24' AND T2.time = '16:25:00';
```

### Q1515 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** date filter malformed as '2012-08-23 21:20:00' (date+time concatenated) instead of gold's plain '2012-08-23'; join-vs-subquery restructuring is a semantically equivalent, vestigial difference

**Gold SQL:**

```sql
SELECT T2.Segment FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.date = '2012-08-23' AND T1.time = '21:20:00'
```

**Predicted SQL:**

```sql
SELECT segment FROM customers WHERE customer_id = (SELECT customer_id FROM transactions_1k WHERE date = '2012-08-23 21:20:00' AND time = '21:20:00')
```

### Q1521 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** single-table query on transactions_1k filters on bare 'segment', which doesn't exist there; the real, needed attribute (Country='CZE', on gasstations) is never joined

**Gold SQL:**

```sql
SELECT COUNT(T1.TransactionID) FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-26' AND T1.Time BETWEEN '08:00:00' AND '09:00:00' AND T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM transactions_1k WHERE date BETWEEN '2012-08-26 08:00:00' AND '2012-08-26 09:00:00' AND segment = 'CZE'
```

### Q1524 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.nationality referenced, but 'nationality' does not exist anywhere in the debit_card_specializing schema

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT T1.nationality FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T2.date = '2012-08-24' AND T2.consumption = 548.4;
```

### Q1525 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** WHERE clause uses T2.currency but T2 is aliased to transactions_1k; currency is real on customers (T1), already joined -- alias mix-up (SELECT list correctly uses T1.currency)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE T2.date LIKE '2012/08/25%' AND T2.currency = 'EUR'
```

### Q1526 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold requires a nested subquery to first identify the target CustomerID (via transactions_1k+gasstations joined on date+price) before aggregating yearmonth by year; predicted has no such subquery and instead filters transactions_1k directly by date/amount with an unrelated computation

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T2.date = '2012-08-25' THEN T1.amount ELSE 0 END) - SUM(T1.amount)) / SUM(T1.amount) * 100 AS consumption_decrease_rate
FROM 
    transactions_1k AS T1
JOIN 
    yearmonth AS T2 ON T1.customer_id = T2.customer_id
WHERE 
    T1.date = '2012-08-25'
    AND T1.amount = 634.8;
```

### Q1528 (simple, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only gasstations (no join, single table); predicted substitutes an unrelated customers+transactions_1k join, omitting gasstations (which holds both Country and the intended Segment='Premium') entirely

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.segment = 'premium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE T1.country = 'SVK'
```

### Q1529 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** gold's conditional aggregation (SUM(CASE WHEN Date LIKE '2012-08%' ...)) for one of two output columns is replaced by a WHERE date filter restricting the whole result set; total_spent also drops the Price multiplication (SUM(amount) vs SUM(amount*price))

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_spent
FROM transactions_1k
WHERE customer_id = 38508
  AND strftime('%Y-%m', date) = '2012-08';
```

### Q1531 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** p.price referenced but p is aliased to products (no Price column there); price is real on transactions_1k (aliased t), already joined -- alias mix-up

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT c.customer_id, SUM(p.price * t.amount) AS total_spent, AVG(p.price) AS avg_price_per_item
FROM customers c
JOIN transactions_1k t ON c.customer_id = t.customer_id
JOIN products p ON t.product_id = p.product_id
GROUP BY c.customer_id
ORDER BY total_spent DESC
LIMIT 1;
```

### Q1533 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T2.consumption_status selected, but 'consumption_status' does not exist anywhere in the schema

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT T2.consumption_status
FROM yearmonth AS T1
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id
WHERE T2.product_id = 5 AND T1.date LIKE '2012-08%'
AND T2.amount > 29.00;
```

---

## european_football_2 (49 failures)

### Q1025 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** name is real on League/T1 (already joined); predicted references T2.name where T2 is Match -- alias mix-up; also uses season=2016 (an integer) instead of the string '2015/2016', and COUNT(*) instead of SUM(goals) for ranking

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.name FROM League AS T1 INNER JOIN Match AS T2 ON T1.id = T2.league_id WHERE T2.season = 2016 GROUP BY T1.name ORDER BY COUNT(*) DESC LIMIT 1
```

### Q1028 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Team+Match (source of team_long_name output and away_team_goal/season data) are both replaced wholesale by Team_Attributes, which has none of league_id/away_team_api_id/away_team_goals/team_name; League also has no season column (that's Match's)

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T2.team_name
FROM League AS T1
JOIN Team_Attributes AS T2 ON T1.id = T2.league_id
WHERE T1.name = 'Scotland Premier League'
  AND T1.season = 2010
  AND T2.away_team_api_id = (SELECT T1.team_api_id FROM League AS T1 INNER JOIN Team_Attributes AS T2 ON T1.id = T2.league_id WHERE T1.name = 'Scotland Premier League' AND T1.season = 2010 AND T2.away_team_api_id IS NOT NULL)
ORDER BY T2.away_team_goals DESC
LIMIT 1;
```

### Q1029 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Team_Attributes+Team (source of buildUpPlaySpeed) are replaced wholesale by Player_Attributes+League, joined via a nonexistent League.player_api_id; build_up_play_speed_class/build_up_play_speed don't exist on Player_Attributes (they're Team_Attributes columns)

**Gold SQL:**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT T2.build_up_play_speed
FROM Player_Attributes AS T1
JOIN League AS T2 ON T1.player_fifa_api_id = T2.player_api_id
WHERE T1.build_up_play_speed_class = 'Top 4'
ORDER BY T1.build_up_play_speed DESC
LIMIT 4;
```

### Q1030 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters Match.stage='Draw' instead of gold's home_team_goal = away_team_goal (the real column-to-column comparison that identifies a drawn match); also uses season=2016 instead of '2015/2016' and drops the GROUP BY/COUNT ranking structure

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT name FROM League WHERE id = (SELECT league_id FROM Match WHERE season = 2016 AND stage = 'Draw') ORDER BY count(*) DESC LIMIT 1
```

### Q1031 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted calls YEAR(), a non-SQLite function

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
SELECT *
FROM Player_Attributes
WHERE sprint_speed >= 97 AND YEAR(date) BETWEEN 2013 AND 2015;
```

### Q1032 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'matches' does not exist anywhere (would need to be computed via COUNT(Match.id) with a join/GROUP BY, which predicted entirely drops); Match is dropped from the query altogether

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT name FROM League ORDER BY matches DESC LIMIT 1
```

### Q1035 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** buildup_play_speed is real on Team_Attributes/T2 (already present, though unnecessarily joined); predicted references T1.buildup_play_speed where T1 is Player_Attributes -- alias mix-up; gold needs only Team_Attributes (single table, no join at all)

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT T2.team_fifa_api_id FROM Player_Attributes AS T1 INNER JOIN Team_Attributes AS T2 ON T1.player_fifa_api_id = T2.player_fifa_api_id WHERE T1.buildup_play_speed BETWEEN 50 AND 60;
```

### Q1036 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** team_long_name is real on Team/T1 (already joined); predicted references T2.team_long_name where T2 is Team_Attributes -- alias mix-up; also filters T1.name='Team A' even though Team has no bare 'name' column, and drops the year=2012/all-teams-average comparison logic

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T2.team_long_name FROM Team AS T1 INNER JOIN Team_Attributes AS T2 ON T1.id = T2.team_fifa_api_id WHERE T1.name = 'Team A' AND T2.buildup_play_passing > (SELECT AVG(T2.buildup_play_passing) FROM Team_Attributes AS T2 WHERE T2.team_fifa_api_id = T1.id AND T1.name = 'Team A')
```

### Q1037 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** gold computes percent left-footed via a CASE-conditional COUNT within an unfiltered join; predicted moves preferred_foot='left' into a blanket WHERE filter instead, changing the numerator/denominator; birthday BETWEEN 1987 AND 1992 also compares a formatted date string to bare year integers

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(T1.player_api_id) AS REAL) * 100 / COUNT(T2.id) FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.preferred_foot = 'left' AND T2.birthday BETWEEN 1987 AND 1992;
```

### Q1039 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'long_shot' (singular) does not exist anywhere; the real column is 'long_shots' (plural, unchanged in S3); the query also drops the Player table entirely, using player_name directly on Player_Attributes where it doesn't exist

**Gold SQL:**

```sql
SELECT AVG(pa.`long_shots`) AS avg_long_shots
FROM `Player` AS p
JOIN `Player_Attributes` AS pa ON p.`player_api_id` = pa.`player_api_id`
WHERE p.`player_name` = 'Ahmed Samir Farag';
```

**Predicted SQL:**

```sql
SELECT AVG(long_shot) FROM Player_Attributes WHERE player_name = 'Ahmed Samir Farag';
```

### Q1040 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** player_name is real on Player/T2 (already joined); predicted references T1.player_name where T1 is Player_Attributes -- alias mix-up; also drops the GROUP BY/AVG aggregation, ordering by a single row's heading_accuracy instead of each player's average

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
SELECT T1.player_name
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T2.height > 180
ORDER BY T1.heading_accuracy DESC
LIMIT 10;
```

### Q1042 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** name is real on League/T1 (already joined); predicted references T2.name where T2 is Match -- alias mix-up; the query is also severely garbled (a nonsensical self-referential subquery, AVG() misused directly in WHERE, and home_goals/away_goals instead of the real home_team_goals/away_team_goals aliases)

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2009/2010' GROUP BY t1.name HAVING (CAST(SUM(t2.home_team_goal) AS REAL) / COUNT(DISTINCT t2.id)) - (CAST(SUM(t2.away_team_goal) AS REAL) / COUNT(DISTINCT t2.id)) > 0
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.name FROM League AS T1 INNER JOIN Match AS T2 ON T1.id = T2.league_id WHERE T1.name IN (
    SELECT T2.league_id FROM League AS T1 INNER JOIN Match AS T2 ON T1.id = T2.league_id WHERE T1.name = '2009/2010'
) AND AVG(T2.home_goals) > AVG(T2.away_goals)
```

### Q1044 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'birthyear'/'birthmonth' do not exist anywhere (the real column is a single 'birthday' date-string field on Player); query also substitutes Player_Attributes for gold's Player table entirely

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE SUBSTR(birthday, 1, 7) = '1970-10'
```

**Predicted SQL:**

```sql
SELECT *
FROM Player_Attributes
WHERE birthyear = 1970 AND birthmonth = 10;
```

### Q1048 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'year' does not exist anywhere in this schema (Player_Attributes.date holds the full date; there's no separate 'year' column on any table); predicted also misattributes the date-based filter to the Player subquery instead of correctly joining Player_Attributes

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Gabriel Tamas' AND strftime('%Y', t2.date) = '2011'
```

**Predicted SQL:**

```sql
SELECT overall_rating FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Gabriel Tamas' AND year = 2011);
```

### Q1057 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** predicted's 'country_id=... AND season=2010 OR season=2011' lacks parentheses, so due to operator precedence it becomes '(country_id=... AND season=2010) OR season=2011', including all matches from season 2011 regardless of country; season values are also stored as range strings like '2010/2011', not bare year integers

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.home_team_goal) AS REAL) / COUNT(t2.id) FROM Country AS t1 INNER JOIN Match AS t2 ON t1.id = t2.country_id WHERE t1.name = 'Poland' AND t2.season = '2010/2011'
```

**Predicted SQL:**

```sql
SELECT AVG(home_team_goals) FROM Match WHERE country_id = (SELECT id FROM Country WHERE name = 'Poland') AND season = 2010 OR season = 2011;
```

### Q1058 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** overall_rating is real on Player_Attributes, not Player; used inside a subquery whose FROM is Player alone, no join; the tallest-vs-shortest UNION comparison logic is also replaced with an unrelated finishing-vs-short_passing CASE comparison

**Gold SQL:**

```sql
SELECT A FROM (SELECT AVG(finishing) result, 'highest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MAX(height) FROM Player) UNION SELECT AVG(finishing) result, 'shortest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MIN(height) FROM Player)) tmp ORDER BY result DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CASE 
    WHEN AVG(finishing) > AVG(short_passing) THEN 'highest'
    ELSE 'shortest'
END AS average_finishing_rate
FROM Player_Attributes
WHERE player_api_id = (SELECT player_api_id FROM Player ORDER BY overall_rating DESC LIMIT 1);
```

### Q1068 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'player_age' does not exist anywhere (there's no computed-age column on Player or Player_Attributes; gold's real filter is height>170, a column predicted has available but doesn't use)

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
SELECT AVG(T1.overall_rating) AS average_overall_rating
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T2.player_age > 170
  AND T1.date BETWEEN '2010-01-01' AND '2015-12-31';
```

### Q1076 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** gold computes a difference between two named players' average ball_control via CASE-conditional aggregation; predicted drops the second player ('Aaron Appindangoye') and the subtraction entirely, just returning the first player's average

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL:**

```sql
SELECT AVG(ball_control) FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Abdou Diallo');
```

### Q1078 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only Player (single table); predicted substitutes Player_Attributes as the outer table (with Player relegated to an ID-lookup subquery), and player_name doesn't exist on Player_Attributes; also orders by Player_Attributes.date DESC instead of Player.birthday ASC

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT player_name
FROM Player_Attributes
WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Aaron Lennon' OR player_name = 'Abdelaziz Barrada')
ORDER BY date DESC
LIMIT 1;
```

### Q1080 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** attacking_work_rate is a categorical text column ('low'/'medium'/'high'); predicted compares it with >0 (a numeric comparison) instead of gold's ='low', changing the predicate's meaning entirely; also uses COUNT(*) instead of COUNT(DISTINCT player_api_id)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate > 0;
```

### Q1084 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'player_birthday' does not exist anywhere (the real column is 'birthday' on Player, which is dropped from the query entirely); 'player_positioning' is also hallucinated (the real 'positioning' column holds numeric ratings, not 'Defensive'/'Attacking' labels -- gold's real filter is defensive_work_rate='high')

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE player_birthday < '1986-01-01' 
  AND (player_positioning = 'Defensive' OR player_positioning = 'Attacking');
```

### Q1088 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Player (source of player_name) and the volleys/dribbling filter columns are effectively replaced by a nonsensical join to Match via T1.player_api_id=T2.home_team_api_id (comparing a player ID to a team ID); volley_score/dribbling_score don't exist anywhere (the real columns are volleys/dribbling on Player_Attributes)

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.player_name FROM Player_Attributes AS T1 INNER JOIN Match AS T2 ON T1.player_api_id = T2.home_team_api_id WHERE T2.volley_score > 70 OR T2.dribbling_score > 70;
```

### Q1091 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'month' does not exist anywhere (there's no separate month column; the real approach is SUBSTR/strftime on the date field, which predicted doesn't use); also uses season=2009 (a bare year) instead of matching the '2009-04' date substring

**Gold SQL:**

```sql
SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND SUBSTR(t2."date", 1, 7) = '2009-04'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Match WHERE league_id = (SELECT id FROM League WHERE name = 'Belgium Jupiler League') AND season = 2009 AND month = 4;
```

### Q1092 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** season is real on Match, not League; predicted's FROM is League alone with no join to Match at all; the filter 'season=2008 AND season=2009' is also self-contradictory

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS match_count FROM Match AS t2 WHERE t2.season = '2008/2009' GROUP BY t2.league_id))
```

**Predicted SQL:**

```sql
SELECT name FROM League WHERE season = 2008 AND season = 2009 GROUP BY name ORDER BY count(*) DESC LIMIT 1;
```

### Q1094 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** overall_rating is real on Player_Attributes/T1 (already joined); predicted references T2.overall_rating where T2 is Player -- alias mix-up; the query also misattributes player_name to T1 instead of T2, and collapses gold's two-CTE latest-rating structure into a self-contradictory WHERE clause plus a boolean comparison instead of a percent-difference

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.overall_rating > T2.overall_rating THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.player_name = 'Ariel Borysiuk' AND T2.player_name = 'Paulin Puel';
```

### Q1096 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** player_name is real on Player, not Player_Attributes; predicted's FROM is Player_Attributes alone with no join at all

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.player_name = 'Pietro Marino'
```

**Predicted SQL:**

```sql
SELECT AVG(overall_rating) FROM Player_Attributes WHERE player_name = 'Pietro Marino';
```

### Q1098 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'classification' does not exist anywhere (the real column is chance_creation_passing_class); the query also routes team identification through a nonsensical Player_Attributes/Player chain treating 'Ajax' as a player_name instead of Team.team_long_name

**Gold SQL:**

```sql
SELECT t2.chanceCreationPassing, t2.chanceCreationPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Ajax' ORDER BY t2.chanceCreationPassing DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(chance_creation_passing) AS highest_chance_creation_passing_score, 
       classification AS classification
FROM Team_Attributes
WHERE team_api_id = (SELECT team_api_id FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Ajax'));
```

### Q1102 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** player_name is real on Player/T2 (already joined); predicted references T1.player_name where T1 is Player_Attributes -- alias mix-up; also uses a malformed date '2016/6/23' instead of '2016-06-23', and orders by Player_Attributes.id instead of Player.birthday

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.player_name
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T1.overall_rating = 77 AND T1.date = '2016/6/23'
ORDER BY T1.id ASC
LIMIT 1;
```

### Q1103 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold uses a direct Player+Player_Attributes join to filter both player_name and date on the same row; predicted replaces this with a Player_Attributes outer query plus a Player subquery that incorrectly references 'date' (not a real Player column), resolving via accidental correlation to the outer Player_Attributes.date instead of being properly paired with the player; the date format is also wrong

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT overall_rating FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Aaron Mooy' AND date = '2016/2/4');
```

### Q1105 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** predicted's date filter uses '2015/5/1' (slash-separated, no zero-padding) instead of gold's '2015-05-01' pattern -- same column (Player_Attributes.date), same intent, just a different/incompatible surface format

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.attacking_work_rate
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T2.player_name = 'Francesco Migliore' AND T1.date = '2015/5/1';
```

### Q1107 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted orders by overall_rating instead of gold's crossing (both real columns on Player_Attributes) to pick which date snapshot to return; also drops the secondary date ASC tiebreak

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT date FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Kevin Constant') ORDER BY overall_rating DESC LIMIT 1;
```

### Q1110 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Team+Team_Attributes (source of team_long_name and buildUpPlayPassingClass) are replaced wholesale by Player_Attributes+League, joined via a nonexistent League.player_api_id; build_up_play_passing_class doesn't exist on League, and the date format is also wrong

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT T2.build_up_play_passing_class FROM Player_Attributes AS T1 INNER JOIN League AS T2 ON T1.player_fifa_api_id = T2.player_api_id WHERE T2.name = 'FC Lorient' AND T1.date = '2010/2/22';
```

### Q1113 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'defense_aggression_class' (American spelling) does not match the real S3 alias 'defence_aggression_class' (British spelling); also uses a nonexistent Team.team_name (real columns are team_long_name/team_short_name)

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT defense_aggression_class FROM Team_Attributes WHERE team_api_id = (SELECT team_api_id FROM Team WHERE team_name = 'Hannover 96') AND date = '2015-09-10';
```

### Q1114 (challenging, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** gold joins Player to Player_Attributes via player_fifa_api_id; predicted joins via player_api_id instead -- same two tables, different join key, which yields a different matched row set/average

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(T1.overall_rating) AS average_overall_rating
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T2.player_name = 'Marko Arnautovic'
  AND T1.date BETWEEN '2007-02-22' AND '2016-04-21';
```

### Q1115 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** overall_rating is real on Player_Attributes/T1 (already joined); predicted references T2.overall_rating where T2 is Player -- alias mix-up; the query also drops the second player (Jordan Bowery) and the percent-difference computation, replacing it with a boolean count-based ratio

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.overall_rating > T2.overall_rating THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.date = '2013-07-12' AND T2.player_name = 'Landon Donovan';
```

### Q1122 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** player_name is real on Player, not Player_Attributes; predicted's FROM is Player_Attributes alone with no join at all

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player_Attributes ORDER BY overall_rating DESC LIMIT 1
```

### Q1124 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** player_name is real on Player/T2 (already joined); predicted references T1.player_name where T1 is Player_Attributes -- alias mix-up; the filter is also entirely wrong/self-contradictory (T1.preferred_foot='left' AND T2.preferred_foot='right' on the same joined player row)

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT T1.player_name
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T1.preferred_foot = 'left' AND T2.preferred_foot = 'right';
```

### Q1130 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Team (source of team_short_name output) is missing entirely, replaced by Player_Attributes joined to Team_Attributes via a nonexistent player_api_id key; chance_creation_passing/_class (real on Team_Attributes/T2, already joined) are also misattributed to the Player_Attributes alias T1

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T2.team_short_name FROM Player_Attributes AS T1 INNER JOIN Team_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.chance_creation_passing > 0 AND T1.chance_creation_passing_class = 'Safe';
```

### Q1133 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** predicted uses player_name='Aaron' (exact match) instead of gold's player_name LIKE 'Aaron%' (prefix match) -- a wrong comparison operator/structure on the same column, likely matching zero or very different rows

**Gold SQL:**

```sql
SELECT COUNT(id) FROM Player WHERE STRFTIME('%Y', birthday) > '1990' AND player_name LIKE 'Aaron%'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player WHERE birthday > '1990-01-01' AND player_name = 'Aaron';
```

### Q1134 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** jumping is real on Player_Attributes/T1 (already present); predicted references T2.jumping where T2 is Player -- alias mix-up; the query also adds an unnecessary Player join and restructures gold's CASE-based self-comparison into a self-contradictory join condition

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1
```

**Predicted SQL:**

```sql
SELECT T2.jumping FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.id = 6 AND T2.id = 23;
```

### Q1135 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted selects player_api_id instead of gold's id -- both real columns on Player_Attributes, but different ones (id is Player_Attributes' own row identifier; player_api_id is the FK to Player)

**Gold SQL:**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT player_api_id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4;
```

### Q1136 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on potential=(MAX potential) instead of gold's crossing=(MAX crossing) -- both real columns on Player_Attributes, wrong one chosen; the preferred_foot='left' condition is also moved into a Player subquery where it doesn't exist, resolving via accidental correlation to the outer table

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Player_Attributes WHERE player_api_id IN (
    SELECT player_api_id FROM Player WHERE preferred_foot = 'left'
) AND potential = (SELECT MAX(potential) FROM Player_Attributes)
```

### Q1139 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'final_score' does not exist anywhere (the real columns are Match.home_team_goal/away_team_goal); the query also substitutes a nonsensical Player_Attributes join for gold's League+Match pair, drops the League name filter, and invents stage='Final'

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT T1.final_score FROM Player_Attributes AS T1 INNER JOIN Match AS T2 ON T1.player_api_id = T2.home_team_api_id WHERE T2.date = '2008-09-24' AND T2.stage = 'Final';
```

### Q1141 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'team_name' does not exist on Team (the real columns are team_long_name/team_short_name, neither renamed to bare 'team_name')

**Gold SQL:**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL:**

```sql
SELECT buildup_play_speed_class FROM Team_Attributes WHERE team_api_id = (SELECT team_api_id FROM Team WHERE team_name = 'KSV Cercle Brugge');
```

### Q1144 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** finishing/curve are real on Player_Attributes/T1 (already joined); predicted references T2.finishing/T2.curve where T2 is Player -- alias mix-up

**Gold SQL:**

```sql
SELECT finishing, curve FROM Player_Attributes WHERE player_api_id IN (SELECT player_api_id FROM Player WHERE weight = (SELECT MAX(weight) from Player))
```

**Predicted SQL:**

```sql
SELECT T2.finishing, T2.curve FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.weight = (SELECT MAX(weight) FROM Player);
```

### Q1145 (simple, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** the SELECT list references 'league.name', but the FROM clause aliases the table as 'l' (League AS l), not 'league' -- an alias that was never introduced; also uses season=2015 instead of '2015/2016' and adds a wrong stage='Final' filter

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT league.name
FROM League AS l
JOIN Match AS m ON l.id = m.league_id
WHERE m.season = 2015 AND m.stage = 'Final'
GROUP BY l.name
ORDER BY COUNT(*) DESC
LIMIT 4;
```

### Q1146 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Match (source of away_team_goal ranking) is replaced wholesale by Player_Attributes, which has none of away_team_api_id/home_team_api_id/shots_on_target as real relationships to Match's concepts; Team's name columns are also wrong (team_name doesn't exist)

**Gold SQL:**

```sql
SELECT t2.team_long_name FROM Match AS t1 INNER JOIN Team AS t2 ON t1.away_team_api_id = t2.team_api_id ORDER BY t1.away_team_goal DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.team_name FROM Player_Attributes AS T1 INNER JOIN Team AS T2 ON T1.away_team_api_id = T2.team_api_id WHERE T1.home_team_api_id = (SELECT T2.id FROM Team AS T2 WHERE T2.name = 'Away Team') ORDER BY T1.shots_on_target DESC LIMIT 1
```

### Q1147 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'overall_strength' does not exist anywhere (the real column is 'overall_rating'; 'strength' is a separate, different real column) -- also referenced on Player, which doesn't have it at all

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT player_name FROM Player WHERE overall_strength = (SELECT MAX(overall_strength) FROM Player_Attributes);
```

### Q1148 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted computes the percentage using T1.strength>70 instead of gold's T2.overall_rating>70 (both real columns on Player_Attributes, but a different metric entirely)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.height < 180;
```

---

## financial (28 failures)

### Q89 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** T2.frequency='POPLATEK PO OBRATU' filter (present in gold) is wholesale dropped from predicted; predicted only filters by district region

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM account WHERE district_id = (SELECT district_id FROM district WHERE region = 'East Bohemia');
```

### Q93 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** gold joins client directly to district (client has district_id); predicted needlessly inserts disp using a nonexistent district.disposition_id join key; district-only columns (number_cities/average_salary) are misattributed to the client alias

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN district AS T3 ON T2.disposition_id = T3.disposition_id WHERE T3.district_name = 'North Bohemia' AND T1.gender = 'Male' AND T1.number_cities > 0 AND T1.average_salary > 8000;
```

### Q94 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** district (source of average_salary/A11) and disp (bridge from account to client) are both missing from predicted's join graph; account.client_id is used as an invalid direct key (account has no client_id)

**Gold SQL:**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.account_id, AVG(T2.average_salary) - MIN(T2.average_salary) AS gap
FROM account AS T1
JOIN client AS T2 ON T1.client_id = T2.client_id
WHERE T2.gender = 'Female'
ORDER BY T1.date DESC
LIMIT 1;
```

### Q95 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** district and disp are both missing from predicted's join graph; account.client_id is used as an invalid direct key (real path is account->disp->client)

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT T1.account_id FROM account AS T1 INNER JOIN client AS T2 ON T1.client_id = T2.client_id WHERE T2.gender = 'Female' ORDER BY T1.average_salary ASC LIMIT 1
```

### Q98 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T2.approved_date selected, but 'approved_date' does not exist anywhere in the schema (loan only has date/duration/payments/status)

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.account_id, T1.district_id, T1.statement_frequency, T1.date
FROM account AS T1
JOIN loan AS T2 ON T1.account_id = T2.account_id
WHERE T2.approved_date = '1997-01-01'
ORDER BY T1.amount ASC
LIMIT 1;
```

### Q100 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gold's district (source of A2='Sokolov') is replaced wholesale by account; client is common to both, but account has no client_id (real path needs disp), and the district filter is dropped entirely

**Gold SQL:**

```sql
SELECT COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'F' AND STRFTIME('%Y', T2.birth_date) < '1950' AND T1.A2 = 'Sokolov'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.client_id) FROM account AS T1 INNER JOIN client AS T2 ON T1.client_id = T2.client_id WHERE T2.gender = 'female' AND T2.birth_date < '1950-01-01'
```

### Q112 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** disp (bridge from client to account) and district (source of district_name/A2) are both missing from predicted's 2-table query; account.client_id is used as an invalid direct key

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
SELECT T2.district_name FROM client AS T1 INNER JOIN account AS T2 ON T1.client_id = T2.client_id WHERE T1.gender = 'Female' AND T1.birth_date = '1976-01-29';
```

### Q115 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** gold joins client directly to district (client has district_id, no account needed); predicted adds an unnecessary account table via a nonexistent client.account_id key, and gender (real on client) is misattributed to the district alias

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'Male' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.district_id) FROM account AS T1 INNER JOIN client AS T2 ON T1.account_id = T2.account_id INNER JOIN district AS T3 ON T1.district_id = T3.district_id WHERE T3.region = 'South Bohemia' AND T3.number_inhabitants = (SELECT MAX(number_inhabitants) FROM district);
```

### Q116 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted references the reserved keyword table `order` unquoted, causing a syntax error (gold correctly double-quotes it)

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.status = 'approved' THEN T2.balance_after_transaction - T1.balance_after_transaction ELSE 0 END) AS REAL) * 100 / SUM(T1.balance_after_transaction) FROM loan AS T1 INNER JOIN order AS T2 ON T1.account_id = T2.account_id WHERE T1.date BETWEEN '1993-07-05' AND '1998-12-27';
```

### Q117 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted references the reserved keyword table `order` unquoted, causing a syntax error

**Gold SQL:**

```sql
SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.amount = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.amount) FROM loan AS T1 INNER JOIN order AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.transaction_type_code = 'loan';
```

### Q118 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** which condition is the WHERE filter vs. which is aggregated is swapped: gold filters on amount<100000 and aggregates status='C'; predicted filters on status='active' (an invented value) and aggregates amount<100000

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.amount < 100000 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.account_id) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE T1.status = 'active';
```

### Q125 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted references the reserved keyword table `order` unquoted, causing a syntax error

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT 
    d.district_name, 
    SUM(CASE WHEN T2.status = 'running' THEN 1 ELSE 0 END) AS running_loans_count,
    SUM(CASE WHEN T2.status = 'running' THEN T2.unemployment_rate_1995 ELSE 0 END) AS running_unemployment_rate_increment
FROM 
    loan AS T1
JOIN 
    order AS T2 ON T1.account_id = T2.account_id
JOIN 
    district AS d ON T2.recipient_bank = d.district_id
WHERE 
    T1.status = 'running'
GROUP BY 
    d.district_name;
```

### Q128 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.number_of_clients selected, but that column does not exist anywhere in the schema -- gold instead needs a COUNT() aggregate with GROUP BY, which predicted drops entirely

**Gold SQL:**

```sql
SELECT T2.A2 FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' GROUP BY T2.district_id, T2.A2 ORDER BY COUNT(T1.client_id) DESC LIMIT 9
```

**Predicted SQL:**

```sql
SELECT T1.district_name FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'Female' ORDER BY T1.number_of_clients DESC LIMIT 9;
```

### Q129 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** district (source of district_name/A2) is never joined; predicted also substitutes loan for gold's trans and references a nonexistent loan.disposition_id

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT T1.district_name FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date LIKE '2023-01%' AND T2.disposition_id NOT IN (SELECT disposition_id FROM disp WHERE type = 'Credit Card') ORDER BY T1.statement_frequency DESC LIMIT 10;
```

### Q136 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** account (source of frequency='POPLATEK MESICNE') is entirely missing from predicted's single-table loan query; the frequency filter is dropped wholesale along with the join

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM loan WHERE date BETWEEN '1995-01-01' AND '1997-12-31' AND amount >= 250000;
```

### Q137 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** loan (source of status IN ('C','D')) is entirely missing from predicted's single-table account query; predicted substitutes an unrelated account.frequency='running' filter for the intended loan.status filter

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(account_id) FROM account WHERE district_id = 1 AND statement_frequency = 'running';
```

### Q138 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted references the reserved keyword table `order` unquoted, causing a syntax error

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A15 = (SELECT T3.A15 FROM district AS T3 ORDER BY T3.A15 DESC LIMIT 1, 1)
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN order AS T2 ON T1.client_id = T2.recipient_client_id WHERE T2.transaction_type_code = 'CRIME' AND T2.date BETWEEN '2023-01-01' AND '2023-12-31' AND T1.gender = 'M' AND T1.birth_date >= '1995-01-01' AND T1.birth_date <= '1995-12-31' AND T1.district_id IN (SELECT district_id FROM district WHERE number_crimes_1995 > 0) ORDER BY T1.number_crimes_1995 DESC LIMIT 1;
```

### Q145 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** gold's trans (transaction records, filtered by operation='VYBER KARTOU') is replaced wholesale by loan; account is common to both, but the operation filter and correct 1998 date range are lost, replaced with an unrelated 2023 range

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.account_id FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.amount < (SELECT AVG(amount) FROM loan WHERE date >= '2023-01-01' AND date <= '2023-12-31')
```

### Q149 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** type is real on disp/T2 (already joined) not account/T1 -- alias mix-up; the query also fabricates dozens of district-only columns (average_salary, unemployment_rate, number_crimes, etc.) directly onto the account alias with district never joined

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
SELECT DISTINCT T1.type FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id WHERE T1.disposition_id IN (SELECT disposition_id FROM disp WHERE type = 'Resident') AND T1.statement_frequency = 'Monthly' AND T1.date >= DATE('now', '-3 months') AND T1.date <= DATE('now') AND T1.number_municipalities_below_499 > 0 AND T1.number_municipalities_500_to_1999 > 0 AND T1.number_municipalities_2000_to_9999 > 0 AND T1.number_municipalities_above_10000 > 0 AND T1.number_cities > 0 AND T1.urban_inhabitant_ratio > 0 AND T1.average_salary > 8000 AND T1.unemployment_rate_1995 > 0 AND T1.unemployment_rate_1996 > 0 AND T1.enterpreneurs_per_1000 > 0 AND T1.number_crimes_1995 > 0 AND T1.number_crimes_1996 > 0;
```

### Q152 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** number_crimes_1995 (A15) is real only on district; predicted's FROM is loan alone with no join at all

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(number_crimes_1995) 
FROM loan 
WHERE YEAR(date) = 1995 
  AND number_crimes_1995 > 4000 
  AND district_id IN (SELECT district_id FROM account WHERE account_id IN (SELECT account_id FROM loan WHERE date >= '1997-01-01' AND date < '1998-01-01'));
```

### Q159 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gold's trans (all records for the client's account, filtered by operation='VYBER') is replaced wholesale by loan; transaction_type_code (k_symbol) is real on trans/order, not loan

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT *
FROM loan
WHERE account_id = (SELECT account_id FROM client WHERE client_id = 3356) AND transaction_type_code = 'cash';
```

### Q168 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** gender is real on client/T1 (already present in the query); predicted references T3.gender where T3 is aliased to account, reached via an unnecessary disp+account chain

**Gold SQL:**

```sql
SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'W' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T1.district_id = (SELECT district_id FROM district WHERE average_salary > 10000)
```

### Q169 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted calls YEAR(), a non-SQLite function

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(amount) AS REAL) / COUNT(*) * 100 FROM loan WHERE client_id IN (SELECT client_id FROM client WHERE gender = 'Male' AND YEAR(date) BETWEEN 1996 AND 1997)
```

### Q173 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** amount does not exist on account (single-table query, no join at all); it is real on order/loan/trans; predicted also drops gold's derived-table/GROUP BY structure entirely

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS statement_count, SUM(amount) AS total_amount
FROM account
WHERE account_id = 3
AND statement_frequency = 'daily';
```

### Q186 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** client (source of gender) is never joined; predicted only joins account+disp

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'Male' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.client_id) FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id WHERE T1.statement_frequency = 'Weekly';
```

### Q189 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** disp (bridge to client) and district (source of average_salary) are both missing; account.client_id is used as an invalid direct key

**Gold SQL:**

```sql
SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id  WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.account_id FROM account AS T1 INNER JOIN client AS T2 ON T1.client_id = T2.client_id WHERE T2.gender = 'Female' ORDER BY T1.average_salary ASC LIMIT 1
```

### Q192 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** statement_frequency (frequency) is real on account, not loan; predicted's single-table loan query never joins account

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(amount) FROM loan WHERE status = 'running' AND statement_frequency > 0;
```

### Q194 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'age' does not exist anywhere in the schema (client only stores birth_date, not a computed age); query also invents a nonexistent client.card_id

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT client_id, age FROM client WHERE card_id IN (SELECT card_id FROM disp WHERE type = 'high_level_credit_card' AND status = 'active')
```

---

## formula_1 (64 failures)

### Q846 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'race_number' does not exist anywhere in the schema (races only has raceId/round); query also substitutes results for gold's qualifying table and entirely drops the ORDER BY q1 DESC LIMIT 5 logic

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.driver_ref_name FROM drivers AS T1 JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T2.race_id = (SELECT race_id FROM races WHERE race_number = 20) AND T2.status_id IN (SELECT status_id FROM status WHERE status = 'Eliminated');
```

### Q847 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'driver_last_name' doesn't match any real column or alias (drivers.surname's alias is 'last_name'); query substitutes driverStandings/results for gold's drivers+qualifying and invents a nonexistent 'qualifying_period' column

**Gold SQL:**

```sql
SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 ORDER BY T1.q2 ASC NULLS LAST LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.driver_last_name FROM results AS T1 INNER JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id = (SELECT race_id FROM qualifying WHERE number = 19 AND qualifying_period = 2) ORDER BY T1.laps DESC LIMIT 1
```

### Q850 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** predicted correctly reproduces gold's join logic and filter (races/circuits, country='Germany') but omits DISTINCT, so repeated race names are not deduplicated

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN circuits AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.country = 'Germany'
```

### Q854 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of the race-name filter) replaced wholesale by constructors; circuits is common to both, but constructors has no country column (only nationality), and predicted selects location instead of gold's lat/lng

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.location FROM circuits AS T1 INNER JOIN constructors AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.country = 'Australia';
```

### Q857 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** races replaced wholesale by constructorResults; circuits is common to both, but constructorResults has no circuit_id or race-name filter capability, and the race-name filter is misattributed to the circuits alias

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.latitude, T1.longitude FROM circuits AS T1 INNER JOIN constructorResults AS T2 ON T1.circuit_id = T2.circuit_id WHERE T1.name = 'Abu Dhabi Grand Prix';
```

### Q859 (simple, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted uses malformed triple-part identifiers (T1.results.result_id, ...), invalid syntax since T1 is already aliased to results; also substitutes results+qualifying for gold's qualifying+drivers and drops the forename/surname filter

**Gold SQL:**

```sql
SELECT T1.q1 FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 354 AND T2.forename = 'Bruno' AND T2.surname = 'Senna'
```

**Predicted SQL:**

```sql
SELECT T1.results.result_id, T1.results.driver_id, T1.results.constructor_id, T1.results.number, T1.results.grid_position, T1.results.position, T1.results.position_text, T1.results.position_order, T1.results.points, T1.results.laps, T1.results.time, T1.results.milliseconds, T1.results.fastest_lap_number, T1.results.rank, T1.results.fastest_lap_time, T1.results.fastest_lap_speed, T1.results.status_id
FROM results AS T1
JOIN qualifying AS T2 ON T1.result_id = T2.result_id
WHERE T2.number = 354 AND T2.qualifying_1_time IS NOT NULL;
```

### Q861 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** drivers (source of the output column and the q3 time filter) is replaced by driverStandings via a garbled correlated-subquery chain through qualifying/races; the q3 LIKE '1:54%' filter and driver-number output are lost, replaced by an unrelated COUNT

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT COUNT(driver_id) FROM driverStandings WHERE driver_id = (SELECT driver_id FROM qualifying WHERE race_id = (SELECT race_id FROM races WHERE name = 'Q3' AND round = 903 AND number = 903))
```

### Q862 (simple, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of the year=2007/name filter) and results (source of time IS NULL/status_id) are both missing from predicted's drivers+qualifying join; qualifying has neither a year nor status_id column

**Gold SQL:**

```sql
SELECT COUNT(T3.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T1.year = 2007 AND T1.name = 'Bahrain Grand Prix' AND T2.time IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.driver_id) FROM drivers AS T1 INNER JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T2.year = 2007 AND T2.status_id = 4;
```

### Q865 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** predicted inserts an unnecessary driverStandings table between drivers and results, joined via a nonexistent driverStandings.result_id column; gold only needs a direct drivers-results join

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name
FROM drivers AS T1
JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id
JOIN results AS T3 ON T2.result_id = T3.result_id
WHERE T3.race_id = 592 AND T3.position = 592
ORDER BY T1.date_of_birth ASC
LIMIT 1;
```

### Q866 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'introduction_website' doesn't match any real column or alias (drivers.url keeps its original name 'url'); query also substitutes qualifying for gold's lapTimes and invents a nonexistent qualifying.lap_time column

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name, T1.introduction_website
FROM drivers AS T1
JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id
WHERE T2.number = 161 AND T2.lap_time = '0:01:27'
ORDER BY T1.first_name, T1.last_name;
```

### Q868 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted selects circuits.location instead of gold's lat/lng (all real columns on circuits, correctly joined to races); also drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.name = 'Malaysian Grand Prix';
```

### Q869 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'introduction_website' doesn't match any real column or alias (constructors.url keeps its original name 'url'); also wraps race_id=9 in a bogus subquery against a nonexistent races.name='No. 9' instead of using the literal directly

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.introduction_website FROM constructors AS T1 JOIN constructorResults AS T2 ON T1.constructor_id = T2.constructor_id WHERE T2.race_id = (SELECT race_id FROM races WHERE name = 'No. 9') ORDER BY T2.points DESC LIMIT 1
```

### Q872 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** qualifying+drivers replaced wholesale by results+driverStandings; driver_code (a real, correctly-named alias of drivers.code) is misattributed to the results alias since drivers isn't joined; race identification is rerouted through a bogus races.name='Race No. 45' subquery

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT T1.driver_code FROM results AS T1 INNER JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id = (SELECT race_id FROM races WHERE name = 'Race No. 45') AND T1.time = '0:01:33'
```

### Q875 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on races.name='Race No. 901' (an invented value not matching real race-name data) instead of gold's races.raceId=901 -- wrong column chosen for the filter, though the rest of the join/output (seasons.url) is correct

**Gold SQL:**

```sql
SELECT T2.url FROM races AS T1 INNER JOIN seasons AS T2 ON T2.year = T1.year WHERE T1.raceId = 901
```

**Predicted SQL:**

```sql
SELECT T1.url FROM seasons AS T1 INNER JOIN races AS T2 ON T1.year = T2.year WHERE T2.name = 'Race No. 901';
```

### Q877 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** predicted inserts an unnecessary driverStandings table between drivers and results, joined via a nonexistent driverStandings.result_id column

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name
FROM drivers AS T1
JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id
JOIN results AS T3 ON T2.result_id = T3.result_id
WHERE T3.race_id = 872 AND T3.position = 1
ORDER BY T1.date_of_birth ASC
LIMIT 1;
```

### Q879 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** results (source of fastestLapSpeed) replaced wholesale by driverStandings; drivers is common to both, but driverStandings has no fastest_lap_speed column

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.nationality FROM driverStandings AS T1 INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id WHERE T1.fastest_lap_speed = (SELECT MAX(fastest_lap_speed) FROM driverStandings);
```

### Q880 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** drivers (needed to filter to the single driver 'Paul di Resta') is missing entirely from predicted's degenerate self-join on results (T1.result_id=T2.result_id, matching each row to itself); race identification also uses bogus races.name string matches ('No. 853'/'Next Race') instead of literal raceId values

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
SELECT CAST(SUM(CASE WHEN T1.fastest_lap_speed > T2.fastest_lap_speed THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.fastest_lap_speed) FROM results AS T1 INNER JOIN results AS T2 ON T1.result_id = T2.result_id WHERE T1.race_id = (SELECT race_id FROM races WHERE name = 'No. 853') AND T2.race_id = (SELECT race_id FROM races WHERE name = 'Next Race');
```

### Q881 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** results (source of the time IS NOT NULL completion count) is replaced wholesale by qualifying, which has no year column and represents a different concept (qualifying sessions, not race results)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(DISTINCT T1.driver_id) AS REAL) * 100 / COUNT(T1.driver_id) FROM drivers AS T1 INNER JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T2.year = 1983 AND T2.race_id = (SELECT race_id FROM races WHERE date = '1983-07-16')
```

### Q884 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** name is real on races/T1 (the only table gold needs); predicted needlessly joins constructorResults as T2 and misattributes name to it instead of T1; also drops the month-matching condition entirely, using only year

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.name FROM races AS T1 INNER JOIN constructorResults AS T2 ON T1.race_id = T2.race_id WHERE T1.year = (SELECT MIN(year) FROM races)
```

### Q892 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** predicted uses COUNT(r.points) instead of gold's SUM(r.points) -- counts the number of point-scoring result rows instead of summing total points, a wrong aggregate function choice on an otherwise correct join/group

**Gold SQL:**

```sql
SELECT d.`forename`, d.`surname`, SUM(r.`points`) AS total_points
FROM `results` r
JOIN `drivers` d ON d.`driverId` = r.`driverId`
GROUP BY r.`driverId`
ORDER BY total_points DESC
LIMIT 1;
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, COUNT(r.points) AS total_points
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
GROUP BY d.driver_id
ORDER BY total_points DESC
LIMIT 1;
```

### Q894 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** drivers+lapTimes+races (needed for the fastest single-lap time) are entirely replaced by results+qualifying, joined via a nonexistent qualifying.result_id column; the three-table 'fastest lap of all time' concept (lapTimes.milliseconds) is lost

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.time, T1.driver_id, T1.race_id FROM results AS T1 JOIN qualifying AS T2 ON T1.result_id = T2.result_id ORDER BY T1.time DESC LIMIT 1;
```

### Q895 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** 'lap' is real on lapTimes (the per-lap number column), not results; predicted's outer FROM is results alone with no join to lapTimes; also references a bare 'year' which would need races (also unjoined), and substitutes nationality='Malaysia' for the Hamilton driver filter

**Gold SQL:**

```sql
SELECT AVG(T2.milliseconds) FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.year = 2009 AND T1.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT AVG(lap) FROM results WHERE driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Lewis' AND last_name = 'Hamilton' AND nationality = 'Malaysia') AND year = 2009;
```

### Q896 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** drivers has no 'name' column (that exists only on circuits/constructors/races); gold identifies the driver via surname='Hamilton' directly, which predicted has available on T1 but doesn't use; query also invents a nonexistent circuits.circuit_name and misses driverStandings/races entirely

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(DISTINCT T1.driver_id) AS REAL) * 100 / COUNT(T1.driver_id) FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T1.name = 'Hamilton' AND T2.circuit_id = (SELECT circuit_id FROM circuits WHERE circuit_name = 'F1') AND T2.year > 2010 AND T2.round = 1 AND T2.position = 1;
```

### Q897 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** predicted inserts an unnecessary results table joined via a nonexistent driverStandings.result_id column; gold only needs drivers+driverStandings directly, filtered on wins>=1 (predicted instead filters on results.status_id=1, an unrelated concept)

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, MAX(r.points) AS max_points
FROM drivers d
JOIN driverStandings ds ON d.driver_id = ds.driver_id
JOIN results r ON ds.result_id = r.driver_id
WHERE r.status_id = 1
GROUP BY d.driver_id
ORDER BY max_points DESC
LIMIT 1;
```

### Q898 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** predicted filters nationality='Japan' instead of gold's 'Japanese' (the real domain value); it also restructures the query into independent MIN(date_of_birth)/MIN(first_name) aggregates that don't correspond to the same row, and never computes the requested age

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(date_of_birth) AS youngest_japanese_driver_age, MIN(first_name) AS youngest_japanese_driver_name
FROM drivers
WHERE nationality = 'Japan';
```

### Q901 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** location is real on circuits/T2 (already joined); predicted references T1.location where T1 is races -- alias mix-up; also replaces the STRFTIME month='09' date filter with a nonsensical circuits.location LIKE 'September%' condition

**Gold SQL:**

```sql
SELECT DISTINCT T2.name, T1.name, T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.year = 2005 AND STRFTIME('%m', T2.date) = '09'
```

**Predicted SQL:**

```sql
SELECT T1.name, T1.location FROM races AS T1 INNER JOIN circuits AS T2 ON T1.circuit_id = T2.circuit_id WHERE T1.year = 2005 AND T2.location LIKE 'September%'
```

### Q902 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** driverStandings (bridging race+driver+position) is replaced wholesale by constructorResults (an unrelated constructor-focused table); races has no driver_id (invented), and name (real on races/T1) is misattributed to the constructorResults alias T2

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT T2.name
FROM races AS T1
JOIN constructorResults AS T2 ON T1.race_id = T2.race_id
WHERE T1.driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Alex' AND last_name = 'Yoong') AND T2.number < 20;
```

### Q904 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** lapTimes (source of the fastest-single-lap milliseconds ranking) is replaced wholesale by qualifying; the ORDER BY target also changes from lapTimes.milliseconds ASC to races.time DESC, an unrelated column and reversed direction

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.name, T1.year
FROM races AS T1
JOIN qualifying AS T2 ON T1.race_id = T2.race_id
WHERE T2.driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Michael' AND last_name = 'Schumacher')
ORDER BY T1.time DESC
LIMIT 1;
```

### Q906 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of the race name and year-ascending ordering) and driverStandings (bridging driver+race+points) are both missing, replaced by a direct drivers-results join; neither race name nor points exist on the drivers alias where they're referenced

**Gold SQL:**

```sql
SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.name, T1.points FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T1.first_name = 'Lewis' AND T1.last_name = 'Hamilton';
```

### Q909 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** circuits (source of country='Germany') replaced wholesale by constructors; races is common to both, but races has no constructor_id to bridge to constructors, and constructors.nationality is a different real-world attribute from circuits.country

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T1.country = 'Germany' THEN T2.circuitID END) AS REAL) * 100 / COUNT(T2.circuitId) FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'European Grand Prix'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(DISTINCT T1.race_id) AS REAL) * 100 / COUNT(T1.year) FROM races AS T1 INNER JOIN constructors AS T2 ON T1.constructor_id = T2.constructor_id WHERE T2.nationality = 'Germany'
```

### Q910 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on circuit_ref_name (circuitRef, a short reference code) instead of gold's name='Silverstone Circuit'; also selects location instead of gold's lat/lng

**Gold SQL:**

```sql
SELECT lat, lng FROM circuits WHERE name = 'Silverstone Circuit'
```

**Predicted SQL:**

```sql
SELECT location FROM circuits WHERE circuit_ref_name = 'Silverstone Circuit';
```

### Q915 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** 'country' is not a real column on drivers (the real column is 'nationality', not renamed to 'country'); 'country' only exists on circuits, which isn't joined; predicted also adds an unnecessary constructorStandings join and replaces ORDER BY dob ASC LIMIT 1 with an unrelated MAX(number) filter

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.country FROM drivers AS T1 JOIN constructorStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.number = (SELECT MAX(number) FROM drivers)
```

### Q928 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of the 'Canadian Grand Prix'/year=2007 filter) is missing entirely; predicted substitutes drivers.nationality='Canada' (a wrong-concept, wrong-value proxy) and inserts an unnecessary driverStandings table joined via a nonexistent result_id column

**Gold SQL:**

```sql
SELECT d.forename, d.surname, d.driverRef FROM drivers AS d JOIN results AS r ON d.driverId = r.driverId JOIN races AS ra ON r.raceId = ra.raceId WHERE ra.name = 'Canadian Grand Prix' AND ra.year = 2007 AND r.position = 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name, T1.driver_ref_name
FROM drivers AS T1
JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id
JOIN results AS T3 ON T2.result_id = T3.result_id
WHERE T3.year = 2007 AND T3.rank = 1 AND T1.nationality = 'Canada'
ORDER BY T1.rank ASC
LIMIT 1;
```

### Q930 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** gold filters results.rank=0 (races where Hamilton didn't finish) and returns all matching race names; predicted drops that filter entirely and instead returns just the single race with Hamilton's highest points via ORDER BY points DESC LIMIT 1

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id WHERE T2.driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Lewis' AND last_name = 'Hamilton') ORDER BY T2.points DESC LIMIT 1
```

### Q931 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of name='Spanish Grand Prix'/year=2009) replaced wholesale by driverStandings; results is common to both, but neither has year or country columns; ORDER BY target also changes from fastestLapSpeed to points

**Gold SQL:**

```sql
SELECT T2.fastestLapSpeed FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.name = 'Spanish Grand Prix' AND T1.year = 2009 AND T2.fastestLapSpeed IS NOT NULL ORDER BY T2.fastestLapSpeed DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.fastest_lap_speed FROM results AS T1 INNER JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.year = 2009 AND T2.country = 'Spain' ORDER BY T1.points DESC LIMIT 1;
```

### Q933 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** rank is real on results/T1 (already present); predicted references T2.rank where T2 is driverStandings -- alias mix-up; the query is also otherwise deeply garbled (races and drivers both missing, driver identification attempted via a nonsensical constructors.name='Lewis Hamilton' lookup)

**Gold SQL:**

```sql
SELECT T2.positionOrder FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.name = 'Chinese Grand Prix' AND T1.year = 2008
```

**Predicted SQL:**

```sql
SELECT T2.rank FROM results AS T1 INNER JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.result_id = (SELECT result_id FROM results ORDER BY fastest_lap_time DESC LIMIT 1) AND T1.year = 2008 AND T1.constructor_id = (SELECT constructor_id FROM constructors WHERE name = 'Lewis Hamilton');
```

### Q937 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** time is real on results/T1 (already present, correctly used for the race_id subquery); predicted references T2.time where T2 is driverStandings -- alias mix-up; the race-name filter is also corrupted into a garbled string 'AustChineseralian Grand Prix'

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT T2.time FROM results AS T1 INNER JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id = (SELECT race_id FROM races WHERE year = 2008 AND name = 'AustChineseralian Grand Prix') AND T2.position = 2;
```

### Q940 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of name='Chinese Grand Prix'/year=2008) is replaced wholesale by qualifying inside the subquery; qualifying has no year column, and gold's derived-table/GROUP BY/HAVING structure for counting participating drivers is dropped

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT driver_id) FROM results WHERE race_id IN (SELECT race_id FROM qualifying WHERE year = 2008 AND status_id = 1)
```

### Q944 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of the 'Australian Grand Prix'/year=1988 filter) is missing entirely from predicted's results+driverStandings query; gold's CTE-based champion-vs-last-driver milliseconds comparison is replaced with an unrelated speed-comparison ratio

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.driver_id = T2.driver_id THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.driver_id) AS speed_difference
FROM results AS T1
JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id
WHERE T1.year = 1988 AND T1.rank = (SELECT MAX(rank) FROM results WHERE year = 1988)
ORDER BY T1.points DESC
LIMIT 1;
```

### Q945 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** gold filters on two separate columns (location='Adelaide' AND country='Australia'); predicted collapses both into a single non-matching literal 'Adelaide, Australia' compared against just location, effectively dropping the country condition

**Gold SQL:**

```sql
SELECT COUNT(circuitId) FROM circuits WHERE location = 'Adelaide' AND country = 'Australia'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM circuits WHERE location = 'Adelaide, Australia';
```

### Q948 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** points is real on constructorStandings, not constructors; predicted's FROM is constructors alone with no join at all

**Gold SQL:**

```sql
SELECT MAX(T1.points) FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T2.nationality = 'British'
```

**Predicted SQL:**

```sql
SELECT MAX(points) FROM constructors WHERE nationality = 'British';
```

### Q950 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** constructorStandings (source of points=0) is replaced wholesale by constructorResults; predicted also references a nonexistent status_id column there (constructorResults only has 'status', a different concept from points=0)

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT T1.constructor_ref_name FROM constructors AS T1 JOIN constructorResults AS T2 ON T1.constructor_id = T2.constructor_id WHERE T2.status_id = 0 AND T2.race_id = 291 GROUP BY T1.constructor_ref_name HAVING COUNT(*) = 0;
```

### Q951 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on constructorResults.status='0' instead of gold's points=0 (both real columns, wrong one chosen); also drops the nationality='Japanese' filter and gold's GROUP BY constructorId HAVING COUNT(raceId)=2 structure, replacing it with a nonsensical races.year=2 subquery

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructor_id) FROM constructors AS T1 INNER JOIN constructorResults AS T2 ON T1.constructor_id = T2.constructor_id WHERE T2.status = '0' AND T2.race_id IN (SELECT race_id FROM races WHERE year = 2)
```

### Q954 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of the year BETWEEN 2007 AND 2009 filter) is missing entirely from predicted's drivers+results query; predicted also substitutes driver_code='JPN' (a real but wrong column) for the intended nationality='Japanese' filter

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.driver_code = 'JPN' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.driver_id) FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T2.year BETWEEN 2007 AND 2009;
```

### Q955 (challenging, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** gold groups by year to compute a per-year average lap time (milliseconds/1000); predicted has no GROUP BY at all (one overall average), uses the text-formatted time column instead of numeric milliseconds, and drops the position=1 (winners-only) filter

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT AVG(T1.time) AS average_time_seconds
FROM results AS T1
JOIN races AS T2 ON T1.race_id = T2.race_id
WHERE T2.year < 1975;
```

### Q959 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** year is real on races, not results; predicted's FROM is results alone with no join; also substitutes a status_id IN (...'Champion') filter (an implausible status value) for gold's time-format-validity check

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT fastest_lap_number FROM results WHERE year = 2009 AND status_id IN (SELECT status_id FROM status WHERE status = 'Champion');
```

### Q962 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** results (source of laps>50) and races (source of year BETWEEN 2000-2005) are both replaced by qualifying; qualifying.number (car number) is substituted for results.laps, an unrelated concept, and the year filter is dropped entirely

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(DISTINCT T1.driver_id) AS REAL) * 100 / COUNT(T1.driver_id) FROM drivers AS T1 INNER JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T1.date_of_birth < '1985-01-01' AND T2.number = 50;
```

### Q963 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** lapTimes (per-lap time data) is replaced wholesale by results (overall race-time data); the nationality='French' filter is also dropped entirely, and the time comparison is a naive string comparison ('02:00:00') rather than gold's parsed seconds-based computation

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.driver_id) FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T2.time < '02:00:00'
```

### Q964 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only drivers (single table, no join); predicted invents an unnecessary join to constructors via a nonexistent drivers.constructor_id key; also selects driver_ref_name instead of gold's code and moves the nationality filter to constructors

**Gold SQL:**

```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.driver_ref_name FROM drivers AS T1 INNER JOIN constructors AS T2 ON T1.constructor_id = T2.constructor_id WHERE T2.nationality = 'American';
```

### Q967 (simple, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** gold uses a derived subquery (drivers ordered by dob DESC LIMIT 3) to isolate the 3 youngest drivers, then counts how many are Dutch; predicted has no such subquery, instead joining driverStandings and filtering on position=1 and an invented position_text='Youngest' value, plus 'Netherlands' instead of 'Dutch'

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.driver_id) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.nationality = 'Netherlands' AND T2.position = 1 AND T2.position_text = 'Youngest';
```

### Q971 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** drivers has no 'name' column (only forename/surname/driverRef); 'name' exists only on circuits/constructors/races, none of which hold driver identity; gold wants driverRef; predicted also uses nationality='Germany' instead of 'German' and orders by an unnecessarily-joined constructorStandings.position instead of dob

**Gold SQL:**

```sql
SELECT driverRef FROM drivers WHERE nationality = 'German' ORDER BY JULIANDAY(dob) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.name FROM drivers AS T1 JOIN constructorStandings AS T2 ON T1.driver_id = T2.driver_id WHERE T1.nationality = 'Germany' ORDER BY T2.position ASC LIMIT 1
```

### Q972 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** results (source of fastestLapTime IS NOT NULL) replaced wholesale by qualifying; drivers is common to both, but qualifying has no fastest_lap_time column; predicted also adds an unwarranted ORDER BY/LIMIT 1 gold doesn't have

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.driver_id, T1.driver_code FROM drivers AS T1 INNER JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id WHERE T1.date_of_birth = '1971' ORDER BY T2.fastest_lap_time DESC LIMIT 1;
```

### Q977 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'race_no' does not exist anywhere in the schema (races only has raceId/round); query also substitutes driverStandings for gold's results and entirely drops the statusId=2 filter

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT driver_id) FROM driverStandings WHERE race_id IN (SELECT race_id FROM races WHERE race_no BETWEEN 50 AND 100)
```

### Q978 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** predicted's SELECT list omits latitude entirely (gold selects location, lat, lng; predicted only returns location, longitude) and drops DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, longitude FROM circuits WHERE country = 'Austria';
```

### Q981 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of all 4 requested output columns: year, name, date, time) is missing entirely from predicted's drivers+qualifying query; the driver-selection logic is also wrong (MIN(number), a car-number concept, instead of ORDER BY dob DESC LIMIT 1)

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.year, T1.name, T1.date, T1.time
FROM drivers AS T1
JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id
WHERE T1.number = (SELECT MIN(number) FROM drivers)
ORDER BY T1.date ASC;
```

### Q988 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** p.stops references an alias 'p' that was never introduced anywhere in the FROM/JOIN clause (only d and q are aliased); also drops the required dob BETWEEN 1980-1985 filter, substitutes qualifying for gold's pitStops, and uses 'Germany' instead of 'German'

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.date_of_birth
FROM drivers d
JOIN qualifying q ON d.driver_id = q.driver_id
WHERE d.nationality = 'Germany'
GROUP BY d.driver_id
ORDER BY AVG(p.stops) ASC
LIMIT 3;
```

### Q989 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of name='Canadian Grand Prix'/year=2008) replaced wholesale by constructorStandings; results is common to both, but constructorStandings has no year column, and the query substitutes an unrelated constructor-position/'Champion'-status filter

**Gold SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN constructorStandings AS T2 ON T1.constructor_id = T2.constructor_id WHERE T2.position = (SELECT position FROM constructorStandings ORDER BY position DESC LIMIT 1) AND T1.year = 2008 AND T1.status_id = (SELECT status_id FROM status WHERE status = 'Champion');
```

### Q990 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** results+races (source of the Singapore GP/2009/time-format filters) are replaced wholesale by constructorResults, which has no year column; the race-name filter is misattributed to constructors.name, and status_id is invented (constructorResults only has 'status')

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T1.constructor_ref_name FROM constructors AS T1 JOIN constructorResults AS T2 ON T1.constructor_id = T2.constructor_id WHERE T2.year = 2009 AND T2.status_id = (SELECT status_id FROM status WHERE status = 'Champion') AND T1.name = 'Singapore Grand Prix';
```

### Q994 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** points is real on constructorResults/T2 (already joined and used for the race_id filter); predicted references T1.points where T1 is constructors -- alias mix-up; the Monaco Grand Prix name filter and gold's GROUP BY/SUM(points) aggregation are also dropped

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.name, T1.nationality, T1.points
FROM constructors AS T1
JOIN constructorResults AS T2 ON T1.constructor_id = T2.constructor_id
WHERE T2.race_id IN (SELECT race_id FROM races WHERE year BETWEEN 1980 AND 2010)
ORDER BY T1.points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** races (source of the year=2008 filter and circuit linkage) is missing entirely from predicted's drivers+qualifying query; 'rank' (real only on results) and a nonexistent circuits.circuit_name are also referenced; MAX (instead of MIN/ASC) qualifying_3_time reverses gold's fastest-time intent

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name
FROM drivers AS T1
JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id
WHERE T2.rank = 1 AND T2.qualifying_3_time = (SELECT MAX(qualifying_3_time) FROM qualifying)
AND T2.year = 2008 AND T2.circuit_id = (SELECT circuit_id FROM circuits WHERE circuit_name = 'Marina Bay Street Circuit')
ORDER BY T1.first_name, T1.last_name ASC LIMIT 1;
```

### Q1002 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** driverStandings (bridging driver to race) is missing entirely; predicted instead attempts a direct drivers-races join via a nonexistent races.driver_id column; the driver-selection logic and sort direction (oldest vs. gold's youngest-by-dob) are also wrong

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, T3.name FROM drivers AS T1 INNER JOIN driverStandings AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T2.raceId = T3.raceId ORDER BY JULIANDAY(T1.dob) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name, T1.nationality, T2.name
FROM drivers AS T1
JOIN races AS T2 ON T1.driver_id = T2.driver_id
WHERE T2.year = (SELECT MIN(year) FROM races)
ORDER BY T1.date_of_birth ASC
LIMIT 1;
```

### Q1003 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** gold groups by driverId (within Canadian GP + statusId=3 results) and takes the most frequent driver's count; predicted has no GROUP BY at all, instead computing an unrelated COUNT(*) of all results for whichever driver has the most wins per driverStandings -- races and status are both dropped entirely

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM results WHERE driver_id = (SELECT driver_id FROM driverStandings ORDER BY wins DESC LIMIT 1)
```

### Q1011 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** lapTimes (source of the derived-subquery MIN(milliseconds)-per-driver ranking) is replaced wholesale by qualifying; qualifying has neither a rank nor a laps column (both belong to results); gold's derived-table structure for each driver's fastest lap is also dropped

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT T1.first_name, T1.last_name
FROM drivers AS T1
JOIN qualifying AS T2 ON T1.driver_id = T2.driver_id
WHERE T2.rank = (SELECT MIN(rank) FROM qualifying)
ORDER BY T2.laps DESC
LIMIT 20;
```

### Q1014 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** results has no circuit_id (the real path is results->races->circuits); predicted's direct results-circuits join key is invalid; 'lap' also doesn't exist on results (real on lapTimes/pitStops); gold's CTE-based fastest-lap-time-parsing logic is dropped entirely

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.lap FROM results AS T1 INNER JOIN circuits AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.country = 'Italy'
```

---

## student_club (44 failures)

### Q1317 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted escapes the apostrophe in 'Women's Soccer' using a backslash (\'), which is not valid SQLite string-literal syntax (SQLite requires doubling the quote: ''), causing a syntax error regardless of the rest of the (also somewhat garbled) query logic

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.member_id) FROM attendance AS T1 INNER JOIN member AS T2 ON T1.member_id = T2.member_id WHERE T1.event_id = (SELECT event_id FROM event WHERE event_name = 'Women\'s Soccer') AND T2.position = 'T_Shirt_Size' AND T2.t_shirt_size = 'Medium';
```

### Q1322 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** status is real on event, not member; predicted's subquery scope is member alone with no join to event; the query is severely restructured, using major_name='Student_Club' (nonsensical) and event_date on member instead of gold's simple event+attendance join with type='Meeting' GROUP BY/HAVING

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(event_id) FROM attendance WHERE member_id IN (SELECT member_id FROM member WHERE major_id = (SELECT major_id FROM major WHERE major_name = 'Student_Club') AND status = 'Active' AND event_date >= DATE('now', '-1 year')) AND type = 'Meeting';
```

### Q1323 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted output is a severely repetitive, truncated generation artifact (100+ nested subqueries alternating event_id/member_id membership checks against attendance) that includes literal markdown code-fence text ('```sql'), causing a syntax error ('unrecognized token')

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
```sql
SELECT event_name FROM event WHERE event_id IN (
    SELECT event_id FROM attendance WHERE member_id IN (
        SELECT member_id FROM attendance WHERE event_id IN (
            SELECT event_id FROM attendance WHERE member_id IN (
                SELECT member_id FROM attendance WHERE event_id IN (
                    SELECT event_id FROM attendance WHERE member_id IN (
                        SELECT member_id FROM attendance WHERE event_id IN (
                            SELECT event_id FROM attendance WHERE member_id IN (
                                SELECT member_id FROM attendance WHERE event_id IN (
                                    SELECT event_id FROM attendance WHERE member_id IN (
                                        SELECT event_id FROM attendance WHERE member_id IN (
                                            SELECT event_id FROM attendance WHERE member_id IN (
                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                        SELECT event_id FROM attendance WHERE member_id IN (
                                                            SELECT event_id FROM attendance WHERE member_id IN (
                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                        SELECT event_id FROM attendance WHERE member_id IN (
                                                                            SELECT event_id FROM attendance WHERE member_id IN (
                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                                        SELECT event_id FROM attendance WHERE member_id IN (
                                                                                            SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                        SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                            SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                        SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                            SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                        SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                            SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                    SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance WHERE member_id IN (
                                                                                                                                                SELECT event_id FROM attendance
```

### Q1331 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted searches for a member whose first_name='Vice President' AND last_name='President' instead of filtering member.position='Vice President' (the real column for this concept, unused); also aggregates via SUM instead of directly selecting the amount as gold does

**Gold SQL:**

```sql
SELECT T2.amount FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Vice President'
```

**Predicted SQL:**

```sql
SELECT SUM(amount) FROM income WHERE member_id = (SELECT member_id FROM member WHERE first_name = 'Vice President' AND last_name = 'President');
```

### Q1334 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** zip_code (source of state='Illinois') is replaced wholesale by an unrelated attendance+event+major join chain; state doesn't exist on member (real only on zip_code), and department='Illinois' misuses major's department field for a state name

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name
FROM member m
JOIN attendance a ON m.member_id = a.member_id
JOIN event e ON a.event_id = e.event_id
JOIN major m2 ON e.major_id = m2.major_id
WHERE m2.department = 'Illinois' AND m.state = 'IL';
```

### Q1338 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'expense_status' does not exist anywhere (expense's real column is 'approved', aliased 'is_approved'); the query also drops event+budget (needed to identify 'October Meeting' specifically) and computes a COUNT instead of returning the approved value

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS approved_expenses
FROM expense
WHERE expense_date LIKE '2019-10-08%' AND expense_status = 'approved';
```

### Q1339 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** member+expense (source of cost/AVG) are replaced wholesale by attendance+event; amount_spent doesn't exist on attendance (real only on budget); the date range is also changed from a repeating Sept/Oct-any-year pattern to a fixed 2023 range

**Gold SQL:**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL:**

```sql
SELECT AVG(T1.amount_spent) AS total_average_cost
FROM attendance AS T1
JOIN event AS T2 ON T1.event_id = T2.event_id
WHERE T1.member_id = (SELECT member_id FROM member WHERE first_name = 'Elijah' AND last_name = 'Allen')
  AND T2.event_date BETWEEN '2023-09-01' AND '2023-10-31';
```

### Q1340 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** budget (source of amount_spent/'spent') is replaced wholesale by attendance/event; amount_spent doesn't exist on either; the query also calls the non-SQLite YEAR() function and routes the 2019/2020 comparison through an unrelated major_name='Student_Club' membership chain

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT SUM(T1.amount_spent) - SUM(T2.amount_spent) AS total_spent_difference
FROM attendance AS T1
JOIN event AS T2 ON T1.event_id = T2.event_id
WHERE T1.member_id IN (SELECT member_id FROM member WHERE major_id = (SELECT major_id FROM major WHERE major_name = 'Student_Club' AND YEAR(event_date) = 2019) OR major_id = (SELECT major_id FROM major WHERE major_name = 'Student_Club' AND YEAR(event_date) = 2020))
```

### Q1344 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** income (source of source='Fundraising'/notes) is replaced wholesale by attendance; notes doesn't exist on attendance (real on income or event); the source='Fundraising' filter is entirely dropped

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM attendance WHERE event_id = (SELECT event_id FROM event WHERE event_date = '2019-09-14');
```

### Q1346 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** gold needs only member (single table); predicted adds an unnecessary INNER JOIN to attendance, which either drops Carlo Jacobs entirely (if he has no attendance records) or duplicates his phone number once per attendance row (if he has several)

**Gold SQL:**

```sql
SELECT phone FROM member WHERE first_name = 'Carlo' AND last_name = 'Jacobs'
```

**Predicted SQL:**

```sql
SELECT T1.phone FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.member_id WHERE T1.first_name = 'Carlo' AND T1.last_name = 'Jacobs';
```

### Q1350 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** budget+expense (source of expense_description/expense_date and the event_status output) are replaced wholesale by event+attendance; event.status (a different, similarly-named real column) is used instead of budget.event_status; a fabricated 'John Doe' member filter is added

**Gold SQL:**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT T1.status FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.event_id WHERE T1.event_name = 'Post Cards, Posters' AND T2.member_id = (SELECT member_id FROM member WHERE first_name = 'John' AND last_name = 'Doe' AND email = 'john.doe@example.com');
```

### Q1352 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** major_id is real on member (aliased from link_to_major), not attendance; predicted's FROM is attendance alone with no join to member; the t_shirt_size='Medium' filter (on member) is also dropped entirely

**Gold SQL:**

```sql
SELECT COUNT(T1.member_id) FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.major_name = 'Business' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(member_id) FROM attendance WHERE major_id = (SELECT major_id FROM major WHERE major_name = 'Business')
```

### Q1356 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** member (source of position='President') replaced wholesale by attendance; 'President' is misattributed as a major.department value instead of member.position

**Gold SQL:**

```sql
SELECT T2.department FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.position = 'President'
```

**Predicted SQL:**

```sql
SELECT T2.department FROM major AS T1 JOIN attendance AS T2 ON T1.major_id = T2.major_id WHERE T1.department = 'President';
```

### Q1357 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** income (source of date_received, filtered by source='Dues') is replaced wholesale by attendance; event_date doesn't exist on attendance (real on event, not joined); the source='Dues' filter is dropped entirely

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT T1.event_date FROM attendance AS T1 INNER JOIN member AS T2 ON T1.member_id = T2.member_id WHERE T2.first_name = 'Connor' AND T2.last_name = 'Hilton';
```

### Q1359 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** event (source of event_name/type) is replaced wholesale by attendance inside both subqueries, which has neither column; the whole ratio computation is also replaced by an unrelated COUNT(*)

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM budget WHERE event_id IN (SELECT event_id FROM attendance WHERE event_name = 'Yearly Kickoff' AND type = 'Advertisement') AND event_id IN (SELECT event_id FROM attendance WHERE event_name = 'October Meeting');
```

### Q1361 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** expense (source of cost, filtered by expense_description='Pizza') is replaced wholesale by attendance+event; amount doesn't exist on attendance, and 'Pizza' is misattributed as an event.type value instead of expense.expense_description

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_description = 'Pizza'
```

**Predicted SQL:**

```sql
SELECT SUM(T1.amount) AS total_cost
FROM attendance AS T1
JOIN event AS T2 ON T1.event_id = T2.event_id
WHERE T2.type = 'pizza';
```

### Q1362 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters state='Orange County' instead of gold's county='Orange County' -- both real columns on zip_code, but 'Orange County' is a county value, not a state; the state='Virginia' filter is also replaced by state_abbr='VA'

**Gold SQL:**

```sql
SELECT COUNT(distinct city) FROM zip_code WHERE county = 'Orange County' AND state = 'Virginia'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT city) FROM zip_code WHERE state = 'Orange County' AND state_abbr = 'VA';
```

### Q1368 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** member (source of phone='809-555-3360') is replaced wholesale by attendance (with major as the join anchor); 'phone_number' also doesn't match any real column/alias (member.phone keeps its original name)

**Gold SQL:**

```sql
SELECT T2.major_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.phone = '809-555-3360'
```

**Predicted SQL:**

```sql
SELECT T2.major_name FROM major AS T1 INNER JOIN attendance AS T2 ON T1.major_id = T2.major_id WHERE T1.phone_number = '809-555-3360';
```

### Q1371 (simple, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted escapes the apostrophe in 'Women's Soccer' using a backslash (\'), which is not valid SQLite string-literal syntax, causing a syntax error

**Gold SQL:**

```sql
SELECT COUNT(T2.link_to_member) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.event_name = 'Women''s Soccer'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM attendance WHERE event_id = (SELECT event_id FROM event WHERE event_name = 'Women\'s Soccer');
```

### Q1375 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** member links directly to major via member.major_id (aliased from link_to_major); predicted instead routes through an unnecessary attendance+event detour, inventing a nonexistent event.major_id column (event has no major relationship at all)

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.department = 'School of Applied Sciences, Technology and Education'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, m.email
FROM member m
JOIN attendance a ON m.member_id = a.member_id
JOIN event e ON a.event_id = e.event_id
JOIN major m2 ON e.major_id = m2.major_id
WHERE m2.department = 'School of Applied Sciences, Technology and Education';
```

### Q1376 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted computes SUM(amount_spent)/SUM(amount_remaining) instead of gold's SUM(spent)/SUM(amount) -- amount_remaining and amount are different real columns on budget; also uses status='closed' (wrong case) and an unnecessary attendance join that can fan out budget rows per event

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT e.event_name
FROM event e
JOIN attendance a ON e.event_id = a.event_id
JOIN budget b ON a.event_id = b.event_id
WHERE e.status = 'closed'
GROUP BY e.event_id
ORDER BY SUM(b.amount_spent) / SUM(b.amount_remaining) DESC
LIMIT 1;
```

### Q1380 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** budget (source of spent/category='Food') is replaced wholesale by expense, which has neither amount_spent (budget's 'spent', aliased) nor a 'type' column (expense has expense_description instead)

**Gold SQL:**

```sql
SELECT SUM(spent) FROM budget WHERE category = 'Food'
```

**Predicted SQL:**

```sql
SELECT SUM(amount_spent) FROM expense WHERE type = 'food';
```

### Q1381 (moderate, aggregate) — **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** gold groups by member (link_to_member) to find members who attended more than 7 events; predicted instead groups by event to find events with more than 7 attendees, then returns any member who attended one of those events -- a different entity/granularity entirely

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name
FROM member m
JOIN attendance a ON m.member_id = a.member_id
WHERE a.event_id IN (
    SELECT event_id
    FROM attendance
    GROUP BY event_id
    HAVING COUNT(*) > 7
);
```

### Q1387 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'year' does not exist anywhere in the schema; the query also drops event (needed for 'Yearly Kickoff') and expense (needed to link to a specific member) entirely, and never checks member.position='Treasurer' at all, using an invented event_status='Entrained' value instead

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name
FROM member m
JOIN attendance a ON m.member_id = a.member_id
JOIN budget b ON a.event_id = b.event_id
WHERE b.event_status = 'Entrained' AND b.year = 2023;
```

### Q1389 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** amount is real on budget/income, not event; predicted's FROM is event alone with no join to budget/expense at all

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT event_name FROM event ORDER BY amount ASC LIMIT 1
```

### Q1390 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** budget+expense (source of cost/amount_spent) are replaced wholesale by attendance, which has neither; an irrelevant type='Event' filter is also added that gold doesn't have

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T2.amount_spent ELSE 0 END) AS REAL) * 100 / SUM(T2.amount_spent) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.event_id WHERE T1.type = 'Event';
```

### Q1392 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** budget (unrelated to income) is joined via a nonsensical income_id=event_id key; event_date doesn't exist on budget (real on event); gold needs only income (single table, filtered by date_received and ordered by source)

**Gold SQL:**

```sql
SELECT source FROM income WHERE date_received BETWEEN '2019-09-01' and '2019-09-30' ORDER BY source DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.income_source FROM income AS T1 INNER JOIN budget AS T2 ON T1.income_id = T2.event_id WHERE T2.event_date LIKE '2019-09%' ORDER BY T2.amount DESC LIMIT 1;
```

### Q1394 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** major_id is real on member (aliased from link_to_major), not attendance; predicted's FROM is attendance alone with no join to member at all

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(member_id) FROM attendance WHERE major_id = (SELECT major_id FROM major WHERE major_name = 'Physics Teaching');
```

### Q1398 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** amount_spent is real on budget, not member; predicted's innermost subquery scope is member alone with no join to budget; the category='Advertisement' filter and budget-event linkage are replaced with an unrelated member/attendance chain

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' ORDER BY T1.spent DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT event_name FROM event WHERE event_id = (SELECT event_id FROM attendance WHERE member_id = (SELECT member_id FROM member ORDER BY amount_spent DESC LIMIT 1))
```

### Q1399 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted escapes the apostrophe in 'Women's Soccer' using a backslash (\'), invalid SQLite string-literal syntax, causing a syntax error; the query also drops the Maya Mclean member-specific filter entirely, just counting total attendance at the event

**Gold SQL:**

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean' AND T3.event_name = 'Women''s Soccer'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM attendance WHERE event_id = (SELECT event_id FROM event WHERE event_name = 'Women\'s Soccer');
```

### Q1401 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** event+expense (source of event_name/expense_description/cost) are replaced wholesale by attendance+budget; event_name doesn't exist on attendance (real on event); the expense_description='Posters' filter and cost output are lost, replaced with budget.amount_spent

**Gold SQL:**

```sql
SELECT T3.cost FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'September Speaker' AND T3.expense_description = 'Posters'
```

**Predicted SQL:**

```sql
SELECT T2.amount_spent FROM attendance AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.event_id WHERE T1.event_name = 'September Speaker';
```

### Q1403 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'member_id' does not exist on budget (budget's only real FK is event_id, from link_to_event; member_id is real on member/attendance/expense/income instead); the query also replaces event_status='Closed' AND remaining<0 with an unrelated amount_spent>amount_remaining comparison

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.event_name
FROM event AS T1
JOIN attendance AS T2 ON T1.event_id = T2.event_id
JOIN budget AS T3 ON T2.member_id = T3.member_id
WHERE T3.amount_spent > T3.amount_remaining
ORDER BY T3.amount_spent DESC
LIMIT 1;
```

### Q1404 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** event (source of event_name='October Meeting') is missing entirely, with event_name misattributed directly to expense (which has no such column) and attendance substituted in its place; amount doesn't exist on attendance either; expense also has no event_id

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
SELECT T2.category, SUM(T3.amount) AS total_value_approved
FROM expense AS T1
JOIN budget AS T2 ON T1.budget_id = T2.budget_id
JOIN attendance AS T3 ON T1.event_id = T3.event_id
WHERE T1.event_name = 'October Meeting'
GROUP BY T2.category;
```

### Q1405 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** event (source of event_name='April Speaker') is missing entirely, misattributed directly to budget instead; expense has no event_id (only member_id/budget_id); amount is also misattributed to expense (whose own cost column is 'cost', not 'amount')

**Gold SQL:**

```sql
SELECT T2.category, SUM(T2.amount) FROM event AS T1 JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.event_name = 'April Speaker' GROUP BY T2.category ORDER BY SUM(T2.amount) ASC
```

**Predicted SQL:**

```sql
SELECT T1.category, SUM(T2.amount) AS total_budgeted
FROM budget AS T1
JOIN expense AS T2 ON T1.event_id = T2.event_id
WHERE T1.event_name = 'April Speaker'
GROUP BY T1.category
ORDER BY T1.category ASC;
```

### Q1409 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** cost is real and directly available on expense/T1 (gold's own target column); predicted instead sums T3.amount, where T3 is attendance (added unnecessarily along with a nonexistent expense.event_id join), which has no amount column at all; an invented 'John Doe' member filter is also added

**Gold SQL:**

```sql
SELECT SUM(cost) FROM expense WHERE expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT SUM(T3.amount) AS total_expense
FROM expense AS T1
JOIN budget AS T2 ON T1.budget_id = T2.budget_id
JOIN attendance AS T3 ON T1.event_id = T3.event_id
WHERE T1.expense_date = '2019-08-20'
AND T3.member_id = (SELECT member_id FROM member WHERE first_name = 'John' AND last_name = 'Doe');
```

### Q1410 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** cost is expense's real column for this concept; predicted references e.amount instead, which doesn't exist on expense (real on budget/income); the join to expense is also routed through a nonexistent expense.event_id via an unnecessary attendance detour instead of member.member_id directly

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name, SUM(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.member_id = 'rec4BLdZHS2Blfp4v'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, SUM(e.amount) AS total_cost
FROM member m
JOIN attendance a ON m.member_id = a.member_id
JOIN expense e ON a.event_id = e.event_id
WHERE a.member_id = 'rec4BLdZHS2Blfp4v'
GROUP BY m.member_id;
```

### Q1411 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** expense links directly to member via member_id (aliased from link_to_member); predicted instead routes through an unnecessary attendance detour, inventing a nonexistent expense.event_id column (expense has no event relationship at all)

**Gold SQL:**

```sql
SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'
```

**Predicted SQL:**

```sql
SELECT e.expense_description
FROM expense e
JOIN attendance a ON e.event_id = a.event_id
JOIN member m ON a.member_id = m.member_id
WHERE m.first_name = 'Sacha' AND m.last_name = 'Harrison';
```

### Q1422 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** category is real on budget, not event; gold's target column is event.type, which predicted doesn't use; the query also references a nonexistent attendance.major_id (major_id is real on member) and misattributes location value 'MU 215' to a major_name filter

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT T2.category FROM attendance AS T1 JOIN event AS T2 ON T1.event_id = T2.event_id WHERE T1.major_id = (SELECT major_id FROM major WHERE major_name = 'MU 215')
```

### Q1427 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** category is real on budget/T2 (already joined and correctly used in WHERE); predicted references T3.category where T3 is an unnecessarily-added attendance table -- alias mix-up; also substitutes a nonsensical category='Budget' condition for gold's type='Guest Speaker' filter

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT T3.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.event_id INNER JOIN attendance AS T3 ON T1.event_id = T3.event_id WHERE T1.location = 'MU 215' AND T2.category = 'Budget' AND T2.amount_spent = 0;
```

### Q1432 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** income (source of amount=50) is replaced wholesale by attendance+member; amount doesn't exist on member; t_shirt_size is misattributed to attendance (real on member); the position='Member' filter is replaced by a nonsensical member_id='Student_Club' condition

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.member_id = 'Student_Club' THEN T2.amount ELSE 0 END) AS REAL) * 100 / SUM(T2.amount) FROM attendance AS T1 INNER JOIN member AS T2 ON T1.member_id = T2.member_id WHERE T1.t_shirt_size = 'medium';
```

### Q1435 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** predicted uses status='closed' and type='game' (lowercase) instead of gold's 'Closed'/'Game' (capitalized) -- SQLite string equality is case-sensitive, so both conditions would always be false; the query also adds an unnecessary attendance join with a correlated event_date subquery instead of filtering event.event_date directly

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.event_name
FROM event AS T1
JOIN attendance AS T2 ON T1.event_id = T2.event_id
WHERE T2.member_id IN (
    SELECT member_id
    FROM attendance
    WHERE event_date BETWEEN '2019-03-15' AND '2020-03-20'
)
AND T1.status = 'closed'
AND T1.type = 'game';
```

### Q1457 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** cost is expense's real column for this concept; predicted references e.amount instead, which doesn't exist on expense (real on budget/income); the query also restructures gold's per-expense-row 'cost > overall average' filter into a per-member 'AVG(cost) > overall average' aggregation, a different question

**Gold SQL:**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, m.email, m.phone
FROM member m
JOIN expense e ON m.member_id = e.member_id
GROUP BY m.member_id
HAVING AVG(e.amount) > (SELECT AVG(amount) FROM expense);
```

### Q1460 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** category is real on budget, not expense (expense's descriptive column is expense_description, a single field); predicted splits gold's single expense_description match into three self-contradictory category='water'/'veggie tray'/'supplies' conditions on the same row; amount also doesn't exist on expense

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, e.expense_description, e.cost
FROM member m
JOIN attendance a ON m.member_id = a.member_id
JOIN expense e ON a.event_id = e.event_id
WHERE e.category = 'water' AND e.category = 'veggie tray' AND e.category = 'supplies'
ORDER BY e.amount DESC
LIMIT 1;
```

### Q1464 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** income (source of amount received on date_received='2019-09-09') is replaced wholesale by attendance+expense, an entirely different concept (money spent, not received); amount doesn't exist on expense (real column there is 'cost'), and expense has no event_id

**Gold SQL:**

```sql
SELECT M.`first_name`, M.`last_name`, I.`amount`
FROM `Income` I
JOIN `Member` M ON M.`member_id` = I.`link_to_member`
WHERE I.`date_received` = '2019-09-09';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, SUM(e.amount) AS total_amount_received
FROM member m
JOIN attendance a ON m.member_id = a.member_id
JOIN expense e ON a.event_id = e.event_id
WHERE e.event_date = '2019-09-09'
GROUP BY m.member_id;
```

---

## superhero (49 failures)

### Q717 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** hero_power+superpower (source of power_name) replaced wholesale by hero_attribute, which has no power_name column (a separate has-power relation, not a numeric attribute); also filters on full_name instead of gold's superhero_name

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.power_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.full_name = '3-D Man';
```

### Q719 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters superhero_name='Super Strength' instead of joining hero_power+superpower on power_name='Super Strength' -- 'Super Strength' is a power, not a hero name; hero_power/superpower are dropped entirely

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.height_cm > 200
```

**Predicted SQL:**

```sql
SELECT COUNT(id) FROM superhero WHERE superhero_name = 'Super Strength' AND height_cm > 200;
```

### Q723 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** hero_power (linking superhero to superpower via power_id) is replaced by hero_attribute, joined via attribute_id=superpower.id -- conflating the separate has-power relation with the numeric-attribute relation

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.attribute_id = T3.id WHERE T1.eye_colour_id = (SELECT id FROM colour WHERE colour = 'Blue') AND T3.power_name = 'Agility';
```

### Q724 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** colour (joined twice, for eye_colour_id and hair_colour_id) is replaced wholesale by hero_attribute+attribute, an unrelated numeric-trait system; attribute_value (real on hero_attribute, not the attribute lookup table T3) is also misattributed

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'blue' AND T3.attribute_value = 'blond';
```

### Q726 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** publisher links directly to superhero via superhero.publisher_id; predicted instead routes through an unnecessary hero_attribute+attribute chain, inventing a nonexistent attribute.publisher_id column to reach publisher

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT T1.id, T1.full_name, T1.height_cm
FROM superhero AS T1
JOIN hero_attribute AS T2 ON T1.id = T2.hero_id
JOIN attribute AS T3 ON T2.attribute_id = T3.id
JOIN publisher AS T4 ON T3.publisher_id = T4.id
WHERE T4.publisher_name = 'Marvel Comics'
ORDER BY T1.height_cm DESC;
```

### Q728 (moderate, aggregate) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** 'superhero_attribute' does not exist anywhere (the real table is 'hero_attribute'); the query also references a nonexistent 'hero' table (the real table is 'superhero') and treats the publisher filter as if 'Marvel Comics' were a superhero_name

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT eye_colour_id, COUNT(*) AS count
FROM superhero_attribute
JOIN hero ON superhero_attribute.hero_id = hero.id
JOIN attribute ON hero_attribute.attribute_id = attribute.id
WHERE superhero_name = 'Marvel Comics'
GROUP BY eye_colour_id
ORDER BY count DESC
LIMIT 1;
```

### Q730 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** hero_power (which has a real power_id column) is replaced by hero_attribute (which only has attribute_id, not power_id); the Marvel Comics publisher EXISTS condition is also dropped entirely

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_power AS T2 INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.id = T2.hero_id)AND EXISTS (SELECT 1 FROM publisher AS T4 WHERE T4.publisher_name = 'Marvel Comics' AND T1.publisher_id = T4.id)
```

**Predicted SQL:**

```sql
SELECT s.full_name, s.gender_id, s.eye_colour_id, s.hair_colour_id, s.skin_colour_id, s.race_id, s.publisher_id, s.alignment_id, s.height_cm, s.weight_kg
FROM superhero s
JOIN hero_attribute sa ON s.id = sa.hero_id
JOIN superpower sp ON sa.power_id = sp.id
WHERE sp.power_name = 'Super Strength';
```

### Q733 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** publisher (publisher_name='Marvel Comics') and colour (colour='Gold') are both replaced wholesale by hero_attribute+attribute, with 'Gold' misattributed as attribute_name; the real filters are replaced by arbitrary hardcoded gender_id/race_id/publisher_id/alignment_id=1 conditions

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Gold' AND T1.gender_id = 1 AND T1.race_id = 1 AND T1.publisher_id = 1 AND T1.alignment_id = 1;
```

### Q736 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** attribute (needed to scope both the outer query and the MIN subquery to 'Intelligence' specifically) is missing entirely; predicted computes the MIN over all attribute types combined, not just Intelligence values

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T2.attribute_value = (SELECT MIN(attribute_value) FROM hero_attribute)
```

### Q737 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on full_name='Copycat' instead of gold's superhero_name='Copycat' -- both real columns on superhero, but different fields; 'Copycat' is very likely stored as the superhero_name (codename), not full_name

**Gold SQL:**

```sql
SELECT T2.race FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id WHERE T1.superhero_name = 'Copycat'
```

**Predicted SQL:**

```sql
SELECT T2.race FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id WHERE T1.full_name = 'Copycat';
```

### Q738 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'hero_attribute_id' does not exist anywhere (hero_attribute's columns are hero_id/attribute_id/attribute_value); the query also self-joins hero_attribute to itself instead of joining the separate 'attribute' table (needed for attribute_name='Durability'), which is missing entirely

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_attribute AS T2 INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Durability' AND T2.attribute_value < 50 AND T1.id = T2.hero_id)
```

**Predicted SQL:**

```sql
SELECT s.superhero_name
FROM superhero s
JOIN hero_attribute sa ON s.id = sa.hero_id
JOIN hero_attribute pa ON sa.attribute_id = pa.hero_attribute_id
WHERE pa.attribute_value < 50;
```

### Q739 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** hero_power is replaced by hero_attribute, joined to superpower via attribute_id=id -- conflating the has-power relation (hero_power) with the numeric-attribute relation (hero_attribute)

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Death Touch'
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 JOIN hero_attribute AS T2 ON T1.id = T2.hero_id JOIN superpower AS T3 ON T2.attribute_id = T3.id WHERE T3.power_name = 'Death Touch';
```

### Q740 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'strength_value' does not exist anywhere (the real approach requires joining hero_attribute+attribute and filtering attribute_name='Strength', attribute_value=100, which predicted entirely drops)

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.attribute_name = 'Strength' AND T2.attribute_value = 100 AND T4.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT COUNT(id) FROM superhero WHERE gender_id = (SELECT id FROM gender WHERE gender = 'female') AND strength_value = 100;
```

### Q743 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** alignment (alignment='Bad') is replaced by hero_attribute+superpower, using invented power names ('Self-Interest'/'Make Decisions Based on Own Moral Code') that don't correspond to a real alignment concept; operator precedence of the added OR/AND also breaks the Marvel Comics condition's scope; an irrelevant gender_id=1 filter is also invented

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender_id = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) AS percentage
FROM superhero AS T1
JOIN hero_attribute AS T2 ON T1.id = T2.hero_id
JOIN superpower AS T3 ON T2.attribute_id = T3.id
WHERE T3.power_name = 'Self-Interest' OR T3.power_name = 'Make Decisions Based on Own Moral Code'
AND T1.publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Marvel Comics');
```

### Q744 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** hero_id doesn't exist on superhero (T2's own PK is just 'id'; hero_id is the FK name used on hero_attribute/hero_power); the query also adds an unnecessary hero_attribute join and replaces gold's single conditional-SUM computation with a self-contradictory WHERE filter ('DC' AND != 'Marvel Comics')

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
SELECT T1.publisher_name, COUNT(T2.hero_id) - COUNT(T3.hero_id) AS difference
FROM publisher AS T1
JOIN superhero AS T2 ON T1.id = T2.publisher_id
JOIN hero_attribute AS T3 ON T2.id = T3.hero_id
WHERE T1.publisher_name = 'DC' AND T1.publisher_name != 'Marvel Comics'
GROUP BY T1.publisher_name;
```

### Q745 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** publisher's own primary key is 'id', not 'publisher_id' (which is the FK name used on superhero referencing publisher); predicted confuses the FK name with the PK name on the table itself

**Gold SQL:**

```sql
SELECT id FROM publisher WHERE publisher_name = 'Star Trek'
```

**Predicted SQL:**

```sql
SELECT publisher_id FROM publisher WHERE publisher_name = 'Star Trek';
```

### Q750 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** predicted drops gold's weight_kg > 0 filter entirely, which excludes missing/zero-weight records from skewing the average

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero WHERE gender_id = (SELECT id FROM gender WHERE gender = 'female');
```

### Q751 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** hero_power+superpower (source of power_name) are replaced wholesale by hero_attribute, which has no power_name column

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.power_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.gender_id = (SELECT id FROM gender WHERE gender = 'Male');
```

### Q753 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** colour (needed for colour='No Colour') is replaced wholesale by hero_attribute; both eye_colour_id and superhero_name (real on superhero/T1) are misattributed to the hero_attribute alias T2 instead

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT T2.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.eye_colour_id IS NULL
```

### Q758 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** race+colour (needed for race='Human' and the colour name output) are both replaced by hero_attribute; hair_colour_id (real on superhero/T1) is misattributed to T2, and the output is the raw FK id rather than the joined colour name

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT T2.hair_colour_id FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.height_cm = 185;
```

### Q760 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** predicted filters T2.publisher_id=1 (publisher has no publisher_id column; its own PK is just 'id') instead of gold's T2.publisher_name = 'Marvel Comics' -- confuses the FK name with the table's own PK, and hardcodes an assumed id value

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.height_cm BETWEEN 150 AND 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.publisher_id = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.height_cm BETWEEN 150 AND 180;
```

### Q761 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only superhero+gender; predicted adds an unnecessary hero_attribute+superpower join via a nonexistent hero_attribute.power_id column; the weight_kg*100 > avg*79 scaling comparison is also simplified to a plain weight_kg > avg comparison

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id WHERE T2.gender = 'Male' AND T1.weight_kg * 100 > ( SELECT AVG(weight_kg) FROM superhero WHERE weight_kg > 0) * 79
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.gender_id = (SELECT id FROM gender WHERE gender = 'male') AND T1.weight_kg > (SELECT AVG(weight_kg) FROM superhero)
```

### Q764 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** hero_power+superpower (source of power_name) are replaced wholesale by superhero+hero_attribute

**Gold SQL:**

```sql
SELECT DISTINCT T2.power_name FROM hero_power AS T1 INNER JOIN superpower AS T2 ON T1.power_id = T2.id WHERE T1.hero_id = 1
```

**Predicted SQL:**

```sql
SELECT T2.power_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.id = 1;
```

### Q765 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** hero_power (with its real power_id link to superpower) is replaced by hero_attribute, joined via attribute_id=superpower.id -- conflating the has-power relation with the numeric-attribute relation; superhero is also added unnecessarily

**Gold SQL:**

```sql
SELECT COUNT(T1.hero_id) FROM hero_power AS T1 INNER JOIN superpower AS T2 ON T1.power_id = T2.id WHERE T2.power_name = 'Stealth'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.attribute_id = T3.id WHERE T3.power_name = 'Stealth';
```

### Q766 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** attribute (needed to identify which attribute_id corresponds to 'Strength') is missing entirely; predicted's subquery picks the globally highest attribute_value across all attribute types, not specifically Strength, and doesn't handle ties the way gold's CTE-based join does

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T2.attribute_id = (SELECT attribute_id FROM hero_attribute ORDER BY attribute_value DESC LIMIT 1)
```

### Q769 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** predicted output is a severely repetitive, truncated generation artifact (100+ nonsensical self-joins on a nonexistent 'superhero_attribute' table) that includes literal markdown code-fence text ('```sql'), causing a syntax error ('unrecognized token')

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL:**

```sql
```sql
SELECT s.full_name
FROM superhero s
JOIN hero_attribute sa ON s.id = sa.hero_id
JOIN hero_attribute pa ON sa.attribute_id = pa.attribute_id
JOIN superhero_attribute sp ON pa.attribute_id = sp.attribute_id
JOIN superhero_attribute sp2 ON sp.attribute_id = sp2.attribute_id
JOIN superhero_attribute sp3 ON sp2.attribute_id = sp3.attribute_id
JOIN superhero_attribute sp4 ON sp3.attribute_id = sp4.attribute_id
JOIN superhero_attribute sp5 ON sp4.attribute_id = sp5.attribute_id
JOIN superhero_attribute sp6 ON sp5.attribute_id = sp6.attribute_id
JOIN superhero_attribute sp7 ON sp6.attribute_id = sp7.attribute_id
JOIN superhero_attribute sp8 ON sp7.attribute_id = sp8.attribute_id
JOIN superhero_attribute sp9 ON sp8.attribute_id = sp9.attribute_id
JOIN superhero_attribute sp10 ON sp9.attribute_id = sp10.attribute_id
JOIN superhero_attribute sp11 ON sp10.attribute_id = sp11.attribute_id
JOIN superhero_attribute sp12 ON sp11.attribute_id = sp12.attribute_id
JOIN superhero_attribute sp13 ON sp12.attribute_id = sp13.attribute_id
JOIN superhero_attribute sp14 ON sp13.attribute_id = sp14.attribute_id
JOIN superhero_attribute sp15 ON sp14.attribute_id = sp15.attribute_id
JOIN superhero_attribute sp16 ON sp15.attribute_id = sp16.attribute_id
JOIN superhero_attribute sp17 ON sp16.attribute_id = sp17.attribute_id
JOIN superhero_attribute sp18 ON sp17.attribute_id = sp18.attribute_id
JOIN superhero_attribute sp19 ON sp18.attribute_id = sp19.attribute_id
JOIN superhero_attribute sp20 ON sp19.attribute_id = sp20.attribute_id
JOIN superhero_attribute sp21 ON sp20.attribute_id = sp21.attribute_id
JOIN superhero_attribute sp22 ON sp21.attribute_id = sp22.attribute_id
JOIN superhero_attribute sp23 ON sp22.attribute_id = sp23.attribute_id
JOIN superhero_attribute sp24 ON sp23.attribute_id = sp24.attribute_id
JOIN superhero_attribute sp25 ON sp24.attribute_id = sp25.attribute_id
JOIN superhero_attribute sp26 ON sp25.attribute_id = sp26.attribute_id
JOIN superhero_attribute sp27 ON sp26.attribute_id = sp27.attribute_id
JOIN superhero_attribute sp28 ON sp27.attribute_id = sp28.attribute_id
JOIN superhero_attribute sp29 ON sp28.attribute_id = sp29.attribute_id
JOIN superhero_attribute sp30 ON sp29.attribute_id = sp30.attribute_id
JOIN superhero_attribute sp31 ON sp30.attribute_id = sp31.attribute_id
JOIN superhero_attribute sp32 ON sp31.attribute_id = sp32.attribute_id
JOIN superhero_attribute sp33 ON sp32.attribute_id = sp33.attribute_id
JOIN superhero_attribute sp34 ON sp33.attribute_id = sp34.attribute_id
JOIN superhero_attribute sp35 ON sp34.attribute_id = sp35.attribute_id
JOIN superhero_attribute sp36 ON sp35.attribute_id = sp36.attribute_id
JOIN superhero_attribute sp37 ON sp36.attribute_id = sp37.attribute_id
JOIN superhero_attribute sp38 ON sp37.attribute_id = sp38.attribute_id
JOIN superhero_attribute sp39 ON sp38.attribute_id = sp39.attribute_id
JOIN superhero_attribute sp40 ON sp39.attribute_id = sp40.attribute_id
JOIN superhero_attribute sp41 ON sp40.attribute_id = sp41.attribute_id
JOIN superhero_attribute sp42 ON sp41.attribute_id = sp42.attribute_id
JOIN superhero_attribute sp43 ON sp42.attribute_id = sp43.attribute_id
JOIN superhero_attribute sp44 ON sp43.attribute_id = sp44.attribute_id
JOIN superhero_attribute sp45 ON sp44.attribute_id = sp45.attribute_id
JOIN superhero_attribute sp46 ON sp45.attribute_id = sp46.attribute_id
JOIN superhero_attribute sp47 ON sp46.attribute_id = sp47.attribute_id
JOIN superhero_attribute sp48 ON sp47.attribute_id = sp48.attribute_id
JOIN superhero_attribute sp49 ON sp48.attribute_id = sp49.attribute_id
JOIN superhero_attribute sp50 ON sp49.attribute_id = sp50.attribute_id
JOIN superhero_attribute sp51 ON sp50.attribute_id = sp51.attribute_id
JOIN superhero_attribute sp52 ON sp51.attribute_id = sp52.attribute_id
JOIN superhero_attribute sp53 ON sp52.attribute_id = sp53.attribute_id
JOIN superhero_attribute sp54 ON sp53.attribute_id = sp54.attribute_id
JOIN superhero_attribute sp55 ON sp54.attribute_id = sp55.attribute_id
JOIN superhero_attribute sp56 ON sp55.attribute_id = sp56.attribute_id
JOIN superhero_attribute sp57 ON sp56.attribute_id = sp57.attribute_id
JOIN superhero_attribute sp58 ON sp57.attribute_id = sp58.attribute_id
JOIN superhero_attribute sp59 ON sp58.attribute_id = sp59.attribute_id
JOIN superhero_attribute sp60 ON sp59.attribute_id = sp60.attribute_id
JOIN superhero_attribute sp61 ON sp60.attribute_id = sp61.attribute_id
JOIN superhero_attribute sp62 ON sp61.attribute_id = sp62.attribute_id
JOIN superhero_attribute sp63 ON sp62.attribute_id = sp63.attribute_id
JOIN superhero_attribute sp64 ON sp63.attribute_id = sp64.attribute_id
JOIN superhero_attribute sp65 ON sp64.attribute_id = sp65.attribute_id
JOIN superhero_attribute sp66 ON sp65.attribute_id = sp66.attribute_id
JOIN superhero_attribute sp67 ON sp66.attribute_id = sp67.attribute_id
JOIN superhero_attribute sp68 ON sp67.attribute_id = sp68.attribute_id
JOIN superhero_attribute sp69 ON sp68.attribute_id = sp69.attribute_id
JOIN superhero_attribute sp70 ON sp69.attribute_id = sp70.attribute_id
JOIN superhero_attribute sp71 ON sp70.attribute_id = sp71.attribute_id
JOIN superhero_attribute sp72 ON sp71.attribute_id = sp72.attribute_id
JOIN superhero_attribute sp73 ON sp72.attribute_id = sp73.attribute_id
JOIN superhero_attribute sp74 ON sp73.attribute_id = sp74.attribute_id
JOIN superhero_attribute sp75 ON sp74.attribute_id = sp75.attribute_id
JOIN superhero_attribute sp76 ON sp75.attribute_id = sp76.attribute_id
JOIN superhero_attribute sp77 ON sp76.attribute_id = sp77.attribute_id
JOIN superhero_attribute sp78 ON sp77.attribute_id = sp78.attribute_id
JOIN superhero_attribute sp79 ON sp78.attribute_id = sp79.attribute_id
JOIN superhero_attribute sp80 ON sp79.attribute_id = sp80.attribute_id
JOIN superhero_attribute sp81 ON sp80.attribute_id = sp81.attribute_id
JOIN superhero_attribute sp82 ON sp81.attribute_id = sp82.attribute_id
JOIN superhero_attribute sp83 ON sp82.attribute_id = sp83.attribute_id
JOIN superhero_attribute sp84 ON sp83.attribute_id = sp84.attribute_id
JOIN superhero_attribute sp85 ON sp84.attribute_id = sp85.attribute_id
JOIN superhero_attribute sp86 ON sp85.attribute_id = sp86.attribute_id
JOIN superhero_attribute sp87 ON sp86.attribute_id = sp87.attribute_id
JOIN superhero_attribute sp88 ON sp87.attribute_id = sp88.attribute_id
JOIN superhero_attribute sp89 ON sp88.attribute_id = sp89.attribute_id
JOIN superhero_attribute sp90 ON sp89.attribute_id = sp90.attribute_id
JOIN superhero_attribute sp91 ON sp90.attribute_id = sp91.attribute_id
JOIN superhero_attribute sp92 ON sp91.attribute_id = sp92.attribute_id
JOIN superhero_attribute sp93 ON sp92.attribute_id = sp93.attribute_id
JOIN superhero_attribute sp94 ON sp93.attribute_id = sp94.attribute_id
JOIN superhero_attribute sp95 ON sp94.attribute_id = sp95.attribute_id
JOIN superhero_attribute sp96 ON sp95.attribute_id = sp96.attribute_id
JOIN superhero_attribute sp97 ON sp96.attribute_id = sp97.attribute_id
JOIN superhero_attribute sp98 ON sp97.attribute_id = sp98.attribute_id
JOIN superhero_attribute sp99 ON sp98.attribute_id = sp99.attribute_id
JOIN superhero_attribute sp100 ON sp99.attribute_id = sp100.attribute_id
JOIN superhero_attribute sp101 ON sp100.attribute_id = sp101.attribute_id
JOIN superhero_attribute sp102 ON sp101.attribute_id = sp102.attribute_id
JOIN superhero_attribute sp103 ON sp102.attribute_id = sp103.attribute_id
JOIN superhero_attribute sp104 ON sp103.attribute_id = sp104.attribute_id
JOIN superhero_attribute sp105 ON sp104.attribute_id = sp105.attribute_id
JOIN superhero_attribute sp106 ON sp105.attribute_id = sp106.attribute_id
JOIN superhero_attribute sp107 ON sp
```

### Q772 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'eye_colour'/'hair_colour'/'skin_colour' (without the '_id' suffix) don't exist; the real columns are eye_colour_id/hair_colour_id/skin_colour_id; the query also adds an unnecessary hero_attribute+superpower join via a nonexistent hero_attribute.power_id column

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT T1.eye_colour, T1.hair_colour, T1.skin_colour
FROM superhero AS T1
JOIN hero_attribute AS T2 ON T1.id = T2.hero_id
JOIN superpower AS T3 ON T2.power_id = T3.id
WHERE T1.gender_id = (SELECT id FROM gender WHERE gender = 'Female')
  AND T1.publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Dark Horse Comics')
```

### Q773 (challenging, retrieval) — **Invalid SQL** (Wrong table)

**Outcome:** `error` · **Reason:** 'color' (American spelling) does not exist; the real table is 'colour' (British spelling); the query also drops the publisher join/output entirely and replaces gold's self-consistency check with three specific hardcoded colour values

**Gold SQL:**

```sql
SELECT T1.superhero_name, T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.eye_colour_id = T1.hair_colour_id AND T1.eye_colour_id = T1.skin_colour_id
```

**Predicted SQL:**

```sql
SELECT T1.publisher_name, T2.publisher_name
FROM superhero AS T1
JOIN hero_attribute AS T2 ON T1.id = T2.hero_id
WHERE T1.eye_colour_id = (SELECT T3.id FROM color AS T3 WHERE T3.colour = 'blue')
  AND T1.hair_colour_id = (SELECT T4.id FROM color AS T4 WHERE T4.colour = 'red')
  AND T1.skin_colour_id = (SELECT T5.id FROM color AS T5 WHERE T5.colour = 'green');
```

### Q775 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gender+colour (needed for gender='Female' and skin colour='Blue') are both replaced by hero_attribute; gender_id (real on superhero/T1) is misattributed to T2, and the whole percentage computation is replaced with an unrelated, arbitrary gender_id-based ratio hardcoded with FK=1 filters

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.gender_id = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T2.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.gender_id = 1 AND T1.race_id = 1 AND T1.alignment_id = 1;
```

### Q779 (simple, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'superhero_id' does not exist on hero_power (the real FK column is 'hero_id')

**Gold SQL:**

```sql
SELECT COUNT(T1.power_id) FROM hero_power AS T1 INNER JOIN superhero AS T2 ON T1.hero_id = T2.id WHERE T2.superhero_name = 'Amazo'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT power_id) FROM hero_power WHERE superhero_id = (SELECT id FROM superhero WHERE superhero_name = 'Amazo');
```

### Q781 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** colour (colour='Amber', joined via superhero.eye_colour_id) is replaced wholesale by hero_attribute+attribute, an unrelated numeric-trait system; attribute_value (real on hero_attribute) is also misattributed to the attribute lookup table T3

**Gold SQL:**

```sql
SELECT T1.height_cm FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T2.colour = 'Amber'
```

**Predicted SQL:**

```sql
SELECT T1.height_cm FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'eye_colour' AND T3.attribute_value = 'amber';
```

### Q782 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** colour (joined twice via eye_colour_id/hair_colour_id, both ='Black') is replaced wholesale by hero_attribute+attribute; attribute_value is misattributed to the attribute lookup table T3 instead of hero_attribute

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'eyes' AND T3.attribute_value = 'black' INTERSECT SELECT T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'hair' AND T3.attribute_value = 'black';
```

### Q785 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** predicted uses alignment='neutral' (lowercase) instead of gold's 'Neutral' (capitalized) -- SQLite string equality is case-sensitive, so this is a surface-form mismatch of the same real value

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id WHERE T2.alignment = 'Neutral'
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id WHERE T2.alignment = 'neutral'
```

### Q786 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'strength' does not exist as a column anywhere (it's a value of attribute_name within hero_attribute+attribute, not its own column); the query drops hero_attribute+attribute entirely, querying superhero instead

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
SELECT COUNT(id) FROM superhero WHERE strength = (SELECT MAX(strength) FROM superhero);
```

### Q788 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gender is missing entirely (needed to scope the whole percentage to Female superheroes); gender_id is misattributed to publisher/T2 (which doesn't have it); publisher_name is also misattributed to T1 (superhero) instead of T2 (publisher, alias mix-up)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.gender_id = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.publisher_name = 'Marvel Comics';
```

### Q790 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** weight_kg is real on superhero/T1 (already present); predicted references T2.weight_kg where T2 is hero_attribute (an unnecessary join) -- alias mix-up; the query also drops the second person ('Charles Chandler') entirely and references a nonexistent hero_attribute.attribute_name

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT T2.weight_kg - T1.weight_kg FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.full_name = 'Emil Blonsky' AND T2.attribute_id = (SELECT attribute_id FROM hero_attribute WHERE attribute_name = 'weight');
```

### Q791 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** predicted drops gold's height_cm > 0 filter entirely, letting missing/zero-height records skew the average

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero;
```

### Q792 (simple, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `error` · **Reason:** superpower (source of power_name) is missing entirely; predicted only joins superhero+hero_power, but power_name lives on superpower, not hero_power (which just has hero_id/power_id)

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T1.superhero_name = 'Abomination'
```

**Predicted SQL:**

```sql
SELECT T2.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id WHERE T1.superhero_name = 'Abomination';
```

### Q794 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** height_cm/weight_kg are real on superhero/T1 (already present); predicted references T2.height_cm/T2.weight_kg where T2 is hero_attribute -- alias mix-up; the whole attribute_name='Speed'/MAX(attribute_value) logic (requiring the missing 'attribute' table) is replaced with an unrelated ORDER BY height_cm ASC

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT T1.full_name, T2.height_cm, T2.weight_kg
FROM superhero AS T1
JOIN hero_attribute AS T2 ON T1.id = T2.hero_id
ORDER BY T2.height_cm ASC
LIMIT 1;
```

### Q796 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** attribute_name (real on the 'attribute' table, aliased h) and attribute_value (real on hero_attribute, aliased a) have their aliases exactly swapped in the SELECT list; also filters on full_name instead of gold's superhero_name

**Gold SQL:**

```sql
SELECT T3.attribute_name, T2.attribute_value FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T1.superhero_name = '3-D Man'
```

**Predicted SQL:**

```sql
SELECT 
    a.attribute_name, 
    h.attribute_value
FROM 
    hero_attribute a
JOIN 
    superhero s ON a.hero_id = s.id
JOIN 
    attribute h ON a.attribute_id = h.id
WHERE 
    s.full_name = '3-D Man';
```

### Q797 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** colour (joined twice for eye_colour_id/hair_colour_id='Blue'/'Brown') is replaced wholesale by an invalid hero_attribute self-join (via a nonexistent hero_attribute.hero_attribute_id column) plus attribute; attribute_value is also misattributed to the attribute lookup table instead of hero_attribute

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT s.full_name
FROM superhero s
JOIN hero_attribute sa ON s.id = sa.hero_id
JOIN hero_attribute ah ON sa.attribute_id = ah.hero_attribute_id
JOIN attribute a ON ah.attribute_id = a.id
WHERE a.attribute_name = 'blue' AND a.attribute_value = 'brown'
```

### Q798 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted filters on full_name instead of gold's superhero_name -- both real columns on superhero, but different fields; these three character names are likely stored as superhero_name, not full_name

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')
```

**Predicted SQL:**

```sql
SELECT T1.publisher_name FROM publisher AS T1 INNER JOIN superhero AS T2 ON T1.id = T2.publisher_id WHERE T2.full_name = 'Hawkman' OR T2.full_name = 'Karate Kid' OR T2.full_name = 'Speedy';
```

### Q800 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** colour (colour='Blue', joined via eye_colour_id) is replaced by hero_attribute+superpower, using an invented 'Blue Eyes' power name; predicted also hardcodes eye_colour_id=2 as a guess at the Blue colour's id instead of joining colour and comparing by name

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.eye_colour_id = 2 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.attribute_id = T3.id WHERE T3.power_name = 'Blue Eyes';
```

### Q806 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** colour (source of the colour name output) is replaced wholesale by hero_attribute; eye_colour_id (real on superhero/T1) is misattributed to T2, and even if fixed would return the raw FK id rather than the joined colour name

**Gold SQL:**

```sql
SELECT T2.colour FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.full_name = 'Karen Beecher-Duncan'
```

**Predicted SQL:**

```sql
SELECT T2.eye_colour_id FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id WHERE T1.full_name = 'Karen Beecher-Duncan';
```

### Q819 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** predicted drops gold's weight_kg = 0 OR weight_kg IS NULL filter entirely, and replaces the difference-of-two-specific-eye-colour-counts (id=7 minus id=1) with a nonsensical COUNT(id)-COUNT(id) expression that always evaluates to zero

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(id) - COUNT(id) FROM superhero WHERE eye_colour_id = (SELECT id FROM colour WHERE colour = 'blue')
```

### Q822 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** alignment (source of alignment='Bad') is missing entirely from predicted's single-table superhero query; only the skin colour='Green' condition (via colour) survives

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL:**

```sql
SELECT COUNT(id) FROM superhero WHERE skin_colour_id = (SELECT id FROM colour WHERE colour = 'green');
```

### Q824 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** hero_power+superpower (source of power_name='Wind Control') are replaced wholesale by hero_attribute+attribute, using an invented/truncated attribute_name='Wind' value that doesn't correspond to the real power-name concept

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Wind Control' ORDER BY T1.superhero_name
```

**Predicted SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 JOIN hero_attribute AS T2 ON T1.id = T2.hero_id JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Wind' ORDER BY T1.superhero_name ASC;
```

### Q825 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** hero_power+superpower+gender (source of power_name='Phoenix Force' and the gender output) are entirely replaced by hero_attribute+attribute; T1.gender doesn't exist on superhero (only gender_id -- the actual gender text lives on the gender lookup table, which is missing)

**Gold SQL:**

```sql
SELECT T4.gender FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.power_name = 'Phoenix Force'
```

**Predicted SQL:**

```sql
SELECT T1.gender FROM superhero AS T1 JOIN hero_attribute AS T2 ON T1.id = T2.hero_id JOIN attribute AS T3 ON T2.attribute_id = T3.id WHERE T3.attribute_name = 'Phoenix Force'
```

### Q829 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** superhero (needed to count heroes per publisher) is missing entirely; predicted's single-table publisher query just counts DISTINCT publisher_name values matching an IN list, which doesn't compute or compare actual hero counts; also uses 'DC' instead of the real value 'DC Comics'

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
SELECT COUNT(DISTINCT publisher_name) AS difference
FROM publisher
WHERE publisher_name IN ('DC', 'Marvel Comics');
```

---

## thrombosis_prediction (50 failures)

### Q1149 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** sex is real on Patient, not Examination; predicted's FROM is Examination alone with no join; the whole in-patient/out-patient CTE ratio logic is also replaced with a nonsensical COUNT(ID)-COUNT(ID) (always zero) expression

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) AS male_count, COUNT(ID) - COUNT(ID) AS female_count
FROM Examination
WHERE sex = 'Male';
```

### Q1150 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only Patient (single table); predicted invents an unnecessary Examination join via a bogus condition comparing first_record_date (Patient.Description's alias) to first_hospital_visit_date (Patient.'First Date''s alias) as if they were columns on two different tables; sex (real on Patient/T2) is misattributed to the Examination alias T1

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.sex = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.first_record_date = T2.first_hospital_visit_date WHERE T2.birthday > '1930-01-01'
```

### Q1152 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only Patient (single table); predicted invents an unnecessary Examination join via a bogus condition comparing first_record_date (only real on Patient, as Description's alias) to Patient.first_hospital_visit_date, treating both as if they belonged to separate tables

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.diagnosis = 'SLE' THEN 1 ELSE 0 END) AS REAL) / COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.first_record_date = T2.first_hospital_visit_date WHERE T1.diagnosis = 'SLE';
```

### Q1153 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** Laboratory (source of the Date output) replaced wholesale by Examination; Patient is common to both, but Examination has no bare 'Date' column (only 'Examination Date'/examination_date); also filters diagnosis='disease', an invented value

**Gold SQL:**

```sql
SELECT T1.Diagnosis, T2.Date FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 30609
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.Date FROM Examination AS T1 JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.ID = 30609 AND T1.diagnosis = 'disease';
```

### Q1155 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** LDH is real on Laboratory, not Patient; predicted's FROM is Patient alone with no join at all; also uses threshold 1.5 instead of gold's 500

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT ID, sex, birthday FROM Patient WHERE LDH > 1.5;
```

### Q1156 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'AGE' does not exist anywhere (age must be computed via STRFTIME on Birthday, which predicted doesn't do); thrombosis_degree is also misattributed to Patient (real only on Examination, which is dropped from the query)

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT ID, AGE FROM Patient WHERE diagnosis = 'coagulation' AND thrombosis_degree > 0;
```

### Q1157 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id is used as the join key (T1=Examination), but Examination has no patient_id column -- all three tables link via the same-named 'ID' column, not a distinct 'patient_id'; sex is also misattributed to Examination (real only on Patient), and thrombosis_degree='Severe' uses a string instead of the real numeric degree value

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.diagnosis
FROM Examination AS T1
JOIN Patient AS T2 ON T1.patient_id = T2.ID
WHERE T1.thrombosis_degree = 'Severe';
```

### Q1162 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID', not 'patient_id'); gold needs only Patient (single table); predicted also invents an unnecessary Examination join and uses admission_type='Outpatient Clinic' instead of the real code value '-'

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.sex = 'F' AND T2.admission_type = 'Outpatient Clinic' AND T1.examination_date >= '1997-01-01' AND T1.examination_date < '1998-01-01';
```

### Q1164 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); predicted also uses sex='W' instead of 'F' and thrombosis_degree=5 (outside the real 0-3 range)

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
SELECT COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.sex = 'W' AND T1.thrombosis_degree = 5 AND T1.examination_date >= '1997-01-01' AND T1.examination_date <= '1997-12-31';
```

### Q1166 (simple, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); the query also entirely abandons gold's complex UNION structure (finding the oldest patient's symptoms, with a fallback branch) for a simple MIN(first_record_date) lookup

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT T1.diagnosis
FROM Examination AS T1
JOIN Patient AS T2 ON T1.patient_id = T2.ID
WHERE T2.first_record_date = (SELECT MIN(first_record_date) FROM Patient);
```

### Q1168 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); T1.first_hospital_visit_date is also wrong (that column belongs to Patient, not Examination); T1.age is entirely hallucinated (no computed age column exists anywhere); sex='S' is also not a real code value

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    T1.first_hospital_visit_date AS last_completed_date,
    T1.age AS initial_arrival_age
FROM 
    Examination AS T1
JOIN 
    Patient AS T2 ON T1.patient_id = T2.ID
WHERE 
    T2.sex = 'S' AND T2.diagnosis = 'SJS'
ORDER BY 
    T1.examination_date DESC
LIMIT 1;
```

### Q1169 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only Patient+Laboratory; predicted invents an unnecessary Examination join via a bogus condition comparing first_record_date (only real on Patient) to Patient.first_hospital_visit_date; sex (real on Patient/T2) is misattributed to Examination/T1, and the UA numeric threshold logic is replaced with an invented diagnosis string

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.sex = 'M' THEN 1 ELSE 0 END) AS REAL) / COUNT(T1.ID) AS ratio
FROM Examination AS T1
JOIN Patient AS T2 ON T1.first_record_date = T2.first_hospital_visit_date
WHERE T1.diagnosis = 'Abnormal Uric Acid Counts';
```

### Q1171 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted uses Patient's own First Date (first_hospital_visit_date) instead of Examination's Examination Date to test the 1990-1993 range; Examination is never joined at all, so the age-at-examination-under-18 condition (requiring both Birthday and Examination Date) is dropped entirely

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE first_hospital_visit_date BETWEEN '1990-01-01' AND '1993-12-31';
```

### Q1175 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); T1.age is hallucinated (no age column exists anywhere); hemoglobin is also misattributed to Examination (real only on Laboratory, which is dropped from the query entirely, and the self-referential MAX subquery would always match zero rows)

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.age, T1.diagnosis
FROM Examination AS T1
JOIN Patient AS T2 ON T1.patient_id = T2.ID
WHERE T1.hemoglobin > (SELECT MAX(hemoglobin) FROM Examination)
ORDER BY T1.hemoglobin DESC
LIMIT 1;
```

### Q1179 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); predicted also selects antinuclear_antibody_pattern instead of gold's aCL IgM (anticardiolipin_igm), and uses examination_date='1994-02-19' where gold's Description='1994-02-19' filter belongs to Patient, not Examination

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT T1.antinuclear_antibody_pattern FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.diagnosis = 'SLE' AND T1.examination_date = '1994-02-19';
```

### Q1185 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); T1.first_hospital_visit_date and T1.total_cholesterol are also wrong-table references (belonging to Patient and Laboratory respectively, neither to Examination); gold's Laboratory table (the real source of T-CHO) is dropped entirely

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.first_hospital_visit_date >= '1981-11-01' AND T1.first_hospital_visit_date < '1982-12-31' THEN T1.total_cholesterol ELSE 0 END) AS REAL) / COUNT(T1.ID) * 100 FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.birthday = '1959-02-18';
```

### Q1187 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Laboratory (source of GPT/ALB) replaced wholesale by Examination; antinuclear_antibody/antinuclear_antibody_pattern (Examination's own, unrelated columns) are substituted in their place

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT ID FROM Examination WHERE examination_date BETWEEN '1987-07-06' AND '1996-01-31' AND antinuclear_antibody > 30 AND antinuclear_antibody_pattern < 4;
```

### Q1189 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'anti_cardiolipin_igm' (with an extra underscore) doesn't match the real S3 alias 'anticardiolipin_igm'; predicted also filters diagnosis='Thrombosis' instead of the real Thrombosis=2 degree column, and drops gold's self-referential AVG*1.2 threshold subquery for a fixed literal 20

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Examination WHERE diagnosis = 'Thrombosis' AND anti_cardiolipin_igm = 20 AND antinuclear_antibody_pattern = 'S';
```

### Q1192 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** 'laboratory.Date' references a table/alias 'laboratory' that was never introduced in the FROM clause (FROM is Patient alone, no JOIN to Laboratory at all); values are also wrong throughout (2023 dates instead of the real 1991 range, admission_type='outpatient' instead of '-')

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT *
FROM Patient
WHERE first_hospital_visit_date = '2023-10-01'
  AND admission_type = 'outpatient'
  AND DATE(laboratory.Date) = '2023-10-01'
  AND total_bilirubin BETWEEN 150 AND 200;
```

### Q1195 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'blood_albumin' doesn't match the real S3 alias 'albumin' (ALB); 'antilactate_dehydrogenase' likewise doesn't match any real column; the query also collapses Patient+Laboratory into a single (wrong) Examination table, where 'sex' doesn't exist either

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(blood_albumin) FROM Examination WHERE diagnosis = 'SLE' AND sex = 'F' AND antilactate_dehydrogenase > 400;
```

### Q1198 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** gold needs only Patient (single table); predicted substitutes Examination instead, which has no sex column (real only on Patient); diagnosis happens to be valid on Examination too since it's a shared column name, masking part of the substitution

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Examination WHERE diagnosis = 'APS' AND sex = 'F';
```

### Q1201 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); predicted also uses COUNT(T1.ID) as the numerator instead of gold's conditional SUM(CASE WHEN sex='F'...), changing what's being measured

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(T1.ID) AS REAL) * 100 / COUNT(T2.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.birthday LIKE '1980%' AND T2.diagnosis = 'RA' AND T2.sex = 'F';
```

### Q1205 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); T1.uric_acid is also wrong (real on Laboratory, dropped entirely, and misattributed to Examination); the SEX-dependent threshold logic (different UA cutoffs for M vs F) is replaced with a single fixed BETWEEN range

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE 
    WHEN T1.uric_acid BETWEEN 100 AND 199 THEN 'true'
    ELSE 'false'
END AS uric_acid_range
FROM Examination AS T1
JOIN Patient AS T2 ON T1.patient_id = T2.ID
WHERE T2.ID = 57266;
```

### Q1208 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'antalcardiolipin_igm' doesn't match the real S3 alias 'anticardiolipin_igm' (a corrupted spelling); the query also collapses Patient+Laboratory into Examination alone and invents a diagnosis string describing GPT instead of filtering the real GPT column

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT ID FROM Examination WHERE diagnosis = 'ALT glutamic pylvic transaminase (GPT)' AND antalcardiolipin_igm > 150 AND antalcardiolipin_igm < 200;
```

### Q1209 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'antalcardiolipin_igg'/'antalcardiolipin_igm' don't match the real S3 aliases 'anticardiolipin_igg'/'anticardiolipin_igm' (corrupted spelling); the query also substitutes Examination for gold's Patient+Laboratory pair and filters on unrelated aCL Ig values instead of GPT

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT diagnosis
FROM Examination
WHERE antalcardiolipin_igg > 150 AND antalcardiolipin_igm < 200
ORDER BY examination_date ASC;
```

### Q1220 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** urea_nitrogen is real on Laboratory, not Patient; predicted's FROM is Patient alone with no join at all; also uses a BETWEEN 100-150 range instead of gold's exact =29

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT ID, sex, birthday FROM Patient WHERE urea_nitrogen BETWEEN 100 AND 150;
```

### Q1225 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); sex is misattributed to Examination (real on Patient), total_bilirubin and tat are misattributed to Patient/Examination respectively (both real only on Laboratory, which is dropped entirely)

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT T1.sex, SUM(T2.total_bilirubin) AS total_bilirubin_level
FROM Examination AS T1
JOIN Patient AS T2 ON T1.patient_id = T2.ID
WHERE T1.tat < 50
GROUP BY T1.sex;
```

### Q1227 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); T1.age is also hallucinated (no age column anywhere); T1.cholesterol doesn't match the real alias 'total_cholesterol' either, and is misattributed to Examination instead of Laboratory; sex='Male' also doesn't match the real code 'M'

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(T1.age) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.sex = 'Male' AND T1.cholesterol > 180;
```

### Q1229 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** TG is real only on Laboratory; predicted's FROM is Examination alone (Patient+Laboratory both dropped), and diagnosis='Triglyceride' is an invented value (Triglyceride is a lab test, not a diagnosis)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Examination WHERE TG > 18.5 AND diagnosis = 'Triglyceride';
```

### Q1231 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); creatinine_phosphokinase is also misattributed to Examination (real only on Laboratory, dropped entirely); the SEX='M' filter and the correct >=250 threshold are also lost

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.birthday BETWEEN '1936-01-01' AND '1956-12-31' AND T1.creatinine_phosphokinase > 15.0;
```

### Q1232 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'age' does not exist anywhere (must be computed via STRFTIME on Birthday); the query also references 'Lab.Date'/'Lab.total_protein'/'Lab.total_cholesterol' via an alias 'Lab' that was never introduced in FROM (only Patient is present, no JOIN to Laboratory at all)

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT ID, sex, age FROM Patient WHERE Lab.Date BETWEEN '2021-01-01' AND '2021-12-31' AND Lab.total_protein < 150 AND Lab.total_cholesterol < 150;
```

### Q1235 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); T1.age is also hallucinated (no age column exists anywhere); red_blood_cell_count is misattributed to Patient/T2 (real only on Laboratory, which is dropped from the query entirely)

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.age
FROM Examination AS T1
JOIN Patient AS T2 ON T1.patient_id = T2.ID
WHERE T2.red_blood_cell_count < 5;
```

### Q1238 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** hemoglobin is real on Laboratory, not Patient; predicted's FROM is Patient alone with no join at all; also drops the HGB range filter (10-17) entirely, using it only as a sort key

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT ID, sex FROM Patient WHERE diagnosis = 'SLE' ORDER BY hemoglobin DESC LIMIT 1;
```

### Q1239 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'AGE' does not exist anywhere (must be computed via STRFTIME on Birthday); 'hematoclit' inside the subquery also doesn't match the real alias 'hematocrit' (HCT) -- a corrupted spelling; the subquery also adds an unnecessary Examination join

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT ID, AGE FROM Patient WHERE ID IN (
    SELECT T1.ID FROM Examination AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.hematoclit > 150
)
```

### Q1241 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); platelet_count is also misattributed to Examination (real only on Laboratory, dropped entirely); the two independent low/high-PLT subqueries in gold are collapsed into a single COUNT(T1.ID) expression duplicated for both output columns

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) AS lower_than_normal, COUNT(T1.ID) AS higher_than_normal
FROM Examination AS T1
JOIN Patient AS T2 ON T1.patient_id = T2.ID
WHERE T1.platelet_count < 100 AND T2.diagnosis = 'Abnormal Platelet Level';
```

### Q1242 (challenging, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'age' does not exist anywhere (must be computed via STRFTIME on Birthday); platelet_count is also misattributed to Patient (real only on Laboratory, which is dropped from the query entirely), and the 1984 date filter is lost

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT *
FROM Patient
WHERE age < 50 AND platelet_count < 50;
```

### Q1243 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id doesn't exist (Examination links via 'ID'); prothrombin_time is misattributed to Examination (real only on Laboratory, dropped entirely) and conflated with the age threshold (55 used for both); T2.age is also hallucinated

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.prothrombin_time > 55 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID WHERE T2.age > 55 AND T2.sex = 'F';
```

### Q1247 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** T1.patient_id and T3.patient_id don't exist (all three tables link via the same-named 'ID' column); 'fibrinogen_level' also doesn't match the real alias 'fibrinogen' (FG); sex='Male' is used instead of 'M', and the WBC range filter is dropped entirely

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.patient_id = T2.ID INNER JOIN Laboratory AS T3 ON T1.id = T3.patient_id WHERE T2.sex = 'Male' AND T3.fibrinogen_level = 0;
```

### Q1251 (simple, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Laboratory (source of IGG/immunoglobulin_g) is replaced wholesale by Examination; predicted uses anticardiolipin_igg (Examination's own, conceptually different 'aCL IgG' column) instead, and a very different threshold (1.5 vs 2000)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE anticardiolipin_igg > 1.5;
```

### Q1252 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Laboratory (source of IGG/immunoglobulin_g) and the Symptoms IS NOT NULL check are replaced by Examination's own anticardiolipin_igg='normal' (a categorical value on a numeric-only real column) and diagnosis='symptoms' (Symptoms is a separate column, not a diagnosis value)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Examination WHERE anticardiolipin_igg = 'normal' AND diagnosis = 'symptoms';
```

### Q1254 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Laboratory (source of IGA/immunoglobulin_a) is replaced by Examination's own anticardiolipin_igg (a completely different antibody test, IgG not IgA) using a categorical 'normal' value instead of gold's numeric 80-500 range; examination_date is also used instead of Patient's First Date

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE anticardiolipin_igg = 'normal' AND examination_date > '1990-01-01';
```

### Q1255 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** Laboratory (source of IGM/immunoglobulin_m) is replaced by Examination's own anticardiolipin_igm (a different antibody test); gold's derived-subquery/GROUP BY/ORDER BY COUNT ranking to find the most common diagnosis among extreme-IGM patients is entirely dropped

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT diagnosis
FROM Examination
WHERE anticardiolipin_igm > 150;
```

### Q1256 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** c_reactive_protein (CRP) is real on Laboratory, not Examination; predicted's FROM is Examination alone with no join; also checks IS NULL on the wrong concept entirely (gold's Description IS NULL check is on Patient, unrelated to CRP)

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Examination WHERE C_reactive_protein IS NULL;
```

### Q1257 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** creatinine (CRE) is real on Laboratory, not Patient; predicted's FROM is Patient alone with no join; the age<70 filter is also conflated with the creatinine threshold (both compared to 70), and diagnosis='Abnormal' is an invented value

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE creatinine < 70 AND diagnosis = 'Abnormal';
```

### Q1265 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** anti_ribonuclear_protein (RNP) is real on Laboratory, not Examination; predicted's FROM is Examination alone with no join; also uses invented values 'normal'/'admitted' instead of the real '0'/'negative' and '+'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE anti_ribonuclear_protein = 'normal' AND diagnosis = 'admitted';
```

### Q1267 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** anti_sm (SM) is real on Laboratory, not Examination; predicted's FROM is Examination alone with no join to Laboratory at all; also uses thrombosis_degree IS NULL instead of gold's MAX(COALESCE(Thrombosis,0))=0

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
SELECT COUNT(ID) FROM Examination WHERE anti_sm = 0 AND thrombosis_degree IS NULL;
```

### Q1270 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** symptoms is real on Examination, not Patient; predicted's FROM is Patient alone with no join at all; SC170 (Laboratory) is also entirely dropped, replaced by an invented diagnosis='Normal' filter, and sex='Female' doesn't match the real code 'F'

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
SELECT COUNT(ID) FROM Patient WHERE diagnosis = 'Normal' AND sex = 'Female' AND symptoms = '';
```

### Q1275 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** anti_centromere/anti_ssb (CENTROMEA/SSB) are real on Laboratory, not Examination; predicted's FROM is Examination alone with no join; also uses invented values 'normal'/'male' instead of the real '0'/'negative' and 'M'

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Examination WHERE anti_centromere = 'normal' AND anti_ssb = 'normal' AND sex = 'male';
```

### Q1281 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'birthdate' doesn't match the real column 'Birthday' (unchanged in S3 as 'birthday'); the query also drops the Laboratory join (needed for GOT) entirely, substituting an invented diagnosis string instead of filtering the real column, and MIN instead of gold's ORDER BY DESC LIMIT 1

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(birthdate) FROM Patient WHERE diagnosis = 'Abnormal glutamic oxaloacetic transaminase';
```

### Q1302 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'creatinine_phosphatase' doesn't match the real S3 alias 'creatinine_phosphokinase' (CPK); the query also drops the Laboratory join (needed for CPK) entirely and abandons the KCT/RVVT/LAC OR-condition for an invented diagnosis='Normal' filter

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL:**

```sql
SELECT COUNT(ID) FROM Examination WHERE creatinine_phosphatase > 0 AND diagnosis = 'Normal';
```

---

## toxicology (39 failures)

### Q197 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** molecule_id is real on atom/bond/molecule but not on connected (which only has atom_id/atom_id2/bond_id); predicted's subquery groups on connected alone; also computes AVG(element), a text column, instead of gold's oxygen-atom-count-per-molecule logic via bond_type='-' single-bond molecules

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(element) FROM atom WHERE molecule_id IN (SELECT molecule_id FROM connected GROUP BY molecule_id HAVING COUNT(*) = 1);
```

### Q198 (challenging, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'bond_count' does not exist anywhere (would need to be computed via COUNT, not a stored column); the query also references molecule_id on connected, which doesn't have that column either, and replaces gold's bond_type='-' molecule-count ratio with an unrelated element='C' filter

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) FROM connected WHERE molecule_id IN (SELECT molecule_id FROM atom WHERE element = 'C');
```

### Q200 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** bond+molecule (source of bond_type='#' and label='+') are replaced wholesale by connected+atom (twice); label and bond_type don't exist on connected at all

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT T1.label, T2.element, T3.element
FROM connected AS T1
JOIN atom AS T2 ON T1.atom_id = T2.atom_id2
JOIN atom AS T3 ON T1.atom_id2 = T3.atom_id
WHERE T1.bond_type = 'C'
  AND T2.element IN ('H', 'O', 'N')
  AND T3.element IN ('H', 'O', 'N');
```

### Q201 (moderate, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `error` · **Reason:** predicted's join from connected to bond uses T3.atom_id, but bond has no atom_id column (only bond_id/molecule_id/bond_type; atom_id is real on atom/connected instead); the atom-to-connected join condition (molecule_id=atom_id2) is also nonsensical, comparing unrelated ID spaces

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.atom_id2 INNER JOIN bond AS T3 ON T2.atom_id2 = T3.atom_id WHERE T3.bond_type = 'D'
```

### Q206 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** molecule_id is real on atom/bond/molecule but not on connected; used inside a subquery scoped to connected, resolving via accidental correlation to the outer atom.molecule_id; atom_id/bond_id values are also given as bare integers (8/9) instead of the real compound string IDs ('TR004_8'/'TR004_8_9')

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE molecule_id IN (SELECT molecule_id FROM connected WHERE atom_id = 8 AND bond_id = 9)
```

### Q207 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** predicted uses bond_type='double' instead of the real symbolic value '='; this would match zero rows since the domain stores bond types as single characters, not spelled-out words; the query also drops the connected join, broadening the scope from atoms directly in a double bond to all atoms in any molecule with one

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE molecule_id IN (SELECT molecule_id FROM bond WHERE bond_type = 'double')
```

### Q208 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** element is real on atom, not molecule; predicted's FROM is molecule alone with no join to atom at all

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT label
FROM molecule
WHERE element = 'H'
GROUP BY label
ORDER BY COUNT(*) DESC
LIMIT 1;
```

### Q212 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** molecule (source of label='-') is missing entirely from predicted's single-table atom query; predicted also picks the most common element (ORDER BY COUNT DESC LIMIT 1) instead of gold's least common (HAVING COUNT = MIN(...))

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
SELECT element FROM atom GROUP BY element ORDER BY COUNT(*) DESC LIMIT 1
```

### Q213 (moderate, retrieval) — **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** predicted attempts to link bond to connected via molecule_id, which doesn't exist on connected (resolving via accidental correlation to the outer bond.molecule_id); the correct link is bond_id, which predicted never uses, so it can't isolate the specific bond between the two named atoms

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT bond_type FROM bond WHERE molecule_id = (SELECT molecule_id FROM connected WHERE atom_id = 'TR004_8' AND atom_id2 = 'TR004_20');
```

### Q215 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** bond (source of bond_type='-') is replaced wholesale by connected within the join, which has no bond_type column; also collapses the two separate iodine/sulfur counts into a single COUNT with contradictory AND conditions, and 'S' is used as a bond_type value though it's really an element code

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id2 WHERE T1.element = 'I' AND T2.bond_type = 'S';
```

### Q218 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** molecule (source of label='+') is missing entirely, replaced by a nonsensical connected+bond chain (bond has no atom_id column); the fluorine ('f') filter is also replaced with an unrelated element='C' (carbon) condition

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.atom_id2 INNER JOIN bond AS T3 ON T2.atom_id2 = T3.atom_id WHERE T1.element = 'C'
```

### Q219 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** molecule (source of label='+') is missing entirely; the join chain (connected to bond via atom_id2=molecule_id, an ID-space mismatch) is also nonsensical, and bond_type is misattributed to connected instead of bond

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM connected AS T1 INNER JOIN bond AS T2 ON T1.atom_id2 = T2.molecule_id INNER JOIN atom AS T3 ON T2.molecule_id = T3.molecule_id WHERE T1.bond_type = 'T';
```

### Q220 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** predicted drops gold's molecule_id = 'TR000' filter entirely, returning the 3 alphabetically-first elements across all molecules instead of just molecule TR000's atoms

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT element FROM atom ORDER BY element ASC LIMIT 3;
```

### Q226 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** bond (source of bond_type='=' and molecule_id='TR008') is replaced wholesale by connected+molecule; bond_type doesn't exist on connected, and 'TR008' (a molecule_id value) is incorrectly compared against molecule.label instead

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'D' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM connected AS T1 INNER JOIN molecule AS T2 ON T1.atom_id2 = T2.molecule_id WHERE T2.label = 'TR008';
```

### Q227 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** gold needs only molecule (single table, label='+'); predicted adds a large, unnecessary atom+connected+bond join chain (with a nonsensical atom_id2=bond_id key) and filters on label='Carcinogenic' instead of the real symbolic value '+', restructuring a simple percentage into unrelated conditions

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.atom_id2 INNER JOIN bond AS T3 ON T2.atom_id2 = T3.bond_id INNER JOIN molecule AS T4 ON T3.molecule_id = T4.molecule_id WHERE T4.label = 'Carcinogenic';
```

### Q228 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** 'TR206' is a molecule_id value, but predicted compares it against molecule.label (a different real column, holding '+'/'-' codes) via a garbled, unnecessary connected+molecule join chain instead of gold's direct atom.molecule_id = 'TR206' filter

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.atom_id2 INNER JOIN molecule AS T3 ON T2.atom_id = T3.molecule_id WHERE T3.label = 'TR206'
```

### Q230 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** label is real on molecule, not atom; the outer SELECT references it without molecule joined at all (molecule only appears in an ID-lookup subquery); that subquery also wrongly treats 'TR060' as a label value instead of the molecule_id it actually is

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT element, label FROM atom WHERE molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR060');
```

### Q231 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** 'TR010' is a molecule_id value, but predicted's subquery filters molecule.label = 'TR010' instead of directly using bond.molecule_id = 'TR010' as gold does -- label holds a different, unrelated set of values ('+'/'-')

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT bond_type
FROM bond
WHERE molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR010')
GROUP BY bond_type
ORDER BY COUNT(*) DESC
LIMIT 1;
```

### Q232 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** bond (source of bond_type='-') is missing entirely from predicted's single-table molecule query; the label='-' filter is also dropped, and the output column is label instead of gold's molecule_id

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT label FROM molecule ORDER BY label ASC LIMIT 3
```

### Q234 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** molecule_id doesn't exist on connected (only atom_id/atom_id2/bond_id); the query also adds an unnecessary atom join with an invented element='H' filter, and drops gold's direct atom_id='TR009_12' OR atom_id2='TR009_12' condition entirely

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.bond_id) FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T2.element = 'H' AND T1.molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR009');
```

### Q236 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** atom_id2 is real on connected, not bond; predicted's FROM is bond alone with no join to connected at all; also uses bare integers (69, 1001) instead of the real compound string IDs ('TR001_6_9', 'TR001')

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT bond_type, atom_id2 FROM bond WHERE bond_id = 69 AND molecule_id = 1001;
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** predicted compares atom_id = 19 (a bare integer) instead of applying gold's SUBSTR(atom_id, -2) = '19' transformation to match the compound string ID's suffix; atom_id values are actually full strings like 'TR009_19', so this comparison would never match

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected WHERE atom_id = 19;
```

### Q240 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** 'TR004' is a molecule_id value; predicted's subquery incorrectly filters molecule.label = 'TR004' instead of directly using atom.molecule_id = 'TR004' as gold does

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR004');
```

### Q242 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** atom (source of element and the SUBSTR(atom_id,-2) suffix filter) is missing entirely, replaced by connected+bond; element doesn't exist on bond (real only on atom); molecule_id BETWEEN 21 AND 25 also uses bare integers instead of the real compound string atom_id suffix match

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.label FROM connected AS T1 INNER JOIN molecule AS T2 ON T1.atom_id2 = T2.molecule_id WHERE T1.bond_id IN (SELECT bond_id FROM bond WHERE element = 'C' AND molecule_id BETWEEN 21 AND 25)
```

### Q243 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'atom_id1' does not exist on connected (the real column is 'atom_id'; only 'atom_id2' is numbered); the query also collapses gold's two separate atom roles (filtered to element='n' and element='p' respectively) into a single self-contradictory WHERE a.element='P' AND a.element='N' on the same alias

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.bond_id, b.molecule_id, b.bond_type
FROM bond b
JOIN connected c ON b.bond_id = c.bond_id
JOIN atom a ON c.atom_id1 = a.atom_id
WHERE a.element = 'P' AND a.element = 'N';
```

### Q244 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** COUNT(T2.bond_id) is used in ORDER BY without any GROUP BY clause, an invalid aggregate-function construction (SQLite raises 'misuse of aggregate: COUNT()'); the query also uses bond_type='double' instead of '=', and joins molecule to connected via a nonsensical molecule_id=atom_id condition

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
SELECT T1.label FROM molecule AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.atom_id WHERE T2.bond_id IN (SELECT bond_id FROM bond WHERE bond_type = 'double')
ORDER BY COUNT(T2.bond_id) DESC LIMIT 1;
```

### Q245 (moderate, aggregate) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** 'bond_count' does not exist anywhere (would need to be computed via COUNT, not a stored column); 'element' also doesn't exist on connected (real on atom, dropped from the query entirely), and 'iodine' is used instead of the real single-character code 'i'

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) FROM connected WHERE element = 'iodine';
```

### Q247 (challenging, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** predicted drops the outer DISTINCT (gold: SELECT DISTINCT T.element); if multiple unconnected atoms share the same element, predicted returns duplicate rows for that element instead of gold's deduplicated list

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE atom_id NOT IN (SELECT atom_id FROM connected);
```

### Q248 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** atom_id2 is connected's own column, not bond's; predicted's join condition (T1.atom_id = T2.atom_id2) misattributes it to bond; the bond_type='#' filter is also dropped entirely (only molecule_id='TR041' survives)

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT T1.atom_id FROM connected AS T1 INNER JOIN bond AS T2 ON T1.atom_id = T2.atom_id2 WHERE T2.molecule_id = 'TR041'
```

### Q249 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** connected (needed to resolve bond_id='TR144_8_19' to specific atom_ids) is missing entirely; predicted instead treats the bond_id string as if it were a molecule.label value, which it isn't (labels hold '+'/'-' codes)

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR144_8_19');
```

### Q253 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** element is real on atom, not bond; predicted's FROM is bond alone with no join to atom (via connected) at all; also uses bond_type='TRIPLE' instead of the real symbolic value '#'

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT element FROM bond WHERE bond_type = 'TRIPLE';
```

### Q255 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** bond+molecule (source of bond_type='-'/label='+') are replaced by a nonsensical connected+bond+atom chain with an ID-space-mismatched join (atom_id2=molecule_id); bond_type is misattributed to connected instead of bond

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.bond_type = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM connected AS T1 INNER JOIN bond AS T2 ON T1.atom_id2 = T2.molecule_id INNER JOIN atom AS T3 ON T2.molecule_id = T3.molecule_id WHERE T1.bond_type = 'C';
```

### Q260 (moderate, aggregate) — **JOIN errors** (Wrong column)

**Outcome:** `error` · **Reason:** bond has no atom_id column (only bond_id/molecule_id/bond_type; atom_id is real on atom/connected); predicted also spells out element values ('Phosphorus'/'Bromine') instead of the real codes ('p'/'br'), and drops the bond_type='#' molecule-scoping filter

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id2 INNER JOIN bond AS T3 ON T2.atom_id2 = T3.atom_id WHERE T1.element = 'Phosphorus' OR T1.element = 'Bromine'
```

### Q263 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** atom (correctly present) is joined through a nonsensical connected+bond chain (mismatched ID spaces: molecule_id=atom_id2, atom_id2=bond_id) instead of gold's atom joined to a molecule-in-bond-type='-' subquery; bond_type='Cl' is also a wrong-concept value (Cl is an element code, not a bond type)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN T1.element = 'Cl' THEN 1 ELSE 0 END) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.atom_id2 INNER JOIN bond AS T3 ON T2.atom_id2 = T3.bond_id WHERE T3.bond_type = 'Cl';
```

### Q268 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** connected (needed to resolve bond_id='TR001_10_11' to specific atom_ids) is missing entirely; predicted instead queries bond.atom_id directly, which doesn't exist there, resolving via accidental correlation to the outer atom.atom_id and effectively matching all atoms rather than just the two in that bond

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE atom_id = (SELECT atom_id FROM bond WHERE bond_id = 'TR001_10_11');
```

### Q273 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** molecule (source of label='+') is missing entirely, replaced by a nonsensical connected+bond chain; bond has no atom_id column (real on atom/connected), and bond_type='C' is substituted for the intended label='+' filter

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'Cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.atom_id2 INNER JOIN bond AS T3 ON T2.atom_id2 = T3.atom_id WHERE T3.bond_type = 'C';
```

### Q281 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `error` · **Reason:** molecule (source of label='+') is missing entirely; gold's SUBSTR(atom_id,-2)='_4' per-atom suffix filter is replaced by an unrelated 'ORDER BY molecule_id DESC LIMIT 4' subquery picking entire molecules; bond also has no atom_id column

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id2 INNER JOIN bond AS T3 ON T2.atom_id = T3.atom_id WHERE T1.molecule_id = (SELECT molecule_id FROM molecule ORDER BY molecule_id DESC LIMIT 4) AND T3.bond_type = 'C' AND T1.element != 'H'
```

### Q282 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** element and molecule_id are real on atom (T3, present) but predicted references them via T1 (connected), which has neither -- misattribution throughout; the query also groups by a wholly invented 'T1.element_label' column, and misuses bond.atom_id (bond has no atom_id)

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT 
    T1.element AS element_label,
    CAST(SUM(CASE WHEN T2.bond_type = 'H' THEN 1 ELSE 0 END) AS REAL) / COUNT(T2.bond_id) AS hydrogen_ratio
FROM 
    connected AS T1
JOIN 
    bond AS T2 ON T1.atom_id2 = T2.atom_id
JOIN 
    atom AS T3 ON T2.molecule_id = T3.molecule_id
WHERE 
    T1.molecule_id = 'TR006'
GROUP BY 
    T1.element_label;
```

### Q327 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** atom (needed to count atoms per molecule, filtered to label='-') is missing entirely, replaced by a nonsensical NOT IN chain against connected; the output column and GROUP BY also change from molecule_id to label, and the counting logic no longer reflects atoms-per-molecule

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT label FROM molecule WHERE molecule_id NOT IN (
    SELECT atom_id FROM connected WHERE atom_id2 IN (
        SELECT atom_id FROM connected
    )
)
GROUP BY label HAVING COUNT(*) > 5;
```

---

