# Qwen2.5-Coder-14B (reflexion, 1 retry) · L3·S3 — hand-classified failures (n=263)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. This is the **reflexion** method: the model gets one self-correction retry after its first attempt; `predicted_sql`/`outcome` below reflect the FINAL state after that retry (if one happened), and classification is based on that final SQL vs `gold_sql`, exactly as in every other pass -- the CSV's extra `attempts`/`initial_outcome` columns are not shown here, though a few reasons note cases where the retry visibly helped or hurt. Predicted SQL uses S3 (descriptive snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. Grouped by database, sorted by question id.

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

### Q5 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** counts DISTINCT s.School (school name) instead of gold's CDSCode -- a different real column (verified school names aren't unique: 17686 rows but only 13875 distinct names), which could undercount; also Virtual='Yes' doesn't match the real domain value 'F', and drops the rtype='S' filter entirely

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
SELECT COUNT(DISTINCT s.School) 
FROM schools s 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
WHERE ss.average_score_math > 400 AND s.Virtual = 'Yes';
```

### Q11 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses only enrollment_ages_5_17 (dropping enrollment_k12 entirely) instead of gold's SUM of Enrollment(K-12)+Enrollment(Ages 5-17); also omits the join to schools needed for the 'School is not NULL' filter entirely

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT county_district_school_code 
FROM frpm 
WHERE enrollment_ages_5_17 > 500;
```

### Q12 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** WHERE-clause ratio uses enrollment_grade_12 instead of gold's number_test_takers (NumTstTakr) -- a different real column -- for the 0.3 threshold check; the SELECT itself (percent_eligible_free_ages_5_17) is verified equivalent to gold's manual ratio, not a bug; also drops the rtype='S' and Enrollment(Ages 5-17)>0 filters

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
WHERE s.enrollment_grade_12 > 0 AND s.number_scores_1500_or_above / s.enrollment_grade_12 > 0.3;
```

### Q17 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops both the `CharterNum IS NOT NULL` and `rtype = 'S'` filters entirely, changing which rows qualify for the ranking

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
    RANK() OVER (ORDER BY ss.average_score_writing DESC) as rank
FROM 
    satscores ss
JOIN 
    schools s ON ss.county_district_school_code = s.county_district_school_code
WHERE 
    ss.average_score_writing > 499;
```

### Q23 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds ABS() around the enrollment difference that gold doesn't have, allowing negative differences (Ages 5-17 > K-12) to also qualify when gold only wants the positive-direction difference

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.School, s.Street, s.City, s.State, s.Zip
FROM frpm f
JOIN schools s ON f.county_district_school_code = s.county_district_school_code
WHERE ABS(f.enrollment_k12 - f.enrollment_ages_5_17) > 30;
```

### Q24 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the `rtype = 'S'` filter entirely (the precomputed percent_eligible_free_k12 column is verified equivalent to gold's manual Free Meal Count/Enrollment ratio, not a bug)

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

### Q25 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on County = 'Riverside' instead of gold's District LIKE 'Riverside%' -- County and District are different real columns; also drops the rtype='S' filter

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
SELECT DISTINCT s.School, s.funding_type 
FROM schools s 
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code 
WHERE s.County = 'Riverside'
GROUP BY s.School, s.funding_type
HAVING AVG(ss.average_score_math) > 400;
```

### Q27 (moderate, retrieval) — **JOIN errors** (Join type error)

**Outcome:** `wrong_answer` · **Reason:** uses INNER JOIN to satscores instead of gold's LEFT JOIN, silently dropping schools that have no satscores row at all (which gold's LEFT JOIN preserves, showing NULL AvgScrWrite for them)

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
    (s.open_date > '1991-12-31' OR s.closed_date < '2000-01-01')
```

### Q28 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** funding_type = 'Locally Funded' (wrong case) doesn't match the stored value 'Locally funded' (verified lowercase 'funded'), zeroing both the outer filter and the inner averaging subquery; also adds an unnecessary DISTINCT inside AVG()

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.School, s.district_ownership_type
FROM schools s
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE f.enrollment_k12 - f.enrollment_ages_5_17 > (
    SELECT AVG(DISTINCT f.enrollment_k12 - f.enrollment_ages_5_17)
    FROM frpm f
    JOIN schools s ON f.county_district_school_code = s.county_district_school_code
    WHERE s.funding_type = 'Locally Funded'
)
AND s.funding_type = 'Locally Funded';
```

### Q31 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits the join to schools entirely, dropping gold's 'School is not null' filter (which restricts which frpm rows are eligible before ranking); the ROW_NUMBER()/BETWEEN 10-11 restructuring is otherwise a reasonable, equivalent restatement of gold's LIMIT 9,2

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT percent_eligible_free_k12
FROM (
    SELECT percent_eligible_free_k12,
           ROW_NUMBER() OVER (ORDER BY enrollment_k12 DESC) as rn
    FROM frpm
) ranked
WHERE rn BETWEEN 10 AND 11;
```

### Q32 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** adds an extra unrequested school_name column alongside the correct percent_eligible_free_or_reduced_price_meal_k12 ratio; WHERE/ORDER BY/LIMIT otherwise match gold exactly (school_ownership_code=66 and ordering by FRPM Count K-12 DESC both correct)

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT 
    f.school_name, 
    f.percent_eligible_free_or_reduced_price_meal_k12
FROM 
    frpm f
JOIN 
    schools s ON f.county_district_school_code = s.county_district_school_code
WHERE 
    s.school_ownership_code = 66
ORDER BY 
    f.free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### Q36 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `rtype = 'S'` filter entirely, potentially including district/county-level aggregate rows in the ranking instead of just school-level rows

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

### Q37 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes frpm's percent_eligible_free_or_reduced_price_meal_k12 ratio for gold's satscores-based NumGE1500/NumTstTakr MIN-ratio subquery -- completely different real-world metrics from different tables

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
    s.Street, 
    s.City, 
    s.State, 
    s.Zip 
FROM 
    frpm f
JOIN 
    schools s ON f.county_district_school_code = s.county_district_school_code
ORDER BY 
    f.percent_eligible_free_or_reduced_price_meal_k12 ASC 
LIMIT 1
```

### Q40 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `AvgScrRead IS NOT NULL` and `rtype = 'S'` filters entirely; also adds a redundant (though likely harmless) extra County='Fresno' condition not in gold

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.Phone
FROM schools s
JOIN satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE s.County = 'Fresno' AND s.District = 'Fresno Unified'
ORDER BY ss.average_score_reading ASC
LIMIT 1;
```

### Q41 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's RANK() OVER (PARTITION BY county ORDER BY AvgScrRead DESC) window function entirely, replacing 'top-5 schools per county by reading score' with 'all non-virtual schools located in the 5 counties with the highest average reading score' -- a fundamentally different selection; also Virtual='Yes' doesn't match the real value 'F'

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
AND ss.county_name IN (
    SELECT county_name
    FROM satscores
    GROUP BY county_name
    ORDER BY AVG(average_score_reading) DESC
    LIMIT 5
)
ORDER BY ss.average_score_reading DESC;
```

### Q46 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on educational_option_name = 'Special' (a fabricated, non-existent EdOpsName value; verified real values are Traditional/Juvenile Court School/etc.) instead of gold's DOC=31, and restructures the query into a SUM(enrollment) GROUP BY State aggregate instead of gold's single top-school-by-enrollment pick -- a fundamentally different, wrong kind of answer

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT s.State, SUM(f.enrollment_k12) AS TotalEnrollment
FROM schools s
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE s.educational_option_name = 'Special'
GROUP BY s.State
ORDER BY TotalEnrollment DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on District = 'Elementary School District' (a DOCType value, not a real District name -- District holds actual names like 'Fresno Unified', verified) instead of gold's DOC=52 (a numeric ownership code); also restructures gold's simple COUNT(School)/12 into an AVG over only the non-zero months, overstating the true annual average since zero-count months are excluded

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(school_count) AS avg_schools_opened
FROM (
    SELECT strftime('%Y-%m', open_date) AS month, COUNT(*) AS school_count
    FROM schools
    WHERE County = 'Alameda' AND District = 'Elementary School District' AND strftime('%Y', open_date) = '1980'
    GROUP BY month
);
```

### Q48 (moderate, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** uses frpm.district_type (text district-type names) instead of gold's schools.DOC (numeric district ownership codes 52/54) -- verified different real columns on different tables; also drops the StatusType='Merged' filter entirely from both subqueries

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
    CAST(COUNT(DISTINCT CASE WHEN district_type = 'Unified School District' THEN county_district_school_code END) AS REAL) / 
    COUNT(DISTINCT CASE WHEN district_type = 'Elementary School District' THEN county_district_school_code END) AS ratio
FROM 
    frpm
WHERE 
    county_name = 'Orange County';
```

### Q50 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `rtype = 'S'` and `AvgScrMath IS NOT NULL` filters entirely, changing which rows are eligible for the ranking

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
SELECT DISTINCT s.School, s.mailing_street 
FROM satscores ss 
JOIN schools s ON ss.county_district_school_code = s.county_district_school_code 
ORDER BY ss.average_score_math DESC 
LIMIT 6, 1;
```

### Q62 (challenging, aggregate) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** uses percent_eligible_free_k12 (verified equivalent to the raw Free Meal Count/Enrollment ratio) without gold's *100 scaling, comparing against a 100x-too-small effective threshold

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
AND percent_eligible_free_k12 < 0.18 
AND percent_eligible_free_k12 IS NOT NULL;
```

### Q72 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses county_name='Fremont' instead of gold's City='Fremont' -- County and City are different real columns, and Fremont is a city (in Alameda County), not a county name, so this likely zeroes the result; the educational_option_name='State Special School' substitution for EdOpsCode='SSS' is a reasonable equivalent (same real-world category, verified as a real EdOpsName value), not a bug

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
FROM frpm f 
JOIN schools s ON f.county_district_school_code = s.county_district_school_code 
WHERE f.academic_year = '2014-2015' 
AND f.county_name = 'Fremont' 
AND s.educational_option_name = 'State Special School';
```

### Q77 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses grade_span_offered (GSoffered) instead of gold's grade_span_served (GSserved) for the 'K-9' filter -- a different real column -- and the literal ('Kindergarten to 9th grade') doesn't match the actual GSoffered/GSserved domain format ('K-9', verified); also selects percent_eligible_free_ages_5_17 (the Free-Meal-only percentage) instead of gold's FRPM-based ratio -- a related but different real column/concept

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT 
    DISTINCT s.School, 
    f.percent_eligible_free_ages_5_17
FROM 
    schools s
JOIN 
    frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE 
    s.County = 'Los Angeles' 
    AND s.grade_span_offered = 'Kindergarten to 9th grade';
```

### Q79 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** Virtual='Yes' doesn't match the real value 'F', zeroing/corrupting the count; also unnecessarily joins frpm and uses frpm.county_name instead of gold's schools.County (verified to hold the same values, so harmless on its own)

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT f.county_name, COUNT(*) AS school_count
FROM schools s
JOIN frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE f.county_name IN ('San Diego', 'Santa Barbara') AND s.Virtual = 'Yes'
GROUP BY f.county_name
ORDER BY school_count DESC
LIMIT 1;
```

### Q82 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's ABS() around longitude entirely, finding the algebraically largest (least negative/most eastern) longitude instead of the one with the largest absolute value (furthest from the prime meridian in either direction)

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT grade_span_offered 
FROM schools 
WHERE Longitude = (SELECT MAX(Longitude) FROM schools);
```

### Q83 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** `no such column: f.educational_option_name` -- educational_option_name is a real column, but it belongs to the already-joined `schools` table (aliased s), not `frpm` (aliased f); the underlying intent (matching gold's frpm."NSLP Provision Status" = 'Multiple Provision Types') needed a completely different column anyway, which predicted never references

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT 
    s.City, 
    COUNT(*) AS school_count
FROM 
    schools s
JOIN 
    frpm f ON s.county_district_school_code = f.county_district_school_code
WHERE 
    s.grade_span_offered = 'Kindergarten to 8th' 
    AND f.educational_option_name = 'Multiple Provision Types'
GROUP BY 
    s.City;
```

### Q85 (moderate, retrieval) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** uses percent_eligible_free_k12 (verified equivalent to the raw Free Meal Count/Enrollment ratio) without gold's *100 scaling on the ratio; the WHERE filter (admin_first_name_1='Alusine') itself matches gold exactly

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT DISTINCT f.percent_eligible_free_k12, f.district_code
FROM frpm f
JOIN schools s ON f.county_district_school_code = s.county_district_school_code
WHERE s.admin_first_name_1 = 'Alusine'
   OR s.admin_first_name_2 = 'Alusine'
   OR s.admin_first_name_3 = 'Alusine';
```

### Q87 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** substitutes instruction_level_name (EILName) OR-conditions for gold's DOC=54 AND SOC=62 numeric codes entirely -- a different real column, and neither literal used matches the actual EILName domain (verified real values include 'Intermediate/Middle/Junior High'; 'Unified School' isn't an EILName value at all); also City='San Bernardino City Unified' doesn't match the real City value 'San Bernardino' (that's the District name, not the City, verified)

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

## debit_card_specializing (23 failures)

### Q1472 (moderate, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits customers/Segment='LAM' filter entirely (no join to customers at all); also fails to SUM per customer, comparing to a global MIN reading instead of gold's per-customer SUM ASC LIMIT 1

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

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', date) misapplied to yearmonth's 'YYYYMM' text format returns NULL, so the WHERE filter matches zero rows; also drops the per-customer SUM/derived-table + /12 scaling structure (reflexion retry only added AVG(DISTINCT ...), doesn't touch the blocking predicate)

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(DISTINCT consumption) 
FROM yearmonth 
JOIN customers ON yearmonth.customer_id = customers.customer_id 
WHERE customers.segment = 'SME' AND strftime('%Y', yearmonth.date) = '2013';
```

### Q1476 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** strftime('%Y', y.date) misapplied to yearmonth's 'YYYYMM' text returns NULL for every row, so both SUM(CASE...) terms are zero; reflexion retry added spurious DISTINCT inside each SUM, which doesn't address the blocking predicate

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(DISTINCT CASE WHEN c.currency = 'CZK' THEN y.consumption ELSE 0 END) - 
    SUM(DISTINCT CASE WHEN c.currency = 'EUR' THEN y.consumption ELSE 0 END) AS consumption_difference
FROM 
    customers c
JOIN 
    yearmonth y ON c.customer_id = y.customer_id
WHERE 
    strftime('%Y', y.date) = '2012';
```

### Q1479 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** groups by strftime('%Y', date) (NULL for every row since Date is 'YYYYMM' text) instead of gold's SUBSTR(Date,1,4), collapsing all years into one NULL group; reflexion retry only added a spurious DISTINCT inside SUM, doesn't fix the grouping key

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT strftime('%Y', date) AS year, SUM(DISTINCT consumption) AS total_consumption
FROM yearmonth
JOIN customers ON yearmonth.customer_id = customers.customer_id
WHERE customers.currency = 'CZK'
GROUP BY year
ORDER BY total_consumption DESC
LIMIT 1;
```

### Q1480 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** WHERE strftime('%Y', yearmonth.date) = '2013' misapplied to 'YYYYMM' text returns NULL, matching zero rows; reflexion retry restructured the GROUP BY/aggregate (strftime('%Y-%m',...) + SUM instead of the original's raw date + MAX) but the blocking predicate bug persists unchanged, so the restructuring is moot

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT strftime('%Y-%m', date) AS month, SUM(consumption) AS total_consumption
FROM yearmonth
JOIN customers ON yearmonth.customer_id = customers.customer_id
WHERE customers.segment = 'SME' AND strftime('%Y', yearmonth.date) = '2013'
GROUP BY strftime('%Y-%m', date)
ORDER BY total_consumption DESC
LIMIT 1;
```

### Q1481 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** innermost subqueries reference `consumption` directly on `customers` with no join to yearmonth in that scope (`no such column: consumption`) -- consumption is real but lives only on yearmonth; overall logic also diverges hugely from gold's segment-comparison CTE chain

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
           WHERE currency = 'CZK' AND segment = 'SME' 
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
           WHERE currency = 'CZK' AND segment = 'LAM' 
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
           WHERE currency = 'CZK' AND segment = 'LAM' 
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
           WHERE currency = 'CZK' AND segment = 'KAM' 
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
           WHERE currency = 'CZK' AND segment = 'KAM' 
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
           WHERE currency = 'CZK' AND segment = 'SME' 
           ORDER BY consumption DESC 
           LIMIT 1
       )
    ) AS diff_kam_sme;
```

### Q1482 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** reflexion retry wraps the year extraction in a derived table (`strftime('%Y', date) AS year`) but strftime still can't parse yearmonth's 'YYYYMM' text, so `year` is NULL for every row and every CASE WHEN y.year=2013/2012 branch is zero, corrupting all three ratios via 0/0; also restructures gold's 3 flat scalar columns into a GROUP BY c.segment row-per-segment shape

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    c.segment,
    ((SUM(CASE WHEN y.year = 2013 THEN y.consumption ELSE 0 END) - SUM(CASE WHEN y.year = 2012 THEN y.consumption ELSE 0 END)) * 100.0 / SUM(CASE WHEN y.year = 2012 THEN y.consumption ELSE 0 END)) AS percentage_change
FROM 
    customers c
JOIN 
    (SELECT 
        customer_id, 
        strftime('%Y', date) AS year, 
        SUM(consumption) AS consumption
     FROM 
        yearmonth
     GROUP BY 
        customer_id, 
        year) y ON c.customer_id = y.customer_id
WHERE 
    c.currency = 'EUR' AND c.segment IN ('SME', 'LAM', 'KAM')
GROUP BY 
    c.segment;
```

### Q1483 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN uses ISO-hyphenated date bounds ('2013-08-01'/'2013-11-30') against Date stored as plain 'YYYYMM' text; verified empirically these bounds match 0 of customer 6's rows (vs 4 for the correct '201308'/'201311' bounds)

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
    SUM(CASE WHEN country = 'Czech Republic' THEN 1 ELSE 0 END) - 
    SUM(CASE WHEN country = 'Slovakia' THEN 1 ELSE 0 END) AS difference
FROM 
    gasstations
WHERE 
    segment = 'discount';
```

### Q1486 (simple, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** unnecessary JOIN to transactions_1k changes the query grain from customer to transaction; COUNT(DISTINCT transaction_id) still counts per-transaction not per-customer, so a CZK customer with 5 transactions still contributes 5, inflating both sides of the difference

**Gold SQL:**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(DISTINCT CASE WHEN c.currency = 'CZK' THEN t.transaction_id END) - 
    COUNT(DISTINCT CASE WHEN c.currency = 'EUR' THEN t.transaction_id END) AS difference
FROM 
    customers c
JOIN 
    transactions_1k t ON c.customer_id = t.customer_id
WHERE 
    c.segment = 'SME';
```

### Q1490 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `ambiguous column name: customer_id` -- reflexion retry changed the original's COUNT(*) to COUNT(DISTINCT customer_id) (attempting to fix the dedup issue from the first attempt) but customer_id is unqualified and exists on both joined tables, turning a wrong_answer into a hard execution error; the underlying INNER-vs-LEFT JOIN type bug (dropping customers with no yearmonth rows) is also still present

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consumption > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customer_id) 
FROM yearmonth 
JOIN customers ON yearmonth.customer_id = customers.customer_id 
WHERE customers.segment = 'LAM';
```

### Q1493 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** `date LIKE '2012-02-%'` assumes ISO-hyphenated formatting; verified empirically this matches 0 rows against Date stored as 'YYYYMM' text (vs gold's exact match Date='201202' which matches 18324 rows)

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customer_id) 
FROM yearmonth 
WHERE date LIKE '2012-02-%';
```

### Q1498 (simple, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** GROUP BY is missing entirely (gold groups by SUBSTR(Date,5,2), i.e. by month); the date range filter (date >= '2012-01-01' AND < '2013-01-01') happens to coincidentally match the same 158808 rows as gold's SUBSTR/LIKE filter (verified empirically) so it is not the blocking bug -- the real bug is the missing month grouping plus MAX substituted for SUM, returning a single largest individual reading instead of the peak month's total

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) 
FROM yearmonth 
WHERE date >= '2012-01-01' AND date < '2013-01-01';
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

**Outcome:** `wrong_answer` · **Reason:** country='Czech Republic' instead of the stored code 'CZE'; date comparison itself is fine since transactions_1k.Date is ISO-formatted

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
WHERE gasstations.country = 'Czech Republic' AND transactions_1k.date > '2012-01-01' AND transactions_1k.date IS NOT NULL;
```

### Q1524 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses amount=548.4 instead of gold's price=548.4 (different real column on transactions_1k) to identify the transaction; note the reflexion retry actually fixed the original attempt's wrong-table join (customers -> gasstations) but left this wrong-column bug in place

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT g.country 
FROM transactions_1k t 
JOIN gasstations g 
ON t.gas_station_id = g.gas_station_id 
WHERE t.date = '2012-08-24' AND t.amount = 548.4;
```

### Q1525 (simple, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `ambiguous column name: customer_id` -- reflexion retry introduced COUNT(DISTINCT customer_id) unqualified across two joined tables that both have a customer_id column, turning the original wrong_answer into a hard execution error

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT customer_id) 
FROM customers 
JOIN transactions_1k ON customers.customer_id = transactions_1k.customer_id 
WHERE transactions_1k.date = '2012-08-25';
```

### Q1526 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** subquery uses amount=634.8 instead of gold's price=634.8 (different real column) to identify the customer; also misses the per-year SUM aggregation, self-joining yearmonth month-rows directly instead of aggregating consumption per year first

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
        LIMIT 1
    );
```

### Q1528 (simple, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** unnecessary JOIN to transactions_1k multiplies each gas station row by its transaction count, inflating the numerator; denominator is further broken -- COUNT(DISTINCT g.segment) counts distinct segment labels (at most 3) rather than SUM(Country='SVK'); also 'premium' case differs from gold's 'Premium'

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN g.segment = 'premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT g.segment)) AS percentage_premium
FROM 
    gasstations g
JOIN 
    transactions_1k t ON g.gas_station_id = t.gas_station_id
WHERE 
    g.country = 'SVK';
```

### Q1529 (moderate, aggregate) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** SUM(amount) / SUM(CASE...THEN amount...) drops the *Price multiplier gold applies in both the total and the August-2012 branch (Amount*Price)

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

### Q1531 (moderate, aggregate) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** ranks customers by SUM(t.amount) (item quantity) instead of gold's SUM(Amount*Price) (money spent) to pick the top customer, and computes average_price_per_item as plain AVG(t.price) instead of gold's quantity-weighted SUM(Price*Amount)/SUM(Amount)

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

**Outcome:** `wrong_answer` · **Reason:** y.date LIKE '2012-08-%' assumes ISO-hyphenated formatting and fails to match yearmonth's 'YYYYMM' text (verified empirically that hyphenated LIKE patterns match 0 rows), zeroing the result; also drops the /Amount from gold's Price/Amount > 29.00 ratio, using raw t.price > 29.00 instead

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT y.consumption
FROM yearmonth y
JOIN customers c ON y.customer_id = c.customer_id
WHERE c.customer_id IN (
    SELECT t.customer_id
    FROM transactions_1k t
    WHERE t.product_id = 5 AND t.price > 29.00
)
AND y.date LIKE '2012-08-%';
```

---

## european_football_2 (27 failures)

### Q1025 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2016' doesn't match the stored format 'YYYY/YYYY' (real value '2015/2016'), zeroing the result

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

### Q1028 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's 'count of away-wins per team, tied for the per-league maximum via a nested MAX(win_count) subquery' with a UNION ALL of ALL wins (home+away combined) ordered/limited to top 1 -- a fundamentally different aggregation; also season='2010' doesn't match the stored 'YYYY/YYYY' format (real value '2009/2010'), and selects team_short_name instead of gold's team_long_name

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T3.team_short_name 
FROM (
    SELECT away_team_api_id AS team_api_id 
    FROM Match 
    WHERE league_id = (SELECT id FROM League WHERE name = 'Scotland Premier League') 
      AND season = '2010' 
      AND away_team_goals > home_team_goals
    UNION ALL
    SELECT home_team_api_id AS team_api_id 
    FROM Match 
    WHERE league_id = (SELECT id FROM League WHERE name = 'Scotland Premier League') 
      AND season = '2010' 
      AND home_team_goals > away_team_goals
) AS T1
JOIN Team AS T3 ON T1.team_api_id = T3.team_api_id
GROUP BY T3.team_short_name 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1029 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** adds an unrequested team_long_name column alongside the correct buildup_play_speed; join/ordering/limit otherwise match gold exactly

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

**Outcome:** `wrong_answer` · **Reason:** season='2016' doesn't match the stored format 'YYYY/YYYY' (real value '2015/2016'), zeroing the result

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

### Q1031 (challenging, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** adds an unrequested player_name column alongside the correctly-computed age; the age formula (a valid equivalent using boolean subtraction instead of CASE) and the sprint_speed/date-range filters otherwise match gold's intent

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
    DISTINCT P.player_name, 
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

**Outcome:** `wrong_answer` · **Reason:** collapses gold's tie-preserving HAVING COUNT(m.id) = (SELECT MAX(match_count)...) into a plain ORDER BY match_count DESC LIMIT 1, which would only return one league even if multiple leagues tie for the maximum match count

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

### Q1037 (challenging, aggregate) — **Other** (Missing/redundant DISTINCT/DESC)

**Outcome:** `wrong_answer` · **Reason:** uses SUM(CASE WHEN preferred_foot='left'...) instead of gold's COUNT(DISTINCT CASE WHEN...THEN id END); since a player can have dozens of Player_Attributes snapshot rows (verified up to 56), a player is counted once per matching snapshot rather than once overall, corrupting the numerator relative to the correctly-deduplicated denominator

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN preferred_foot = 'left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT Player.player_api_id) 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.player_api_id = Player.player_api_id 
WHERE strftime('%Y', Player.birthday) BETWEEN '1987' AND '1992';
```

### Q1080 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** preferred_foot='Left' (wrong case; real stored value is lowercase 'left') and attacking_work_rate='High' (wrong case and wrong value entirely -- gold needs 'low', and real domain is also lowercase); also drops DISTINCT, risking double-counting players with multiple qualifying snapshots

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

**Outcome:** `wrong_answer` · **Reason:** adds a fabricated `attacking_work_rate IN ('Medium','Low')` condition with no basis in the question; also defensive_work_rate='High' uses Title Case where the stored domain is lowercase ('high')

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
AND pa.attacking_work_rate IN ('Medium', 'Low') 
AND pa.defensive_work_rate = 'High';
```

### Q1091 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** l.name = 'Jupiler League' doesn't match the actual stored value 'Belgium Jupiler League' (League.name is a single combined string; verified splitting it into a separate Country.name='Belgium' condition via an unneeded join doesn't help since the League.name comparison itself is truncated/wrong), zeroing the result

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

### Q1094 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's two independent per-player 'latest rating as of the most recent date' CTEs with a join requiring both players' Player_Attributes rows to share the exact same date (a.date = b.date), which returns zero or an arbitrary/wrong pairing instead of each player's true most-recent rating

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
    Player_Attributes b ON a.date = b.date
JOIN 
    Player p2 ON b.player_api_id = p2.player_api_id
WHERE 
    p1.player_name = 'Ariel Borysiuk' 
    AND p2.player_name = 'Paulin Puel'
    AND a.date = b.date;
```

### Q1098 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on team_short_name='Ajax' instead of gold's team_long_name='Ajax' (verified Ajax's real team_short_name is 'AJA'), zeroing the join entirely; also orders by date DESC instead of gold's chanceCreationPassing DESC, a different selection criterion for which snapshot to report

**Gold SQL:**

```sql
SELECT t2.chanceCreationPassing, t2.chanceCreationPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Ajax' ORDER BY t2.chanceCreationPassing DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.chance_creation_passing, T2.chance_creation_passing_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id 
WHERE T1.team_short_name = 'Ajax'
ORDER BY T2.date DESC
LIMIT 1;
```

### Q1102 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** PA.date = '2016-06-23' (exact string equality) never matches Player_Attributes' stored datetime format ('2016-06-23 00:00:00', verified empirically), unlike gold's SUBSTR(date,1,10) prefix extraction; the ORDER BY birthday DESC vs gold's ASC is moot given zero rows

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
ORDER BY P.birthday DESC 
LIMIT 1;
```

### Q1103 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** Player_Attributes.date = '2016-02-04' (exact string equality) never matches the stored datetime format ('2016-02-04 00:00:00', verified empirically), unlike gold's SUBSTR(date,1,10) prefix extraction; the added DISTINCT is immaterial since the equality already returns zero rows

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT DISTINCT overall_rating 
FROM Player_Attributes 
JOIN Player ON Player_Attributes.player_api_id = Player.player_api_id 
WHERE Player.player_name = 'Aaron Mooy' AND Player_Attributes.date = '2016-02-04';
```

### Q1107 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** drops gold's secondary tie-breaker `ORDER BY date ASC` (after crossing DESC), so ties in crossing could return an arbitrary/different row than gold's earliest-date pick; the player_api_id vs player_fifa_api_id join key doesn't change results here since Kevin Constant has both IDs consistently populated (verified)

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

**Outcome:** `wrong_answer` · **Reason:** ta.date = '2010-02-22' (exact string equality) never matches Team_Attributes' stored datetime format ('2010-02-22 00:00:00', verified empirically), unlike gold's LIKE '2010-02-22%' prefix match; zeroes the result

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT ta.buildup_play_passing_class 
FROM Team_Attributes ta 
JOIN Team t ON ta.team_api_id = t.team_api_id 
WHERE t.team_long_name = 'FC Lorient' AND ta.date = '2010-02-22'
LIMIT 1;
```

### Q1113 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** T2.date = '2015-09-10' (exact string equality) never matches Team_Attributes' stored datetime format, unlike gold's LIKE '2015-09-10%' prefix match; zeroes the result

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
WHERE T1.team_long_name = 'Hannover 96' AND T2.date = '2015-09-10'
LIMIT 1;
```

### Q1114 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** BETWEEN '2007-02-22' AND '2016-04-21' against Player_Attributes' datetime-suffixed date column excludes any row falling exactly on the upper-bound day (verified empirically: 32 matching rows vs gold's 33, average 75.28 vs gold's 75.39) because 'YYYY-MM-DD 00:00:00' lexicographically exceeds the bare-date upper bound

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

### Q1115 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** L.date = '2013-07-12' (exact string equality) never matches Player_Attributes' stored datetime format, zeroing the result; the L.date = J.date join constraint is otherwise consistent with gold's same-date intent

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
    AND L.date = '2013-07-12'
LIMIT 1;
```

### Q1116 (simple, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DENSE_RANK() OVER (ORDER BY height DESC) window function (which correctly returns ALL players tied for the max height) in favor of a plain GROUP BY player_name / ORDER BY / LIMIT 10, which returns the wrong number of rows whenever the number of max-height ties differs from exactly 10

**Gold SQL:**

```sql
SELECT player_name FROM (SELECT player_name, height, DENSE_RANK() OVER (ORDER BY height DESC) as rank FROM Player) WHERE rank = 1
```

**Predicted SQL:**

```sql
SELECT player_name 
FROM (
    SELECT player_name, MAX(height) AS max_height 
    FROM Player 
    GROUP BY player_name
) 
ORDER BY max_height DESC 
LIMIT 10;
```

### Q1122 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by `strength` instead of gold's `overall_rating` (verified different real columns with different values, e.g. 67 vs 76) to find the 'best' player, and collapses gold's tie-inclusive `= (SELECT MAX(overall_rating)...)` filter into a plain ORDER BY/LIMIT 1 that would only return one player even if several are tied for the true max

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT P.player_name 
FROM Player P 
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id 
ORDER BY PA.strength DESC 
LIMIT 1
```

### Q1130 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** chance_creation_passing_class = 'Low' is not a real domain value (verified real values are Normal/Risky/Safe) -- should be 'Safe'

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T.team_short_name 
FROM Team_Attributes AS TA 
JOIN Team AS T ON TA.team_api_id = T.team_api_id 
WHERE TA.chance_creation_passing_class = 'Low';
```

### Q1136 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds two fabricated conditions gold never has (a nested double-MAX `potential` constraint, and an unrelated `attacking_work_rate = 'High'` filter), and uses preferred_foot='Left' (wrong case; real stored value is lowercase 'left') instead of gold's simple two-condition filter (preferred_foot='left' AND crossing=MAX(crossing))

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Player_Attributes 
WHERE potential = (SELECT MAX(potential) FROM Player_Attributes WHERE crossing = (SELECT MAX(crossing) FROM Player_Attributes)) 
AND preferred_foot = 'Left' 
AND attacking_work_rate = 'High';
```

### Q1139 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** date = '2008-09-24' (exact string equality) never matches Match's stored datetime format (verified empirically), and League.name = 'Belgian Jupiler League' doesn't match the real stored value 'Belgium Jupiler League' -- both independently zero the result

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
JOIN 
    League ON Match.league_id = League.id 
WHERE 
    date = '2008-09-24' 
    AND League.name = 'Belgian Jupiler League';
```

### Q1145 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** season='2015-2016' (hyphen) doesn't match the stored format 'YYYY/YYYY' (real value '2015/2016' uses a slash), zeroing the result

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

### Q1147 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** orders by `strength` instead of gold's `overall_rating` (verified different real columns with different values), and collapses gold's tie-inclusive `= (SELECT MAX(overall_rating)...)` filter into a plain ORDER BY/LIMIT 1

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.overall_rating = ( SELECT MAX(overall_rating) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT P.player_name 
FROM Player P 
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id 
ORDER BY PA.strength DESC 
LIMIT 1
```

### Q1148 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses `strength` instead of gold's `overall_rating` for the >70 condition (verified different real columns); also drops the height<180 WHERE restriction entirely, moving it only into the CASE numerator and changing the denominator's scope from 'short players only' to 'all player-attribute rows', and omits DISTINCT despite players having multiple Player_Attributes snapshots (verified up to 56 per player)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN P.height < 180 AND PA.strength > 70 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Player P
JOIN Player_Attributes PA ON P.player_api_id = PA.player_api_id;
```

---

## financial (21 failures)

### Q89 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** outer SELECT references alias `a`, which is only declared inside the derived subquery's own scope (not in the outer FROM, which only has `issuance_accounts` and `d`); the derived subquery also doesn't project district_id at all despite the outer join needing it; also trans.type='issuance' isn't a real value (real values are PRIJEM/VYDAJ/VYBER) and region='East Bohemia' is wrong case (real value 'east Bohemia')

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT a.account_id) 
FROM (
    SELECT DISTINCT a.account_id 
    FROM account a 
    JOIN trans t ON a.account_id = t.account_id 
    WHERE t.type = 'issuance'
) AS issuance_accounts 
JOIN district d ON issuance_accounts.district_id = d.district_id 
WHERE d.region = 'East Bohemia';
```

### Q93 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** region = 'North Bohemia' (wrong case) doesn't match the stored value 'north Bohemia', zeroing the result

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

### Q95 (moderate, aggregate) — **Other** (Missing/redundant DISTINCT/DESC)

**Outcome:** `wrong_answer` · **Reason:** reverses the ORDER BY direction (ASC instead of gold's DESC) on birth_date, selecting the OLDEST client instead of the YOUNGEST; also adds a LIMIT 1 that could drop legitimate additional accounts gold's GROUP BY would include for that client

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.account_id
FROM account a
JOIN disp d ON a.account_id = d.account_id
JOIN client c ON d.client_id = c.client_id
JOIN district di ON a.district_id = di.district_id
ORDER BY c.birth_date ASC, di.average_salary DESC
LIMIT 1;
```

### Q98 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** statement_frequency = 'weekly' doesn't match the real stored value 'POPLATEK TYDNE', zeroing the result; also adds a fabricated `status = 'A'` condition not present in gold, and restructures the ranking via SUM(amount) per account/GROUP BY instead of gold's raw per-loan amount ordering

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE STRFTIME('%Y', l.date) = '1997' AND l.status = 'A' AND a.statement_frequency = 'weekly'
GROUP BY a.account_id
ORDER BY SUM(l.amount) ASC
LIMIT 1;
```

### Q99 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** adds an extra unrequested l.amount column alongside the correct account_id; the MAX-equality subquery approach is a reasonable equivalent to gold's ORDER BY DESC LIMIT 1 except it could return multiple tied rows instead of gold's single one

**Gold SQL:**

```sql
SELECT T1.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T2.date) = '1993' AND T1.duration > 12 ORDER BY T1.amount DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT a.account_id, l.amount AS approved_amount
FROM account a
JOIN loan l ON a.account_id = l.account_id
WHERE l.duration_months > 12 
  AND strftime('%Y', a.date) = '1993'
  AND l.amount = (
    SELECT MAX(amount)
    FROM loan
    WHERE duration_months > 12 
      AND account_id IN (
        SELECT account_id
        FROM account
        WHERE strftime('%Y', date) = '1993'
      )
  );
```

### Q115 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** joins to district via disp/account (the account's servicing branch's district) instead of gold's direct client.district_id -> district (the client's own home district) -- a different real join path/table role; also region='South Bohemia' (wrong case), GROUP BY district_id instead of gold's A4, and ORDER BY number_inhabitants instead of gold's CAST(A4 AS INTEGER) -- entirely different grouping/ordering columns

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
GROUP BY 
    di.district_id
ORDER BY 
    di.number_inhabitants DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's two SPECIFIC-DATE balance snapshots (SUM(IIF(date='1998-12-27',...)) and SUM(IIF(date='1993-03-22',...))) with MAX/MIN over ALL transactions within a date range -- a fundamentally different computation; also replaces gold's exact loan.date='1993-07-05' filter with a MIN(date) WHERE date >= '1993-07-05' AND status='A' subquery, which could resolve to a different loan/date entirely

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
    l.status = 'A' AND l.date = (
        SELECT MIN(date) 
        FROM loan 
        WHERE status = 'A' AND date >= '1993-07-05'
    )
    AND t.date BETWEEN '1993-03-22' AND '1998-12-27';
```

### Q118 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status = 'A' instead of gold's 'C' -- both real status codes, but different values, giving the percentage of a different loan category

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

### Q125 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** reaches district via client.district_id (through disp/client) instead of gold's direct account.district_id -- a different real join path, since a client's home district need not match their account's servicing district; also adds an unrequested GROUP BY (aggregating to one row per district instead of gold's one row per loan), drops the /A12*100 percentage normalization (just computes the raw A13-A12 difference), uses status='A' instead of gold's 'D', and adds a fabricated amount>0 condition not in gold

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT d.district_id, d.district_name, d.unemployment_rate_1996 - d.unemployment_rate_1995 AS unemployment_rate_increment
FROM loan l
JOIN account a ON l.account_id = a.account_id
JOIN disp d1 ON a.account_id = d1.account_id
JOIN client c ON d1.client_id = c.client_id
JOIN district d ON c.district_id = d.district_id
WHERE l.status = 'A' AND l.amount > 0
GROUP BY d.district_id, d.district_name;
```

### Q129 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** reaches district via client.district_id (through disp/client) instead of gold's direct account.district_id -- a different real join path; also type='withdrawal' doesn't match the real stored value 'VYDAJ' (zeroing the result on its own), and restructures gold's 'top 10 individual transactions by amount' into a GROUP BY district_name ranked by transaction COUNT -- a fundamentally different metric and grain

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
ORDER BY COUNT(DISTINCT t.transaction_id) DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `ambiguous column name: account_id` -- both loan.account_id and account.account_id exist after the join, and the bare `account_id` in COUNT(DISTINCT account_id) doesn't specify which; also statement_frequency='M' doesn't match the real stored value 'POPLATEK MESICNE', and adds a fabricated status='A' condition not present in gold

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT account_id) 
FROM loan 
JOIN account ON loan.account_id = account.account_id 
WHERE loan.amount >= 250000 
AND loan.status = 'A' 
AND account.statement_frequency = 'M' 
AND loan.date BETWEEN '1995-01-01' AND '1997-12-31';
```

### Q137 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** status='A' instead of gold's (status='C' OR status='D') -- a different real status code/condition entirely, not just a case/format variant

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT a.account_id) 
FROM account a 
JOIN loan l ON a.account_id = l.account_id 
WHERE a.district_id = 1 AND l.status = 'A';
```

### Q145 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on card.type = 'credit' (not a real card.type value; verified real values are gold/classic/junior) instead of gold's trans.operation = 'VYBER KARTOU' -- a different real column on a different table entirely, and 'credit' isn't even a real value for either column

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT t.account_id
FROM trans t
JOIN disp d ON t.account_id = d.account_id
JOIN card c ON d.disposition_id = c.disposition_id
WHERE c.type = 'credit' AND t.amount < (SELECT AVG(amount) FROM trans WHERE strftime('%Y', date) = '1998') AND strftime('%Y', t.date) = '1998';
```

### Q149 (challenging, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's simple `disp.type <> 'OWNER'` inequality with a broken `NOT IN (SELECT disp.type FROM disp JOIN loan...)` subquery that compares TYPE STRINGS rather than filtering specific dispositions -- since both 'OWNER' and 'DISPONENT' almost certainly appear among loan-linked dispositions, this would incorrectly exclude both types rather than just 'OWNER'; also average_salary BETWEEN 8000 AND 9000 is inclusive on the lower bound where gold's A11>8000 is exclusive

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
SELECT DISTINCT disp.type, d.average_salary
FROM account a
JOIN disp ON a.account_id = disp.account_id
JOIN district d ON a.district_id = d.district_id
WHERE disp.type NOT IN (SELECT disp.type FROM disp JOIN loan ON disp.account_id = loan.account_id)
AND d.average_salary BETWEEN 8000 AND 9000;
```

### Q152 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on number_inhabitants>4000 instead of gold's A15 (number_crimes_1995)>4000 -- a different real column entirely; also adds an unrequested GROUP BY district_id, returning one average per district instead of gold's single overall average

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
GROUP BY d.district_id;
```

### Q159 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='withdrawal' and transaction_operation='cash' are both fabricated values not in the real domain (trans.type is PRIJEM/VYDAJ/VYBER; trans.operation is VKLAD/PREVOD Z UCTU/PREVOD NA UCET/VYBER/VYBER KARTOU) -- gold's actual condition is operation='VYBER' alone; also selects only 3 columns instead of gold's SELECT * (all trans columns)

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT DISTINCT t.transaction_id, t.date, t.amount
FROM trans t
JOIN disp d ON t.account_id = d.account_id
WHERE d.client_id = 3356 AND t.type = 'withdrawal' AND t.transaction_operation = 'cash';
```

### Q169 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `disp.type = 'OWNER'` filter entirely, including non-owner (DISPONENT) client-account relationships in the computation

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END) = 0 THEN NULL
        ELSE (SUM(CASE WHEN strftime('%Y', l.date) = '1997' THEN l.amount ELSE 0 END) - SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END)) * 100.0 / 
             SUM(CASE WHEN strftime('%Y', l.date) = '1996' THEN l.amount ELSE 0 END)
    END AS growth_rate
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

### Q173 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes the `trans` table (actual transaction records) for gold's `order` table (standing payment orders) -- a completely different real-world entity; also drops the total_amount=3539/k_symbol matching entirely, and 'debit' isn't even a real trans.operation value (real values are VKLAD/PREVOD Z UCTU/PREVOD NA UCET/VYBER/VYBER KARTOU)

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
    account.account_id = 3 AND trans.transaction_operation = 'debit'
GROUP BY 
    statement_frequency;
```

### Q186 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps which condition is the population filter (WHERE) and which is the CASE-based numerator -- computes 'the percentage of male clients who have a weekly-frequency account' instead of gold's 'the percentage of weekly-frequency-account clients who are male'; also statement_frequency='weekly' doesn't match the real stored value 'POPLATEK TYDNE', zeroing the (now-inverted) numerator entirely

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN a.statement_frequency = 'weekly' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(c.client_id) 
FROM account a 
JOIN disp d ON a.account_id = d.account_id 
JOIN client c ON d.client_id = c.client_id 
WHERE c.gender = 'M';
```

### Q192 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `account.frequency = 'POPLATEK PO OBRATU'` filter entirely, replaces gold's `status IN ('C','D')` with a single different code `status = 'A'`, and adds a fabricated, unrelated join to trans with a `trans.date > loan.date` condition that has no basis in the question and would multiply/corrupt the AVG via duplicate matching transaction rows per loan

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(loan.amount) 
FROM loan 
JOIN account ON loan.account_id = account.account_id 
JOIN trans ON loan.account_id = trans.account_id 
WHERE loan.status = 'A' AND trans.date > loan.date;
```

### Q194 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** card.type = 'High level' is a fabricated value unrelated to the real domain (verified real values are gold/classic/junior) -- should be the literal 'gold'

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
WHERE ca.type = 'High level' AND d.type = 'OWNER'
```

---

## formula_1 (36 failures)

### Q846 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results+status (checking for status='Retired') for gold's qualifying table (checking Q1 lap times) -- a wholesale different, unrelated real-world concept, not just a wrong value; also drops the ORDER BY q1 DESC LIMIT 5 ranking entirely

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.driver_ref_name 
FROM drivers d 
JOIN results r ON d.driver_id = r.driver_id 
JOIN status s ON r.status_id = s.status_id 
WHERE r.race_id = 20 AND s.status = 'Retired';
```

### Q854 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters directly on circuits.name = 'australian grand prix' instead of joining races.name -- circuits.name never holds the race name (verified empirically, e.g. no 'Australia'/'Melbourne' match), zeroing the result; omits the join to races entirely

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude 
FROM circuits 
WHERE LOWER(name) = 'australian grand prix'
```

### Q857 (simple, retrieval) — **Other** (Missing/redundant DISTINCT/DESC)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DISTINCT; Abu Dhabi Grand Prix was held 9 times at the same circuit (verified), so predicted returns 9 duplicate (lat,lng) rows instead of gold's single deduplicated pair

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT c.latitude, c.longitude 
FROM races r 
JOIN circuits c ON r.circuit_id = c.circuit_id 
WHERE r.name = 'Abu Dhabi Grand Prix';
```

### Q861 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time = '00:01:54' assumes an 'HH:MM:SS' format that doesn't match the actual stored 'M:SS.mmm' format (verified sample values like '1:26.714'), zeroing the result instead of gold's LIKE '1:54%' prefix match

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT number 
FROM qualifying 
WHERE race_id = 903 AND qualifying_3_time = '00:01:54';
```

### Q865 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses `position > 0` instead of gold's `time IS NOT NULL` -- both real columns on results, but verified to capture different driver sets for this race (e.g. selecting Graham Hill instead of gold's Jean-Pierre Beltoise)

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name 
FROM drivers 
WHERE driver_id IN (
    SELECT DISTINCT driver_id 
    FROM results 
    WHERE race_id = 592 AND position > 0
) 
AND date_of_birth IS NOT NULL 
ORDER BY date_of_birth ASC 
LIMIT 1;
```

### Q866 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** lt.time = '0:01:27' assumes a wrong format that doesn't match lapTimes' actual stored 'M:SS.mmm' format (verified sample '1:49.088'), zeroing the result instead of gold's LIKE '1:27%' prefix match

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.first_name, d.last_name, d.url
FROM drivers d
JOIN laptimes lt ON d.driver_id = lt.driver_id
WHERE lt.race_id = 161 AND lt.time = '0:01:27';
```

### Q868 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters circuits.name LIKE '%Malaysian Grand Prix%' instead of joining races.name -- circuits.name never holds the race name (verified empirically, no 'Malaysia' match), zeroing the result; omits the join to races entirely

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude 
FROM circuits 
WHERE name LIKE '%Malaysian Grand Prix%'
```

### Q869 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorStandings.points (cumulative season points as of that race) for gold's constructorResults.points (points earned in that specific race) -- verified these are different real tables giving different top constructors for this race (constructor 23/112.0 vs gold's constructor 9/18.0)

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

**Outcome:** `wrong_answer` · **Reason:** qualifying_3_time = '0:01:33' assumes a wrong 'H:MM:SS' format that doesn't match the actual stored 'M:SS.mmm' format, zeroing the result instead of gold's LIKE '1:33%' prefix match

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.driver_code 
FROM drivers d 
JOIN qualifying q ON d.driver_id = q.driver_id 
WHERE q.race_id = 45 AND q.qualifying_3_time = '0:01:33';
```

### Q877 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `time IS NOT NULL` filter entirely (no longer restricting to drivers who actually finished with a recorded time) and reverses the sort direction (ASC instead of gold's DESC), together very likely selecting an entirely different driver

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
ORDER BY d.date_of_birth ASC
LIMIT 1;
```

### Q879 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** compares fastest_lap_speed (a TEXT-typed column) directly without gold's CAST(...AS REAL), so MAX()/ordering operates as a lexicographic string comparison rather than numeric (verified empirically: string MAX gives '91.610' vs the true numeric max 257.32), selecting an entirely different 'fastest' row/nationality than gold

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT d.nationality
FROM drivers d
JOIN results r ON d.driver_id = r.driver_id
WHERE r.fastest_lap_speed = (SELECT DISTINCT MAX(fastest_lap_speed) FROM results);
```

### Q881 (moderate, aggregate) — **GROUP BY errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** adds a GROUP BY driver_id that gold doesn't have at all, turning gold's single race-wide completion percentage into a meaningless one-row-per-driver repeat of the same static ratio (each driver has exactly 1 result row per race, so COUNT(result_id) per group is trivially 1); also selects extra unrequested name columns

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT 
    d.first_name, 
    d.last_name, 
    COUNT(r.result_id) * 100.0 / (SELECT COUNT(DISTINCT driver_id) FROM results WHERE race_id IN (SELECT race_id FROM races WHERE date = '1983-07-16')) AS completion_rate
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

**Outcome:** `wrong_answer` · **Reason:** replaces gold's 'same year AND same month as the earliest race' matching with a single exact MIN(date) pick within the min year, dropping races that share the same year+month but not the exact same date (verified empirically: gold returns 3 races -- British GP, Monaco GP, Indianapolis 500, all in the same year+month -- while predicted returns only 1)

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT name 
FROM races 
WHERE year = (SELECT MIN(year) FROM races) 
AND date = (SELECT MIN(date) FROM races WHERE year = (SELECT MIN(year) FROM races));
```

### Q894 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects lt.time (the formatted time string) instead of gold's requested milliseconds value; the WHERE-based min-finding approach is a reasonable equivalent to ORDER BY/LIMIT 1 except it could return multiple tied rows instead of gold's single one

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
WHERE lt.milliseconds = (SELECT MIN(milliseconds) FROM lapTimes);
```

### Q896 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results/races.round (whether it's the first round of the season) entirely for gold's driverStandings.position (Hamilton's championship standing after that race) -- a fundamentally different, unrelated real column/table, not just a wrong value

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN R.round != 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM drivers D 
JOIN results RES ON D.driver_id = RES.driver_id 
JOIN races R ON RES.race_id = R.race_id 
WHERE D.first_name = 'Lewis' AND D.last_name = 'Hamilton' AND R.year >= 2010;
```

### Q897 (moderate, aggregate) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** drops gold's GROUP BY forename,surname,nationality / ORDER BY COUNT(wins) DESC LIMIT 1 (ranking drivers by how many qualifying standings-rows they have) entirely, replacing it with a flat wins = MAX(wins) equality filter (drivers who ever reached the single highest recorded wins tally) -- a fundamentally different selection criterion

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

### Q898 (simple, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** computes age via a truncated julianday/365.25 formula instead of gold's simple STRFTIME year-difference, producing a different numeric age value for the same (correctly-selected, since ORDER BY age ASC is equivalent to gold's dob DESC) driver

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT first_name, last_name, 
       CAST((julianday('now') - julianday(date_of_birth)) / 365.25 AS INTEGER) AS age
FROM drivers
WHERE nationality = 'Japanese'
ORDER BY age ASC
LIMIT 1;
```

### Q902 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results.position (per-race finish position) for gold's driverStandings.position (championship standing position after that race) -- verified different real tables/columns

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT DISTINCT r.name 
FROM races r 
JOIN results res ON r.race_id = res.race_id 
JOIN drivers d ON res.driver_id = d.driver_id 
WHERE d.first_name = 'Alex' AND d.last_name = 'Yoong' AND res.position < 20;
```

### Q904 (moderate, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes results.fastestLapTime (a single per-race summary field) for gold's lapTimes.milliseconds (individual per-lap timing records across the whole dataset) -- a different real table/granularity entirely

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

### Q915 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `error` · **Reason:** `no such column: country` -- country is a real column only on circuits, not drivers, and no join is present in this single-table query (drivers only has `nationality`)

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT country 
FROM drivers 
ORDER BY date_of_birth ASC 
LIMIT 1
```

### Q930 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses results.position (MIN position, i.e. Hamilton's best-ever finish position) instead of gold's results.rank = 0 -- rank and position are separate, distinct real columns on results (verified in schema) capturing different things

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
AND res.position = (
    SELECT MIN(position)
    FROM results
    WHERE driver_id = (
        SELECT driver_id
        FROM drivers
        WHERE first_name = 'Lewis' AND last_name = 'Hamilton'
    )
);
```

### Q937 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on circuits.circuit_ref_name instead of gold's races.name, using a garbled, nonsensical literal ('AustChineseralian Grand Prix') that doesn't correspond to any real value -- likely an artifact of the reflexion self-correction retry corrupting the race-name literal

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT r.time 
FROM results r 
JOIN races ra ON r.race_id = ra.race_id 
JOIN circuits c ON ra.circuit_id = c.circuit_id 
WHERE ra.year = 2008 AND c.circuit_ref_name = 'AustChineseralian Grand Prix' AND r.position = 2;
```

### Q940 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `time IS NOT NULL` filter entirely, and adds a fabricated, unrelated condition requiring the driver to have ALSO competed in some race other than the 2008 Chinese Grand Prix (not asked for in the question)

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
) 
AND driver_id IN (
    SELECT driver_id 
    FROM results 
    WHERE race_id NOT IN (
        SELECT race_id 
        FROM races 
        WHERE year = 2008 AND name = 'Chinese Grand Prix'
    )
);
```

### Q944 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `time IS NOT NULL` filter, so MAX(milliseconds) inadvertently resolves to the same row as the position=1 champion for this 1988 race (verified empirically: predicted's computation yields exactly 0% difference vs gold's correct ~1.16%, since most cars' milliseconds field is NULL that year and MIN/MAX collapse to the one populated row); also uses `position` instead of gold's `positionOrder` to identify the champion

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
        MAX(milliseconds) AS last_place_time
    FROM 
        results r
    JOIN 
        races ra ON r.race_id = ra.race_id
    WHERE 
        ra.year = 1988 AND ra.name = 'Australian Grand Prix'
);
```

### Q950 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes constructorResults.points (points earned in that specific race) for gold's constructorStandings.points (cumulative season standings points as of that race) -- verified different real tables/values

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT DISTINCT c.name 
FROM constructors c 
JOIN constructorResults cr ON c.constructor_id = cr.constructor_id 
WHERE cr.race_id = 291 AND cr.points = 0;
```

### Q955 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `wrong number of arguments to function INSTR()` -- calls INSTR() with 3 arguments (time, ':', start_position), a MySQL/Oracle-style signature SQLite's INSTR() doesn't support (only 2 args), while manually parsing the 'H:MM:SS' time string -- an unnecessarily complex substitute for gold's simple milliseconds/1000.0 (results.milliseconds already stores this as an integer); also joins driverStandings.position=1 instead of gold's results.position=1

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT 
    s.year, 
    AVG(
        CAST(SUBSTR(r.time, 1, INSTR(r.time, ':') - 1) AS INTEGER) * 3600 +
        CAST(SUBSTR(r.time, INSTR(r.time, ':') + 1, INSTR(SUBSTR(r.time, INSTR(r.time, ':') + 1), ':') - 1) AS INTEGER) * 60 +
        CAST(SUBSTR(r.time, INSTR(r.time, ':', INSTR(r.time, ':') + 1) + 1) AS INTEGER)
    ) AS avg_champion_time
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

### Q959 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** uses driverStandings.position=1 (the cumulative championship standing after that race) as a proxy for 'won this race,' a different real concept from gold's results.time LIKE '_:%:__.___' pattern (identifying the race winner via the absolute-elapsed-time format only winners receive)

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT results.fastest_lap_number
FROM results
JOIN driverStandings ON results.driver_id = driverStandings.driver_id AND results.race_id = driverStandings.race_id
JOIN races ON results.race_id = races.race_id
WHERE races.year = 2009 AND driverStandings.position = 1;
```

### Q962 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `wrong number of arguments to function COUNT()` -- COUNT(DISTINCT R.race_id, D.driver_id) passes two comma-separated columns, but SQLite's COUNT(DISTINCT ...) only accepts a single expression

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
WHERE R.year BETWEEN 2000 AND 2005 AND RES.laps = 50;
```

### Q967 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** nationality='Netherlandic' is a fabricated value unrelated to the real domain value 'Dutch'; also reverses the ORDER BY direction (ASC instead of gold's DESC via JULIANDAY), selecting the 3 oldest drivers instead of the 3 youngest

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM (
    SELECT * 
    FROM drivers 
    ORDER BY date_of_birth ASC 
    LIMIT 3
) AS youngest_drivers
WHERE nationality = 'Netherlandic';
```

### Q972 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's simple `fastestLapTime IS NOT NULL` presence check with `= (SELECT MIN(fastest_lap_time)...)`, an entirely different and far more restrictive condition (only the single driver holding the all-time fastest lap would qualify); the MIN() is also computed as a lexicographic string comparison since fastest_lap_time is TEXT-typed, compounding the issue

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
WHERE d.date_of_birth LIKE '1971%' AND r.fastest_lap_time = (
    SELECT MIN(fastest_lap_time)
    FROM results
    WHERE fastest_lap_time IS NOT NULL
);
```

### Q977 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `time IS NOT NULL` condition entirely, counting ALL disqualified results in the race range rather than just those with a recorded time; also uses COUNT(DISTINCT driver_id) instead of gold's SUM(IIF(...)) over raw result rows, deduplicating drivers disqualified in multiple races within the range

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT r.driver_id) 
FROM results r
JOIN status s ON r.status_id = s.status_id
WHERE r.race_id BETWEEN 50 AND 100 
AND s.status = 'Disqualified';
```

### Q981 (moderate, retrieval) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** uses MIN(date_of_birth) instead of gold's effective MAX (via ORDER BY dob DESC), selecting the oldest driver instead of the youngest

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    r.year AS year, 
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
ORDER BY 
    r.date ASC, r.time ASC
LIMIT 1;
```

### Q990 (challenging, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** uses constructorStandings.position=1 (cumulative championship standing after the race) instead of gold's results.time format-based race-winner identification -- the same per-race-result vs cumulative-standings confusion seen elsewhere in this database

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT DISTINCT c.constructor_ref_name, c.url 
FROM constructors c 
JOIN constructorStandings cs ON c.constructor_id = cs.constructor_id 
JOIN races r ON cs.race_id = r.race_id 
WHERE r.name = 'Singapore Grand Prix' AND r.year = 2009 AND cs.position = 1;
```

### Q994 (challenging, aggregate) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** uses constructorStandings.points (a cumulative running total as of each race) instead of gold's constructorResults.points (points earned in that specific race only); summing the cumulative field across many races produces a nonsensical inflated total, unlike gold's correct per-race point summation

**Gold SQL:**

```sql
SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    c.name AS constructor_name, 
    c.nationality AS constructor_nationality, 
    SUM(crs.points) AS total_points
FROM 
    constructorStandings crs
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

### Q1001 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds a fabricated `r.round = 3` condition with no basis in the question (apparently conflating the Q3 qualifying session with 'round 3 of the season' -- an unrelated real column), which would restrict to an entirely different race than the one at Marina Bay Street Circuit in 2008

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
WHERE r.year = 2008 AND c.name = 'Marina Bay Street Circuit' AND r.round = 3 AND q.position = 1;
```

### Q1014 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses lapTimes.lap (the lap NUMBER, e.g. 1st/2nd/3rd lap of the race) instead of any actual timing value -- doesn't query a time-related column at all, let alone gold's results.FastestLapTime field; MIN(lap) is a meaningless comparison unrelated to speed

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(lapTimes.lap) AS min_lap
FROM lapTimes
JOIN races ON lapTimes.race_id = races.race_id
JOIN circuits ON races.circuit_id = circuits.circuit_id
WHERE circuits.country = 'Italy';
```

---

## student_club (22 failures)

### Q1317 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds a fabricated `major_id IN (SELECT major_id FROM major WHERE major_name = 'Student_Club')` filter with no basis in the question -- 'Student_Club' is not a real major_name (verified: 0 matching rows) -- zeroing what should be a plain event/attendance/t-shirt-size count

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT m.member_id) 
FROM member m 
JOIN attendance a ON m.member_id = a.member_id 
JOIN event e ON a.event_id = e.event_id 
WHERE m.major_id IN (SELECT major_id FROM major WHERE major_name = 'Student_Club') 
AND e.event_name = 'Women''s Soccer' 
AND m.t_shirt_size = 'Medium';
```

### Q1322 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type = 'meeting' (lowercase) doesn't match the stored Title-Case value 'Meeting', zeroing the count; the HAVING COUNT(...)>10 subquery structure itself is an equivalent restatement of gold's logic

**Gold SQL:**

```sql
SELECT COUNT(*) FROM (SELECT T1.event_name FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event WHERE T1.type = 'Meeting' GROUP BY T1.event_id HAVING COUNT(T2.link_to_event) > 10)
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM event 
WHERE event_id IN (
    SELECT DISTINCT event_id 
    FROM attendance 
    GROUP BY event_id 
    HAVING COUNT(member_id) > 10
) 
AND type = 'meeting';
```

### Q1331 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** treats income.source (LIKE '%Vice President%') as if it encoded a member's position, with no join to member at all; income.source only ever holds Dues/Fundraising/School Appropration/Sponsorship, so this can never match -- position lives on the separate member table gold joins to

**Gold SQL:**

```sql
SELECT T2.amount FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Vice President'
```

**Predicted SQL:**

```sql
SELECT SUM(amount) 
FROM income 
WHERE income_source LIKE '%Vice President%';
```

### Q1334 (simple, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds a fabricated `m.position = 'Student_Club'` filter (not a real position value; verified real values are Member/Inactive/President/Vice President/Treasurer/Secretary) with no basis in the question, zeroing what should be a plain Illinois-state member list

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.first_name, m.last_name 
FROM member m 
JOIN zip_code z ON m.zip_code = z.zip_code 
WHERE z.state = 'Illinois' AND m.position = 'Student_Club';
```

### Q1338 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** ev.event_date = '2019-10-08' exact-matches against event_date's timestamp-suffixed storage (e.g. '2019-10-08T12:00:00'), returning zero rows, unlike gold's LIKE '2019-10-08%' prefix match; also adds an unwarranted extra expense_date filter and an extra SELECT column not asked for

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
WHERE ev.event_name = 'October Meeting' AND ev.event_date = '2019-10-08' AND e.expense_date = '2019-10-08';
```

### Q1340 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** adds a fabricated `event_status = 'Student_Club'` filter to both subtracted subqueries (not a real event_status value; verified real values are Closed/Open/Planning), zeroing both sides of the difference

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT SUM(amount_spent) 
     FROM budget 
     WHERE event_id IN (SELECT event_id FROM event WHERE strftime('%Y', event_date) = '2019') 
       AND event_status = 'Student_Club') -
    (SELECT SUM(amount_spent) 
     FROM budget 
     WHERE event_id IN (SELECT event_id FROM event WHERE strftime('%Y', event_date) = '2020') 
       AND event_status = 'Student_Club') AS difference;
```

### Q1344 (simple, retrieval) — **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** substitutes event for income (both plausibly hold dated 'notes'), querying event.notes/event_date/type instead of income.notes/date_received/source; also uses type='fundraising' (lowercase, and not even a real event.type value) instead of income.source='Fundraising'

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE event_date = '2019-09-14' AND type = 'fundraising';
```

### Q1357 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** i.income_source = 'dues' (lowercase) doesn't match the stored value 'Dues'

**Gold SQL:**

```sql
SELECT T2.date_received FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Connor' AND T1.last_name = 'Hilton' AND T2.source = 'Dues'
```

**Predicted SQL:**

```sql
SELECT i.date_received 
FROM income i 
JOIN member m ON i.member_id = m.member_id 
WHERE m.first_name = 'Connor' AND m.last_name = 'Hilton' AND i.income_source = 'dues';
```

### Q1359 (challenging, aggregate) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** computes COUNT(*) of Advertisement/Yearly-Kickoff budget rows exceeding a MAX(Advertisement/October-Meeting amount) threshold -- a fundamentally different aggregate/logic construction from gold's SUM(Yearly Kickoff amount)/SUM(October Meeting amount) ratio

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
    SELECT MAX(b2.amount) 
    FROM budget b2 
    JOIN event e2 ON b2.event_id = e2.event_id 
    WHERE b2.category = 'Advertisement' AND e2.event_name = 'October Meeting'
);
```

### Q1376 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** e.status = 'closed' (lowercase) doesn't match the stored value 'Closed', zeroing the result before gold's tie-preserving HAVING ratio = (SELECT MAX(ratio)...) vs the predicted's plain ORDER BY/LIMIT 1 ever comes into play

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
GROUP BY e.event_id 
ORDER BY (SUM(b.amount_spent) / SUM(b.amount)) DESC 
LIMIT 1;
```

### Q1380 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** category = 'food' (lowercase) doesn't match the stored value 'Food'

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

### Q1387 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** `no such column: b.manager_id` -- budget has no member-link column at all (only expense does, via link_to_member); reaching a member from budget requires the intermediate expense table, which the prediction omits entirely

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name 
FROM member m 
JOIN budget b ON m.member_id = b.manager_id 
JOIN event e ON b.event_id = e.event_id 
WHERE e.event_name = 'Yearly Kickoff';
```

### Q1392 (simple, retrieval) — **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** adds a `GROUP BY income_source` + `SUM(amount)` aggregation gold never has, changing the ranking criterion from gold's alphabetically-last source name (plain ORDER BY source DESC) to the source with the highest total amount -- a fundamentally different selection

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

**Outcome:** `wrong_answer` · **Reason:** adds a fabricated `member.position = 'Student_Club'` filter (not a real position value) with no basis in the question, on top of the correct major_name='Physics Teaching' filter, zeroing the count

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT member_id) 
FROM member 
JOIN major ON member.major_id = major.major_id 
WHERE major.major_name = 'Physics Teaching' AND member.position = 'Student_Club';
```

### Q1398 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** b.category = 'advertisement' (lowercase) doesn't match the stored value 'Advertisement', zeroing the result; the added ORDER BY tie-breaker on event_date is immaterial given zero rows match

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
ORDER BY b.amount_spent DESC, e.event_date ASC 
LIMIT 1;
```

### Q1403 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `no such column: e.event_name` -- outer SELECT references alias `e`, which is only declared inside the derived subquery's own scope, not in the outer FROM (only `subquery` is)

**Gold SQL:**

```sql
SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T2.event_id = T1.link_to_event WHERE T1.event_status = 'Closed' AND T1.remaining < 0 ORDER BY T1.remaining LIMIT 1
```

**Predicted SQL:**

```sql
SELECT e.event_name
FROM (
    SELECT e.event_id, e.event_name, SUM(ex.cost) - b.amount AS budget_excess
    FROM event e
    JOIN budget b ON e.event_id = b.event_id
    JOIN expense ex ON b.budget_id = ex.budget_id
    WHERE e.status = 'closed'
    GROUP BY e.event_id, e.event_name
) AS subquery
ORDER BY subquery.budget_excess DESC
LIMIT 1;
```

### Q1404 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** e.is_approved = 1 (integer) instead of the stored TEXT value 'true' -- approved is a TEXT column whose only real value is the string 'true', so comparing it to the integer 1 matches nothing

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
SELECT b.category, SUM(e.cost) AS total_approved_cost
FROM expense e
JOIN budget b ON e.budget_id = b.budget_id
JOIN event ev ON b.event_id = ev.event_id
WHERE ev.event_name = 'October Meeting' AND e.is_approved = 1
GROUP BY b.category;
```

### Q1422 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects b.category (a budget attribute) instead of gold's event.type, via an unnecessary extra join to budget; also adds a status='completed' filter that isn't even a real event.status value (real values: Open/Planning/Closed) and isn't part of the question

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
WHERE e.location = 'MU 215' AND e.status = 'completed';
```

### Q1427 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type = 'guest speaker' (lowercase) doesn't match the stored value 'Guest Speaker', zeroing the result; SELECT column/join/other filters otherwise match gold

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.category 
FROM budget b 
JOIN event e ON b.event_id = e.event_id 
WHERE e.location = 'MU 215' AND e.type = 'guest speaker' AND b.amount_spent = 0;
```

### Q1432 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's position='Member' filter entirely and substitutes a fabricated `income_source = 'Student_Club'` filter (not a real income.source value; verified real values are Dues/Fundraising/School Appropration/Sponsorship) in its place

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN i.amount = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(i.income_id) 
FROM income i 
JOIN member m ON i.member_id = m.member_id 
WHERE m.t_shirt_size = 'Medium' AND i.income_source = 'Student_Club';
```

### Q1435 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** type='game' and status='closed' (both lowercase) don't match the stored Title-Case values 'Game'/'Closed', zeroing the result; the date range comparison itself is immaterial since event_date's ISO timestamp still falls within the given bounds for in-range rows

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT DISTINCT event_name 
FROM event 
WHERE type = 'game' 
AND status = 'closed' 
AND event_date BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1460 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** splits gold's single exact string 'Water, Veggie tray, supplies' into a lowercase 3-item IN-list ('water','veggie tray','supplies'), none of which match any real expense_description value (verified the real row's description is the full comma-joined phrase), returning zero rows; also unnecessarily adds SUM/GROUP BY for what should be a single-row lookup

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, SUM(e.cost) AS total_cost 
FROM member m 
JOIN expense e ON m.member_id = e.member_id 
WHERE e.expense_description IN ('water', 'veggie tray', 'supplies')
GROUP BY m.member_id;
```

---

## superhero (23 failures)

### Q723 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour = 'blue' (lowercase) doesn't match the stored value 'Blue', zeroing the result

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

**Outcome:** `wrong_answer` · **Reason:** eye/hair colour values 'blue'/'blond' (lowercase) don't match the stored Title-Case values 'Blue'/'Blond'

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.superhero_name 
FROM superhero s 
JOIN colour e ON s.eye_colour_id = e.id 
JOIN colour h ON s.hair_colour_id = h.id 
WHERE e.colour = 'blue' AND h.colour = 'blond';
```

### Q726 (moderate, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `height_cm IS NOT NULL AND height_cm != 0` filter entirely, including heroes with missing/zero height in the ordered list; also adds an extra ROW_NUMBER() column not requested

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT 
    superhero.superhero_name, 
    superhero.height_cm,
    ROW_NUMBER() OVER (ORDER BY superhero.height_cm DESC) AS rank
FROM 
    superhero
JOIN 
    publisher ON superhero.publisher_id = publisher.id
WHERE 
    publisher.publisher_name = 'Marvel Comics';
```

### Q728 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank window-function column entirely; GROUP BY/JOIN/filter otherwise match gold

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.colour, COUNT(DISTINCT s.id) as count
FROM superhero s
JOIN colour c ON s.eye_colour_id = c.id
JOIN publisher p ON s.publisher_id = p.id
WHERE p.publisher_name = 'Marvel Comics'
GROUP BY c.colour
ORDER BY count DESC;
```

### Q733 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour = 'gold' (lowercase) doesn't match the stored value 'Gold', zeroing the result

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id WHERE T2.publisher_name = 'Marvel Comics' AND T3.colour = 'Gold'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT superhero.id) 
FROM superhero 
JOIN colour ON superhero.eye_colour_id = colour.id 
JOIN publisher ON superhero.publisher_id = publisher.id 
WHERE colour.colour = 'gold' AND publisher.publisher_name = 'Marvel Comics';
```

### Q736 (moderate, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `no such function: REGEXP` -- calls REGEXP('^[0-9]+$', attribute_value), a function requiring a SQLite extension/loadable module that isn't available by default

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT superhero_name 
FROM superhero 
WHERE id = (SELECT hero_id FROM hero_attribute WHERE attribute_id = (SELECT id FROM attribute WHERE attribute_name = 'intelligence') AND attribute_value IS NOT NULL AND attribute_value REGEXP '^[0-9]+$' ORDER BY CAST(attribute_value AS INTEGER) ASC LIMIT 1);
```

### Q743 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alignment = 'Self-Centric' is a fabricated value with no basis in the real domain (verified real values are Good/Bad/Neutral/N/A) -- should be 'Bad'

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(DISTINCT CASE WHEN a.alignment = 'Self-Centric' THEN s.id END) * 100.0 / COUNT(DISTINCT s.id)) AS percentage_self_centric,
    COUNT(DISTINCT CASE WHEN a.alignment = 'Self-Centric' AND p.publisher_name = 'Marvel Comics' THEN s.id END) AS marvel_self_centric_count
FROM 
    superhero s
JOIN 
    alignment a ON s.alignment_id = a.id
LEFT JOIN 
    publisher p ON s.publisher_id = p.id;
```

### Q744 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** publisher_name='DC'/'Marvel' don't match the stored values 'DC Comics'/'Marvel Comics' (verified), zeroing both counts; also drops gold's CASE WHEN.../ELSE... label indicating which publisher has more heroes, returning only a raw (always-zero) difference

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
    (SELECT COUNT(s.id) FROM superhero s WHERE s.publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'DC')) -
    (SELECT COUNT(s.id) FROM superhero s WHERE s.publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Marvel')) AS difference;
```

### Q750 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `weight_kg > 0` filter entirely, including heroes with a placeholder weight_kg=0 in the average, skewing it downward

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

### Q753 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses `eye_colour_id IS NULL` instead of gold's join+filter for colour = 'No Colour' -- 'No Colour' is an explicit, real value in the colour lookup table (id=1), not the same condition as the foreign key itself being NULL (verified empirically: 15 rows match colour='No Colour' in this height range vs 0 for eye_colour_id IS NULL)

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

### Q766 (moderate, retrieval) — **Other** (Missing/redundant DISTINCT/DESC)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DISTINCT, so multiple different heroes sharing a placeholder full_name ('-') each appear as a separate row instead of being collapsed into one, inflating the result set (verified empirically: predicted returns far more rows than gold, with the same names/placeholders repeated)

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
WHERE a.attribute_name = 'Strength' AND ha.attribute_value = (
    SELECT MAX(ha2.attribute_value)
    FROM hero_attribute ha2
    JOIN attribute a2 ON ha2.attribute_id = a2.id
    WHERE a2.attribute_name = 'Strength'
);
```

### Q772 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects the joined colour.colour/hair colour.colour/skin colour.colour text names instead of gold's raw eye_colour_id/hair_colour_id/skin_colour_id integer values -- different real columns for the same requested attribute

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    c.colour AS eye_colour, 
    h.colour AS hair_colour, 
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

### Q775 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses eye_colour_id instead of gold's skin_colour_id (a different real column) to determine 'Blue' coloring; the colour lookup also uses lowercase 'blue' which never matches the stored 'Blue', additionally zeroing the result

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

**Outcome:** `wrong_answer` · **Reason:** colour = 'black' (lowercase, both eye and hair) doesn't match the stored Title-Case value 'Black', zeroing the result; the dual-join structure is a reasonable, equivalent restatement of gold's single-alias AND condition

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id AND T1.hair_colour_id = T2.id WHERE T2.colour = 'Black'
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.superhero_name 
FROM superhero s 
JOIN colour ec ON s.eye_colour_id = ec.id 
JOIN colour hc ON s.hair_colour_id = hc.id 
WHERE ec.colour = 'black' AND hc.colour = 'black';
```

### Q788 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** moves the Marvel-publisher condition from a CASE WHEN inside the numerator (gold) into a hard WHERE filter restricting the ENTIRE query to Marvel heroes only, flipping the computed percentage from '% of all female heroes who are Marvel' into '% of Marvel heroes who are female' -- a completely different question; also uses INNER JOIN instead of gold's LEFT JOIN to publisher

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

### Q790 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses superhero_name instead of gold's full_name -- verified these are different real columns with different values (e.g. superhero_name='Abomination' vs full_name='Emil Blonsky' for the same hero), zeroing both subqueries

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT 
    (SELECT weight_kg FROM superhero WHERE superhero_name = 'Emil Blonsky') - 
    (SELECT weight_kg FROM superhero WHERE superhero_name = 'Charles Chandler') AS weight_difference;
```

### Q791 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `height_cm > 0` filter entirely, including placeholder height_cm=0 rows in the average, skewing it downward

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) FROM superhero
```

### Q794 (moderate, retrieval) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's tie-preserving `attribute_value = (SELECT MAX(...))` equality with an ORDER BY attribute_value DESC LIMIT 1 subquery that returns only a single hero_id; verified 40 heroes are tied at the actual max Speed value, all of which gold's query would return

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

**Outcome:** `wrong_answer` · **Reason:** eye/hair colour values 'blue'/'brown' (lowercase) don't match the stored Title-Case values 'Blue'/'Brown'

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Brown'
```

**Predicted SQL:**

```sql
SELECT DISTINCT s.superhero_name 
FROM superhero s 
JOIN colour e ON s.eye_colour_id = e.id 
JOIN colour h ON s.hair_colour_id = h.id 
WHERE e.colour = 'blue' AND h.colour = 'brown';
```

### Q800 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour = 'blue' (lowercase) doesn't match the stored value 'Blue', zeroing the numerator

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

### Q819 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** colour = 'blue' (lowercase) doesn't match the stored value 'Blue' (id=7), zeroing the first term entirely; also uses `eye_colour_id IS NULL` instead of gold's colour_id=1 ('No Colour') for the second term, and drops the 'OR weight_kg=0' half of gold's weight filter, keeping only 'weight_kg IS NULL'

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

**Outcome:** `wrong_answer` · **Reason:** alignment='bad' and colour='green' (lowercase) don't match the stored Title-Case values 'Bad'/'Green', zeroing the result

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

**Outcome:** `wrong_answer` · **Reason:** publisher_name = 'DC' doesn't match the stored value 'DC Comics' (verified), zeroing that subquery's count and corrupting the difference; also drops gold's CASE WHEN label indicating which publisher has more heroes

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

## thrombosis_prediction (46 failures)

### Q1149 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex = 'Male' and admission_type = 'Inpatient'/'Outpatient' don't match the stored values 'M' and '+'/'-' (verified: Admission only ever holds '+'/'-'), zeroing the result regardless of the GROUP BY restructuring

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    admission_type, 
    COUNT(*) AS count, 
    ((SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) - SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END)) * 100.0 / COUNT(*)) AS deviation_percentage
FROM 
    Patient
WHERE 
    sex = 'Male'
GROUP BY 
    admission_type;
```

### Q1150 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** moves the SEX condition out of the WHERE clause into the CASE WHEN numerator, changing the denominator's scope from 'F patients only' to 'all patients'; also sex='female' doesn't match the stored value 'F'

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

**Outcome:** `wrong_answer` · **Reason:** admission_type = 'Inpatient'/'Outpatient' don't match the stored values '+'/'-' (verified: Admission only ever holds '+'/'-'), zeroing both sums

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    IFNULL(
        CAST(SUM(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE 0 END) AS REAL) / 
        NULLIF(SUM(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE 0 END), 0),
        0
    ) AS inpatient_to_outpatient_ratio
FROM 
    Patient
WHERE 
    diagnosis = 'SLE';
```

### Q1155 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** lactate_dehydrogenase > 175 instead of gold's > 500 -- a generic reference-range threshold substituted for the value stated in the question

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.lactate_dehydrogenase > 175;
```

### Q1156 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on thrombosis_degree > 0 (the Thrombosis column) instead of gold's RVVT = '+' -- a different real lab test entirely

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, CAST((julianday('now') - julianday(P.birthday)) / 365.25 AS INTEGER) AS age
FROM Patient P
JOIN Examination E ON P.ID = E.ID
WHERE E.thrombosis_degree > 0;
```

### Q1157 (simple, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** thrombosis_degree = 'severe' (a fabricated categorical label) instead of gold's exact numeric value 2 -- Thrombosis is stored as an integer 0-3, not a text severity label

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, P.sex, P.diagnosis 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE E.thrombosis_degree = 'severe';
```

### Q1162 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses `First Date` (aliased first_hospital_visit_date) instead of gold's `Description` (aliased first_record_date) -- both are real but different date columns on Patient; also sex='female' and admission_type='门诊' (Chinese, not the real '+'/'-' domain) and adds an unneeded extra join to Examination

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Examination E ON P.ID = E.ID 
WHERE P.sex = 'female' 
AND strftime('%Y', P.first_hospital_visit_date) = '1997' 
AND P.admission_type = '门诊';
```

### Q1164 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** introduces a `thrombosis_degree = (SELECT MAX(thrombosis_degree) ...)` subquery gold never has, substituting a computed running-max for gold's flat exact literal Thrombosis=1 (and MAX over 1997 rows would be higher than 1 anyway); also sex='女' (Chinese) instead of the real value 'F'

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

### Q1166 (simple, retrieval) — **Other** (Wrong aggregate function or scaling)

**Outcome:** `wrong_answer` · **Reason:** uses MIN(birthday) instead of gold's effective MAX(Birthday) (via ORDER BY DESC), selecting the oldest patient instead of the youngest; also drops the UNION/NOT EXISTS fallback branch that handles the NULL-symptoms edge case

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT E.symptoms, P.diagnosis 
FROM Examination E 
JOIN Patient P ON E.ID = P.ID 
WHERE P.birthday = (SELECT MIN(birthday) FROM Patient) 
LIMIT 1;
```

### Q1169 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `no such column: P.sex` -- outer query references alias P, which is only declared inside the derived subquery's own scope; also collapses gold's dual-threshold M/F UA cutoffs (8.0/6.5) into a single uric_acid>7.0 filter and uses 'male'/'female' instead of 'M'/'F'

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN P.sex = 'male' THEN 1 ELSE 0 END) AS REAL) / 
    SUM(CASE WHEN P.sex = 'female' THEN 1 ELSE 0 END) AS male_to_female_ratio
FROM 
    (SELECT DISTINCT P.ID, P.sex 
     FROM Patient P 
     JOIN Laboratory L ON P.ID = L.ID 
     WHERE L.uric_acid > 7.0) AS DistinctPatients;
```

### Q1171 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** compares E.examination_date < P.birthday directly (essentially always false, since exams occur after birth) instead of gold's actual age-at-examination computation (exam year minus birth year < 18)

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
AND E.examination_date < P.birthday;
```

### Q1175 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** `no such column: E.patient_id` -- Examination/Laboratory's actual join key to Patient is `ID`, not `patient_id`, which doesn't exist anywhere in this schema

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age,
    E.diagnosis
FROM 
    Patient P
JOIN 
    Examination E ON P.ID = E.patient_id
JOIN 
    Laboratory L ON P.ID = L.patient_id
ORDER BY 
    L.hemoglobin DESC
LIMIT 1;
```

### Q1179 (moderate, retrieval) — **Other**

**Outcome:** `wrong_answer` · **Reason:** selects two additional unrequested columns (aCL IgG, aCL IgA) alongside the correct aCL IgM (anticardiolipin_igm), when gold asks for aCL IgM alone; the join/filter logic itself (SLE diagnosis, first_record_date, examination_date) matches gold exactly

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

### Q1185 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `near "PIVOT": syntax error` -- PIVOT is not supported by SQLite at all

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (november_avg - december_avg) / november_avg AS decrease_rate
FROM (
    SELECT 
        strftime('%m', L.Date) AS month,
        AVG(L.total_cholesterol) AS avg_total_cholesterol
    FROM 
        Patient P
    JOIN 
        Laboratory L ON P.ID = L.ID
    WHERE 
        P.birthday = '1959-02-18'
        AND L.Date BETWEEN '1981-11-01' AND '1981-12-31'
    GROUP BY 
        strftime('%m', L.Date)
) AS monthly_avg
PIVOT (
    AVG(avg_total_cholesterol) FOR month IN ('11' AS november_avg, '12' AS december_avg)
);
```

### Q1187 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses Examination's exam date (E.examination_date) for the date-range filter instead of Laboratory's own Date column (verified both tables have distinct real date columns); also unnecessarily joins Patient/Examination and returns a COUNT instead of gold's plain list of matching Laboratory IDs

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID)
FROM Patient P
JOIN Examination E ON P.ID = E.ID
JOIN Laboratory L ON P.ID = L.ID
WHERE E.examination_date BETWEEN '1987-07-06' AND '1996-01-31'
AND L.aspartate_aminotransferase > 30
AND L.albumin < 4;
```

### Q1189 (challenging, aggregate) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** unnecessary INNER JOIN to Patient (in both the outer query and the averaging subquery) silently drops the 700 orphan Examination rows that have no matching Patient row (verified empirically), changing COUNT(*) from gold's 3 to 1 even though every other filter/column matches gold exactly

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
  AND e.anticardiolipin_igm > (
      SELECT AVG(e2.anticardiolipin_igm) * 1.2
      FROM Examination e2
      JOIN Patient p2 ON e2.ID = p2.ID
      WHERE e2.thrombosis_degree = 2
        AND e2.antinuclear_antibody_pattern = 'S'
  );
```

### Q1192 (challenging, retrieval) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** admission_type = '门诊' (Chinese, fabricated; real domain is '+'/'-') and replaces gold's T-BIL<2.0 with an unrelated BETWEEN 5.1 AND 20.0 range (a reference-range hallucination, not a threshold match)

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

**Outcome:** `wrong_answer` · **Reason:** sex = 'female' doesn't match the stored value 'F', zeroing the result; also adds an unnecessary DISTINCT before averaging albumin, which would incorrectly deduplicate legitimately-repeated values across different matching patients

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(albumin) 
FROM (
    SELECT DISTINCT L.albumin 
    FROM Laboratory L 
    JOIN Patient P ON L.ID = P.ID 
    WHERE P.sex = 'female' AND L.platelet_count > 400 AND P.diagnosis = 'SLE'
);
```

### Q1198 (simple, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** uses Examination.diagnosis instead of Patient.diagnosis (both tables have their own real Diagnosis column) via an unneeded extra join; also sex='female' instead of the real value 'F'

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM Patient 
JOIN Examination ON Patient.ID = Examination.ID 
WHERE Patient.sex = 'female' AND Examination.diagnosis = 'APS';
```

### Q1201 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** sex='女' (Chinese, not the real value 'F') and diagnosis LIKE '%RA%' (pattern match) instead of gold's exact Diagnosis='RA'

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN sex = '女' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient 
WHERE strftime('%Y', birthday) = '1980' AND diagnosis LIKE '%RA%';
```

### Q1205 (moderate, retrieval) — **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` · **Reason:** omits the join to Patient (and SEX) entirely, replacing gold's sex-dependent high-UA threshold check (F>6.5 or M>8.0) with a single unrelated 'normal range' BETWEEN 2.4 AND 7.0 check on uric_acid alone

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT CASE WHEN uric_acid BETWEEN 2.4 AND 7.0 THEN 'true' ELSE 'false' END AS is_normal 
FROM Laboratory 
WHERE ID = 57266
```

### Q1208 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' instead of 'M'; alanine_aminotransferase>40 instead of gold's >=60 (a generic reference-range threshold substituted for the question's value)

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID 
FROM Patient P 
JOIN (
    SELECT ID 
    FROM Laboratory 
    WHERE alanine_aminotransferase > 40
) L ON P.ID = L.ID 
WHERE P.sex = 'male';
```

### Q1209 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** alanine_aminotransferase>40 instead of gold's >60 (a generic reference-range threshold substituted for the question's value)

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.diagnosis 
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
SELECT DISTINCT P.ID, P.sex, P.birthday 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.urea_nitrogen = 15;
```

### Q1225 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's single T-BIL>=2.0 threshold with an unrelated two-sided range (<0.3 OR >1.2); also swaps GROUP_CONCAT(DISTINCT ID) for COUNT(DISTINCT ID), a secondary aggregate-choice difference

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT P.sex, COUNT(DISTINCT P.ID) AS patient_count
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.total_bilirubin < 0.3 OR L.total_bilirubin > 1.2
GROUP BY P.sex;
```

### Q1227 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's fixed threshold T-CHO>=250 with a relative 'above the overall average total_cholesterol across all Laboratory rows' subquery-based threshold (a fundamentally different comparison), and uses sex='male' instead of 'M'

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(strftime('%Y', CURRENT_DATE) - strftime('%Y', birthday)) AS average_age
FROM Patient
WHERE sex = 'male' AND ID IN (
    SELECT ID
    FROM Laboratory
    WHERE total_cholesterol > (SELECT AVG(total_cholesterol) FROM Laboratory)
);
```

### Q1229 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** triglyceride>150 instead of gold's >=200 (a generic reference-range threshold substituted for the question's value); age computed with an extra day-precision adjustment gold's simpler year-only subtraction doesn't have

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

**Outcome:** `wrong_answer` · **Reason:** sex='male' instead of 'M'; creatinine_phosphokinase>100 instead of gold's >=250 (a generic reference-range threshold substituted for the question's value)

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

**Outcome:** `wrong_answer` · **Reason:** replaces gold's single-sided GLU>=180 threshold with an 'outside normal range' OR condition (<70 OR >110), and replaces T-CHO<250 with a BETWEEN 125-200 'normal range' check -- both are clinical reference-range hallucinations unrelated to gold's stated thresholds

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT DISTINCT P.ID, P.sex, strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE (L.blood_glucose < 70 OR L.blood_glucose > 110)
AND L.total_cholesterol BETWEEN 125 AND 200;
```

### Q1235 (moderate, retrieval) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** restructures gold's flat WHERE RBC<3.5 into GROUP BY P.ID HAVING AVG(RBC) < (SELECT AVG(RBC) FROM Laboratory) -- introducing both an unrequested per-patient aggregation and a population-average-relative threshold instead of gold's fixed absolute cutoff

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.birthday) AS age, P.diagnosis
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
GROUP BY P.ID
HAVING AVG(L.red_blood_cell_count) < (SELECT AVG(red_blood_cell_count) FROM Laboratory);
```

### Q1239 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** adds L.Date to the GROUP BY (gold groups by ID alone), siloing each date into its own group so HAVING COUNT(DISTINCT L.Date)>=2 is nearly always false, breaking the 'at least 2 qualifying records' logic entirely; also replaces gold's single-sided HCT>=52 threshold with an unrelated two-sided range (<36 OR >44)

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT P.ID, strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday)) AS age
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.hematocrit < 36 OR L.hematocrit > 44
GROUP BY P.ID, L.Date
HAVING COUNT(DISTINCT L.Date) >= 2;
```

### Q1241 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** platelet_count<150/>450 instead of gold's <100/>400 (reference-range thresholds substituted for the question's values); also drops DISTINCT, counting raw Laboratory rows via COUNT(CASE...) rather than distinct patients

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
    Patient P ON L.ID = P.ID;
```

### Q1242 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** platelet_count BETWEEN 150000 AND 450000 uses an absolute-count convention entirely mismatched with this database's actual PLT scale (verified real range is 5-5844, matching gold's 100-400 bounds), zeroing the result; also adds an unneeded join to Examination

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
AND strftime('%Y-%m-%d', 'now') - strftime('%Y-%m-%d', P.birthday) < 50
AND L.platelet_count BETWEEN 150000 AND 450000;
```

### Q1243 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='female' instead of 'F'; prothrombin_time>13.5 instead of gold's >=14 (both a boundary and threshold shift from the question's stated cutoff)

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN P.sex = 'female' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT P.ID) AS percentage_female_with_abnormal_pt
FROM 
    Patient P
JOIN 
    Laboratory L ON P.ID = L.ID
WHERE 
    (strftime('%Y', 'now') - strftime('%Y', P.birthday) - (strftime('%m-%d', 'now') < strftime('%m-%d', P.birthday))) > 55
    AND L.prothrombin_time > 13.5;
```

### Q1247 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** sex='male' instead of 'M'; white_blood_cell_count BETWEEN 4000 AND 11000 uses an absolute-count convention entirely mismatched with this database's actual WBC scale (verified real range is 0.9-35.2, matching gold's 3.5-9.0 bounds), zeroing the result

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

### Q1251 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's single fixed threshold IGG>=2000 with a sex-dependent branching condition (M>16.3 OR F>13.5) using unrelated clinical reference-range values (verified IGG's real scale is 3-6510, matching gold's threshold, not this 'normal range' convention) -- a fundamentally different, unrequested restructuring

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE (P.sex = 'M' AND L.immunoglobulin_g > 16.3) 
   OR (P.sex = 'F' AND L.immunoglobulin_g > 13.5);
```

### Q1252 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** treats immunoglobulin_g (a real INTEGER-valued lab column) as if it held a categorical string 'normal', instead of gold's numeric BETWEEN 900 AND 2000 range check; zeroes the result

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

**Outcome:** `wrong_answer` · **Reason:** treats immunoglobulin_a (a real numeric lab column) as if it held a categorical string 'normal', instead of gold's BETWEEN 80 AND 500 range check; zeroes the result

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

### Q1255 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's two-sided abnormal IGM range (<=40 OR >=400) with a single one-sided threshold (>100), fundamentally changing which patients qualify; also selects an extra COUNT column not requested

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT P.diagnosis, COUNT(DISTINCT P.ID) AS count
FROM Patient P
JOIN Laboratory L ON P.ID = L.ID
WHERE L.immunoglobulin_m > 100
GROUP BY P.diagnosis
ORDER BY count DESC
LIMIT 1;
```

### Q1256 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** checks L.c_reactive_protein IS NULL instead of gold's T1.Description (first_record_date) IS NULL -- a different real column on a different table; also drops the CRP='+' condition entirely, repurposing the same lab column for the null-check instead

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
LEFT JOIN Laboratory L ON P.ID = L.ID 
WHERE L.c_reactive_protein IS NULL;
```

### Q1257 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** creatinine>1.2 instead of gold's >=1.5 (a generic reference-range threshold substituted for the question's value); the age computation via birthday > DATE('now','-70 years') is a valid equivalent restructuring of gold's age<70, not a bug

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

### Q1265 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's exact RNP IN('negative','0') match with a numeric '<=10' comparison against a TEXT-typed column that mixes 'negative' and numeric-titer strings (verified real values include blank/0/1/4/8/15/16/64/256/negative, not a clean numeric scale), and uses admission_type='admitted' (fabricated; real domain is '+'/'-')

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT P.ID) 
FROM Patient P 
JOIN Laboratory L ON P.ID = L.ID 
WHERE L.anti_ribonuclear_protein <= 10 AND P.admission_type = 'admitted';
```

### Q1267 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's CTE-based 'ALL of a patient's Examination records show Thrombosis=0' aggregation (GROUP BY/HAVING MAX(Thrombosis)=0) for a flat single-row 'ANY exam record has thrombosis_degree=0' check; also uses anti_sm='normal' (verified not a real SM domain value; real values are blank/0/1/2/8/negative) instead of gold's IN('negative','0')

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
SELECT COUNT(DISTINCT Patient.ID) 
FROM Patient 
JOIN Examination ON Patient.ID = Examination.ID 
JOIN Laboratory ON Patient.ID = Laboratory.ID 
WHERE Laboratory.anti_sm = 'normal' AND Examination.thrombosis_degree = '0';
```

### Q1270 (challenging, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** drops gold's `NOT EXISTS (SELECT 1 FROM Examination WHERE Symptoms IS NOT NULL)` correlated subquery entirely, substituting an unrelated flat `p.diagnosis IS NULL` condition on a different table/column; also uses sex='female' (wrong value) and anti_scl70='normal' (verified not a real SC170 domain value)

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
JOIN Laboratory l ON p.ID = l.ID 
WHERE p.sex = 'female' 
AND p.diagnosis IS NULL 
AND l.anti_scl70 = 'normal';
```

### Q1275 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** anti_centromere='normal' and anti_ssb='normal' (verified not real domain values; real values include 'negative'/'0'/numeric titers) instead of gold's IN('negative','0'); sex='male' instead of 'M'

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

### Q1281 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** combines aspartate_aminotransferase (GOT, correct) OR alanine_aminotransferase (GPT, a different real lab test not part of the question) via OR, and uses threshold >40 instead of gold's >=60; also selects MIN(birthday) instead of the correctly-ordered ORDER BY Birthday DESC LIMIT 1 (which picks the most recent birthday, not the earliest)

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

## toxicology (38 failures)

### Q197 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='O' (wrong case; real values are lowercase like 'o') and bond_type='single' (wrong; real value is the symbol '-') don't match the stored values, zeroing the result; also unnecessarily joins the 'connected' table, which could inflate the atom count via row multiplication

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(oxygen_count) 
FROM (
    SELECT COUNT(DISTINCT a.atom_id) AS oxygen_count 
    FROM molecule m
    JOIN atom a ON m.molecule_id = a.molecule_id
    JOIN bond b ON m.molecule_id = b.molecule_id
    JOIN connected c ON a.atom_id = c.atom_id AND b.bond_id = c.bond_id
    WHERE a.element = 'O' AND b.bond_type = 'single'
    GROUP BY m.molecule_id
)
```

### Q198 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='single' and label='carcinogenic' don't match the real stored values ('-' and '+' respectively), zeroing the result

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(single_bond_count) 
FROM (
    SELECT COUNT(b.bond_id) AS single_bond_count 
    FROM molecule m 
    JOIN bond b ON m.molecule_id = b.molecule_id 
    WHERE b.bond_type = 'single' AND m.label = 'carcinogenic' 
    GROUP BY m.molecule_id
) AS single_bonds_per_molecule;
```

### Q200 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects m.label instead of gold's molecule_id (returning '+'/'-' values instead of molecule ID strings); also uses bond_type='triple'/label='carcinogenic' (real values are '#' and '+') and adds a NOT EXISTS restructuring requiring ALL of a molecule's bonds to be triple, which gold never requires

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label
FROM molecule m
JOIN bond b ON m.molecule_id = b.molecule_id
WHERE b.bond_type = 'triple'
AND NOT EXISTS (
    SELECT 1
    FROM bond b2
    WHERE b2.molecule_id = m.molecule_id
    AND b2.bond_type != 'triple'
)
AND m.label LIKE '%carcinogenic%';
```

### Q201 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** denominator uses COUNT(DISTINCT m.molecule_id) (molecule count) instead of gold's COUNT(DISTINCT atom_id) (atom count) -- a different real entity entirely; also element='C' and bond_type='double' don't match the real stored values ('c' and '=')

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'C' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT m.molecule_id) 
FROM atom a 
JOIN bond b ON a.molecule_id = b.molecule_id 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE b.bond_type = 'double';
```

### Q206 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR004_8_9' instead of gold's connected.bond_id = 'TR004_8_9' -- label only ever holds '+'/'-' (verified), never a bond-id-like string, zeroing the result; also drops the join to `connected` needed to filter by bond_id

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT a.element 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
JOIN connected c ON a.atom_id = c.atom_id 
JOIN bond b ON c.bond_id = b.bond_id 
WHERE m.label = 'TR004_8_9';
```

### Q207 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='double' doesn't match the real stored value '=', zeroing the result; also selects an extra second element column (a2.element) not requested by gold's single-column DISTINCT

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT DISTINCT a1.element, a2.element 
FROM atom a1 
JOIN connected c1 ON a1.atom_id = c1.atom_id 
JOIN bond b ON c1.bond_id = b.bond_id 
JOIN connected c2 ON b.bond_id = c2.bond_id 
JOIN atom a2 ON c2.atom_id = a2.atom_id 
WHERE b.bond_type = 'double';
```

### Q208 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element = 'H' (wrong case) doesn't match the stored value 'h', so the join subquery returns zero rows and the whole query returns nothing instead of gold's result

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT m.label 
FROM molecule m 
JOIN (
    SELECT DISTINCT molecule_id 
    FROM atom 
    WHERE element = 'H'
) h ON m.molecule_id = h.molecule_id 
GROUP BY m.label 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q212 (challenging, aggregate) — **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` · **Reason:** collapses gold's tie-preserving `HAVING COUNT(*) = (SELECT MIN(cnt)...)` into a plain ORDER BY COUNT(*) ASC LIMIT 1; also the WHERE clause `label != 'carcinogenic'` is a no-op since label only ever holds '+'/'-' (never the string 'carcinogenic'), so it never actually restricts to the intended '-' subset -- silently including every molecule

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
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label != 'carcinogenic' 
GROUP BY element 
ORDER BY COUNT(*) ASC 
LIMIT 1;
```

### Q213 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** compares atom.element (a chemical symbol column, e.g. 'c'/'h'/'o') against atom-ID-like literals ('TR004_8','TR004_20') that are clearly meant for atom_id, not element -- zeroing the result entirely since no element value looks like an atom ID

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT bond.bond_type 
FROM bond 
JOIN connected ON bond.bond_id = connected.bond_id 
JOIN atom AS atom1 ON connected.atom_id = atom1.atom_id 
JOIN atom AS atom2 ON connected.atom_id2 = atom2.atom_id 
WHERE atom1.element = 'TR004_8' AND atom2.element = 'TR004_20';
```

### Q215 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='I'/'S' (wrong case; real values are lowercase 'i'/'s') and bond_type='single' (wrong; real value is '-') don't match the stored values, zeroing both counts; also unnecessarily joins 'connected', risking row multiplication

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(CASE WHEN atom.element = 'I' THEN 1 END) AS iodine_count, 
    COUNT(CASE WHEN atom.element = 'S' THEN 1 END) AS sulfur_count 
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

### Q218 (challenging, aggregate) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `ambiguous column name: molecule_id` -- both atom.molecule_id and molecule.molecule_id exist after the join, and the bare `molecule_id` reference in SELECT/GROUP BY doesn't specify which; also label='carcinogenic' and element='F' don't match the real stored values ('+' and 'f'), which would have zeroed the result even if the syntax error were fixed

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN fluorine_count = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM (
    SELECT molecule_id, COUNT(CASE WHEN element = 'F' THEN 1 END) AS fluorine_count
    FROM atom
    JOIN molecule ON atom.molecule_id = molecule.molecule_id
    WHERE molecule.label = 'carcinogenic'
    GROUP BY molecule_id
) AS subquery;
```

### Q219 (challenging, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** swaps which condition is the population filter and which is the CASE-based numerator -- predicted computes 'the percentage of molecules with ANY triple bond' instead of gold's 'the percentage of already-triple-bonded molecules that are labeled +'; also 'triple' doesn't match the real stored bond_type value ('#')

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN b.bond_type = 'triple' THEN m.molecule_id END) AS REAL) * 100 / COUNT(DISTINCT m.molecule_id) 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id;
```

### Q220 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR000' instead of gold's atom.molecule_id = 'TR000' -- label only ever holds '+'/'-' (verified), never a molecule-id-like string, zeroing the result entirely

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

### Q226 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR008' instead of gold's bond.molecule_id = 'TR008' -- label only ever holds '+'/'-', zeroing the result; also bond_type='double' doesn't match the real stored value '='

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN bond_type = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT bond_id) AS percentage_double_bonds
FROM bond
JOIN molecule ON bond.molecule_id = molecule.molecule_id
WHERE molecule.label = 'TR008';
```

### Q227 (simple, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** label = 'carcinogenic' doesn't match the real stored value '+', zeroing the numerator

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT ROUND(CAST(SUM(CASE WHEN label = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*), 3) AS percentage
FROM molecule;
```

### Q228 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR206' instead of gold's atom.molecule_id = 'TR206' -- label only ever holds '+'/'-', zeroing the result; also element='H' doesn't match the real stored value 'h'

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN a.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(DISTINCT a.atom_id) AS hydrogen_percentage
FROM 
    atom a
JOIN 
    molecule m ON a.molecule_id = m.molecule_id
WHERE 
    m.label = 'TR206';
```

### Q230 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR060' instead of gold's molecule_id = 'TR060' -- label only ever holds '+'/'-', zeroing the result (though the SELECT list itself correctly includes label)

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

### Q231 (challenging, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR010' instead of gold's bond.molecule_id = 'TR010' -- label only ever holds '+'/'-', zeroing the result; also unnecessarily joins `connected`

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT bond.bond_type 
FROM bond 
JOIN molecule ON bond.molecule_id = molecule.molecule_id 
JOIN connected ON bond.bond_id = connected.bond_id 
WHERE molecule.label = 'TR010' 
GROUP BY bond.bond_type 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q232 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects m.label instead of gold's molecule_id; also drops the `bond_type='-'` filter entirely, replaces gold's `label='-'` filter with a no-op `label NOT LIKE '%carcinogenic%'` (always true, since label never contains that substring), and orders by bond count descending instead of gold's molecule_id ascending -- a completely different selection/ordering than gold

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT m.label 
FROM molecule m 
JOIN bond b ON m.molecule_id = b.molecule_id 
GROUP BY m.molecule_id 
HAVING COUNT(b.bond_id) > 0 AND m.label NOT LIKE '%carcinogenic%' 
ORDER BY COUNT(b.bond_id) DESC, m.label ASC 
LIMIT 3;
```

### Q234 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** joins through bond/molecule and filters molecule.label='TR009' (wrong column; label only ever holds '+'/'-') instead of gold's direct connected.atom_id/atom_id2 = 'TR009_12' filter; also compares atom_id/atom_id2 to the bare integer 12 instead of the correct compound string format ('TR009_12')

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT bond.bond_id) 
FROM bond 
JOIN molecule ON bond.molecule_id = molecule.molecule_id 
JOIN connected ON bond.bond_id = connected.bond_id 
WHERE molecule.label = 'TR009' AND (connected.atom_id = 12 OR connected.atom_id2 = 12);
```

### Q236 (moderate, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR001_6_9' instead of gold's connected.bond_id = 'TR001_6_9' -- label only ever holds '+'/'-', zeroing the result; also doesn't reach connected.bond_id via any join for the filter

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.bond_type, c.atom_id, c.atom_id2 
FROM bond b 
JOIN connected c ON b.bond_id = c.bond_id 
JOIN molecule m ON b.molecule_id = m.molecule_id 
WHERE m.label = 'TR001_6_9';
```

### Q239 (simple, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's SUBSTR(atom_id,-2)='19' suffix-matching with an exact `atom_id = 19` (bare integer) comparison against a compound TEXT id format (e.g. 'TR000_19'), which never matches; also selects COUNT(DISTINCT atom_id2) instead of gold's COUNT(bond_id)

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT atom_id2) 
FROM connected 
WHERE atom_id = 19;
```

### Q240 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR004' instead of gold's atom.molecule_id = 'TR004' -- label only ever holds '+'/'-', zeroing the result

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

### Q242 (moderate, retrieval) — **Invalid SQL** (Wrong column)

**Outcome:** `error` · **Reason:** `no such column: m.is_carcinogenic` -- this column doesn't exist anywhere in the schema (molecule only has molecule_id and label; label holds '+'/'-' for this concept); also compares atom_id to bare integers 21-25 instead of gold's SUBSTR(atom_id,-2) suffix-matching against a compound string format

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label 
FROM molecule m 
JOIN atom a ON m.molecule_id = a.molecule_id 
WHERE a.atom_id BETWEEN 21 AND 25 
AND m.is_carcinogenic = 1;
```

### Q243 (moderate, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='phosphorus'/'nitrogen' (spelled-out names) don't match the real stored lowercase codes 'p'/'n', zeroing the result

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT b.bond_id, b.bond_type
FROM bond b
JOIN connected c ON b.bond_id = c.bond_id
JOIN atom a1 ON c.atom_id = a1.atom_id
JOIN atom a2 ON c.atom_id2 = a2.atom_id
WHERE a1.element = 'phosphorus' AND a2.element = 'nitrogen'
```

### Q244 (moderate, aggregate) — **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` · **Reason:** replaces gold's tie-preserving CTE-based MAX-count matching (returning ALL molecules tied for the most '=' bonds) with a single ORDER BY COUNT(...) DESC LIMIT 1 subquery, dropping ties; also bond_type='double' doesn't match the real stored value '=', which alone already zeroes the result

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
WHERE m.molecule_id = (
    SELECT b.molecule_id 
    FROM bond b 
    WHERE b.bond_type = 'double' 
    GROUP BY b.molecule_id 
    ORDER BY COUNT(b.bond_id) DESC 
    LIMIT 1
);
```

### Q245 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='iodine' (spelled-out name) doesn't match the real stored code 'i', zeroing the result

**Gold SQL:**

```sql
SELECT CAST(COUNT(T2.bond_id) AS REAL) / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'i'
```

**Predicted SQL:**

```sql
SELECT AVG(bond_count) 
FROM (
    SELECT COUNT(DISTINCT bond_id) AS bond_count 
    FROM atom 
    JOIN connected ON atom.atom_id = connected.atom_id 
    WHERE atom.element = 'iodine' 
    GROUP BY atom.atom_id
)
```

### Q247 (challenging, retrieval) — **Other** (Missing/redundant DISTINCT/DESC)

**Outcome:** `wrong_answer` · **Reason:** drops gold's DISTINCT keyword entirely; the UNION-based exclusion set (atom_id OR atom_id2) is actually equivalent to gold's atom_id-only check since `connected` is fully symmetric (verified empirically -- both give the same 5 distinct elements), but without DISTINCT, predicted returns 49 raw rows (one per non-bonded atom) instead of gold's 5 deduplicated element values

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element 
FROM atom 
WHERE atom_id NOT IN (SELECT atom_id FROM connected UNION SELECT atom_id2 FROM connected);
```

### Q248 (simple, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR041' instead of gold's bond.molecule_id = 'TR041' -- label only ever holds '+'/'-', zeroing the result; also selects an extra atom_id2 column and uses bond_type='triple' instead of the real value '#'

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT DISTINCT c.atom_id, c.atom_id2 
FROM connected c 
JOIN bond b ON c.bond_id = b.bond_id 
JOIN molecule m ON b.molecule_id = m.molecule_id 
WHERE b.bond_type = 'triple' AND m.label = 'TR041';
```

### Q249 (challenging, retrieval) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** filters on molecule.label = 'TR144_8_19' instead of gold's connected.bond_id = 'TR144_8_19' -- label only ever holds '+'/'-', zeroing the result; drops the join to `connected` needed to filter by bond_id entirely

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT DISTINCT atom.element 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
WHERE molecule.label = 'TR144_8_19';
```

### Q253 (challenging, retrieval) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** bond_type='triple' doesn't match the real stored value '#', zeroing the result

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

### Q255 (moderate, aggregate) — **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` · **Reason:** drops the molecule/label join and condition entirely, computing 'the percentage of ALL bonds that are single-bonds' instead of gold's 'the percentage of already-single-bonded bonds whose molecule is labeled +' -- a completely different question; also bond_type='single' doesn't match the real stored value '-'

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

**Outcome:** `wrong_answer` · **Reason:** moves the element='p'/'br' condition from gold's molecule-qualifying subquery (any atom in a qualifying molecule is counted, regardless of its own element) into a direct atom-level filter (restricting the COUNTED atoms themselves to phosphorus/bromine) -- a fundamentally different count; also element='phosphorus'/'bromine' and bond_type='triple' don't match the real stored values ('p'/'br' and '#')

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT atom.atom_id) 
FROM atom 
JOIN molecule ON atom.molecule_id = molecule.molecule_id 
JOIN bond ON molecule.molecule_id = bond.molecule_id 
WHERE bond.bond_type = 'triple' AND (atom.element = 'phosphorus' OR atom.element = 'bromine');
```

### Q263 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='chlorine' and bond_type='single' don't match the real stored values ('cl' and '-'), zeroing the result (the CTE structure itself is a reasonable equivalent restatement of gold's IN-subquery)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
WITH SingleBondMolecules AS (
    SELECT DISTINCT a.molecule_id
    FROM atom a
    JOIN bond b ON a.molecule_id = b.molecule_id
    WHERE b.bond_type = 'single'
)
SELECT 
    (COUNT(CASE WHEN a.element = 'chlorine' THEN 1 END) * 100.0 / COUNT(a.atom_id)) AS chlorine_percentage
FROM 
    atom a
JOIN 
    SingleBondMolecules sbm ON a.molecule_id = sbm.molecule_id;
```

### Q273 (moderate, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element='chlorine' and label LIKE '%carcinogenic%' don't match the real stored values ('cl' and '+'/'-' exactly), zeroing the result entirely (label never contains the substring 'carcinogenic')

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'chlorine' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(a.atom_id) 
FROM atom a 
JOIN molecule m ON a.molecule_id = m.molecule_id 
WHERE m.label LIKE '%carcinogenic%'
```

### Q281 (challenging, retrieval) — **Invalid SQL** (Other execution error)

**Outcome:** `error` · **Reason:** `no such column: a.element` -- outer SELECT references alias `a`, which is only declared inside the derived subquery's own scope, not in the outer FROM (only `subquery` is); also restructures gold's SUBSTR(atom_id,-2)='_4' suffix-matching into a ROW_NUMBER()-based 4th-atom-per-molecule pick, and uses label='carcinogenic' instead of the real value '+'

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT a.element 
FROM (
    SELECT a.element, a.molecule_id, ROW_NUMBER() OVER (PARTITION BY a.molecule_id ORDER BY a.atom_id) as rn
    FROM atom a 
    JOIN molecule m ON a.molecule_id = m.molecule_id 
    WHERE m.label = 'carcinogenic'
) subquery
WHERE subquery.rn = 4;
```

### Q282 (challenging, aggregate) — **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` · **Reason:** element = 'H' (wrong case) doesn't match the real stored value 'h', zeroing the hydrogen count in the ratio (molecule_id filter itself is correct here)

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 0.0 
        ELSE (COUNT(CASE WHEN element = 'H' THEN 1 END) * 1.0 / COUNT(*)) 
    END AS hydrogen_ratio, 
    m.label 
FROM 
    atom a 
JOIN 
    molecule m ON a.molecule_id = m.molecule_id 
WHERE 
    m.molecule_id = 'TR006';
```

### Q327 (moderate, aggregate) — **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` · **Reason:** selects m.label instead of gold's molecule_id; also the `label NOT LIKE '%carcinogenic%'` filter is a no-op (always true, since label is never a string containing 'carcinogenic'), silently including both '+' and '-' labeled molecules instead of just gold's '-' subset

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label 
FROM molecule m 
JOIN atom a ON m.molecule_id = a.molecule_id 
WHERE m.label NOT LIKE '%carcinogenic%' 
GROUP BY m.molecule_id 
HAVING COUNT(a.atom_id) > 5;
```

---

