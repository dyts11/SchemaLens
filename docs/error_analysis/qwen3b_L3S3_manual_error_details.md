# Qwen2.5-Coder-3B - L3.S3 -- hand-classified failures (n=331)

Every failure was read by hand and classified directly against [`error_taxonomy.md`](error_taxonomy.md) -- no rule-based script was used to produce these labels. Predicted SQL uses S3 (descriptive snake_case) column names throughout -- these are cross-checked against `src/column_aliases.py` before being called a naming bug, so a renamed column that correctly matches its real counterpart is never flagged as wrong; only genuine substitutions of one real column/table for another, or literal-value errors, are. Grouped by database, sorted by question id.

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

## california_schools (29 failures)

### Q5 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References school_name on schools (T1), which doesn't have it -- only frpm's 'School Name' is renamed to school_name, and frpm isn't joined at all here; also drops the rtype = 'S' filter and uses Virtual = 'Yes' instead of the real code 'F'.

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
SELECT COUNT(T1.school_name) 
FROM schools AS T1 
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.average_score_math > 400 AND T1.Virtual = 'Yes';
```

### Q11 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Checks only enrollment_k12 > 500 instead of gold's SUM of Enrollment (K-12) + Enrollment (Ages 5-17) > 500, and drops the schools join / School IS NOT NULL check.

**Gold SQL:**

```sql
SELECT T2.CDSCode
FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
AND School is  not NULL
```

**Predicted SQL:**

```sql
SELECT county_district_school_code FROM frpm WHERE enrollment_k12 > 500;
```

### Q12 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the rtype = 'S' and NumTstTakr > 0 conditions, replaces them with fabricated average_score_reading/math/writing >= 800 thresholds not present in gold at all, and misapplies the > 0.3 threshold to the free-meal percentage instead of the NumGE1500/NumTstTakr ratio gold intends.

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
SELECT MAX(T1.percent_eligible_free_ages_5_17) AS highest_eligible_free_rate
FROM frpm AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.average_score_reading >= 800 AND T2.average_score_math >= 800 AND T2.average_score_writing >= 800
  AND T2.number_scores_1500_or_above > 0
  AND T1.percent_eligible_free_ages_5_17 > 0.3;
```

### Q17 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` -- **Reason:** Uses ROW_NUMBER() OVER (...) instead of gold's RANK() OVER (...), which breaks tie-handling (RANK gives equal ranks to ties, ROW_NUMBER doesn't); also drops the CharterNum IS NOT NULL and rtype = 'S' filters entirely.

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
    T1.charter_number,
    T2.average_score_writing,
    ROW_NUMBER() OVER (ORDER BY T2.average_score_writing DESC) AS rank
FROM 
    schools AS T1
JOIN 
    satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T2.average_score_writing > 499
ORDER BY 
    T2.average_score_writing DESC;
```

### Q23 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.Street where T1 is the frpm alias; Street only exists on schools (T2), which is already joined -- an alias mix-up (aliases are swapped relative to gold).

**Gold SQL:**

```sql
SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" - T2."Enrollment (Ages 5-17)" > 30 AND T1.School is not NULL
```

**Predicted SQL:**

```sql
SELECT T1.school_name, T1.Street, T1.street_abbreviated, T1.City, T1.Zip, T1.State
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.enrollment_k12 - T1.enrollment_ages_5_17 > 30;
```

### Q24 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Uses number_scores_1500_or_above >= 1500 instead of gold's NumGE1500 > 0 -- misreading the column (a count of high scorers) as if it should be compared against the literal value 1500; also drops the rtype = 'S' filter.

**Gold SQL:**

```sql
SELECT T2."School Name"
FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode 
WHERE CAST(T2."Free Meal Count (K-12)" AS REAL) / T2."Enrollment (K-12)" > 0.1 AND T1.NumGE1500 > 0 AND rtype = 'S'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.school_name FROM frpm AS T1 INNER JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T1.percent_eligible_free_k12 > 0.1 AND T2.number_scores_1500_or_above >= 1500
```

### Q25 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters schools.County = 'Riverside' instead of schools.District LIKE 'Riverside%' -- two different real columns with different matching semantics; also drops the GROUP BY sname, FundingType / HAVING AVG(AvgScrMath) > 400 aggregation entirely, applying the score check as a flat row filter, and drops the rtype = 'S' filter.

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
SELECT DISTINCT T1.School, T1.Funding_type
FROM schools AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.County = 'Riverside' AND T2.average_score_math > 400;
```

### Q26 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References Street/City/Zip/State/mailing-address columns via T1 (the frpm alias); those only exist on schools (T2), which is already joined. Also drops the School Type = 'High Schools (Public)' filter entirely.

**Gold SQL:**

```sql
SELECT T1."School Name", T2.Street, T2.City, T2.State, T2.Zip
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Monterey' AND T1."FRPM Count (Ages 5-17)" > 800 AND T1."School Type" = 'High Schools (Public)' AND T2.School is not NULL
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.school_name, 
       T1.street, 
       T1.street_abbreviated, 
       T1.city, 
       T1.zip, 
       T1.state, 
       T1.mailing_street, 
       T1.mailing_street_abbreviated, 
       T1.mailing_city, 
       T1.mailing_zip_code, 
       T1.mailing_state 
FROM frpm AS T1 
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.county_name = 'Monterey' 
  AND T1.enrollment_ages_5_17 > 800 
  AND T1.free_or_reduced_price_meal_count_ages_5_17 > 800;
```

### Q27 (moderate, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.comm_num (satscores alias), which isn't a real column anywhere in the schema; also references T1.school_name, which doesn't exist on satscores either (school names live on frpm/schools, not satscores).

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'
```

**Predicted SQL:**

```sql
SELECT T1.school_name, T1.average_score_writing, T1.comm_num
FROM satscores AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.open_date > '1991' OR T2.closed_date < '2000';
```

### Q28 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.school_name where T1 is the schools alias; school_name only exists on frpm (T2), which is already joined -- an alias mix-up (aliases are swapped relative to gold).

**Gold SQL:**

```sql
SELECT T2.School, T2.DOCType FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.FundingType = 'Locally funded' AND (T1."Enrollment (K-12)" - T1."Enrollment (Ages 5-17)") > (SELECT AVG(T3."Enrollment (K-12)" - T3."Enrollment (Ages 5-17)") FROM frpm AS T3 INNER JOIN schools AS T4 ON T3.CDSCode = T4.CDSCode WHERE T4.FundingType = 'Locally funded')
```

**Predicted SQL:**

```sql
SELECT 
    T1.school_name,
    T1.district_type
FROM 
    schools AS T1
JOIN 
    frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T1.funding_type = 'Locally Funded'
GROUP BY 
    T1.school_name, T1.district_type
HAVING 
    ABS(T2.enrollment_k12 - T2.enrollment_ages_5_17) > (
        SELECT AVG(T2.enrollment_k12 - T2.enrollment_ages_5_17)
        FROM frpm AS T2
        JOIN schools AS T1 ON T2.county_district_school_code = T1.county_district_school_code
        WHERE T1.funding_type = 'Locally Funded'
    )
```

### Q31 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the 'School IS NOT NULL' filter for a fabricated grade_span_served LIKE '%12%' condition not in gold, and replaces gold's LIMIT 9, 2 (rows 10-11 by the MySQL-style offset,count syntax) with a plain LIMIT 10 (rows 1-10) -- an entirely different row window.

**Gold SQL:**

```sql
SELECT CAST("Free Meal Count (K-12)" AS REAL) / "Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode  WHERE T2.school is not null ORDER BY "Enrollment (K-12)" DESC LIMIT 9, 2
```

**Predicted SQL:**

```sql
SELECT 
    T1.percent_eligible_free_k12
FROM 
    frpm AS T1
JOIN 
    schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T2.grade_span_served LIKE '%12%'
ORDER BY 
    T1.enrollment_k12 DESC
LIMIT 10;
```

### Q32 (moderate, retrieval) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted GROUP BY school_name not present in gold, and includes an extra school_name column in the SELECT list beyond gold's single ratio column.

**Gold SQL:**

```sql
SELECT CAST(T1."FRPM Count (K-12)" AS REAL) / T1."Enrollment (K-12)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.SOC = 66 ORDER BY T1."FRPM Count (K-12)" DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT 
    T1.school_name,
    T1.percent_eligible_free_or_reduced_price_meal_k12
FROM 
    frpm AS T1
JOIN 
    schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T2.school_ownership_code = 66
GROUP BY 
    T1.school_name
ORDER BY 
    T1.free_or_reduced_price_meal_count_k12 DESC
LIMIT 5;
```

### Q36 (challenging, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Drops 4 of gold's 6 requested columns (AdmFName2/AdmLName2/AdmFName3/AdmLName3), keeping only the first admin's name pair; also drops the rtype = 'S' filter.

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
SELECT DISTINCT T1.admin_first_name_1, T1.admin_last_name_1
FROM schools AS T1
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T2.number_scores_1500_or_above = (SELECT MAX(number_scores_1500_or_above) FROM satscores)
ORDER BY T2.number_scores_1500_or_above DESC
LIMIT 1;
```

### Q37 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Replaces gold's NumGE1500/NumTstTakr ratio-based MIN-matching with a fabricated average_score_reading/math/writing >= 800 filter not present in gold, and orders by the raw sum of the three scores instead.

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
SELECT T1.Street, T1.City, T1.State, T1.Zip 
FROM schools AS T1 
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T2.average_score_reading >= 800 AND T2.average_score_math >= 800 AND T2.average_score_writing >= 800 
ORDER BY T2.average_score_reading + T2.average_score_math + T2.average_score_writing ASC 
LIMIT 1;
```

### Q40 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters schools.County = 'Fresno' instead of schools.District = 'Fresno Unified' -- a broader, different real column/scope; also uses an invented rtype value 'Fall 1' instead of the real code 'S'.

**Gold SQL:**

```sql
SELECT T2.Phone FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.District = 'Fresno Unified' AND T1.AvgScrRead IS NOT NULL AND rtype = 'S'  ORDER BY T1.AvgScrRead ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.Phone 
FROM schools AS T1 
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.County = 'Fresno' AND T2.record_type = 'Fall 1' 
ORDER BY T2.average_score_reading ASC 
LIMIT 1;
```

### Q41 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's RANK() OVER (PARTITION BY cname ORDER BY AvgScrRead DESC) window function entirely, replacing it with a GROUP BY County + AVG aggregation that returns one row per county instead of the top-5 schools within each county; also uses Virtual = 'Yes' instead of the real code 'F'.

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
SELECT DISTINCT T1.School 
FROM schools AS T1 
JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code 
WHERE T1.Virtual = 'Yes' 
GROUP BY T1.County 
ORDER BY AVG(T2.average_score_reading) DESC 
LIMIT 5;
```

### Q45 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References s.school_name where s is the schools alias; schools has no school_name column (only frpm's 'School Name' is renamed to that) -- schools' own name column is just 'School'. Also adds an unwarranted AVG()/GROUP BY not present in gold's simple row lookup.

**Gold SQL:**

```sql
SELECT T2.School, T1.AvgScrWrite FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.AdmFName1 = 'Ricci' AND T2.AdmLName1 = 'Ulrich'
```

**Predicted SQL:**

```sql
SELECT 
    s.school_name,
    AVG(satscores.average_score_writing) AS average_writing_score
FROM 
    schools s
JOIN 
    satscores ss ON s.county_district_school_code = ss.county_district_school_code
WHERE 
    s.admin_first_name_1 = 'Ricci' AND s.admin_last_name_1 = 'Ulrich'
GROUP BY 
    s.school_name;
```

### Q46 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.school_code where T1 is the schools alias; school_code only exists on frpm (T2), which is already joined. The query is also restructured to answer a different question entirely (counts schools per state via a fabricated school_type = 'Special' filter, instead of gold's DOC = 31 filter with ORDER BY enrollment DESC LIMIT 1).

**Gold SQL:**

```sql
SELECT T2.School 
FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode 
WHERE T2.DOC = 31 AND T2.school is not NULL ORDER BY T1."Enrollment (K-12)" DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.State, COUNT(T1.school_code) AS total_enrollment
FROM schools AS T1
JOIN frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.school_type = 'Special'
GROUP BY T1.State
ORDER BY total_enrollment DESC
LIMIT 1;
```

### Q47 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Queries frpm instead of schools entirely, replacing gold's DOC = 52 filter with an invented district_type = 'Elementary School District' condition and gold's OpenDate-year check with academic_year = 1980 (a different real column, likely a different string format too); also uses AVG(enrollment_k12) instead of COUNT(School) as the numerator.

**Gold SQL:**

```sql
SELECT CAST(COUNT(School) AS REAL) / 12 FROM schools WHERE DOC = 52 AND County = 'Alameda' AND strftime('%Y', OpenDate) = '1980'
```

**Predicted SQL:**

```sql
SELECT AVG(enrollment_k12) / 12 AS monthly_average_schools
FROM frpm
WHERE county_name = 'Alameda' AND district_type = 'Elementary School District' AND academic_year = 1980;
```

### Q48 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Uses frpm.district_type values 'Unified'/'Elementary' instead of gold's schools.DOC codes (52/54) combined with StatusType = 'Merged' -- an entirely different, unrelated real concept -- and doesn't compute a ratio at all, just two raw counts.

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
    SUM(CASE WHEN T1.district_type = 'Unified' THEN 1 ELSE 0 END) AS unified_count,
    SUM(CASE WHEN T1.district_type = 'Elementary' THEN 1 ELSE 0 END) AS elementary_count
FROM 
    frpm AS T1
JOIN 
    schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE 
    T1.county_name = 'Orange';
```

### Q50 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Selects/orders using Street instead of gold's MailStreet -- two distinct real columns on schools; also uses an invented rtype value 'Math' instead of 'S', and reverses the MySQL-style LIMIT 6, 1 (skip 6, take 1) into LIMIT 6 OFFSET 1 (skip 1, take 6), a different row window entirely.

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
SELECT T1.Street, T1.School FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.record_type = 'Math' ORDER BY T2.average_score_math DESC LIMIT 6 OFFSET 1;
```

### Q62 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Uses frpm.is_charter_school = 'N' instead of gold's schools.Charter = 0 -- two distinct columns on different tables for the charter-status concept, with a different value encoding; also compares the precomputed percent_eligible_free_k12 column directly to 0.18 instead of recomputing gold's Free Meal Count (K-12) * 100 / Enrollment (K-12) formula, which may differ in scale.

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

### Q72 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters frpm.county_name = 'Fremont' instead of gold's schools.City = 'Fremont' -- Fremont is a city, not a county; also substitutes school_type = 'State Special School' for the unrelated EdOpsCode = 'SSS' column, and uses COUNT(*) instead of gold's SUM(Enrollment (Ages 5-17)).

**Gold SQL:**

```sql
SELECT SUM(T1."Enrollment (Ages 5-17)") 
FROM frpm AS T1 
INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode
WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" BETWEEN 2014 AND 2015 AND T2.school is not NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM frpm 
WHERE county_name = 'Fremont' 
  AND academic_year = '2014-2015' 
  AND school_type = 'State Special School' 
  AND enrollment_ages_5_17 > 0;
```

### Q77 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.grade_span_served where T1 is the frpm alias; grade_span_served (GSserved) only exists on schools (T2), which is already joined -- an alias mix-up on an already-joined table.

**Gold SQL:**

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.school_name, T1.percent_eligible_free_ages_5_17
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.county_name = 'Los Angeles' AND T1.grade_span_served = 'K-9';
```

### Q79 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.County where T1 is the frpm alias; frpm has no 'County' column (only the differently-named 'County Name'/county_name) -- County only exists on schools (T2), which is already joined.

**Gold SQL:**

```sql
SELECT County, COUNT(Virtual) FROM schools WHERE (County = 'San Diego' OR County = 'Santa Barbara') AND Virtual = 'F' GROUP BY County ORDER BY COUNT(Virtual) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.County, COUNT(T1.school_code) AS Number_of_Schools
FROM frpm AS T1
JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.County IN ('San Diego', 'Santa Barbara')
  AND T2.Virtual = 'No'
GROUP BY T1.County
ORDER BY Number_of_Schools DESC
LIMIT 1;
```

### Q82 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the ABS() transformation around Longitude; since California longitudes are uniformly negative, ordering by the raw (signed) value DESC picks the value closest to zero instead of gold's most-extreme (largest magnitude) longitude.

**Gold SQL:**

```sql
SELECT GSoffered FROM schools ORDER BY ABS(longitude) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT grade_span_offered FROM schools ORDER BY Longitude DESC LIMIT 1;
```

### Q83 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References grade_span_served on frpm (T2) -- itself the wrong one of two similar GS* columns, and frpm doesn't have either; the real grade_span_offered (GSoffered) only exists on schools (T1). Also substitutes the unrelated educational_option_type column for NSLP Provision Status, and uses a spelled-out value 'Kindergarten to 8th grade' instead of the real code 'K-8'.

**Gold SQL:**

```sql
SELECT s.City, COUNT(*) AS school_count FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.GSoffered = 'K-8' AND f."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY s.City
```

**Predicted SQL:**

```sql
SELECT T1.City, COUNT(T1.County_district_school_code) AS Number_of_Schools
FROM schools AS T1
JOIN frpm AS T2 ON T1.County_district_school_code = T2.county_district_school_code
WHERE T2.grade_span_served = 'Kindergarten to 8th grade' AND T2.educational_option_type = 'Multiple Provision Types'
GROUP BY T1.City;
```

### Q85 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Drops the Free Meal Count (K-12) * 100 / Enrollment (K-12) ratio column entirely from the SELECT list, returning only district_code.

**Gold SQL:**

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / T1."Enrollment (K-12)", T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

**Predicted SQL:**

```sql
SELECT T1.district_code FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.county_district_school_code = T2.county_district_school_code WHERE T2.admin_first_name_1 = 'Alusine'
```

### Q87 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the DOC = 54 and SOC = 62 conditions entirely, replacing them with a fabricated grade_span_offered filter not present in gold, and uses City = 'San Bernardino City Unified' (a district-sounding value) instead of the real 'San Bernardino'.

**Gold SQL:**

```sql
SELECT T2.AdmEmail1, T2.AdmEmail2 FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino' AND T2.DOC = 54 AND strftime('%Y', T2.OpenDate) BETWEEN '2009' AND '2010' AND T2.SOC = 62
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.admin_email_1, T1.admin_email_2
FROM schools AS T1
JOIN frpm AS T2 ON T1.county_district_school_code = T2.county_district_school_code
WHERE T1.County = 'San Bernardino'
  AND T1.City = 'San Bernardino City Unified'
  AND T1.open_date BETWEEN '2009-01-01' AND '2010-12-31'
  AND T1.grade_span_offered IN ('Intermediate/Middle School', 'Unified School');
```

---

## debit_card_specializing (27 failures)

### Q1471 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** T2.currency (transactions_1k alias) should be T1.currency (customers); currency only exists on customers, so this is an alias mix-up on an already-joined table, not a hallucination.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T2.currency = 'EUR' THEN 1 ELSE 0 END) / COUNT(T1.customer_id) AS ratio_eur,
    SUM(CASE WHEN T2.currency = 'CZK' THEN 1 ELSE 0 END) / COUNT(T1.customer_id) AS ratio_czk
FROM 
    customers AS T1
JOIN 
    transactions_1k AS T2 ON T1.customer_id = T2.customer_id;
```

### Q1472 (moderate, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Uses MIN(consumption) grouped per customer with no ORDER BY/LIMIT, instead of SUM(consumption) per customer ordered ascending and limited to 1, so it returns every customer's monthly minimum rather than the single lowest-total-consumption customer.

**Gold SQL:**

```sql
SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.customer_id, MIN(T3.consumption) AS min_consumption
FROM customers AS T1
JOIN yearmonth AS T3 ON T1.customer_id = T3.customer_id
WHERE T1.segment = 'LAM' AND strftime('%Y', T3.date) = '2012'
GROUP BY T1.customer_id;
```

### Q1473 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Calls YEAR(date), a non-SQLite function; no such function error.

**Gold SQL:**

```sql
SELECT AVG(TotalConsumption) / 12 FROM (SELECT SUM(T2.Consumption) AS TotalConsumption FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY T1.CustomerID)
```

**Predicted SQL:**

```sql
SELECT AVG(consumption) AS average_monthly_consumption
FROM yearmonth
WHERE customer_id IN (
    SELECT customer_id
    FROM customers
    WHERE segment = 'SME'
)
AND YEAR(date) = 2013;
```

### Q1476 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds a spurious extra join to transactions_1k, then joins yearmonth on transaction date instead of customer, shifting the join grain and misapplying the year filter to the transaction date instead of yearmonth's date.

**Gold SQL:**

```sql
SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T1.currency = 'CZK' THEN T3.consumption ELSE 0 END) - SUM(CASE WHEN T1.currency = 'EUR' THEN T3.consumption ELSE 0 END) AS consumption_difference
FROM 
    customers AS T1
JOIN 
    transactions_1k AS T2 ON T1.customer_id = T2.customer_id
JOIN 
    yearmonth AS T3 ON T2.date = T3.date
WHERE 
    strftime('%Y', T2.date) = '2012';
```

### Q1479 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References T2.year; no 'year' column exists anywhere in the schema (yearmonth stores YYYYMM as a text Date column, not a separate year).

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.year, SUM(T3.consumption) AS total_consumption
FROM customers AS T1
JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id
JOIN transactions_1k AS T3 ON T1.customer_id = T3.customer_id
WHERE T1.currency = 'CZK'
GROUP BY T2.year
ORDER BY total_consumption DESC
LIMIT 1;
```

### Q1480 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** T2.consumption (customers alias) should be T1.consumption (yearmonth); alias mix-up on an already-joined table.

**Gold SQL:**

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.date, MAX(T2.consumption) AS max_consumption
FROM yearmonth AS T1
JOIN customers AS T2 ON T1.customer_id = T2.customer_id
WHERE T2.segment = 'SME' AND strftime('%Y', T1.date) = '2013'
GROUP BY T1.date;
```

### Q1481 (challenging, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` -- **Reason:** Gold chains four CTEs to compute per-customer/segment totals then segment minimums; predicted collapses everything into one flat aggregation with an unrelated extra join and no CTEs at all.

**Gold SQL:**

```sql
WITH customer_consumption AS (SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS TotalConsumption, COUNT(DISTINCT ym.CustomerID) AS CustomerCount FROM customers AS c JOIN yearmonth AS ym ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201301' AND '201312' AND c.Currency = 'CZK' GROUP BY c.Segment, c.CustomerID), customer_average_consumption AS (SELECT Segment, TotalConsumption, CAST(TotalConsumption AS REAL) / CustomerCount AS AnnualAverageConsumption FROM customer_consumption), segment_min_consumption AS (SELECT Segment, MIN(TotalConsumption) LeastConsumptionCustomer FROM customer_average_consumption GROUP BY Segment), segment_min_consumption_avg AS (SELECT T1.Segment, T2.AnnualAverageConsumption FROM segment_min_consumption T1 JOIN customer_average_consumption T2 ON T1.Segment = T2.Segment AND T1.LeastConsumptionCustomer = T2.TotalConsumption) SELECT SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'LAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)), SUM(IIF(Segment = 'KAM', AnnualAverageConsumption, 0)) - SUM(IIF(Segment = 'SME', AnnualAverageConsumption, 0)) FROM segment_min_consumption_avg
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T1.segment = 'SME' THEN T3.consumption ELSE 0 END) - SUM(CASE WHEN T1.segment = 'LAM' THEN T3.consumption ELSE 0 END)) AS SME_LAM_diff,
    (SUM(CASE WHEN T1.segment = 'LAM' THEN T3.consumption ELSE 0 END) - SUM(CASE WHEN T1.segment = 'KAM' THEN T3.consumption ELSE 0 END)) AS LAM_KAM_diff,
    (SUM(CASE WHEN T1.segment = 'KAM' THEN T3.consumption ELSE 0 END) - SUM(CASE WHEN T1.segment = 'SME' THEN T3.consumption ELSE 0 END)) AS KAM_SME_diff
FROM 
    customers AS T1
JOIN 
    transactions_1k AS T2 ON T1.customer_id = T2.customer_id
JOIN 
    yearmonth AS T3 ON T2.date = T3.date
WHERE 
    T1.currency = 'CZK'
    AND T2.date BETWEEN '2013-01-01' AND '2013-12-31'
GROUP BY 
    T1.segment;
```

### Q1482 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Calls YEAR(date), a non-SQLite function.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0))) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'SME' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'LAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)), CAST(SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2013%', T2.Consumption, 0)) - SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) AS FLOAT) * 100 / SUM(IIF(T1.Segment = 'KAM' AND T2.Date LIKE '2012%', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'EUR'
```

**Predicted SQL:**

```sql
SELECT 
    segment,
    (SUM(CASE WHEN YEAR(date) = 2013 THEN consumption ELSE 0 END) - SUM(CASE WHEN YEAR(date) = 2012 THEN consumption ELSE 0 END)) / SUM(CASE WHEN YEAR(date) = 2012 THEN consumption ELSE 0 END) * 100 AS percentage_change
FROM 
    yearmonth
JOIN 
    customers ON yearmonth.customer_id = customers.customer_id
WHERE 
    customers.segment IN ('SME', 'LAM', 'KAM')
GROUP BY 
    segment;
```

### Q1483 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** BETWEEN uses ISO-style date strings '2013-08-01'/'2013-11-30' against yearmonth.Date, which is stored as YYYYMM text ('201308'...), so the bound format doesn't actually bracket the real values -- a wrong date-format transformation, not just a wrong literal.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE CustomerID = 6 AND Date BETWEEN '201308' AND '201311'
```

**Predicted SQL:**

```sql
SELECT SUM(consumption) AS total_consumption
FROM yearmonth
WHERE customer_id = 6 AND date BETWEEN '2013-08-01' AND '2013-11-30';
```

### Q1484 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Gold needs no join at all (single-table gasstations query); predicted invents a join from gasstations to yearmonth via a gas_station_id column yearmonth doesn't have -- reaching it would require transactions_1k as the connecting table.

**Gold SQL:**

```sql
SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS difference
FROM gasstations AS g
JOIN yearmonth AS y ON g.gas_station_id = y.gas_station_id
WHERE g.country = 'Czech Republic' AND y.consumption > 0
EXCEPT
SELECT COUNT(*)
FROM gasstations AS g
JOIN yearmonth AS y ON g.gas_station_id = y.gas_station_id
WHERE g.country = 'Slovakia' AND y.consumption > 0;
```

### Q1486 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** T2.currency (transactions_1k alias) should be T1.currency (customers); alias mix-up.

**Gold SQL:**

```sql
SELECT SUM(Currency = 'CZK') - SUM(Currency = 'EUR') FROM customers WHERE Segment = 'SME'
```

**Predicted SQL:**

```sql
SELECT SUM(CASE WHEN T2.currency = 'CZK' THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.currency = 'EUR' THEN 1 ELSE 0 END) AS difference
FROM customers AS T1
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id
WHERE T1.segment = 'SME';
```

### Q1490 (moderate, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Drops COUNT(DISTINCT ...) for both numerator and denominator, so it counts customer-month rows from the join instead of distinct customers.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Consumption > 46.73, T1.CustomerID, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.CustomerID) FROM customers AS T1 LEFT JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.consumption > 46.73 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.customer_id = T2.customer_id WHERE T1.segment = 'LAM'
```

### Q1493 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unnecessary extra join to transactions_1k, multiplying rows, and applies the date filter to the wrong joined table's date column (transaction date) instead of yearmonth's month field.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id INNER JOIN yearmonth AS T3 ON T2.customer_id = T3.customer_id WHERE strftime('%Y-%m', T2.date) = '2012-02'
```

### Q1498 (simple, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Drops the GROUP BY month entirely, collapsing gold's per-month SUM + top-1 selection into a flat MAX(consumption) over the whole year.

**Gold SQL:**

```sql
SELECT SUM(Consumption) FROM yearmonth WHERE SUBSTR(Date, 1, 4) = '2012' GROUP BY SUBSTR(Date, 5, 2) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MAX(consumption) AS highest_monthly_consumption
FROM yearmonth
WHERE strftime('%Y', date) = '2012';
```

### Q1500 (simple, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Missing DISTINCT on the returned description column, allowing duplicate rows.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T1.Date LIKE '2012-08-%'
```

**Predicted SQL:**

```sql
SELECT T3.description FROM transactions_1k AS T1 INNER JOIN products AS T3 ON T1.product_id = T3.product_id WHERE strftime('%Y-%m', T1.date) = '2012-08'
```

### Q1505 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins to transactions_1k instead of yearmonth to reach the consumption filter; transactions_1k has no consumption column.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.customer_id) 
FROM customers AS T1 
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id 
WHERE T1.currency = 'EUR' AND T2.consumption > 1000;
```

### Q1506 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses 'Czech Republic' instead of the country code 'CZE' -- same column/operator, just the wrong surface form of the value.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Description FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN products AS T3 ON T1.ProductID = T3.ProductID WHERE T2.Country = 'CZE'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.description 
FROM transactions_1k AS T1 
JOIN gasstations AS T2 ON T1.gas_station_id = T2.gas_station_id 
JOIN products AS T3 ON T1.product_id = T3.product_id 
WHERE T2.country = 'Czech Republic';
```

### Q1507 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** T2.time (gasstations alias) should be T1.time (transactions_1k); alias mix-up on an already-joined table.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Time FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T2.ChainID = 11
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.time FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.gas_station_id = T2.gas_station_id WHERE T2.chain_id = 11;
```

### Q1509 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses 'Czech Republic' instead of 'CZE'.

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
SELECT COUNT(T1.transaction_id) 
FROM transactions_1k AS T1 
JOIN gasstations AS T2 ON T1.gas_station_id = T2.gas_station_id 
WHERE T2.country = 'Czech Republic' AND T1.date > '2012-01-01';
```

### Q1514 (simple, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Missing DISTINCT on the returned currency column.

**Gold SQL:**

```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Predicted SQL:**

```sql
SELECT T1.currency 
FROM customers AS T1 
JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id 
WHERE T2.date = '2012-08-24' AND T2.time = '16:25:00';
```

### Q1524 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters T1.amount = 548.4 instead of T1.price = 548.4; both are real columns on transactions_1k, wrong one used.

**Gold SQL:**

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price  = 548.4
```

**Predicted SQL:**

```sql
SELECT T3.country FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.customer_id = T2.customer_id INNER JOIN gasstations AS T3 ON T1.gas_station_id = T3.gas_station_id WHERE T1.date = '2012-08-24' AND T1.amount = 548.4;
```

### Q1525 (simple, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Drops COUNT(DISTINCT ...) for numerator and denominator, counting rows instead of distinct customers.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(T2.Currency = 'EUR', T1.CustomerID, NULL)) AS FLOAT) * 100 / COUNT(DISTINCT T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.currency = 'EUR' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.customer_id = T2.customer_id WHERE T2.date = '2012-08-25'
```

### Q1526 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Inner subquery filters amount = 634.8 instead of price = 634.8 (both real transactions_1k columns), which finds the wrong/no target customer; outer query also drops gold's per-year SUM aggregation in favor of a raw self-join.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) - SUM(IIF(SUBSTRING(Date, 1, 4) = '2013', Consumption, 0)) AS FLOAT) / SUM(IIF(SUBSTRING(Date, 1, 4) = '2012', Consumption, 0)) FROM yearmonth WHERE CustomerID = ( SELECT T1.CustomerID FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-25' AND T1.Price  = 634.8 )
```

**Predicted SQL:**

```sql
SELECT 
    T1.consumption AS consumption_2012,
    T2.consumption AS consumption_2013,
    (T1.consumption - T2.consumption) / T1.consumption * 100 AS consumption_decrease_rate
FROM 
    yearmonth AS T1
JOIN 
    yearmonth AS T2 ON T1.customer_id = T2.customer_id AND T2.date LIKE '2013%'
WHERE 
    T1.customer_id = (SELECT customer_id FROM transactions_1k WHERE date = '2012-08-25' AND amount = 634.8)
ORDER BY 
    T1.date ASC
LIMIT 1;
```

### Q1528 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Gold needs no join (single-table gasstations query); predicted adds a spurious join to customers via a customer_id column gasstations doesn't have.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN T2.segment = 'premium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.customer_id) AS premium_percentage
FROM 
    customers AS T1
JOIN 
    gasstations AS T2 ON T1.customer_id = T2.customer_id
WHERE 
    T2.country = 'SVK';
```

### Q1529 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Unnecessary join to yearmonth introduces an ambiguous unqualified customer_id reference shared by both joined tables.

**Gold SQL:**

```sql
SELECT SUM(Amount * Price) AS total_spent, SUM(CASE WHEN Date LIKE '2012-08%' THEN Amount * Price ELSE 0 END) AS august_2012_spent FROM transactions_1k WHERE CustomerID = 38508
```

**Predicted SQL:**

```sql
SELECT SUM(amount) AS total_spent, SUM(consumption) AS total_consumption
FROM transactions_1k
JOIN yearmonth ON transactions_1k.customer_id = yearmonth.customer_id AND transactions_1k.date = yearmonth.date
WHERE customer_id = 38508 AND strftime('%Y-%m', date) = '2012-08';
```

### Q1531 (moderate, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Uses plain AVG(price) instead of the weighted SUM(price*amount)/SUM(amount), and picks the top spender by SUM(amount) instead of SUM(amount*price).

**Gold SQL:**

```sql
SELECT c.CustomerID, SUM(t.Price * t.Amount) / SUM(t.Amount) AS average_price_per_item, c.Currency FROM transactions_1k AS t JOIN customers AS c ON t.CustomerID = c.CustomerID WHERE t.CustomerID = ( SELECT CustomerID FROM transactions_1k GROUP BY CustomerID ORDER BY SUM(Amount * Price) DESC LIMIT 1 ) GROUP BY c.CustomerID, c.Currency;
```

**Predicted SQL:**

```sql
SELECT 
    c.customer_id,
    AVG(t.price) AS average_price_per_item,
    c.currency
FROM 
    customers c
JOIN 
    transactions_1k t ON c.customer_id = t.customer_id
GROUP BY 
    c.customer_id, c.currency
ORDER BY 
    SUM(t.amount) DESC
LIMIT 1;
```

### Q1533 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the Price/Amount ratio filter, comparing raw Amount > 29 instead of Price/Amount > 29 -- a restructured expression, not just a different value.

**Gold SQL:**

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / T1.Amount > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

**Predicted SQL:**

```sql
SELECT T3.consumption 
FROM transactions_1k AS T1 
JOIN products AS T2 ON T1.product_id = T2.product_id 
JOIN yearmonth AS T3 ON T1.customer_id = T3.customer_id AND strftime('%Y-%m', T1.date) = '2012-08' 
WHERE T2.product_id = 5 AND T1.amount > 29.00;
```

---

## european_football_2 (39 failures)

### Q1025 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** season = '2016' instead of the real format '2015/2016'.

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

### Q1028 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Returns team_short_name instead of team_long_name (both real Team columns); also uses season = '2010' instead of '2009/2010', and collapses gold's tie-preserving HAVING = (SELECT MAX(win_count)...) subquery into a plain ORDER BY ... LIMIT 1.

**Gold SQL:**

```sql
SELECT DISTINCT t.team_long_name FROM Team t JOIN Match m ON t.team_api_id = m.away_team_api_id JOIN League l ON m.league_id = l.id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY t.team_api_id, t.team_long_name HAVING COUNT(*) = ( SELECT MAX(win_count) FROM ( SELECT COUNT(*) AS win_count FROM Match m2 JOIN League l2 ON m2.league_id = l2.id WHERE l2.name = 'Scotland Premier League' AND m2.season = '2009/2010' AND m2.away_team_goal > m2.home_team_goal GROUP BY m2.away_team_api_id ) );
```

**Predicted SQL:**

```sql
SELECT T2.team_short_name
FROM Match AS T1
JOIN Team AS T2 ON T1.away_team_api_id = T2.team_api_id
JOIN League AS T3 ON T1.league_id = T3.id
WHERE T3.name = 'Scotland Premier League' AND T1.season = 2010
GROUP BY T2.team_short_name
ORDER BY COUNT(T1.id) DESC
LIMIT 1;
```

### Q1029 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** T2.buildup_play_speed (Team alias) should be T1.buildup_play_speed (Team_Attributes); alias mix-up on an already-joined table.

**Gold SQL:**

```sql
SELECT t1.buildUpPlaySpeed FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id ORDER BY t1.buildUpPlaySpeed DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT T2.buildup_play_speed, T2.buildup_play_speed_class
FROM Team_Attributes AS T1
JOIN Team AS T2 ON T1.team_api_id = T2.team_api_id
ORDER BY T1.buildup_play_speed DESC
LIMIT 4;
```

### Q1030 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the home_team_goal = away_team_goal draw condition entirely, replacing it with an unrelated M.card = 'D' condition (card stores unrelated card-event data, not match outcome); also uses season = '2016' instead of '2015/2016'.

**Gold SQL:**

```sql
SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT L.name
FROM League L
JOIN Match M ON L.id = M.league_id
WHERE M.season = '2016' AND M.card = 'D'
GROUP BY L.name
ORDER BY COUNT(M.id) DESC
LIMIT 1;
```

### Q1031 (challenging, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's leap-day-aware CASE month/day adjustment in the age formula, using a plain year(now)-year(birthday) subtraction instead; also misses DISTINCT.

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
SELECT T1.player_name, (strftime('%Y', 'now') - strftime('%Y', T1.birthday)) AS age
FROM Player AS T1
JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T2.sprint_speed >= 97 AND T2.date BETWEEN '2013-01-01' AND '2015-12-31'
GROUP BY T1.player_name;
```

### Q1032 (moderate, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` -- **Reason:** Collapses gold's tie-preserving GROUP BY ... HAVING match_count = (SELECT MAX(match_count)...) subquery into a plain ORDER BY ... LIMIT 1.

**Gold SQL:**

```sql
SELECT l.name, COUNT(m.id) AS match_count FROM League AS l JOIN Match AS m ON l.id = m.league_id GROUP BY l.id, l.name HAVING COUNT(m.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(id) AS match_count FROM Match GROUP BY league_id ) )
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(M.id) AS total_matches
FROM League L
JOIN Match M ON L.id = M.league_id
GROUP BY L.id
ORDER BY total_matches DESC
LIMIT 1;
```

### Q1035 (simple, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unneeded join from Team_Attributes to Team using ON T1.team_api_id = T2.id (Team's own primary key, not its api id) instead of T2.team_api_id; gold needs no join at all since Team_Attributes already has team_fifa_api_id directly.

**Gold SQL:**

```sql
SELECT DISTINCT team_fifa_api_id FROM Team_Attributes WHERE buildUpPlaySpeed > 50 AND buildUpPlaySpeed < 60
```

**Predicted SQL:**

```sql
SELECT T2.team_fifa_api_id FROM Team_Attributes AS T1 INNER JOIN Team AS T2 ON T1.team_api_id = T2.id WHERE T1.buildup_play_speed BETWEEN 50 AND 59
```

### Q1036 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T3.team_long_name where T3 is the League alias; team_long_name only exists on Team (T2), which is already joined -- an alias mix-up, on top of adding unneeded League/Country joins.

**Gold SQL:**

```sql
SELECT DISTINCT t4.team_long_name FROM Team_Attributes AS t3 INNER JOIN Team AS t4 ON t3.team_api_id = t4.team_api_id WHERE SUBSTR(t3."date", 1, 4) = '2012' AND t3.buildUpPlayPassing > ( SELECT CAST(SUM(t2.buildUpPlayPassing) AS REAL) / COUNT(t1.id) FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE STRFTIME('%Y',t2."date") = '2012')
```

**Predicted SQL:**

```sql
SELECT T3.team_long_name
FROM Team_Attributes AS T1
JOIN Team AS T2 ON T1.team_api_id = T2.team_api_id
JOIN League AS T4 ON T2.league_id = T4.id
JOIN Country AS T5 ON T4.country_id = T5.id
WHERE T1.date LIKE '2012%'
GROUP BY T2.team_long_name
HAVING AVG(T1.buildup_play_passing) > (SELECT AVG(buildup_play_passing) FROM Team_Attributes WHERE date LIKE '2012%')
```

### Q1037 (challenging, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** preferred_foot = 'Left' instead of the real lowercase value 'left'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.preferred_foot = 'left' THEN t1.id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t1.birthday, 1, 4) BETWEEN '1987' AND '1992'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.preferred_foot = 'Left' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.player_api_id) FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.birthday BETWEEN '1987-01-01' AND '1992-12-31'
```

### Q1040 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Filters pa.height > 180 (Player_Attributes alias); height only exists on Player, which is already joined.

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
SELECT p.player_name
FROM Player p
JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id
WHERE pa.height > 180
GROUP BY p.player_api_id
ORDER BY AVG(pa.heading_accuracy) DESC
LIMIT 10;
```

### Q1044 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unnecessary join to Player_Attributes that gold doesn't need at all, which can duplicate the single matching Player row once per attribute-history entry.

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE SUBSTR(birthday, 1, 7) = '1970-10'
```

**Predicted SQL:**

```sql
SELECT T1.player_name FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE strftime('%Y', T1.birthday) = '1970' AND strftime('%m', T1.birthday) = '10'
```

### Q1057 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through a nonexistent Team.league_id column to reach League/Country, when Match already links directly to Country via its own country_id -- Team has no league_id at all.

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.home_team_goal) AS REAL) / COUNT(t2.id) FROM Country AS t1 INNER JOIN Match AS t2 ON t1.id = t2.country_id WHERE t1.name = 'Poland' AND t2.season = '2010/2011'
```

**Predicted SQL:**

```sql
SELECT AVG(home_team_goals) AS average_home_goals
FROM Match
JOIN Team ON Match.home_team_api_id = Team.team_api_id
JOIN League ON Team.league_id = League.id
JOIN Country ON League.country_id = Country.id
WHERE Season = '2010/2011' AND Country.name = 'Poland';
```

### Q1058 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.player_name where T1 is the Player_Attributes alias; player_name only exists on Player (T2), which is already joined -- an alias mix-up, on top of replacing gold's tallest/shortest UNION comparison with an unrelated overall_rating BETWEEN MAX/MIN range.

**Gold SQL:**

```sql
SELECT A FROM (SELECT AVG(finishing) result, 'highest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MAX(height) FROM Player) UNION SELECT AVG(finishing) result, 'shortest' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = (SELECT MIN(height) FROM Player)) tmp ORDER BY result DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CASE WHEN T1.player_name = (SELECT T2.player_name FROM Player AS T2 ORDER BY T2.height ASC LIMIT 1) THEN 'shortest' ELSE 'highest' END AS result
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T1.overall_rating BETWEEN (SELECT MAX(overall_rating) FROM Player_Attributes) AND (SELECT MIN(overall_rating) FROM Player_Attributes)
GROUP BY T1.player_name
ORDER BY AVG(T1.finishing) DESC
LIMIT 1;
```

### Q1076 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T2.ball_control where T2 is the Player alias; ball_control only exists on Player_Attributes (T1), which is already joined -- an alias mix-up.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Abdou Diallo' THEN t2.id ELSE NULL END) - CAST(SUM(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.ball_control ELSE 0 END) AS REAL) / COUNT(CASE WHEN t1.player_name = 'Aaron Appindangoye' THEN t2.id ELSE NULL END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
```

**Predicted SQL:**

```sql
SELECT AVG(T1.ball_control) - AVG(T2.ball_control) AS ball_control_difference
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T2.player_name IN ('Abdou Diallo', 'Aaron Appindangoye');
```

### Q1078 (simple, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** ORDER BY birthday DESC instead of gold's ASC, returning the younger of the two named players instead of the older one.

**Gold SQL:**

```sql
SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.player_name FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.player_name = 'Aaron Lennon' OR T1.player_name = 'Abdelaziz Barrada' ORDER BY T1.birthday DESC LIMIT 1;
```

### Q1080 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Adds a spurious join from Player_Attributes to Team_Attributes via a nonexistent team_fifa_api_id column on Player_Attributes, and replaces the attacking_work_rate = 'low' condition with an unrelated buildup_play_dribbling_class = 'High' condition on the wrongly-joined table.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes WHERE preferred_foot = 'left' AND attacking_work_rate = 'low'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.player_api_id) 
FROM Player_Attributes AS T1 
JOIN Team_Attributes AS T2 ON T1.team_fifa_api_id = T2.team_fifa_api_id 
WHERE T1.preferred_foot = 'Left' AND T2.buildup_play_dribbling_class = 'High'
```

### Q1084 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted attacking_work_rate = 'High' condition not present in gold, alongside the intended defensive_work_rate = 'High'; also misses DISTINCT.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.player_api_id) 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.birthday < '1986-01-01' 
AND T1.attacking_work_rate = 'High' 
AND T1.defensive_work_rate = 'High';
```

### Q1088 (moderate, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.volley (singular); the real column, and its S3 name, is 'volleys' (plural) -- a hallucinated near-miss spelling.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.volleys > 70 AND t2.dribbling > 70
```

**Predicted SQL:**

```sql
SELECT T2.player_name FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.volley > 70 AND T1.dribbling > 70;
```

### Q1092 (simple, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` -- **Reason:** Collapses gold's tie-preserving GROUP BY ... HAVING match_count = (SELECT MAX(match_count)...) subquery into a plain ORDER BY ... LIMIT 1.

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
LIMIT 1;
```

### Q1094 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Self-joins Player_Attributes to Player_Attributes instead of joining Player, which is where player_name actually lives; also drops gold's CTE-based 'most recent rating per player' (ORDER BY date DESC LIMIT 1) selection logic entirely.

**Gold SQL:**

```sql
with ab as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where t1.player_name = 'Ariel Borysiuk'  order by date desc limit 1),
pp as (select t2.overall_rating  as rating from  Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id where  t1.player_name = 'Paulin Puel' order by date desc limit 1)
select (t3.rating - t4.rating) * 100.0 / t4.rating from ab t3 cross  join pp t4
```

**Predicted SQL:**

```sql
SELECT 
    (T1.overall_rating - T2.overall_rating) * 100 / T2.overall_rating AS percentage_difference
FROM 
    Player_Attributes AS T1
JOIN 
    Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id
WHERE 
    T1.player_name = 'Ariel Borysiuk' AND T2.player_name = 'Paulin Puel';
```

### Q1102 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** ORDER BY birthday DESC instead of gold's ASC, returning the youngest matching player instead of the oldest.

**Gold SQL:**

```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-06-23' AND t2.overall_rating = 77 ORDER BY t1.birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.player_name FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.overall_rating = 77 AND T1.date = '2016-06-23' ORDER BY T2.birthday DESC LIMIT 1;
```

### Q1103 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the SUBSTR(date,1,10) transformation, comparing the raw date/timestamp column directly against a date-only literal instead of just its date portion.

**Gold SQL:**

```sql
SELECT t2.overall_rating FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE SUBSTR(t2."date", 1, 10) = '2016-02-04' AND t1.player_name = 'Aaron Mooy'
```

**Predicted SQL:**

```sql
SELECT T1.overall_rating FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Aaron Mooy' AND T1.date = '2016-02-04';
```

### Q1105 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the LIKE '2015-05-01%' pattern match for an exact date = '2015-05-01' equality, which can miss rows whose date column carries a time component.

**Gold SQL:**

```sql
SELECT t2.attacking_work_rate FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2."date" LIKE '2015-05-01%' AND t1.player_name = 'Francesco Migliore'
```

**Predicted SQL:**

```sql
SELECT T1.attacking_work_rate FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Francesco Migliore' AND T1.date = '2015-05-01';
```

### Q1107 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Drops the secondary ORDER BY date ASC tie-break key, keeping only crossing DESC -- can select a different row than gold's LIMIT 1 when multiple rows share the maximum crossing value.

**Gold SQL:**

```sql
SELECT t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC, t2.`date` ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.date FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.player_name = 'Kevin Constant' ORDER BY T1.crossing DESC LIMIT 1;
```

### Q1110 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Selects T3.buildup_play_passing_class, but alias T3 was never introduced in the FROM/JOIN clauses at all (the query uses T1/T2/T4/T5).

**Gold SQL:**

```sql
SELECT t2.buildUpPlayPassingClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'FC Lorient' AND t2."date" LIKE '2010-02-22%'
```

**Predicted SQL:**

```sql
SELECT T3.buildup_play_passing_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id 
JOIN League AS T4 ON T1.league_id = T4.id 
JOIN Country AS T5 ON T4.country_id = T5.id 
WHERE T1.team_long_name = 'FC Lorient' AND T2.date = '2010-02-22'
```

### Q1113 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the LIKE '2015-09-10%' pattern match for an exact date equality, which can miss rows whose date column carries a time component.

**Gold SQL:**

```sql
SELECT t2.defenceAggressionClass FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t1.team_long_name = 'Hannover 96' AND t2."date" LIKE '2015-09-10%'
```

**Predicted SQL:**

```sql
SELECT T2.defence_aggression_class 
FROM Team AS T1 
JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id 
WHERE T1.team_long_name = 'Hannover 96' AND T2.date = '2015-09-10';
```

### Q1114 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the SUBSTR(date,1,10) transformation before the BETWEEN comparison, comparing the raw date/timestamp column directly against date-only bounds.

**Gold SQL:**

```sql
SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Marko Arnautovic' AND SUBSTR(t2."date", 1, 10) BETWEEN '2007-02-22' AND '2016-04-21'
```

**Predicted SQL:**

```sql
SELECT AVG(T1.overall_rating) 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T2.player_name = 'Marko Arnautovic' AND T1.date BETWEEN '2007-02-22' AND '2016-04-21';
```

### Q1115 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.player_name where T1 is the Player_Attributes alias; player_name only exists on Player (T2), which is already joined -- an alias mix-up, on top of replacing gold's relative percentage-difference formula with two independent per-player percentages.

**Gold SQL:**

```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / 
SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END) LvsJ_percent 
FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.date, 1, 10) = '2013-07-12'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.player_name = 'Landon Donovan' THEN T1.overall_rating ELSE 0 END) AS REAL) * 100 / COUNT(T1.player_name) AS ldonovan_percentage,
       CAST(SUM(CASE WHEN T1.player_name = 'Jordan Bowery' THEN T1.overall_rating ELSE 0 END) AS REAL) * 100 / COUNT(T1.player_name) AS jbowery_percentage
FROM Player_Attributes AS T1
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T1.date = '2013-07-12'
```

### Q1116 (simple, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's DENSE_RANK() OVER (ORDER BY height DESC) window function, which returns all tallest players tied at rank 1, in favor of a plain ORDER BY height DESC LIMIT 10.

**Gold SQL:**

```sql
SELECT player_name FROM (SELECT player_name, height, DENSE_RANK() OVER (ORDER BY height DESC) as rank FROM Player) WHERE rank = 1
```

**Predicted SQL:**

```sql
SELECT T2.player_name FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id ORDER BY T2.height DESC LIMIT 10;
```

### Q1124 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins Player to Team_Attributes via a nonexistent home_player_1_api_id column on Team_Attributes (that column actually lives on Match) -- an invented relationship between two unrelated tables, replacing the intended attacking_work_rate = 'high' filter on Player_Attributes.

**Gold SQL:**

```sql
SELECT DISTINCT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t2.attacking_work_rate = 'high'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.player_name
FROM Player AS T1
JOIN Team_Attributes AS T2 ON T1.player_api_id = T2.home_player_1_api_id
WHERE T2.buildup_play_dribbling_class = 'High' OR T2.buildup_play_passing_class = 'High' OR T2.buildup_play_positioning_class = 'High';
```

### Q1130 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Missing DISTINCT, so a team with multiple Team_Attributes history rows matching chance_creation_passing_class = 'Safe' can appear as duplicate output rows.

**Gold SQL:**

```sql
SELECT DISTINCT t1.team_short_name FROM Team AS t1 INNER JOIN Team_Attributes AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.chanceCreationPassingClass = 'Safe'
```

**Predicted SQL:**

```sql
SELECT T2.team_short_name FROM Team_Attributes AS T1 INNER JOIN Team AS T2 ON T1.team_api_id = T2.team_api_id WHERE T1.chance_creation_passing_class = 'Safe';
```

### Q1133 (simple, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unnecessary join to Player_Attributes that gold doesn't need, which can inflate the count when a player has multiple attribute-history rows.

**Gold SQL:**

```sql
SELECT COUNT(id) FROM Player WHERE STRFTIME('%Y', birthday) > '1990' AND player_name LIKE 'Aaron%'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.player_api_id) FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.birthday > '1990-01-01' AND T1.player_name LIKE 'Aaron%'
```

### Q1134 (simple, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Self-joins Player_Attributes to itself ON player_api_id (always the same player), then filters by date/attacking_work_rate, instead of gold's approach of filtering two specific Player_Attributes rows directly by their own id values (6 and 23) with no join at all.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1
```

**Predicted SQL:**

```sql
SELECT T1.jumping - T2.jumping AS jumping_difference
FROM Player_Attributes AS T1
JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id
WHERE T1.date = '2013-04-01' AND T2.date = '2013-04-01'
AND T1.attacking_work_rate = 'High' AND T2.attacking_work_rate = 'High';
```

### Q1135 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Returns player_api_id instead of id (Player_Attributes' own primary key, which is what gold selects); also wraps the ORDER BY ... LIMIT 4 selection in an unneeded IN-subquery that can return more than 4 rows when there are ties in potential.

**Gold SQL:**

```sql
SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT player_api_id FROM Player_Attributes WHERE preferred_foot = 'right' AND potential IN (
    SELECT potential FROM Player_Attributes ORDER BY potential ASC LIMIT 4
)
ORDER BY potential ASC;
```

### Q1136 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted attacking_work_rate = 'High' condition not present in gold, and narrows the MAX(crossing) subquery to left-footed players only instead of gold's global maximum.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT t1.player_api_id) FROM Player_Attributes AS t1 WHERE t1.preferred_foot = 'left' AND t1.crossing = ( SELECT MAX(crossing) FROM Player_Attributes)
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.player_api_id) 
FROM Player_Attributes AS T1 
JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id 
WHERE T1.crossing = (SELECT MAX(crossing) FROM Player_Attributes WHERE preferred_foot = 'Left') 
  AND T1.preferred_foot = 'Left' 
  AND T1.attacking_work_rate = 'High';
```

### Q1139 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Misspells the league name as 'Belgian Jupiler League' instead of the real 'Belgium Jupiler League', and separately drops the LIKE '2008-09-24%' date-pattern match for an exact-date equality.

**Gold SQL:**

```sql
SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2."date" LIKE '2008-09-24%'
```

**Predicted SQL:**

```sql
SELECT home_team_goals, away_team_goals
FROM Match
WHERE date = '2008-09-24' AND league_id = (SELECT id FROM League WHERE name = 'Belgian Jupiler League');
```

### Q1141 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through a nonexistent Team.league_id column to add an unneeded League join, when Team_Attributes already reaches buildUpPlaySpeedClass directly via the existing Team_Attributes+Team join.

**Gold SQL:**

```sql
SELECT DISTINCT t1.buildUpPlaySpeedClass FROM Team_Attributes AS t1 INNER JOIN Team AS t2 ON t1.team_api_id = t2.team_api_id WHERE t2.team_long_name = 'KSV Cercle Brugge'
```

**Predicted SQL:**

```sql
SELECT T3.buildup_play_speed_class FROM Team AS T1 INNER JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id INNER JOIN League AS T3 ON T1.league_id = T3.id WHERE T1.team_long_name = 'KSV Cercle Brugge'
```

### Q1145 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** season = '2015-2016' (hyphen) instead of the real format '2015/2016' (slash), which matches zero rows.

**Gold SQL:**

```sql
SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4
```

**Predicted SQL:**

```sql
SELECT L.name, COUNT(M.id) AS game_count
FROM League L
JOIN Match M ON L.id = M.league_id
WHERE M.season = '2015-2016'
GROUP BY L.id
ORDER BY game_count DESC
LIMIT 4;
```

### Q1148 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.strength where T1 is the Player alias; strength only exists on Player_Attributes (T2), which is already joined -- and it's also the wrong attribute entirely (should be overall_rating, not strength); the population filter (height<180) and CASE condition (overall_rating>70) are also swapped relative to gold.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN t2.overall_rating > 70 AND t1.height < 180 THEN t1.id END) AS REAL) * 100 / COUNT(DISTINCT t1.id) percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height < 180
```

**Predicted SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T1.height < 180 AND T1.strength > 70 THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.overall_rating > 70
```

---

## financial (28 failures)

### Q89 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Filters trans.transaction_operation = 'Issuance after transaction' (an invented English gloss on an unrelated table) instead of gold's account.frequency = 'POPLATEK PO OBRATU'; also uses 'East Bohemia' instead of the real lowercase 'east Bohemia'.

**Gold SQL:**

```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.account_id) 
FROM account AS T1 
JOIN district AS T2 ON T1.district_id = T2.district_id 
JOIN trans AS T3 ON T1.account_id = T3.account_id 
WHERE T2.region = 'East Bohemia' AND T3.transaction_operation = 'Issuance after transaction';
```

### Q93 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References client_id via an unnecessarily-added account alias (T3); client_id only exists on client (T2), which is already joined -- an alias mix-up. Also uses 'North Bohemia' instead of the real lowercase 'north Bohemia'.

**Gold SQL:**

```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'M' AND T2.A3 = 'north Bohemia' AND T2.A11 > 8000
```

**Predicted SQL:**

```sql
SELECT COUNT(T3.client_id) 
FROM district AS T1 
JOIN client AS T2 ON T1.district_id = T2.district_id 
JOIN account AS T3 ON T2.client_id = T3.client_id 
WHERE T1.region = 'North Bohemia' AND T2.gender = 'M' AND T1.average_salary > 8000;
```

### Q94 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins account directly to client via a nonexistent account.client_id column; account and client are only related through the disp bridge table, which is dropped entirely.

**Gold SQL:**

```sql
SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T4.client_id = ( SELECT client_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    T1.account_id AS oldest_female_client_account,
    MAX(T3.average_salary) - MIN(T3.average_salary) AS salary_gap
FROM 
    client AS T1
JOIN 
    account AS T2 ON T1.client_id = T2.client_id
JOIN 
    district AS T3 ON T1.district_id = T3.district_id
WHERE 
    T1.gender = 'F'
ORDER BY 
    T1.birth_date ASC
LIMIT 1;
```

### Q95 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins account directly to client via a nonexistent account.client_id column; account and client are only related through the disp bridge table, which is dropped entirely.

**Gold SQL:**

```sql
SELECT T1.account_id  FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id
```

**Predicted SQL:**

```sql
SELECT account.account_id
FROM account
JOIN client ON account.client_id = client.client_id
JOIN district ON client.district_id = district.district_id
ORDER BY client.birth_date ASC, district.average_salary DESC
LIMIT 1;
```

### Q98 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the account.frequency = 'POPLATEK TYDNE' condition entirely, keeping only the loan-date year filter.

**Gold SQL:**

```sql
SELECT T2.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1997' AND T2.frequency = 'POPLATEK TYDNE' ORDER BY T1.amount LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.account_id
FROM account AS T1
JOIN loan AS T2 ON T1.account_id = T2.account_id
WHERE strftime('%Y', T2.date) = '1997'
ORDER BY T2.amount ASC
LIMIT 1;
```

### Q99 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted status = 'approved' condition not present in gold, using an invented value that doesn't match the real single-letter status codes ('A'/'B'/'C'/'D').

**Gold SQL:**

```sql
SELECT T1.account_id FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T2.date) = '1993' AND T1.duration > 12 ORDER BY T1.amount DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT DISTINCT t1.account_id
FROM account AS t1
JOIN loan AS t2 ON t1.account_id = t2.account_id
WHERE t2.status = 'approved' AND t2.duration_months > 12 AND strftime('%Y', t1.date) = '1993'
ORDER BY t2.amount DESC
LIMIT 1;
```

### Q100 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Adds a spurious join to account via a nonexistent account.client_id column; gold needs no account join at all, just client joined directly to district.

**Gold SQL:**

```sql
SELECT COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T2.gender = 'F' AND STRFTIME('%Y', T2.birth_date) < '1950' AND T1.A2 = 'Sokolov'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.client_id) 
FROM client AS T1 
JOIN account AS T2 ON T1.client_id = T2.client_id 
JOIN district AS T3 ON T2.district_id = T3.district_id 
WHERE T1.gender = 'F' 
  AND T1.birth_date < '1950-01-01' 
  AND T3.district_name = 'Sokolov';
```

### Q112 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins client directly to account via a nonexistent account.client_id column; client and account are only related through the disp bridge table, which is dropped entirely.

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
SELECT T3.district_name FROM client AS T1 INNER JOIN account AS T2 ON T1.client_id = T2.client_id INNER JOIN district AS T3 ON T2.district_id = T3.district_id WHERE T1.gender = 'F' AND T1.birth_date = '1976-01-29'
```

### Q115 (challenging, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's GROUP BY T2.A4 (number_municipalities_below_499) entirely, and orders by number_inhabitants DESC instead of CAST(A4 AS INTEGER) DESC -- an unrelated column driving the top-1 selection.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY CAST(T2.A4 AS INTEGER) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T3.client_id) AS percentage_male_clients
FROM district AS T1
JOIN client AS T3 ON T1.district_id = T3.district_id
WHERE T1.region = 'South Bohemia'
ORDER BY T1.number_inhabitants DESC
LIMIT 1;
```

### Q116 (challenging, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References balance_before_transaction, which isn't a real column anywhere (trans has only a single 'balance' column, no before/after variants); also adds a fabricated status = 'approved' condition.

**Gold SQL:**

```sql
SELECT CAST((SUM(IIF(T3.date = '1998-12-27', T3.balance, 0)) - SUM(IIF(T3.date = '1993-03-22', T3.balance, 0))) AS REAL) * 100 / SUM(IIF(T3.date = '1993-03-22', T3.balance, 0)) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN trans AS T3 ON T3.account_id = T2.account_id WHERE T1.date = '1993-07-05'
```

**Predicted SQL:**

```sql
SELECT 
    (balance_after_transaction - balance_before_transaction) * 100 / balance_before_transaction AS increase_rate
FROM 
    trans
WHERE 
    account_id = (
        SELECT 
            account_id
        FROM 
            loan
        WHERE 
            status = 'approved'
            AND date = '1993-07-05'
        ORDER BY 
            date ASC
        LIMIT 1
    )
    AND date BETWEEN '1993-03-22' AND '1998-12-27';
```

### Q117 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses status = 'Fully Paid' instead of the real single-letter code 'A'.

**Gold SQL:**

```sql
SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN t.status = 'Fully Paid' THEN t.amount ELSE 0 END) AS REAL) * 100 / SUM(t.amount) FROM loan t
```

### Q118 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T3.status where T3 is the disp alias; status only exists on loan (T2), which is already joined -- an alias mix-up (disp has no status column at all); also uses the invented value 'Running' instead of the real code 'C'.

**Gold SQL:**

```sql
SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.status = 'Running' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id WHERE T2.amount < 100000
```

### Q125 (challenging, retrieval) -- **JOIN errors** (Wrong column)

**Outcome:** `error` -- **Reason:** Joins district directly to loan via ON d.district_id = l.account_id -- comparing a district id to an account id, a domain mismatch that isn't a real relationship; also references l.client_id, which doesn't exist on loan at all (the real path to a client goes through account+disp).

**Gold SQL:**

```sql
SELECT (d.A13 - d.A12) / d.A12 * 100 FROM loan AS l JOIN account AS a ON l.account_id = a.account_id JOIN district AS d ON a.district_id = d.district_id WHERE l.status = 'D' AND NOT d.A12 IS NULL AND NOT d.A13 IS NULL AND d.A12 > 0
```

**Predicted SQL:**

```sql
SELECT 
    d.district_name,
    (d.unemployment_rate_1996 - d.unemployment_rate_1995) AS unemployment_rate_increment
FROM 
    district d
JOIN 
    loan l ON d.district_id = l.account_id
WHERE 
    l.status = 'running'
    AND l.client_id IN (
        SELECT 
            c.client_id
        FROM 
            client c
        JOIN 
            disp dis ON c.client_id = dis.client_id
        WHERE 
            dis.type = 'debt'
    )
GROUP BY 
    d.district_name;
```

### Q128 (moderate, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Adds an extra COUNT(client_id) column to the SELECT list beyond gold's single district-name column.

**Gold SQL:**

```sql
SELECT T2.A2 FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' GROUP BY T2.district_id, T2.A2 ORDER BY COUNT(T1.client_id) DESC LIMIT 9
```

**Predicted SQL:**

```sql
SELECT d.district_name, COUNT(c.client_id) AS female_client_count
FROM client c
JOIN district d ON c.district_id = d.district_id
WHERE c.gender = 'F'
GROUP BY d.district_id
ORDER BY female_client_count DESC
LIMIT 9;
```

### Q129 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** Adds a fabricated T2.type != 'credit card' condition not present in gold; account has no type column at all (type is only real on trans, card, and disp), and 'credit card' doesn't match any of those columns' real domains either.

**Gold SQL:**

```sql
SELECT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY T3.amount DESC LIMIT 10
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.district_name
FROM trans AS T1
JOIN account AS T2 ON T1.account_id = T2.account_id
JOIN district AS T3 ON T2.district_id = T3.district_id
WHERE T1.date LIKE '1996-01-%' AND T1.type = 'withdrawal' AND T2.type != 'credit card'
ORDER BY T1.amount DESC
LIMIT 10;
```

### Q136 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Uses statement_frequency = 'monthly' instead of the real code 'POPLATEK MESICNE', and adds a fabricated status = 'approved' condition not present in gold, using an invented value that doesn't match the real single-letter status codes.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.date BETWEEN '1995-01-01' AND '1997-12-31' AND T1.frequency = 'POPLATEK MESICNE' AND T2.amount >= 250000
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.account_id) 
FROM loan AS T1 
JOIN account AS T2 ON T1.account_id = T2.account_id 
WHERE T1.amount >= 250000 
AND T2.statement_frequency = 'monthly' 
AND T1.status = 'approved' 
AND T1.date BETWEEN '1995-01-01' AND '1997-12-31';
```

### Q137 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Ambiguous column name: account_id -- both joined account and loan tables have this column and the unqualified COUNT(DISTINCT account_id) reference doesn't disambiguate; also uses the invented status value 'running' instead of the real codes 'C'/'D'.

**Gold SQL:**

```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN loan AS T3 ON T1.account_id = T3.account_id WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT account_id) 
FROM account 
JOIN loan ON account.account_id = loan.account_id 
WHERE district_id = 1 AND status = 'running';
```

### Q145 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Adds a spurious, invalid join from trans to card via a nonexistent card.account_id column; card only relates to account through the disp bridge table, and gold needs no card join at all.

**Gold SQL:**

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE STRFTIME('%Y', T1.date) = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE STRFTIME('%Y', date) = '1998')
```

**Predicted SQL:**

```sql
SELECT DISTINCT t1.account_id FROM trans AS t1 INNER JOIN card AS t2 ON t1.account_id = t2.account_id WHERE t1.date LIKE '1998%' AND t1.amount < (SELECT AVG(amount) FROM trans WHERE date LIKE '1998%')
```

### Q149 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Uses card.type instead of gold's disp.type -- two distinct real columns holding different domains ('gold'/'classic'/'junior' vs 'OWNER'/'DISPONENT') -- and joins card directly to account via a nonexistent card.card_id-on-account relationship (card only relates to account through disp).

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
SELECT DISTINCT t1.type FROM card AS t1 INNER JOIN account AS t2 ON t1.card_id = t2.card_id INNER JOIN district AS t3 ON t2.district_id = t3.district_id WHERE t1.type NOT IN ('credit', 'debit') AND t3.average_salary BETWEEN 8000 AND 9000;
```

### Q152 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters/averages district.number_inhabitants instead of gold's number_crimes_1995 (A15) -- two distinct real columns; also converts gold's DISTINCT-district-membership subquery into a direct join to account, which can multiply-count districts having several qualifying accounts.

**Gold SQL:**

```sql
SELECT AVG(T1.A15) FROM district AS T1 WHERE T1.district_id IN (SELECT DISTINCT T2.district_id FROM account T2 WHERE STRFTIME('%Y', T2.date) >= '1997') AND T1.A15 > 4000
```

**Predicted SQL:**

```sql
SELECT AVG(d.number_crimes_1995) 
FROM district d 
JOIN account a ON d.district_id = a.district_id 
WHERE d.number_inhabitants > 4000 
AND a.date >= '1997-01-01';
```

### Q159 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins trans/account directly to client via a nonexistent account.client_id column; account and client are only related through the disp bridge table, which is dropped entirely. Also uses operation = 'withdrawal' instead of the real code 'VYBER', and adds a fabricated type = 'cash' condition (trans.type only holds 'PRIJEM'/'VYDAJ'/'VYBER').

**Gold SQL:**

```sql
SELECT T4.* FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'
```

**Predicted SQL:**

```sql
SELECT t.transaction_id, t.date, t.type, t.transaction_operation, t.amount, t.balance_after_transaction, t.transaction_type_code, t.bank, t.account
FROM trans t
JOIN account a ON t.account_id = a.account_id
JOIN client c ON a.client_id = c.client_id
WHERE t.transaction_operation = 'withdrawal' AND t.type = 'cash' AND c.client_id = 3356;
```

### Q168 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T3.gender where T3 is an unnecessarily-added account alias; gender only exists on client (T2), which is already joined -- account has no gender column at all.

**Gold SQL:**

```sql
SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T3.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.client_id = T3.client_id WHERE T1.average_salary > 10000
```

### Q169 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins account directly to client via a nonexistent account.client_id column; account and client are only related through the disp bridge table, which is dropped entirely, along with the disp.type = 'OWNER' filter; the query also restructures the comparison from year-over-year (1997 vs 1996) to gender-over-gender (M vs F), a fundamentally different computation.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT 
    (SUM(CASE WHEN T3.gender = 'M' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN T3.gender = 'F' THEN T1.amount ELSE 0 END)) / SUM(CASE WHEN T3.gender = 'M' THEN T1.amount ELSE 0 END) * 100 AS growth_rate
FROM 
    loan AS T1
JOIN 
    account AS T2 ON T1.account_id = T2.account_id
JOIN 
    client AS T3 ON T2.client_id = T3.client_id
WHERE 
    T1.date BETWEEN '1996-01-01' AND '1997-12-31';
```

### Q173 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Uses the trans table instead of gold's "order" table (a standing-order table) for the k_symbol/total-amount computation -- a fundamentally different, unrelated table -- and uses invented values ('debit', 'withdrawal') that don't match trans's real domains.

**Gold SQL:**

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

**Predicted SQL:**

```sql
SELECT COUNT(*) AS statement_frequency, SUM(amount) AS total_debit
FROM account
JOIN trans ON account.account_id = trans.account_id
WHERE account_id = 3 AND type = 'debit' AND transaction_operation = 'withdrawal';
```

### Q186 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses statement_frequency = 'WEEKLY' instead of the real code 'POPLATEK TYDNE'; also counts account_id instead of gold's client_id in the denominator.

**Gold SQL:**

```sql
SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id WHERE T3.frequency = 'POPLATEK TYDNE'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.account_id) FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id WHERE T1.statement_frequency = 'WEEKLY'
```

### Q189 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins account directly to client via a nonexistent account.client_id column; account and client are only related through the disp bridge table, which is dropped entirely.

**Gold SQL:**

```sql
SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id  WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT account.account_id
FROM account
JOIN client ON account.client_id = client.client_id
WHERE client.gender = 'F'
ORDER BY client.birth_date ASC, district.district_id ASC, district.average_salary ASC
LIMIT 1;
```

### Q192 (moderate, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted GROUP BY account.date not present in gold, turning a single overall average into a per-date breakdown; also uses invented values 'running'/'monthly' instead of the real status codes ('C'/'D') and frequency code ('POPLATEK PO OBRATU').

**Gold SQL:**

```sql
SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'
```

**Predicted SQL:**

```sql
SELECT AVG(loan.amount) 
FROM loan 
JOIN account ON loan.account_id = account.account_id 
WHERE loan.status = 'running' AND account.statement_frequency = 'monthly' 
GROUP BY account.date;
```

### Q194 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Calls TIMESTAMPDIFF(YEAR, ...), a non-SQLite function; also uses card.type = 'High Level Credit Card' instead of the real lowercase 'gold', and compares loan.account_id to client.client_id in a nonsensical EXISTS subquery -- a domain mismatch.

**Gold SQL:**

```sql
SELECT T1.client_id, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T3.birth_date) FROM disp AS T1 INNER JOIN card AS T2 ON T2.disp_id = T1.disp_id INNER JOIN client AS T3 ON T1.client_id = T3.client_id WHERE T2.type = 'gold' AND T1.type = 'OWNER'
```

**Predicted SQL:**

```sql
SELECT c.client_id, TIMESTAMPDIFF(YEAR, c.birth_date, CURDATE()) AS age
FROM client c
JOIN card ON c.client_id = card.client_id
WHERE card.type = 'High Level Credit Card'
  AND EXISTS (
    SELECT 1
    FROM loan l
    WHERE l.account_id = c.client_id
      AND l.status = 'Approved'
  );
```

---

## formula_1 (59 failures)

### Q846 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Uses races+results instead of qualifying+drivers, so driver_ref_name is unreachable; also filters by round instead of raceId, and replaces the ORDER BY q1 DESC LIMIT 5 with an unrelated status_id = 1 filter.

**Gold SQL:**

```sql
SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
```

**Predicted SQL:**

```sql
SELECT T2.driver_ref_name FROM races AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id WHERE T1.round = 20 AND T2.status_id = 1;
```

### Q847 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** Adds an unneeded extra join to results and selects T3.last_name from it; surname/last_name only exists on drivers (T2), which is already correctly joined.

**Gold SQL:**

```sql
SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 ORDER BY T1.q2 ASC NULLS LAST LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.last_name FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id INNER JOIN results AS T3 ON T1.driver_id = T3.driver_id WHERE T1.race_id = 19 AND T1.qualifying_2_time IS NOT NULL ORDER BY T1.qualifying_2_time ASC LIMIT 1;
```

### Q850 (simple, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Missing DISTINCT; otherwise structurally identical to gold.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.country = 'Germany'
```

**Predicted SQL:**

```sql
SELECT T2.name FROM circuits AS T1 INNER JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T1.country = 'Germany';
```

### Q854 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Selects circuits.location instead of circuits.lat/lng -- both real columns, wrong ones chosen.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Australian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.name = 'Australian Grand Prix';
```

### Q857 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Drops the join to races entirely and filters circuits.circuit_ref_name = 'Abu Dhabi Grand Prix' instead; circuitRef holds an unrelated short code, not the Grand Prix event name, which only exists on races.name.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Abu Dhabi Grand Prix'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE circuit_ref_name = 'Abu Dhabi Grand Prix';
```

### Q859 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.round (races-only column, not on qualifying) as if it were raceId = 354, and pulls T2.position from an unnecessarily-added results join instead of qualifying's own q1 column.

**Gold SQL:**

```sql
SELECT T1.q1 FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 354 AND T2.forename = 'Bruno' AND T2.surname = 'Senna'
```

**Predicted SQL:**

```sql
SELECT T2.position FROM qualifying AS T1 INNER JOIN results AS T2 ON T1.qualify_id = T2.qualify_id WHERE T1.driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Bruno' AND last_name = 'Senna') AND T1.round = 354 AND T1.position = 1;
```

### Q861 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.time, which doesn't exist on qualifying (only q1/q2/q3 do); also replaces the q3 LIKE '1:54%' condition with an unrelated position = 3 filter.

**Gold SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
```

**Predicted SQL:**

```sql
SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id = 903 AND T1.position = 3 AND T1.time = '0:01:54';
```

### Q862 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters results.position IS NULL instead of results.time IS NULL -- both real columns on results with different meanings (DNF-with-no-time vs unclassified position).

**Gold SQL:**

```sql
SELECT COUNT(T3.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T1.year = 2007 AND T1.name = 'Bahrain Grand Prix' AND T2.time IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT driver_id) FROM results WHERE race_id IN (SELECT race_id FROM races WHERE circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Bahrain Grand Prix') AND year = 2007) AND position IS NULL;
```

### Q865 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the drivers table entirely (joins races+results only), so forename/surname/dob are unreachable; also filters by round instead of raceId.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 592 AND T2.time IS NOT NULL AND T1.dob IS NOT NULL ORDER BY T1.dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.first_name, T2.last_name
FROM races AS T1
JOIN results AS T2 ON T1.race_id = T2.race_id
WHERE T1.round = 592
ORDER BY T2.date_of_birth DESC
LIMIT 1;
```

### Q866 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Uses results.time instead of lapTimes.time to match the '1:27%' pattern -- these hold different concepts (overall finish time vs a specific lap time); also filters by round instead of raceId and uses an exact match instead of gold's LIKE pattern.

**Gold SQL:**

```sql
SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'
```

**Predicted SQL:**

```sql
SELECT T3.first_name, T3.last_name, T3.url FROM races AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id INNER JOIN drivers AS T3 ON T2.driver_id = T3.driver_id WHERE T1.round = 161 AND T2.time = '0:01:27';
```

### Q868 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Selects circuits.location instead of circuits.lat/lng.

**Gold SQL:**

```sql
SELECT DISTINCT T1.lat, T1.lng FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.name = 'Malaysian Grand Prix';
```

### Q869 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Routes through an added races join and filters races.round = 9 instead of directly filtering constructorResults.raceId = 9.

**Gold SQL:**

```sql
SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.url FROM races AS T1 INNER JOIN constructorResults AS T3 ON T1.race_id = T3.race_id INNER JOIN constructors AS T2 ON T3.constructor_id = T2.constructor_id WHERE T1.round = 9 ORDER BY T3.points DESC LIMIT 1;
```

### Q872 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the drivers table entirely (joins races+qualifying only), so driver_code is unreachable; also filters by round instead of raceId, and uses an exact match instead of gold's LIKE pattern for q3.

**Gold SQL:**

```sql
SELECT T2.code FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 45 AND T1.q3 LIKE '1:33%'
```

**Predicted SQL:**

```sql
SELECT T2.driver_code FROM races AS T1 INNER JOIN qualifying AS T2 ON T1.race_id = T2.race_id WHERE T1.round = 45 AND T2.qualifying_3_time = '0:01:33';
```

### Q875 (simple, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.season; no such column exists anywhere in the schema (races has 'year', not 'season', and even the seasons table's own column is named 'year').

**Gold SQL:**

```sql
SELECT T2.url FROM races AS T1 INNER JOIN seasons AS T2 ON T2.year = T1.year WHERE T1.raceId = 901
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.year FROM races AS T1 INNER JOIN seasons AS T2 ON T1.season = T2.season WHERE T1.round = 901;
```

### Q877 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the drivers table entirely (joins races+results only), so forename/surname/dob are unreachable; also filters by round instead of raceId.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.first_name, T2.last_name
FROM races AS T1
JOIN results AS T2 ON T1.race_id = T2.race_id
WHERE T1.round = 872
ORDER BY T2.date_of_birth ASC
LIMIT 1;
```

### Q879 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Selects constructors.nationality instead of drivers.nationality after adding an unneeded join to constructors -- both real 'nationality' columns but on different entities.

**Gold SQL:**

```sql
SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.nationality FROM results AS T1 INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id INNER JOIN constructors AS T3 ON T1.constructor_id = T3.constructor_id WHERE T1.fastest_lap_speed = (SELECT MAX(fastest_lap_speed) FROM results)
```

### Q880 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Self-joins qualifying to itself and references fastest_lap_speed, which only exists on results, not qualifying; also filters by qualifying.number = 853/854 instead of raceId, and drops the driver-name filter entirely.

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
    (T1.fastest_lap_speed - T2.fastest_lap_speed) * 100 / T2.fastest_lap_speed AS percentage_faster
FROM 
    qualifying AS T1
JOIN 
    qualifying AS T2 ON T1.race_id = T2.race_id AND T1.driver_id = T2.driver_id
WHERE 
    T1.number = 853 AND T2.number = 854;
```

### Q881 (moderate, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Replaces gold's completion-rate formula (% of this race's results with a non-null time) with an unrelated COUNT(DISTINCT driver_id)/COUNT(DISTINCT race_id) ratio -- a different, nonsensical aggregate/formula.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.time IS NOT NULL THEN T2.driverId END) AS REAL) * 100 / COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '1983-07-16'
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT driver_id) / COUNT(DISTINCT race_id) * 100 AS race_completion_rate
FROM results
WHERE race_id IN (
    SELECT race_id
    FROM races
    WHERE date = '1983-07-16'
);
```

### Q884 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Selects circuits.name instead of races.name, and replaces gold's correlated month/year-matching subquery against the earliest race date with an unrelated ORDER BY year, round LIMIT 1.

**Gold SQL:**

```sql
SELECT name FROM races WHERE STRFTIME('%Y', date) = ( SELECT STRFTIME('%Y', date) FROM races ORDER BY date ASC LIMIT 1 ) AND STRFTIME('%m', date) = ( SELECT STRFTIME('%m', date) FROM races ORDER BY date ASC LIMIT 1 )
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.name FROM races AS T1 INNER JOIN circuits AS T2 ON T1.circuit_id = T2.circuit_id ORDER BY T1.year ASC, T1.round ASC LIMIT 1;
```

### Q894 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** Selects T1.name where T1 is the (unnecessarily added) qualifying alias; race name only exists on races (T2), which is already joined -- an alias mix-up.

**Gold SQL:**

```sql
SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.time, T4.first_name, T4.last_name, T1.name AS race_name
FROM qualifying AS T1
JOIN races AS T2 ON T1.race_id = T2.race_id
JOIN drivers AS T4 ON T1.driver_id = T4.driver_id
JOIN lapTimes AS T3 ON T1.race_id = T3.race_id AND T1.driver_id = T3.driver_id
ORDER BY T3.time ASC
LIMIT 1;
```

### Q895 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Averages results.time (the race finish-time string) instead of lapTimes.milliseconds -- gold's 'average lap time' concept lives on lapTimes, not results.

**Gold SQL:**

```sql
SELECT AVG(T2.milliseconds) FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' AND T1.year = 2009 AND T1.name = 'Malaysian Grand Prix'
```

**Predicted SQL:**

```sql
SELECT AVG(T2.time) AS average_lap_time
FROM drivers AS T1
JOIN results AS T2 ON T1.driver_id = T2.driver_id
JOIN races AS T3 ON T2.race_id = T3.race_id
WHERE T1.first_name = 'Lewis' AND T1.last_name = 'Hamilton' AND T3.year = 2009 AND T3.circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Malaysian Grand Prix');
```

### Q896 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops driverStandings and races entirely (joins drivers+results only), so the year filter has no column to bind to -- results has no year column, only races does.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010
```

**Predicted SQL:**

```sql
SELECT 
    (COUNT(CASE WHEN T2.position = 1 THEN 1 ELSE NULL END) * 100.0 / COUNT(T2.driver_id)) AS percentage_not_at_first_track
FROM 
    drivers AS T1
JOIN 
    results AS T2 ON T1.driver_id = T2.driver_id
WHERE 
    T1.first_name = 'Lewis' AND T1.last_name = 'Hamilton'
    AND T2.year >= 2010;
```

### Q897 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the driverStandings.wins >= 1 filter entirely, and orders by MAX(points) instead of gold's COUNT(wins), changing which driver is selected.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, d.nationality, MAX(rs.points) AS max_points
FROM drivers d
JOIN driverStandings rs ON d.driver_id = rs.driver_id
GROUP BY d.driver_id
ORDER BY max_points DESC
LIMIT 1;
```

### Q898 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins drivers to constructors instead of using drivers alone; constructors has neither driver names nor the driver's own nationality (constructors.nationality is a different, unrelated real column).

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.first_name, T2.last_name, (strftime('%Y', 'now') - strftime('%Y', T2.date_of_birth)) AS age
FROM drivers AS T1
JOIN constructors AS T2 ON T1.constructor_id = T2.constructor_id
WHERE T2.nationality = 'Japan'
ORDER BY T2.date_of_birth ASC
LIMIT 1;
```

### Q901 (simple, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Calls MONTH(races.date), a non-SQLite function.

**Gold SQL:**

```sql
SELECT DISTINCT T2.name, T1.name, T1.location FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.year = 2005 AND STRFTIME('%m', T2.date) = '09'
```

**Predicted SQL:**

```sql
SELECT races.name, circuits.name AS circuit_name, circuits.location
FROM races
JOIN circuits ON races.circuit_id = circuits.circuit_id
WHERE races.year = 2005 AND MONTH(races.date) = 9;
```

### Q902 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Filters results.number < 20 (car number) instead of driverStandings.position < 20 -- a completely different real column/table substituted for the intended role.

**Gold SQL:**

```sql
SELECT T1.name FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Alex' AND T3.surname = 'Yoong' AND T2.position < 20
```

**Predicted SQL:**

```sql
SELECT r.name FROM races r
JOIN results rs ON r.race_id = rs.race_id
JOIN drivers d ON rs.driver_id = d.driver_id
WHERE d.first_name = 'Alex' AND d.last_name = 'Yoong' AND rs.number < 20;
```

### Q904 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops drivers and lapTimes entirely, replacing them with an invented lookup on driverStandings.driver_name/fastest_lap_time, neither of which exists on that table.

**Gold SQL:**

```sql
SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.name, T1.year FROM results AS T1 INNER JOIN races AS T2 ON T1.race_id = T2.race_id WHERE T1.driver_id = (SELECT driver_id FROM driverStandings WHERE driver_name = 'Michael Schumacher' ORDER BY fastest_lap_time ASC LIMIT 1)
```

### Q909 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Replaces the races.name = 'European Grand Prix' population filter with an invented circuits.country = 'Europe' condition (a continent, not a real country value in that column), which also makes the country = 'Germany' numerator condition on the same column self-contradictory.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T1.country = 'Germany' THEN T2.circuitID END) AS REAL) * 100 / COUNT(T2.circuitId) FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'European Grand Prix'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.country = 'Germany' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.race_id) FROM races AS T1 INNER JOIN circuits AS T2 ON T1.circuit_id = T2.circuit_id WHERE T2.country = 'Europe'
```

### Q910 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters circuits.circuit_ref_name = 'Silverstone' instead of circuits.name = 'Silverstone Circuit' -- circuitRef is a short slug, a different real column from the full circuit name gold uses.

**Gold SQL:**

```sql
SELECT lat, lng FROM circuits WHERE name = 'Silverstone Circuit'
```

**Predicted SQL:**

```sql
SELECT latitude, longitude FROM circuits WHERE circuit_ref_name = 'Silverstone';
```

### Q915 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Adds a spurious join from drivers to circuits via a nonexistent drivers.circuit_id column; gold needs no join at all since nationality lives directly on drivers.

**Gold SQL:**

```sql
SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.country FROM drivers AS T1 INNER JOIN circuits AS T2 ON T1.circuit_id = T2.circuit_id ORDER BY T1.date_of_birth ASC LIMIT 1;
```

### Q928 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Identifies the race via circuits.name = 'Canadian Grand Prix' instead of races.name; circuits.name holds the venue's own name (e.g. 'Circuit Gilles Villeneuve'), not the Grand Prix event name, so the subquery returns no match (verified empty result against the real database, vs. gold's non-empty result).

**Gold SQL:**

```sql
SELECT d.forename, d.surname, d.driverRef FROM drivers AS d JOIN results AS r ON d.driverId = r.driverId JOIN races AS ra ON r.raceId = ra.raceId WHERE ra.name = 'Canadian Grand Prix' AND ra.year = 2007 AND r.position = 1
```

**Predicted SQL:**

```sql
SELECT T3.first_name, T3.last_name, T3.driver_ref_name
FROM races AS T1
JOIN results AS T2 ON T1.race_id = T2.race_id
JOIN drivers AS T3 ON T2.driver_id = T3.driver_id
WHERE T1.year = 2007 AND T1.circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Canadian Grand Prix')
AND T2.position = 1;
```

### Q930 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Uses driverStandings.position < 1 (ORDER BY position ASC LIMIT 1) instead of gold's results.rank = 0 filter -- a different table/column substituted for an unrelated concept, also collapsing a potentially multi-row IN-subquery result into a single top-1 row.

**Gold SQL:**

```sql
SELECT name FROM races WHERE raceId IN ( SELECT raceId FROM results WHERE rank = 0 AND driverId = ( SELECT driverId FROM drivers WHERE forename = 'Lewis' AND surname = 'Hamilton' ) )
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.name FROM driverStandings AS T1 INNER JOIN races AS T2 ON T1.race_id = T2.race_id WHERE T1.driver_id = (SELECT driver_id FROM drivers WHERE first_name = 'Lewis' AND last_name = 'Hamilton') ORDER BY T1.position ASC LIMIT 1;
```

### Q931 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Identifies the race via circuits.name = 'Spanish Grand Prix' instead of races.name -- the same circuits/races name confusion as Q928; also drops the ORDER BY fastestLapSpeed DESC LIMIT 1 top-1 selection and the IS NOT NULL filter, returning every matching row instead of just the fastest.

**Gold SQL:**

```sql
SELECT T2.fastestLapSpeed FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.name = 'Spanish Grand Prix' AND T1.year = 2009 AND T2.fastestLapSpeed IS NOT NULL ORDER BY T2.fastestLapSpeed DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.fastest_lap_speed FROM results AS T1 INNER JOIN races AS T2 ON T1.race_id = T2.race_id WHERE T2.year = 2009 AND T2.circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Spanish Grand Prix')
```

### Q937 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters driverStandings.position = 2 instead of results.position = 2 -- wrong table for that condition -- and the race-name literal is corrupted to 'AustChineseralian Grand Prix' instead of 'Chinese Grand Prix'.

**Gold SQL:**

```sql
SELECT r.time FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year = 2008 AND ra.name = 'Chinese Grand Prix' AND r.position = 2
```

**Predicted SQL:**

```sql
SELECT T2.time FROM driverStandings AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T1.race_id IN (SELECT race_id FROM races WHERE year = 2008 AND name = 'AustChineseralian Grand Prix') AND T1.position = 2
```

### Q940 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Identifies the race via circuits.circuit_ref_name = 'Shanghai' instead of races.name = 'Chinese Grand Prix', and replaces the time IS NOT NULL finisher condition with an unrelated position = 1 (winner-only) filter.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T2.driver_id) FROM races AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id WHERE T1.year = 2008 AND T1.circuit_id IN (SELECT circuit_id FROM circuits WHERE circuit_ref_name = 'Shanghai') AND T2.position = 1;
```

### Q944 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Uses results.position instead of positionOrder to identify the champion/last-place rows, and identifies the race via circuits.circuit_ref_name = 'Melbourne' instead of races.name = 'Australian Grand Prix'; also subtracts the text time column instead of the numeric milliseconds column gold uses.

**Gold SQL:**

```sql
WITH time_in_seconds AS (SELECT T1.positionOrder, T1.milliseconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 1988), champion_time AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS (SELECT milliseconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)) SELECT CAST((SELECT milliseconds FROM last_driver_incremental) - (SELECT milliseconds FROM champion_time) AS REAL) * 100 / (SELECT milliseconds FROM last_driver_incremental)
```

**Predicted SQL:**

```sql
SELECT 
    (T1.time - T2.time) * 100 / T2.time AS percentage_faster
FROM 
    results AS T1
JOIN 
    results AS T2 ON T1.race_id = T2.race_id AND T1.position = 1
WHERE 
    T1.race_id = (SELECT race_id FROM races WHERE year = 1988 AND circuit_id = (SELECT circuit_id FROM circuits WHERE circuit_ref_name = 'Melbourne'))
ORDER BY 
    T1.position DESC
LIMIT 1;
```

### Q950 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Uses constructorResults instead of constructorStandings -- both real, similarly-named tables holding different data (per-race results vs. cumulative standings).

**Gold SQL:**

```sql
SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291
```

**Predicted SQL:**

```sql
SELECT T2.name FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructor_id = T2.constructor_id WHERE T1.race_id = 291 AND T1.points = 0;
```

### Q951 (simple, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's HAVING COUNT(raceId) = 2 condition entirely (which restricts to constructors with exactly two zero-point races), and also uses nationality = 'Japan' instead of 'Japanese' plus an unwarranted year filter not in gold.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.constructorId) 
FROM constructorResults AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T2.constructor_id) 
FROM races AS T1 
JOIN constructorResults AS T2 ON T1.race_id = T2.race_id 
WHERE T1.year IN (2005, 2006) 
  AND T2.points = 0 
  AND T2.constructor_id IN (SELECT constructor_id FROM constructors WHERE nationality = 'Japan');
```

### Q954 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the drivers table entirely (joins races+results only), so the nationality filter has no column to bind to -- results has no nationality column.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.time IS NOT NULL, 1, 0)) AS REAL) * 100 / COUNT(T1.raceId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T3.nationality = 'Japanese' AND T2.year BETWEEN 2007 AND 2009
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(CASE WHEN T2.nationality = 'Japan' THEN 1 ELSE NULL END) * 100 / COUNT(T1.race_id) AS race_completion_percentage
FROM 
    races AS T1
JOIN 
    results AS T2 ON T1.race_id = T2.race_id
WHERE 
    T1.year BETWEEN 2007 AND 2009;
```

### Q955 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Uses seasons+constructorStandings instead of races+results, joined via a nonexistent seasons.season_id column, and references constructorStandings.time, which doesn't exist on that table.

**Gold SQL:**

```sql
SELECT r.year, AVG(res.milliseconds / 1000.0) AS avg_time_seconds FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.position = 1 AND res.milliseconds IS NOT NULL GROUP BY r.year
```

**Predicted SQL:**

```sql
SELECT T1.year, AVG(T2.time) / 1000 AS average_time_seconds
FROM seasons AS T1
JOIN constructorStandings AS T2 ON T1.season_id = T2.race_id
WHERE T1.year < 1975
GROUP BY T1.year;
```

### Q959 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Uses constructorStandings instead of races, so the year filter has no column to bind to -- constructorStandings has no year column.

**Gold SQL:**

```sql
SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T2.fastest_lap_number FROM constructorStandings AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id WHERE T1.year = 2009 AND T1.position = 1 ORDER BY T2.points DESC LIMIT 1;
```

### Q962 (challenging, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `error` -- **Reason:** Joins races directly to drivers via a nonexistent races.driver_id column; the real relationship must go through results. Also changes laps > 50 to laps = 50.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, T1.driverId, NULL)) AS REAL) * 100 / COUNT(DISTINCT T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers AS T3 on T1.driverId = T3.driverId WHERE T2.year BETWEEN 2000 AND 2005
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.date_of_birth < '1985-01-01' AND T3.laps = 50 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T3.driver_id) FROM races AS T1 INNER JOIN drivers AS T2 ON T1.driver_id = T2.driver_id INNER JOIN results AS T3 ON T1.race_id = T3.race_id WHERE T1.year BETWEEN 2000 AND 2005
```

### Q963 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins circuits+races+drivers via a nonexistent races.driver_id column, inventing a direct driver-to-race relationship that doesn't exist; the real link needed is drivers+lapTimes, and circuits.country is used in place of drivers.nationality.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 1) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 3, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 6, 3) AS REAL) / 1000) < 120
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T2.driver_id) 
FROM circuits AS T1 
JOIN races AS T2 ON T1.circuit_id = T2.circuit_id 
JOIN drivers AS T3 ON T2.driver_id = T3.driver_id 
WHERE T1.country = 'France' AND T3.nationality = 'French' AND T2.time < '02:00:00';
```

### Q964 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Adds an unnecessary join to results and selects driver_code from it; gold needs no join at all since code lives directly on drivers.

**Gold SQL:**

```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.driver_code FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driver_id = T2.driver_id WHERE T1.nationality = 'American';
```

### Q967 (simple, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses nationality = 'Netherlands' instead of the real value 'Dutch'; also applies the nationality filter before the ORDER BY/LIMIT 3 instead of gold's 'find the 3 youngest overall, then check how many are Dutch' shape, and flips ORDER BY direction (ASC instead of DESC), picking the oldest drivers instead of the youngest.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'
```

**Predicted SQL:**

```sql
SELECT COUNT(driver_id) 
FROM drivers 
WHERE nationality = 'Netherlands' 
ORDER BY date_of_birth ASC 
LIMIT 3;
```

### Q971 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T2.driver_ref_name where T2 is the constructors alias; driver_ref_name only exists on drivers (T1), which is already joined -- an alias mix-up, on top of using nationality = 'Germany' instead of 'German'.

**Gold SQL:**

```sql
SELECT driverRef FROM drivers WHERE nationality = 'German' ORDER BY JULIANDAY(dob) ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.driver_ref_name FROM drivers AS T1 INNER JOIN constructorResults AS T3 ON T1.driver_id = T3.driver_id INNER JOIN constructors AS T2 ON T3.constructor_id = T2.constructor_id WHERE T1.nationality = 'Germany' ORDER BY T1.date_of_birth ASC LIMIT 1;
```

### Q972 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References driver_code on results (T2), which doesn't have it -- it only exists on drivers, which is used only inside an unrelated subquery, not joined for the SELECT; the query also layers on multiple fabricated conditions (year = 2023, an exact date, a self-referential MIN(time) subquery) not present in gold at all.

**Gold SQL:**

```sql
SELECT DISTINCT T2.driverId, T2.code 
FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId 
WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT T2.driver_id, T2.driver_code
FROM races AS T1
JOIN results AS T2 ON T1.race_id = T2.race_id
WHERE T1.year = 2023 AND T2.position = 1 AND T2.time = (SELECT MIN(time) FROM results WHERE race_id = T1.race_id AND position = 1)
AND T2.date = '2023-05-28'
AND T2.driver_id IN (SELECT driver_id FROM drivers WHERE date_of_birth LIKE '1971%')
```

### Q977 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Changes the exclusive raceId > 50 AND < 100 bounds to an inclusive BETWEEN 50 AND 100, and replaces gold's SUM(time IS NOT NULL) completion metric with an unrelated COUNT(DISTINCT driver_id).

**Gold SQL:**

```sql
SELECT SUM(IIF(time IS NOT NULL, 1, 0)) FROM results WHERE statusId = 2 AND raceID < 100 AND raceId > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT driver_id) FROM results WHERE race_id BETWEEN 50 AND 100 AND status_id = (SELECT status_id FROM status WHERE status = 'Disqualified')
```

### Q978 (simple, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Missing DISTINCT; otherwise structurally identical to gold.

**Gold SQL:**

```sql
SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
```

**Predicted SQL:**

```sql
SELECT location, latitude, longitude FROM circuits WHERE country = 'Austria';
```

### Q981 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Uses MIN(date_of_birth) instead of gold's ORDER BY dob DESC LIMIT 1 (i.e. the MAX), which picks the oldest driver instead of the youngest one gold intends.

**Gold SQL:**

```sql
SELECT T3.year, T3.name, T3.date, T3.time FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T1.raceId = T3.raceId WHERE T1.driverId = ( SELECT driverId FROM drivers ORDER BY dob DESC LIMIT 1 ) ORDER BY T3.date ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.year, T2.name, T2.date, T2.time
FROM drivers AS T1
JOIN qualifying AS T3 ON T1.driver_id = T3.driver_id
JOIN races AS T2 ON T3.race_id = T2.race_id
WHERE T1.date_of_birth = (SELECT MIN(date_of_birth) FROM drivers)
ORDER BY T2.year ASC
LIMIT 1;
```

### Q988 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Calls YEAR(date_of_birth), a non-SQLite function.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND STRFTIME('%Y', T2.dob) BETWEEN '1980' AND '1985' GROUP BY T2.forename, T2.surname ORDER BY AVG(T1.duration) LIMIT 3
```

**Predicted SQL:**

```sql
SELECT d.first_name, d.last_name, AVG(p.duration) AS avg_pit_stop_duration
FROM drivers d
JOIN pitStops p ON d.driver_id = p.driver_id
WHERE d.nationality = 'Germany' AND YEAR(d.date_of_birth) BETWEEN 1980 AND 1985
GROUP BY d.driver_id
ORDER BY avg_pit_stop_duration ASC
LIMIT 3;
```

### Q989 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Uses constructorStandings instead of races, so the year filter has no column to bind to -- constructorStandings has no year column.

**Gold SQL:**

```sql
SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T2.time FROM constructorStandings AS T1 INNER JOIN results AS T2 ON T1.race_id = T2.race_id AND T1.constructor_id = T2.constructor_id WHERE T1.year = 2008 AND T1.position = 1 AND T2.circuit_id = (SELECT circuit_id FROM races WHERE year = 2008 AND name = 'Canadian Grand Prix')
```

### Q990 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Identifies the race via circuits.name = 'Singapore Grand Prix' instead of races.name (the same circuits/races confusion as Q928), and substitutes constructorResults for results; also adds a fabricated ORDER BY points DESC LIMIT 1 not present in gold.

**Gold SQL:**

```sql
SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'
```

**Predicted SQL:**

```sql
SELECT T2.constructor_ref_name, T2.url FROM races AS T1 INNER JOIN constructorResults AS T3 ON T1.race_id = T3.race_id INNER JOIN constructors AS T2 ON T3.constructor_id = T2.constructor_id WHERE T1.year = 2009 AND T1.circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Singapore Grand Prix') ORDER BY T3.points DESC LIMIT 1;
```

### Q994 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Identifies the race via circuits.circuit_ref_name = 'Monaco Grand Prix' instead of races.name -- the recurring circuits/races name confusion.

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
    r.circuit_id IN (SELECT circuit_id FROM circuits WHERE circuit_ref_name = 'Monaco Grand Prix')
    AND r.year BETWEEN 1980 AND 2010
GROUP BY 
    c.constructor_id
ORDER BY 
    total_points DESC
LIMIT 1;
```

### Q1001 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** References circuit_id directly on qualifying (T1), which doesn't have it -- only races does; also adds fabricated round = 3 and position = 1 filters not in gold, replacing gold's ORDER BY (parsed q3 lap time) ASC LIMIT 1 selection.

**Gold SQL:**

```sql
SELECT T2.forename, T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 ON T1.raceid = T3.raceid WHERE q3 IS NOT NULL AND T3.year = 2008 AND T3.circuitId IN ( SELECT circuitId FROM circuits WHERE name = 'Marina Bay Street Circuit' ) ORDER BY CAST(SUBSTR(q3, 1, INSTR(q3, ':') - 1) AS INTEGER) * 60 + CAST(SUBSTR(q3, INSTR(q3, ':') + 1, INSTR(q3, '.') - INSTR(q3, ':') - 1) AS REAL) + CAST(SUBSTR(q3, INSTR(q3, '.') + 1) AS REAL) / 1000 ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T3.first_name, T3.last_name
FROM qualifying AS T1
JOIN races AS T2 ON T1.race_id = T2.race_id
JOIN drivers AS T3 ON T1.driver_id = T3.driver_id
WHERE T2.year = 2008 AND T2.round = 3 AND T1.circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Marina Bay Street Circuit')
AND T1.position = 1;
```

### Q1002 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops driverStandings and races entirely (joins drivers+results only), so race name is unreachable; also adds a fabricated position = 1 filter not in gold and flips ORDER BY direction (ASC instead of DESC), picking the oldest driver instead of the youngest.

**Gold SQL:**

```sql
SELECT T1.forename, T1.surname, T1.nationality, T3.name FROM drivers AS T1 INNER JOIN driverStandings AS T2 on T1.driverId = T2.driverId INNER JOIN races AS T3 on T2.raceId = T3.raceId ORDER BY JULIANDAY(T1.dob) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT 
    d.first_name, 
    d.last_name, 
    d.nationality, 
    r.name AS race_name
FROM 
    drivers d
JOIN 
    results r ON d.driver_id = r.driver_id
WHERE 
    r.position = 1
ORDER BY 
    d.date_of_birth ASC
LIMIT 1;
```

### Q1003 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Identifies the race via a nested circuits.name = 'Canadian Grand Prix' lookup instead of races.name -- the recurring circuits/races name confusion, one join level deeper.

**Gold SQL:**

```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM results 
WHERE status_id = (SELECT status_id FROM status WHERE status = 'Accident') 
AND race_id = (SELECT race_id FROM races WHERE circuit_id = (SELECT circuit_id FROM circuits WHERE name = 'Canadian Grand Prix')) 
GROUP BY driver_id 
ORDER BY COUNT(*) DESC 
LIMIT 1;
```

### Q1011 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Uses lapTimes.time (a formatted text string) instead of lapTimes.milliseconds (the numeric value gold uses) for MIN() and ORDER BY, producing a lexicographic instead of numeric sort.

**Gold SQL:**

```sql
SELECT d.forename, d.surname FROM drivers d INNER JOIN (SELECT driverId, MIN(milliseconds) as min_ms FROM lapTimes WHERE milliseconds IS NOT NULL GROUP BY driverId) lt ON d.driverId = lt.driverId ORDER BY lt.min_ms ASC LIMIT 20;
```

**Predicted SQL:**

```sql
SELECT T2.first_name, T2.last_name
FROM (
    SELECT driver_id, MIN(time) AS min_time
    FROM lapTimes
    GROUP BY driver_id
    ORDER BY min_time ASC
    LIMIT 20
) AS T1
JOIN drivers AS T2 ON T1.driver_id = T2.driver_id;
```

### Q1014 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops results entirely (joins only circuits+races), so FastestLapTime is unreachable, and references a nonexistent races.lap column instead.

**Gold SQL:**

```sql
WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.circuit_id, T1.name, MIN(T2.lap) AS min_lap
FROM circuits AS T1
JOIN races AS T2 ON T1.circuit_id = T2.circuit_id
WHERE T1.country = 'Italy'
GROUP BY T1.circuit_id, T1.name;
```

---

## student_club (27 failures)

### Q1317 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** t_shirt_size = 'M' instead of the real value 'Medium'.

**Gold SQL:**

```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.member_id) 
FROM member AS T1 
JOIN attendance AS T2 ON T1.member_id = T2.member_id 
JOIN event AS T3 ON T2.event_id = T3.event_id 
WHERE T3.event_name = 'Women''s Soccer' AND T1.t_shirt_size = 'M';
```

### Q1338 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins expense directly to event, skipping the budget bridge table; expense has no event_id, only a link to budget.

**Gold SQL:**

```sql
SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'
```

**Predicted SQL:**

```sql
SELECT e.is_approved FROM expense e 
JOIN event ev ON e.event_id = ev.event_id 
WHERE ev.event_name = 'October Meeting' AND ev.event_date = '2019-10-08'
```

### Q1339 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Hardcodes a specific year (BETWEEN '2023-09-01' AND '2023-10-31') instead of gold's year-agnostic SUBSTR-based month check.

**Gold SQL:**

```sql
SELECT AVG(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.last_name = 'Allen' AND T1.first_name = 'Elijah' AND (SUBSTR(T2.expense_date, 6, 2) = '09' OR SUBSTR(T2.expense_date, 6, 2) = '10')
```

**Predicted SQL:**

```sql
SELECT AVG(expense.cost) AS average_cost
FROM expense
JOIN member ON expense.member_id = member.member_id
WHERE member.first_name = 'Elijah' AND member.last_name = 'Allen'
  AND expense.expense_date BETWEEN '2023-09-01' AND '2023-10-31';
```

### Q1340 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** event_date is referenced via the member alias (T3) instead of the event alias (T1) that's already joined; also adds a spurious major_id filter not in gold.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T3.event_date BETWEEN '2019-01-01' AND '2019-12-31' THEN T4.amount_spent ELSE 0 END) - 
    SUM(CASE WHEN T3.event_date BETWEEN '2020-01-01' AND '2020-12-31' THEN T4.amount_spent ELSE 0 END) AS amount_difference
FROM 
    event AS T1
JOIN 
    attendance AS T2 ON T1.event_id = T2.event_id
JOIN 
    member AS T3 ON T2.member_id = T3.member_id
JOIN 
    budget AS T4 ON T1.event_id = T4.event_id
WHERE 
    T3.major_id = (SELECT major_id FROM major WHERE major_name = 'Student_Club');
```

### Q1344 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Selects notes from event instead of income; both tables happen to have a notes column, so the source table for the same-role attribute was swapped.

**Gold SQL:**

```sql
SELECT notes FROM income WHERE source = 'Fundraising' AND date_received = '2019-09-14'
```

**Predicted SQL:**

```sql
SELECT notes FROM event WHERE event_date = '2019-09-14' AND type = 'fundraising';
```

### Q1350 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Selects status from event instead of event_status from budget, and joins expense directly to event, which has no event_id.

**Gold SQL:**

```sql
SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'
```

**Predicted SQL:**

```sql
SELECT T1.status 
FROM event AS T1 
JOIN expense AS T2 ON T1.event_id = T2.event_id 
WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20';
```

### Q1352 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters major.department instead of major.major_name; both are real columns on major.

**Gold SQL:**

```sql
SELECT COUNT(T1.member_id) FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.major_name = 'Business' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT COUNT(member_id) 
FROM member 
JOIN major ON member.major_id = major.major_id 
WHERE major.department = 'Business' AND t_shirt_size = 'Medium';
```

### Q1359 (challenging, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Replaces gold's ratio-of-sums (CASE-based SUM/SUM division across two events) with a plain COUNT and an unrelated != filter, a wrong aggregate/shape.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.event_name = 'Yearly Kickoff' THEN T1.amount ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.event_name = 'October Meeting' THEN T1.amount ELSE 0 END) FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T1.category = 'Advertisement' AND T2.type = 'Meeting'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.event_id) 
FROM budget AS T1 
JOIN event AS T2 ON T1.event_id = T2.event_id 
WHERE T2.event_name = 'Yearly Kickoff' AND T1.category = 'Advertisement' 
AND T2.event_name != 'October Meeting';
```

### Q1375 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Adds member_id to the SELECT list beyond gold's two columns (first_name, last_name), changing the output shape.

**Gold SQL:**

```sql
SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T2.department = 'School of Applied Sciences, Technology and Education'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.member_id, m.first_name, m.last_name
FROM member m
JOIN major j ON m.major_id = j.major_id
WHERE j.department = 'School of Applied Sciences, Technology and Education';
```

### Q1376 (moderate, retrieval) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` -- **Reason:** Collapses gold's tie-preserving GROUP BY ... HAVING ratio = (SELECT MAX(...)) subquery pattern into a plain ORDER BY ... LIMIT 1, also dropping the GROUP BY/HAVING > 0 guard.

**Gold SQL:**

```sql
SELECT e.event_name FROM event AS e JOIN budget AS b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' GROUP BY e.event_id, e.event_name HAVING SUM(b.amount) > 0 AND SUM(b.spent) / SUM(b.amount) = ( SELECT MAX(ratio) FROM ( SELECT SUM(b2.spent) * 1.0 / SUM(b2.amount) AS ratio FROM budget AS b2 JOIN event AS e2 ON b2.link_to_event = e2.event_id WHERE e2.status = 'Closed' GROUP BY e2.event_id HAVING SUM(b2.amount) > 0 ) )
```

**Predicted SQL:**

```sql
SELECT e.event_name, b.amount_spent / b.amount AS spend_to_budget_ratio
FROM event e
JOIN budget b ON e.event_id = b.event_id
WHERE e.status = 'closed'
ORDER BY spend_to_budget_ratio DESC
LIMIT 1;
```

### Q1387 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins member directly to budget, which has no member relationship at all, skipping expense and event; also filters budget.event_status against an event name.

**Gold SQL:**

```sql
SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff' AND T4.position = 'Treasurer';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name
FROM member m
JOIN budget b ON m.member_id = b.member_id
WHERE b.event_status = 'Yearly Kickoff';
```

### Q1389 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the budget/expense joins entirely and orders by 'cost', a column that only exists on expense.

**Gold SQL:**

```sql
SELECT T1.event_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget ORDER BY T3.cost, T1.event_name LIMIT 1
```

**Predicted SQL:**

```sql
SELECT event_name FROM event ORDER BY cost ASC, event_name ASC LIMIT 1;
```

### Q1390 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the budget/expense joins entirely and references 'amount', a column that only exists on budget.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.event_name = 'Yearly Kickoff' THEN T3.cost ELSE 0 END) AS REAL) * 100 / SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN e.event_name = 'Yearly Kickoff' THEN e.amount ELSE 0 END) AS REAL) * 100 / SUM(e.amount) FROM event e
```

### Q1392 (simple, retrieval) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted GROUP BY income_source + SUM(amount) and orders by that sum, when gold has no aggregation at all and simply orders by the source name.

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

### Q1394 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted position = 'Student_Club' filter not present in gold, which appears to be an invented/hallucinated condition.

**Gold SQL:**

```sql
SELECT COUNT(T2.member_id) FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T1.major_name = 'Physics Teaching'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.member_id) 
FROM member AS T1 
JOIN major AS T2 ON T1.major_id = T2.major_id 
WHERE T2.major_name = 'Physics Teaching' AND T1.position = 'Student_Club';
```

### Q1401 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the event table and tries to filter event_name directly on budget, which doesn't have that column.

**Gold SQL:**

```sql
SELECT T3.cost FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'September Speaker' AND T3.expense_description = 'Posters'
```

**Predicted SQL:**

```sql
SELECT SUM(cost) AS total_poster_cost
FROM expense
JOIN budget ON expense.budget_id = budget.budget_id
WHERE expense_description LIKE '%Posters%'
  AND budget.event_name = 'September Speaker';
```

### Q1403 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Rewrites remaining < 0 as amount_spent > amount_remaining (not an equivalent condition) and reorders by that difference instead of remaining.

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
  AND b.amount_spent > b.amount_remaining
ORDER BY b.amount_spent - b.amount_remaining DESC
LIMIT 1;
```

### Q1404 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Adds a spurious budget.event_status = 'Approved' condition not in gold (event_status isn't an approval flag) and changes approved = 'true' to is_approved = 1.

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
SELECT b.category, SUM(e.cost) AS total_approved
FROM budget b
JOIN expense e ON b.budget_id = e.budget_id
WHERE b.event_status = 'Approved'
  AND e.is_approved = 1
  AND b.event_id IN (
      SELECT event_id
      FROM event
      WHERE event_name = 'October Meeting'
  )
GROUP BY b.category;
```

### Q1405 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Selects/sums budget.spent (amount_spent) instead of budget.amount -- two distinct real columns -- and drops gold's GROUP BY/aggregation.

**Gold SQL:**

```sql
SELECT T2.category, SUM(T2.amount) FROM event AS T1 JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.event_name = 'April Speaker' GROUP BY T2.category ORDER BY SUM(T2.amount) ASC
```

**Predicted SQL:**

```sql
SELECT b.category, b.amount_spent
FROM budget b
JOIN event e ON b.event_id = e.event_id
WHERE e.event_name = 'April Speaker'
ORDER BY b.category ASC;
```

### Q1422 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Returns budget.category via spurious extra joins instead of event.type; both real columns, wrong one filling the SELECT role.

**Gold SQL:**

```sql
SELECT `type`
FROM `event`
WHERE `location` = 'MU 215';
```

**Predicted SQL:**

```sql
SELECT T3.category FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.event_id INNER JOIN budget AS T3 ON T1.event_id = T3.event_id WHERE T1.location = 'MU 215';
```

### Q1426 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Output is a garbled, markdown-fenced, non-terminating repetition of column names -- not valid SQL at all.

**Gold SQL:**

```sql
SELECT T2.last_name, T1.department, T1.college FROM major AS T1 INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major WHERE T2.position = 'Member' AND T1.major_name = 'Environmental Engineering'
```

**Predicted SQL:**

```sql
```sql
SELECT m.last_name, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m.last_name, m.email, m.position, m.t_shirt_size, m.phone, m.zip_code, m.major_id, m.first_name, m
```

### Q1427 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Adds a spurious join to member via a nonexistent event.member_id column that isn't needed for this query.

**Gold SQL:**

```sql
SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.category 
FROM budget b 
JOIN event e ON b.event_id = e.event_id 
JOIN member m ON e.member_id = m.member_id 
WHERE e.location = 'MU 215' AND e.type = 'Guest Speaker' AND b.amount_spent = 0;
```

### Q1432 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the position = 'Member' / t_shirt_size = 'Medium' population filter and substitutes an invented income_source = 'Student_Club' condition instead.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN T2.t_shirt_size = 'medium' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.member_id) AS percentage
FROM 
    income AS T1
JOIN 
    member AS T2 ON T1.member_id = T2.member_id
WHERE 
    T1.income_source = 'Student_Club' AND T1.amount = 50;
```

### Q1435 (moderate, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Lowercases the type/status literals ('game'/'closed' vs the real 'Game'/'Closed'), which fail to match under SQLite's case-sensitive string comparison.

**Gold SQL:**

```sql
SELECT DISTINCT event_name FROM event WHERE type = 'Game' AND date(SUBSTR(event_date, 1, 10)) BETWEEN '2019-03-15' AND '2020-03-20' AND status = 'Closed'
```

**Predicted SQL:**

```sql
SELECT e.event_name FROM event e
JOIN budget b ON e.event_id = b.event_id
WHERE e.type = 'game' AND e.status = 'closed'
AND b.event_status = 'closed'
AND e.event_date BETWEEN '2019-03-15' AND '2020-03-20';
```

### Q1457 (challenging, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Missing DISTINCT, so members with multiple qualifying high-cost expenses appear as duplicate output rows.

**Gold SQL:**

```sql
SELECT DISTINCT T3.first_name, T3.last_name, T3.phone FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member WHERE T1.cost > ( SELECT AVG(T1.cost) FROM expense AS T1 INNER JOIN budget AS T2 ON T1.link_to_budget = T2.budget_id INNER JOIN member AS T3 ON T3.member_id = T1.link_to_member )
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, m.phone
FROM member m
JOIN expense e ON m.member_id = e.member_id
WHERE e.cost > (SELECT AVG(cost) FROM expense)
```

### Q1460 (challenging, retrieval) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted GROUP BY + SUM(cost) aggregation not in gold, and breaks the exact description match into a 3-item IN list of lowercase substrings.

**Gold SQL:**

```sql
SELECT T2.first_name, T2.last_name, T1.cost FROM expense AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T1.expense_description = 'Water, Veggie tray, supplies'
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, SUM(e.cost) AS total_cost
FROM expense e
JOIN member m ON e.member_id = m.member_id
WHERE e.expense_description IN ('water', 'veggie tray', 'supplies')
GROUP BY m.member_id;
```

### Q1464 (challenging, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References 'amount_received', which isn't a real column anywhere (the real column, and its correct S3 rename, is just 'amount').

**Gold SQL:**

```sql
SELECT M.`first_name`, M.`last_name`, I.`amount`
FROM `Income` I
JOIN `Member` M ON M.`member_id` = I.`link_to_member`
WHERE I.`date_received` = '2019-09-09';
```

**Predicted SQL:**

```sql
SELECT m.first_name, m.last_name, i.amount_received
FROM member m
JOIN income i ON m.member_id = i.member_id
WHERE i.date_received = '2019-09-09';
```

---

## superhero (34 failures)

### Q723 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Represents eye colour via the generic hero_attribute/attribute mechanism (attribute_name = 'Eye Colour') instead of superhero.eye_colour_id -> colour, which is how colour is actually modeled; also references a nonexistent attribute.attribute_value column (attribute_value only lives on hero_attribute).

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN colour AS T4 ON T1.eye_colour_id = T4.id WHERE T3.power_name = 'Agility' AND T4.colour = 'Blue'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.id) 
FROM superhero AS T1 
JOIN hero_attribute AS T2 ON T1.id = T2.hero_id 
JOIN attribute AS T3 ON T2.attribute_id = T3.id 
JOIN superpower AS T4 ON T1.id = T5.hero_id 
JOIN hero_power AS T5 ON T4.id = T5.power_id 
WHERE T3.attribute_name = 'Eye Colour' AND T3.attribute_value = 'Blue' AND T4.power_name = 'Agility';
```

### Q724 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Represents eye/hair colour via the generic hero_attribute/attribute mechanism with invented attribute_name values ('blue eyes', 'blond hair') instead of the dedicated eye_colour_id/hair_colour_id -> colour joins gold uses.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T2.colour = 'Blue' AND T3.colour = 'Blond'
```

**Predicted SQL:**

```sql
SELECT superhero.superhero_name
FROM superhero
JOIN hero_attribute ON superhero.id = hero_attribute.hero_id
JOIN attribute ON hero_attribute.attribute_id = attribute.id
WHERE attribute.attribute_name IN ('blue eyes', 'blond hair');
```

### Q726 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the height_cm IS NOT NULL AND height_cm != 0 sanity filter entirely, letting null/zero-height heroes into the ordered result; also selects an extra height_cm column not in gold's output.

**Gold SQL:**

```sql
SELECT superhero_name FROM superhero AS s JOIN publisher AS p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL AND s.height_cm != 0 ORDER BY s.height_cm DESC
```

**Predicted SQL:**

```sql
SELECT superhero.superhero_name, superhero.height_cm
FROM superhero
JOIN publisher ON superhero.publisher_id = publisher.id
WHERE publisher.publisher_name = 'Marvel Comics'
ORDER BY superhero.height_cm DESC;
```

### Q728 (moderate, aggregate) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's RANK() OVER (ORDER BY COUNT(...) DESC) window function and the COUNT column itself from the SELECT list, returning only bare colour names instead of colour/count/rank triples.

**Gold SQL:**

```sql
SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
```

**Predicted SQL:**

```sql
SELECT c.colour FROM colour c
JOIN superhero s ON c.id = s.eye_colour_id
JOIN publisher p ON s.publisher_id = p.id
WHERE p.publisher_name = 'Marvel Comics'
GROUP BY c.colour
ORDER BY COUNT(*) DESC;
```

### Q732 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Substitutes superhero.height_cm (via a MIN(height_cm) subquery) for the Speed attribute's attribute_value reached through hero_attribute/attribute -- an entirely different, unrelated real column standing in for the intended one.

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN hero_attribute AS T3 ON T1.id = T3.hero_id INNER JOIN attribute AS T4 ON T3.attribute_id = T4.id WHERE T4.attribute_name = 'Speed' ORDER BY T3.attribute_value LIMIT 1
```

**Predicted SQL:**

```sql
SELECT p.publisher_name
FROM publisher p
JOIN superhero s ON p.id = s.publisher_id
WHERE s.height_cm = (SELECT MIN(height_cm) FROM superhero)
ORDER BY p.publisher_name ASC
LIMIT 1;
```

### Q736 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Uses the alignment table with a fabricated value 'Dumb' instead of the hero_attribute/attribute mechanism for the Intelligence attribute -- alignment (Good/Bad/Neutral) is an unrelated concept from intelligence.

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Intelligence' AND ha.attribute_value = ( SELECT MIN(attribute_value) FROM hero_attribute WHERE attribute_id = ( SELECT id FROM attribute WHERE attribute_name = 'Intelligence' ) )
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE alignment_id = (SELECT id FROM alignment WHERE alignment = 'Dumb')
```

### Q740 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References gender_name; the real column (and its S3 identity-mapped name) is just 'gender'.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.attribute_name = 'Strength' AND T2.attribute_value = 100 AND T4.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.id) 
FROM superhero AS T1 
JOIN hero_attribute AS T2 ON T1.id = T2.hero_id 
JOIN attribute AS T3 ON T2.attribute_id = T3.id 
WHERE T1.gender_id = (SELECT id FROM gender WHERE gender_name = 'Female') 
AND T3.attribute_name = 'Strength' 
AND T2.attribute_value = 100;
```

### Q743 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.alignment directly on superhero, which doesn't exist there (only alignment_id does; the text value lives on the joined alignment table, which isn't joined at all here); also substitutes invented values 'Selfish'/'Moral Code' for the real 'Bad'.

**Gold SQL:**

```sql
SELECT (CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM superhero)), SUM(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN alignment AS T3 ON T3.id = T1.alignment_id WHERE T3.alignment = 'Bad'
```

**Predicted SQL:**

```sql
SELECT 
    CAST(SUM(CASE WHEN T1.alignment = 'Selfish' OR T1.alignment = 'Moral Code' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) AS percentage_selfish_moral_code,
    COUNT(CASE WHEN T1.publisher_id = (SELECT id FROM publisher WHERE publisher_name = 'Marvel Comics') AND (T1.alignment = 'Selfish' OR T1.alignment = 'Moral Code') THEN 1 ELSE NULL END) AS count_marvel_selfish_moral_code
FROM superhero AS T1;
```

### Q744 (challenging, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Replaces gold's clean subquery-based SUM(CASE...) Marvel/DC counts with a convoluted self-referential double LEFT JOIN of superhero to publisher and a CASE expression that doesn't correctly compute a marvel-count-minus-dc-count difference for arbitrary publishers.

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
    CASE 
        WHEN T1.publisher_name = 'DC Comics' THEN COUNT(T2.id) - COUNT(T3.id)
        ELSE COUNT(T3.id) - COUNT(T2.id)
    END AS difference
FROM 
    publisher AS T1
LEFT JOIN 
    superhero AS T2 ON T1.id = T2.publisher_id
LEFT JOIN 
    superhero AS T3 ON T1.id = T3.publisher_id AND T1.publisher_name != 'DC Comics'
GROUP BY 
    T1.publisher_name;
```

### Q745 (simple, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** Selects publisher_id directly on the publisher table, which doesn't exist there (publisher's own primary key is just 'id'; publisher_id is only the foreign-key column name on superhero) -- a real column name borrowed from a sibling table with no join present.

**Gold SQL:**

```sql
SELECT id FROM publisher WHERE publisher_name = 'Star Trek'
```

**Predicted SQL:**

```sql
SELECT publisher_id FROM publisher WHERE publisher_name = 'Star Trek';
```

### Q750 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the weight_kg > 0 sanity filter entirely, letting null/zero-weight heroes skew the average.

**Gold SQL:**

```sql
SELECT AVG(weight_kg) FROM superhero s JOIN gender g ON s.gender_id = g.id WHERE g.gender = 'Female' AND weight_kg > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(weight_kg) AS average_weight
FROM superhero
JOIN gender ON superhero.gender_id = gender.id
WHERE gender.gender = 'Female';
```

### Q751 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted DISTINCT not present in gold, collapsing what should be one row per male-hero/power combination down to unique power names only.

**Gold SQL:**

```sql
SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male'
```

**Predicted SQL:**

```sql
SELECT DISTINCT sp.power_name 
FROM superhero s 
JOIN hero_power hp ON s.id = hp.hero_id 
JOIN superpower sp ON hp.power_id = sp.id 
JOIN gender g ON s.gender_id = g.id 
WHERE g.gender = 'Male';
```

### Q753 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters eye_colour_id IS NULL instead of joining colour and checking colour = 'No Colour' -- 'No Colour' is an actual named value in the colour table, not a missing/null foreign key; also drops DISTINCT.

**Gold SQL:**

```sql
SELECT DISTINCT T1.superhero_name FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.height_cm BETWEEN 170 AND 190 AND T2.colour = 'No Colour'
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE height_cm BETWEEN 170 AND 190 AND eye_colour_id IS NULL;
```

### Q758 (moderate, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References race_name in a subquery; the real column is just 'race'. Also misuses the hero_attribute/attribute mechanism (joining attribute_value directly to colour.id) instead of superhero.hair_colour_id for hair colour.

**Gold SQL:**

```sql
SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'
```

**Predicted SQL:**

```sql
SELECT T3.colour FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN colour AS T3 ON T2.attribute_value = T3.id WHERE T1.height_cm = 185 AND T1.race_id = (SELECT id FROM race WHERE race_name = 'Human')
```

### Q761 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References gender_name; the real column is just 'gender'.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id WHERE T2.gender = 'Male' AND T1.weight_kg * 100 > ( SELECT AVG(weight_kg) FROM superhero WHERE weight_kg > 0) * 79
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE gender_id = (SELECT id FROM gender WHERE gender_name = 'Male') AND weight_kg > (SELECT AVG(weight_kg) * 0.79 FROM superhero)
```

### Q766 (moderate, retrieval) -- **Nesting problem** (Wrong sub-query)

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's CTE that finds the MAX Strength attribute_value and joins back to find all tied heroes, replacing it with a plain ORDER BY attribute_value DESC LIMIT 1, which misses any heroes tied at the maximum.

**Gold SQL:**

```sql
WITH max_strength AS (SELECT attribute_id, MAX(attribute_value) attribute_value FROM hero_attribute INNER JOIN attribute ON attribute_id = attribute.id WHERE attribute.attribute_name = 'Strength' GROUP BY 1) SELECT distinct T1.full_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN max_strength AS T3 ON T2.attribute_id = T3.attribute_id AND T2.attribute_value = T3.attribute_value
```

**Predicted SQL:**

```sql
SELECT superhero.full_name
FROM superhero
JOIN hero_attribute ON superhero.id = hero_attribute.hero_id
JOIN attribute ON hero_attribute.attribute_id = attribute.id
WHERE attribute.attribute_name = 'Strength'
ORDER BY hero_attribute.attribute_value DESC
LIMIT 1;
```

### Q769 (challenging, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Orders by COUNT(*) DESC instead of gold's attribute_value DESC, picking a hero by row count rather than by their actual Durability score.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN attribute AS T3 ON T3.id = T2.attribute_id INNER JOIN publisher AS T4 ON T4.id = T1.publisher_id WHERE T4.publisher_name = 'Dark Horse Comics' AND T3.attribute_name = 'Durability' ORDER BY T2.attribute_value DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT superhero_name
FROM superhero
JOIN publisher ON superhero.publisher_id = publisher.id
JOIN hero_attribute ON superhero.id = hero_attribute.hero_id
JOIN attribute ON hero_attribute.attribute_id = attribute.id
WHERE publisher_name = 'Dark Horse Comics' AND attribute_name = 'Durability'
GROUP BY superhero_name
ORDER BY COUNT(*) DESC
LIMIT 1;
```

### Q772 (challenging, retrieval) -- **Invalid SQL** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins a nonexistent 'superhero_publisher' table; the real relationship is a direct publisher_id foreign key on superhero, no bridge table needed.

**Gold SQL:**

```sql
SELECT T1.eye_colour_id, T1.hair_colour_id, T1.skin_colour_id FROM superhero AS T1 INNER JOIN publisher AS T2 ON T2.id = T1.publisher_id INNER JOIN gender AS T3 ON T3.id = T1.gender_id WHERE T2.publisher_name = 'Dark Horse Comics' AND T3.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT 
    c.colour AS eye_colour,
    h.hair_colour,
    s.skin_colour
FROM 
    superhero s
JOIN 
    colour c ON s.eye_colour_id = c.id
JOIN 
    superhero_publisher sp ON s.id = sp.hero_id
JOIN 
    publisher p ON sp.publisher_id = p.id
WHERE 
    s.gender_id = (SELECT id FROM gender WHERE gender_name = 'Female')
    AND p.publisher_name = 'Dark Horse Comics';
```

### Q773 (challenging, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Misuses the hero_attribute/attribute mechanism with invented attribute_name values ('eye_colour', 'hair_colour', 'skin_colour') instead of directly comparing superhero.eye_colour_id/hair_colour_id/skin_colour_id gold uses; also references publisher_name directly on superhero without joining publisher.

**Gold SQL:**

```sql
SELECT T1.superhero_name, T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.eye_colour_id = T1.hair_colour_id AND T1.eye_colour_id = T1.skin_colour_id
```

**Predicted SQL:**

```sql
SELECT superhero.superhero_name, superhero.publisher_name
FROM superhero
JOIN hero_attribute ha ON superhero.id = ha.hero_id
JOIN colour c ON ha.attribute_value = c.id
WHERE ha.attribute_name IN ('eye_colour', 'hair_colour', 'skin_colour')
GROUP BY superhero.id
HAVING COUNT(DISTINCT ha.attribute_name) = 3;
```

### Q775 (challenging, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References gender_name in a subquery; the real column is just 'gender'. (Also separately joins colour via hair_colour_id instead of the intended skin_colour_id, but the query fails before that matters.)

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.colour = 'Blue' THEN T1.id ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.gender = 'Female'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.hair_colour_id = T2.id WHERE T1.gender_id = (SELECT id FROM gender WHERE gender_name = 'Female')
```

### Q781 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Misuses the hero_attribute/attribute mechanism (joining attribute_value to colour.id) instead of the direct superhero.eye_colour_id -> colour join gold uses; also lowercases the colour literal ('amber' vs 'Amber').

**Gold SQL:**

```sql
SELECT T1.height_cm FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T2.colour = 'Amber'
```

**Predicted SQL:**

```sql
SELECT superhero.height_cm FROM superhero 
JOIN hero_attribute ON superhero.id = hero_attribute.hero_id 
JOIN colour ON hero_attribute.attribute_value = colour.id 
WHERE colour.colour = 'amber';
```

### Q785 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Replaces the alignment = 'Neutral' name-based filter (via a join to alignment) with a hardcoded, unverified alignment_id = 2 guess, bypassing the lookup entirely.

**Gold SQL:**

```sql
SELECT T1.superhero_name FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id WHERE T2.alignment = 'Neutral'
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero WHERE alignment_id = 2
```

### Q788 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Swaps which population is the denominator: gold computes the percentage of female heroes who are Marvel, predicted computes the percentage of Marvel heroes who are (an assumed) gender_id = 2, using an INNER JOIN to publisher and a hardcoded gender id instead of gold's LEFT JOIN and gender-table lookup.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T3.gender = 'Female' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 LEFT JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.gender_id = 2 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T2.publisher_name = 'Marvel Comics'
```

### Q790 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Self-joins on superhero_name = 'Emil Blonsky'/'Charles Chandler' instead of full_name; these are different real columns (codename vs. civilian/full name), and 'Emil Blonsky' is a full_name value, not a superhero_name.

**Gold SQL:**

```sql
SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE
```

**Predicted SQL:**

```sql
SELECT T1.weight_kg - T2.weight_kg AS weight_difference
FROM superhero AS T1
JOIN superhero AS T2 ON T1.superhero_name = 'Emil Blonsky' AND T2.superhero_name = 'Charles Chandler';
```

### Q791 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the height_cm > 0 sanity filter entirely, letting null/zero-height heroes skew the average.

**Gold SQL:**

```sql
SELECT AVG(height_cm) FROM superhero WHERE height_cm > 0;
```

**Predicted SQL:**

```sql
SELECT AVG(height_cm) AS average_height FROM superhero;
```

### Q794 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Orders by height_cm DESC instead of the Speed attribute's attribute_value reached through hero_attribute/attribute -- an entirely different, unrelated real column standing in for the intended one.

**Gold SQL:**

```sql
SELECT s.superhero_name FROM superhero AS s JOIN hero_attribute AS ha ON s.id = ha.hero_id JOIN attribute AS a ON ha.attribute_id = a.id WHERE a.attribute_name = 'Speed' AND ha.attribute_value = ( SELECT MAX(ha2.attribute_value) FROM hero_attribute AS ha2 JOIN attribute AS a2 ON ha2.attribute_id = a2.id WHERE a2.attribute_name = 'Speed' )
```

**Predicted SQL:**

```sql
SELECT superhero_name FROM superhero ORDER BY height_cm DESC LIMIT 1
```

### Q798 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unnecessary INNER JOIN to hero_power, which can silently drop any of the three named heroes that have no listed powers from the result, unlike gold's simpler direct join to publisher.

**Gold SQL:**

```sql
SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.publisher_name 
FROM superhero AS T1 
JOIN hero_power AS T2 ON T1.id = T2.hero_id 
JOIN publisher AS T3 ON T1.publisher_id = T3.id 
WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy');
```

### Q800 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References T2.eye_colour on the colour table; the real column is just 'colour'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.colour = 'Blue' THEN 1 ELSE NULL END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.eye_colour = 'Blue' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id
```

### Q801 (moderate, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Uses COUNT(T2.gender) (all rows with a non-null gender) as the denominator instead of gold's COUNT of Female-only rows, changing the ratio from Male/Female to roughly Male/Total.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T2.gender = 'Male' THEN T1.id ELSE NULL END) AS REAL) / COUNT(CASE WHEN T2.gender = 'Female' THEN T1.id ELSE NULL END) FROM superhero AS T1 INNER JOIN gender AS T2 ON T1.gender_id = T2.id
```

**Predicted SQL:**

```sql
SELECT COUNT(CASE WHEN T2.gender = 'Male' THEN 1 ELSE NULL END) / COUNT(T2.gender) AS ratio
FROM superhero AS T1
JOIN gender AS T2 ON T1.gender_id = T2.id;
```

### Q806 (simple, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Misuses the hero_attribute/attribute mechanism (joining attribute_value to colour.id) instead of the direct superhero.eye_colour_id -> colour join gold uses.

**Gold SQL:**

```sql
SELECT T2.colour FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.full_name = 'Karen Beecher-Duncan'
```

**Predicted SQL:**

```sql
SELECT T3.colour FROM superhero AS T1 INNER JOIN hero_attribute AS T2 ON T1.id = T2.hero_id INNER JOIN colour AS T3 ON T2.attribute_value = T3.id WHERE T1.full_name = 'Karen Beecher-Duncan';
```

### Q819 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Uses different, unverified colour id values (eye_colour_id = 2 and eye_colour_id IS NULL) in place of gold's colour.id = 7 and colour.id = 1, and drops the weight_kg = 0 OR clause, keeping only the IS NULL half of the population filter.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN T2.id = 7 THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.id = 1 THEN 1 ELSE 0 END) FROM superhero AS T1 INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id WHERE T1.weight_kg = 0 OR T1.weight_kg is NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(CASE WHEN T1.eye_colour_id = 2 THEN 1 ELSE NULL END) - COUNT(CASE WHEN T1.eye_colour_id IS NULL THEN 1 ELSE NULL END) AS difference
FROM superhero AS T1
LEFT JOIN hero_attribute AS T2 ON T1.id = T2.hero_id
WHERE T1.weight_kg IS NULL;
```

### Q822 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins race instead of alignment and filters race.alignment = 'Villain' -- the race table (species like Human/Alien) has no alignment column at all, and 'Villain' is a fabricated value in place of the real 'Bad'.

**Gold SQL:**

```sql
SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN alignment AS T2 ON T1.alignment_id = T2.id INNER JOIN colour AS T3 ON T1.skin_colour_id = T3.id WHERE T2.alignment = 'Bad' AND T3.colour = 'Green'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) 
FROM superhero 
JOIN race ON superhero.race_id = race.id 
JOIN colour ON superhero.skin_colour_id = colour.id 
WHERE race.alignment = 'Villain' AND colour.colour = 'Green';
```

### Q825 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the required join to the gender table entirely and selects T1.gender directly off superhero, which only has gender_id, not the resolved gender text.

**Gold SQL:**

```sql
SELECT T4.gender FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T2.power_id = T3.id INNER JOIN gender AS T4 ON T1.gender_id = T4.id WHERE T3.power_name = 'Phoenix Force'
```

**Predicted SQL:**

```sql
SELECT T1.gender 
FROM superhero AS T1 
JOIN hero_power AS T2 ON T1.id = T2.hero_id 
JOIN superpower AS T3 ON T2.power_id = T3.id 
WHERE T3.power_name = 'Phoenix Force';
```

### Q829 (challenging, aggregate) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Uses the same convoluted self-referential double LEFT JOIN/CASE construction as Q744, which doesn't correctly replicate gold's subquery-based dc-count-minus-marvel-count difference.

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
    CASE 
        WHEN T1.publisher_name = 'DC Comics' THEN COUNT(T2.id) - COUNT(T3.id)
        ELSE COUNT(T3.id) - COUNT(T2.id)
    END AS difference
FROM 
    publisher AS T1
LEFT JOIN 
    superhero AS T2 ON T1.id = T2.publisher_id
LEFT JOIN 
    superhero AS T3 ON T1.id = T3.publisher_id AND T2.superhero_name != T3.superhero_name;
```

---

## thrombosis_prediction (50 failures)

### Q1149 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses invented domain values 'Inpatient'/'Outpatient'/'Male' in place of the real codes '+'/'-'/'M', on an otherwise structurally similar ratio-of-conditional-counts query.

**Gold SQL:**

```sql
WITH male_counts AS ( SELECT SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '+' THEN 1 ELSE 0 END) AS in_count, SUM(CASE WHEN p.SEX = 'M' AND p.Admission = '-' THEN 1 ELSE 0 END) AS out_count FROM Patient p ) SELECT CASE WHEN in_count > out_count THEN 'in-patient' ELSE 'outpatient' END, CAST(in_count AS FLOAT) * 100 / out_count AS percentage FROM male_counts;
```

**Predicted SQL:**

```sql
SELECT 
    CASE 
        WHEN admission_type = 'Inpatient' THEN 'Inpatient'
        ELSE 'Outpatient'
    END AS patient_type,
    COUNT(*) AS count,
    (COUNT(*) - (SELECT COUNT(*) FROM Patient WHERE sex = 'Male' AND admission_type = 'Inpatient')) / COUNT(*) * 100 AS deviation_percentage
FROM 
    Patient
WHERE 
    sex = 'Male'
GROUP BY 
    patient_type;
```

### Q1150 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Swaps which condition gates the WHERE population filter vs. the CASE-based percentage numerator (birthday-year vs. sex), changing the denominator from all female patients to all patients born after 1930.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.sex = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T2.ID) FROM Patient AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T1.birthday > '1930-01-01'
```

### Q1152 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses invented domain values admission_type = 'Inpatient'/'Outpatient' instead of the real codes '+'/'-'.

**Gold SQL:**

```sql
SELECT SUM(CASE WHEN Admission = '+' THEN 1.0 ELSE 0 END) / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE Diagnosis = 'SLE'
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(CASE WHEN admission_type = 'Inpatient' THEN 1 ELSE NULL END) / COUNT(CASE WHEN admission_type = 'Outpatient' THEN 1 ELSE NULL END) AS ratio
FROM 
    Patient
WHERE 
    diagnosis = 'SLE';
```

### Q1153 (simple, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** Joins on T2.patient_id; Laboratory has no such column (or S3 rename) -- the real join key is just ID.

**Gold SQL:**

```sql
SELECT T1.Diagnosis, T2.Date FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 30609
```

**Predicted SQL:**

```sql
SELECT T1.diagnosis, T2.Date
FROM Patient AS T1
JOIN Laboratory AS T2 ON T1.ID = T2.patient_id
WHERE T1.ID = 30609;
```

### Q1155 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Threshold changed from LDH > 500 to lactate_dehydrogenase > 150.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.LDH > 500
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.lactate_dehydrogenase > 150;
```

### Q1156 (moderate, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Uses TIMESTAMPDIFF(YEAR, ...), a non-SQLite function/syntax; also swaps RVVT for the unrelated Thrombosis column, but the query fails to execute before that matters.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.RVVT = '+'
```

**Predicted SQL:**

```sql
SELECT T1.ID, TIMESTAMPDIFF(YEAR, T1.birthday, CURDATE()) AS age
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T2.thrombosis_degree = 'positive';
```

### Q1157 (simple, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses thrombosis_degree = 'severe' (an invented string) instead of the real numeric level 2.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.Thrombosis = 2
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.diagnosis FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.thrombosis_degree = 'severe';
```

### Q1162 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters by first_hospital_visit_date ('First Date') instead of first_record_date ('Description') for the year check -- both real Patient columns; also adds a spurious extra join to Examination with a fabricated date condition.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE STRFTIME('%Y', Description) = '1997' AND SEX = 'F' AND Admission = '-'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'F' 
  AND strftime('%Y', T1.first_hospital_visit_date) = '1997' 
  AND T1.admission_type = 'Outpatient' 
  AND T2.examination_date = DATE(T1.first_hospital_visit_date, '+1 day');
```

### Q1164 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses invented literals thrombosis_degree = 'most serious' and sex = 'female' instead of the real codes 1 and 'F'.

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
SELECT COUNT(T2.ID) 
FROM Examination AS T1 
JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T1.thrombosis_degree = 'most serious' AND T1.examination_date LIKE '1997%' AND T2.sex = 'female';
```

### Q1166 (simple, retrieval) -- **Nesting problem** (Wrong set operation)

**Outcome:** `wrong_answer` -- **Reason:** Drops gold's UNION, which handles the tie-break case where the oldest patient has no Symptoms row via a NULL-padded second branch; predicted also inverts MIN/MAX, picking the oldest patient instead of the intended one.

**Gold SQL:**

```sql
SELECT DISTINCT e.Symptoms, p.Diagnosis FROM Patient AS p INNER JOIN Examination AS e ON p.ID = e.ID WHERE p.Birthday = ( SELECT MAX(p2.Birthday) FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID ) AND NOT e.Symptoms IS NULL UNION SELECT NULL AS Symptoms, p.Diagnosis FROM Patient AS p WHERE p.ID = (SELECT p2.ID FROM Patient AS p2 INNER JOIN Examination AS e2 ON p2.ID = e2.ID WHERE p2.Birthday = (SELECT MAX(p3.Birthday) FROM Patient AS p3 INNER JOIN Examination AS e3 ON p3.ID = e3.ID ) ) AND NOT EXISTS( SELECT 1 FROM Examination AS e WHERE e.ID = p.ID AND NOT e.Symptoms IS NULL )
```

**Predicted SQL:**

```sql
SELECT T1.symptoms, T1.diagnosis
FROM Examination AS T1
JOIN Patient AS T2 ON T1.ID = T2.ID
WHERE T2.birthday = (SELECT MIN(birthday) FROM Patient)
ORDER BY T2.birthday ASC
LIMIT 1;
```

### Q1168 (challenging, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Uses TIMESTAMPDIFF(YEAR, ...), a non-SQLite function.

**Gold SQL:**

```sql
SELECT T1.Date, STRFTIME('%Y', T2."First Date") - STRFTIME('%Y', T2.Birthday) FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC, T1.Date DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.first_record_date, T1.birthday, TIMESTAMPDIFF(YEAR, T1.birthday, T1.first_record_date) AS age
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T1.diagnosis = 'SJS'
ORDER BY T1.birthday DESC
LIMIT 1;
```

### Q1169 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Collapses the two different sex-specific UA thresholds (<=8.0 for M, <=6.5 for F) embedded per-branch in gold's CASE expressions into one unconditional global WHERE uric_acid > 42 filter applied to the whole population.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN T1.ID ELSE NULL END) AS REAL) / COUNT(DISTINCT CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN T1.ID ELSE NULL END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID
```

**Predicted SQL:**

```sql
SELECT COUNT(CASE WHEN T1.sex = 'M' THEN 1 END) / COUNT(CASE WHEN T1.sex = 'F' THEN 1 END) AS male_female_ratio
FROM Patient AS T1
JOIN Laboratory AS T2 ON T1.ID = T2.ID
WHERE T2.uric_acid > 42;
```

### Q1171 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Replaces the age-at-examination-time condition (exam year minus birth year < 18) with an unrelated WHERE birthday > DATE('now','-3 years') filter computed relative to today instead of the examination date.

**Gold SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T2."Examination Date") BETWEEN '1990' AND '1993' AND STRFTIME('%Y', T2."Examination Date") - STRFTIME('%Y', T1.Birthday) < 18
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.birthday > DATE('now', '-3 years') AND T2.examination_date BETWEEN '1990-01-01' AND '1993-12-31';
```

### Q1175 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** References T2.hemoglobin via an Examination alias; HGB/hemoglobin only exists on Laboratory, so Examination was substituted for Laboratory in the join.

**Gold SQL:**

```sql
SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.birthday, T2.diagnosis
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T2.hemoglobin = (SELECT MAX(hemoglobin) FROM Examination);
```

### Q1179 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Selects anticardiolipin_igg instead of anticardiolipin_igm (aCL IgM); also drops the Description = '1994-02-19' sub-filter that disambiguates the patient.

**Gold SQL:**

```sql
SELECT "aCL IgM" FROM Examination WHERE ID IN (SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19') AND "Examination Date" = '1993-11-12'
```

**Predicted SQL:**

```sql
SELECT T1.anticardiolipin_igg FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.diagnosis = 'SLE' AND T1.examination_date = '1993-11-12'
```

### Q1185 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References total_cholesterol via the Patient alias (T1), which doesn't have that column -- it only exists on Laboratory (T2); the query also fails to aggregate two separate month totals via SUM the way gold does.

**Gold SQL:**

```sql
SELECT CAST((SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) - SUM(CASE WHEN T2.Date LIKE '1981-12-%' THEN T2."T-CHO" ELSE 0 END)) AS REAL) / SUM(CASE WHEN T2.Date LIKE '1981-11-%' THEN T2."T-CHO" ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Birthday = '1959-02-18'
```

**Predicted SQL:**

```sql
SELECT 
    (T2.total_cholesterol - T1.total_cholesterol) / T1.total_cholesterol * 100 AS decrease_rate
FROM 
    Patient AS T1
JOIN 
    Laboratory AS T2
ON 
    T1.ID = T2.ID
WHERE 
    T1.birthday = '1959-02-18'
    AND T2.Date BETWEEN '1981-11-01' AND '1981-12-31';
```

### Q1187 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins Examination instead of Laboratory, and references aspartate_aminotransferase (GOT) instead of alanine_aminotransferase (GPT) -- both a wrong table and a wrong sibling-column mixup.

**Gold SQL:**

```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Predicted SQL:**

```sql
SELECT T2.ID FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T1.examination_date BETWEEN '1987-07-06' AND '1996-01-31' AND T1.aspartate_aminotransferase > 30 AND T1.albumin < 4 ORDER BY T2.ID;
```

### Q1189 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unnecessary INNER JOIN to Patient (gold queries Examination alone), which can silently drop Examination rows without a matching Patient row and change the COUNT.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S' AND "aCL IgM" > (SELECT AVG("aCL IgM") * 1.2 FROM Examination WHERE Thrombosis = 2 AND "ANA Pattern" = 'S')
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Examination AS T1 
JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T1.thrombosis_degree = 2 
  AND T1.antinuclear_antibody_pattern = 'S' 
  AND T1.anticardiolipin_igm > (SELECT AVG(anticardiolipin_igm) FROM Examination WHERE thrombosis_degree = 2 AND antinuclear_antibody_pattern = 'S') * 1.2;
```

### Q1192 (challenging, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Restructures T-BIL < 2.0 into total_bilirubin BETWEEN 0 AND 150, a drastically different range/operator, not merely a different literal.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Admission = '-' AND T2."T-BIL" < 2.0 AND T2.Date LIKE '1991-10-%'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.ID 
FROM Laboratory AS T1 
JOIN Patient AS T2 ON T1.ID = T2.ID 
WHERE T1.Date BETWEEN '1991-10-01' AND '1991-10-31' 
  AND T1.total_bilirubin BETWEEN 0 AND 150 
  AND T2.admission_type = 'Outpatient';
```

### Q1195 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Averages total_protein (TP) instead of albumin (ALB) -- both real, sibling Laboratory columns.

**Gold SQL:**

```sql
SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'
```

**Predicted SQL:**

```sql
SELECT AVG(Lab.total_protein) AS average_albumin
FROM Laboratory Lab
JOIN Patient Pat ON Lab.ID = Pat.ID
WHERE Pat.sex = 'F' AND Lab.platelet_count > 400 AND Pat.diagnosis = 'SLE';
```

### Q1198 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Uses Examination.diagnosis (reached via an unneeded join) instead of Patient.diagnosis; both are real, distinct columns of the same name on different tables, and the extra join can also duplicate counts across multiple exam rows per patient.

**Gold SQL:**

```sql
SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'F' AND T2.diagnosis = 'APS';
```

### Q1201 (moderate, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T2.sex where T2 is the Examination alias; sex only exists on the already-joined Patient (T1) -- an alias mix-up; also conflates the Diagnosis = 'RA' condition with a fabricated Examination.rheumatoid_factor_ra column.

**Gold SQL:**

```sql
SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T2.sex = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE strftime('%Y', T1.birthday) = '1980' AND T2.rheumatoid_factor_ra = 1;
```

### Q1205 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Drops the required join to Patient (needed to determine sex) entirely, replacing gold's sex-dependent UA threshold branching with one fixed BETWEEN 1.4 AND 7 range.

**Gold SQL:**

```sql
SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN 'true' ELSE 'false' END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266
```

**Predicted SQL:**

```sql
SELECT 
    uric_acid,
    CASE 
        WHEN uric_acid BETWEEN 1.4 AND 7 THEN 'true'
        ELSE 'false'
    END AS uric_acid_normal
FROM 
    Laboratory
WHERE 
    ID = 57266;
```

### Q1208 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted extra GOT/aspartate_aminotransferase > 50 condition not in gold, and changes the GPT threshold/operator from >= 60 to > 50.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.GPT >= 60
```

**Predicted SQL:**

```sql
SELECT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.sex = 'M' AND T2.aspartate_aminotransferase > 50 AND T2.alanine_aminotransferase > 50;
```

### Q1209 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted extra GOT/aspartate_aminotransferase > 50 condition not in gold, and changes the GPT threshold/operator from > 60 to > 50.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC
```

**Predicted SQL:**

```sql
SELECT T1.diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.aspartate_aminotransferase > 50 AND T2.alanine_aminotransferase > 50 ORDER BY T1.birthday ASC;
```

### Q1220 (simple, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Restructures UN = 29 (exact match) into urea_nitrogen BETWEEN 5 AND 15, an unrelated range that doesn't even contain 29.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX, T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.UN = 29
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, T1.birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.urea_nitrogen BETWEEN 5 AND 15;
```

### Q1225 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Restructures T-BIL >= 2.0 into total_bilirubin NOT BETWEEN 15 AND 25, a drastically different threshold/units and inverted logic; also swaps GROUP_CONCAT(DISTINCT ID) for COUNT(ID), a wrong aggregate/shape.

**Gold SQL:**

```sql
SELECT GROUP_CONCAT(DISTINCT T1.ID),T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX
```

**Predicted SQL:**

```sql
SELECT T1.sex, COUNT(T1.ID) AS patient_count
FROM Patient AS T1
JOIN Laboratory AS T2 ON T1.ID = T2.ID
WHERE T2.total_bilirubin NOT BETWEEN 15 AND 25
GROUP BY T1.sex;
```

### Q1227 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** References total_cholesterol via an Examination alias; T-CHO only exists on Laboratory. Also averages raw birthday values divided by 365 instead of computing age via year subtraction.

**Gold SQL:**

```sql
SELECT AVG(age) FROM (SELECT DISTINCT T1.ID, STRFTIME('%Y', date('NOW')) - STRFTIME('%Y', T1.Birthday) as age FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2."T-CHO" >= 250 AND T1.SEX = 'M')
```

**Predicted SQL:**

```sql
SELECT AVG(T1.birthday) / 365 AS average_age
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T1.sex = 'M' AND T2.total_cholesterol > 200;
```

### Q1229 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Threshold changed from TG >= 200 to triglyceride > 150.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.TG >= 200 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 50
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.triglyceride > 150 AND T1.birthday < DATE('now', '-50 years');
```

### Q1231 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins Examination instead of Laboratory to reach CPK/creatinine_phosphokinase, which only exists on Laboratory.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', T1.Birthday) BETWEEN '1936' AND '1956' AND T1.SEX = 'M' AND T2.CPK >= 250
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'M' 
  AND T2.creatinine_phosphokinase > 100 
  AND strftime('%Y', T1.birthday) BETWEEN '1936' AND '1956';
```

### Q1232 (challenging, retrieval) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Uses TIMESTAMPDIFF(YEAR, ...), a non-SQLite function, and an unquoted T2.T-CHO reference.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, T1.SEX , STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GLU >= 180 AND T2."T-CHO" < 250
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex, TIMESTAMPDIFF(YEAR, T1.birthday, CURDATE()) AS age
FROM Patient AS T1
JOIN Laboratory AS T2 ON T1.ID = T2.ID
WHERE T2.GLU NOT BETWEEN 40 AND 100
  AND T2.T-CHO BETWEEN 150 AND 250;
```

### Q1235 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** References red_blood_cell_count (RBC) via an Examination alias; RBC only exists on Laboratory, so Examination was substituted for Laboratory.

**Gold SQL:**

```sql
SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.birthday, T1.diagnosis
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T2.red_blood_cell_count < (SELECT AVG(red_blood_cell_count) FROM Examination);
```

### Q1238 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** References hemoglobin (HGB) via an Examination alias; HGB only exists on Laboratory.

**Gold SQL:**

```sql
SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T1.ID, T1.sex
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T1.diagnosis = 'SLE' AND T2.hemoglobin IS NOT NULL AND T2.hemoglobin = 120
ORDER BY T1.birthday ASC
LIMIT 1;
```

### Q1239 (challenging, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Uses TIMESTAMPDIFF(YEAR, ...), a non-SQLite function.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )
```

**Predicted SQL:**

```sql
SELECT T1.ID, TIMESTAMPDIFF(YEAR, T1.birthday, CURDATE()) AS age
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T2.hematocrit > 50
GROUP BY T1.ID
HAVING COUNT(T2.ID) >= 2;
```

### Q1241 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Queries platelet_count directly on Patient with no join at all; PLT/platelet_count only exists on Laboratory.

**Gold SQL:**

```sql
SELECT (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT < 100) AS low_count, (SELECT COUNT(DISTINCT ID) FROM Laboratory WHERE PLT > 400) AS high_count;
```

**Predicted SQL:**

```sql
SELECT 
    COUNT(CASE WHEN platelet_count < 150 THEN 1 ELSE NULL END) AS lower_than_normal,
    COUNT(CASE WHEN platelet_count > 450 THEN 1 ELSE NULL END) AS higher_than_normal
FROM 
    Patient
WHERE 
    platelet_count IS NOT NULL;
```

### Q1242 (challenging, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References T2.age; no 'age' column exists anywhere in the schema (age must be derived from Birthday), so this is a genuine hallucination, not a missed join.

**Gold SQL:**

```sql
SELECT DISTINCT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT BETWEEN 100 AND 400 AND STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) < 50 AND STRFTIME('%Y', T2.Date) = '1984'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T2.ID, T2.sex, T2.birthday, T2.first_record_date, T2.first_hospital_visit_date, T2.admission_type, T2.diagnosis
FROM Examination AS T1
JOIN Patient AS T2 ON T1.ID = T2.ID
WHERE T1.examination_date BETWEEN '1984-01-01' AND '1984-12-31'
  AND T2.age < 50
  AND T1.platelet_count >= 150;
```

### Q1243 (challenging, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `error` -- **Reason:** Joins Examination instead of Laboratory to reach prothrombin_time (PT), which only exists on Laboratory.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN T1.ID END) AS REAL) * 100 / COUNT(DISTINCT CASE WHEN T2.PT >= 14 THEN T1.ID END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
```

**Predicted SQL:**

```sql
SELECT COUNT(CASE WHEN T1.sex = 'F' THEN 1 ELSE NULL END) * 100 / COUNT(T1.ID) AS female_abnormal_pt_percentage
FROM Patient AS T1
JOIN Examination AS T2 ON T1.ID = T2.ID
WHERE T1.birthday < DATE('now', '-55 years')
  AND T2.prothrombin_time > 15;
```

### Q1247 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops one branch of gold's (FG<=150 OR FG>=450) OR-condition, keeping only fibrinogen<150, and uses a unit-mismatched WBC range (4000-10000) instead of the real 3.5-9.0 scale.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.FG <= 150 OR T2.FG >= 450) AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'M' 
  AND T2.white_blood_cell_count BETWEEN 4000 AND 10000 
  AND T2.fibrinogen < 150;
```

### Q1251 (simple, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References immunoglobulin_g directly on Patient with no join at all; IGG only exists on Laboratory. Threshold also changed from 2000 to 1.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGG >= 2000
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM Patient WHERE immunoglobulin_g > 1
```

### Q1252 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the required Laboratory table (needed for the IGG condition), keeping only Patient+Examination, and changes the BETWEEN 900-2000 condition to an unrelated = 0 check.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T2.immunoglobulin_g = 0 AND T2.symptoms IS NOT NULL;
```

### Q1254 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References 'antiglobulin_a', which isn't a real column or valid S3 rename anywhere (the real column is immunoglobulin_a on Laboratory); also wrong table (Examination instead of Laboratory) and wrong Patient date column (birthday instead of First Date).

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGA BETWEEN 80 AND 500 AND strftime('%Y', T1."First Date") >= '1990'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.birthday > '1990-01-01' AND T2.antiglobulin_a = 0;
```

### Q1255 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References 'antinuclear_antibody_igm', a hallucinated column name that doesn't exist anywhere in the schema (conflates the separate ANA and IgM markers).

**Gold SQL:**

```sql
SELECT Diagnosis FROM (SELECT DISTINCT T1.ID, T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM <= 40 OR T2.IGM >= 400) GROUP BY Diagnosis ORDER BY COUNT(*) DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT T2.diagnosis FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T1.antinuclear_antibody_igm > 0 GROUP BY T2.diagnosis ORDER BY COUNT(*) DESC LIMIT 1;
```

### Q1256 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Both filter conditions are restructured to different columns and different operators: CRP = '+' becomes c_reactive_protein IS NULL, and Description IS NULL becomes diagnosis != 'Normal'.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+') AND T1.Description IS NULL
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.c_reactive_protein IS NULL AND T1.diagnosis != 'Normal'
```

### Q1257 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Replaces the relative age condition (current year - birth year < 70) with a hardcoded absolute cutoff birthday < '1970-01-01', which isn't equivalent to the intended relative-age comparison.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.creatinine > 1.5 AND T1.birthday < '1970-01-01';
```

### Q1265 (moderate, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Joins Examination instead of Laboratory and uses the ANA column (antinuclear_antibody) instead of RNP (anti_ribonuclear_protein) -- a different real marker on a different real table; also uses an invented admission_type = 'Admitted' value.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.RNP = 'negative' OR T2.RNP = '0') AND T1.Admission = '+'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.admission_type = 'Admitted' AND T2.antinuclear_antibody = 0;
```

### Q1267 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References 'antism', which isn't a real column or valid S3 rename anywhere (the real S3 name is anti_sm); also drops gold's CTE-based HAVING MAX(COALESCE(Thrombosis,0))=0 aggregation entirely.

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
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.antism = 0 AND T2.thrombosis_degree = 0;
```

### Q1270 (challenging, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References antiscl70_igg/antiscl70_igm/antiscl70_iga, none of which are real columns anywhere -- SC170 has no IgG/IgM/IgA breakdown in this schema; that pattern belongs to the separate aCL antibody columns.

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
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T1.sex = 'F' 
  AND T2.antiscl70_igg IS NULL 
  AND T2.antiscl70_igm IS NULL 
  AND T2.antiscl70_iga IS NULL 
  AND T2.symptoms IS NULL;
```

### Q1275 (moderate, aggregate) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References antiscl70/antissb-style names that aren't real columns or valid S3 renames, picking entirely unrelated markers (ANA Pattern, SC170) from the wrong table (Examination instead of Laboratory) in place of CENTROMEA/SSB.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T1.sex = 'M' AND T2.antinuclear_antibody_pattern = 'Normal' AND T2.antiscl70 = 'Normal' AND T2.antissb = 'Normal'
```

### Q1281 (moderate, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Uses MIN(birthday), which picks the oldest qualifying patient, instead of gold's ORDER BY Birthday DESC LIMIT 1 shape (intended to pick a specific one via ordering, not an aggregate); also uses a wrong GOT threshold (>50 vs >=60).

**Gold SQL:**

```sql
SELECT T1.Birthday FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GOT >= 60 ORDER BY T1.Birthday DESC LIMIT 1
```

**Predicted SQL:**

```sql
SELECT MIN(T1.birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.aspartate_aminotransferase > 50;
```

### Q1302 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the required Laboratory table (needed for the CPK condition), keeping only Patient+Examination, and replaces the KCT/RVVT/LAC OR-condition with an unrelated thrombosis_degree = 'Positive' check.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')
```

**Predicted SQL:**

```sql
SELECT COUNT(T1.ID) 
FROM Patient AS T1 
JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE T2.creatinine_phosphokinase BETWEEN 35 AND 180 
AND T2.thrombosis_degree = 'Positive';
```

---

## toxicology (38 failures)

### Q197 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Ambiguous column name: atom_id -- both the joined atom and connected tables have an atom_id column and the unqualified reference doesn't disambiguate; the query is also restructured with an unrelated HAVING COUNT(DISTINCT element)=1 condition and the wrong bond_type value 'single' instead of '-'.

**Gold SQL:**

```sql
WITH oxygen_atoms_per_molecule AS (SELECT atom.molecule_id, SUM(atom.element = 'o') AS oxygen_count FROM atom GROUP BY atom.molecule_id), single_bond_molecules AS (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-') SELECT AVG(oxygen_atoms_per_molecule.oxygen_count) AS average_oxygen_atoms FROM single_bond_molecules JOIN oxygen_atoms_per_molecule ON single_bond_molecules.molecule_id = oxygen_atoms_per_molecule.molecule_id
```

**Predicted SQL:**

```sql
SELECT AVG(atom_count) 
FROM (
    SELECT COUNT(atom_id) AS atom_count 
    FROM atom 
    JOIN connected ON atom.atom_id = connected.atom_id 
    JOIN bond ON connected.bond_id = bond.bond_id 
    WHERE bond.bond_type = 'single' 
    GROUP BY molecule_id 
    HAVING COUNT(DISTINCT element) = 1 
    AND SUM(CASE WHEN element = 'O' THEN 1 ELSE 0 END) > 0
);
```

### Q198 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through the connected junction table to reach molecule_id, but connected has no molecule_id column at all -- gold joins bond directly to molecule on molecule_id, no connected needed; also uses invented values 'single'/'carcinogenic' instead of the real '-'/'+' codes.

**Gold SQL:**

```sql
SELECT CAST(SUM(IIF(T1.bond_type = '-', 1, 0)) AS REAL) / COUNT(DISTINCT T1.molecule_id) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT AVG(CASE WHEN T3.bond_type = 'single' THEN 1 ELSE 0 END) AS avg_single_bonds
FROM molecule AS T1
JOIN connected AS T2 ON T1.molecule_id = T2.molecule_id
JOIN bond AS T3 ON T2.bond_id = T3.bond_id
WHERE T1.label = 'carcinogenic';
```

### Q200 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through connected (which has no molecule_id) instead of joining bond directly to molecule; also uses invented values 'triple' and 'cancerous'/'carcinogenic' instead of the real '#'/'+' codes.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '#' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT m.label
FROM molecule m
JOIN connected c ON m.molecule_id = c.molecule_id
JOIN bond b ON c.bond_id = b.bond_id
WHERE b.bond_type = 'triple' AND m.label IN ('cancerous', 'carcinogenic');
```

### Q201 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses element = 'C' and bond_type = 'double' instead of the real lowercase codes 'c' and '='; also drops DISTINCT on the atom_id count.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'C' AND T2.bond_type = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = 'double'
```

### Q206 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters bond.molecule_id = 'TR004_8_9' instead of connected.bond_id = 'TR004_8_9' -- 'TR004_8_9' is a bond_id-shaped value, not a molecule_id, and no bond join is even needed since connected already has bond_id directly.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id = 'TR004_8_9'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element 
FROM atom AS T1 
JOIN connected AS T2 ON T1.atom_id = T2.atom_id 
JOIN bond AS T3 ON T2.bond_id = T3.bond_id 
WHERE T3.molecule_id = 'TR004_8_9';
```

### Q207 (challenging, retrieval) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses bond_type = 'double' instead of the real code '='.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '='
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element 
FROM atom AS T1 
JOIN connected AS T2 ON T1.atom_id = T2.atom_id 
JOIN bond AS T3 ON T2.bond_id = T3.bond_id 
WHERE T3.bond_type = 'double';
```

### Q208 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unneeded join to connected, which fans out the row count since an atom can appear in multiple connected rows (one per bond), distorting the COUNT-based ranking gold computes via a direct atom-molecule join; also uses element = 'H' instead of 'h'.

**Gold SQL:**

```sql
SELECT T.label FROM ( SELECT T2.label, COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.element = 'h' GROUP BY T2.label ORDER BY COUNT(T2.molecule_id) DESC LIMIT 1 ) t
```

**Predicted SQL:**

```sql
SELECT T3.label FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN molecule AS T3 ON T1.molecule_id = T3.molecule_id WHERE T1.element = 'H' GROUP BY T3.label ORDER BY COUNT(*) DESC LIMIT 1;
```

### Q212 (challenging, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` -- **Reason:** Collapses gold's tie-preserving GROUP BY ... HAVING COUNT(*) = (SELECT MIN(cnt)...) subquery into a plain ORDER BY COUNT ASC LIMIT 1; also filters label != 'Carcinogenic' instead of label = '-'.

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
SELECT T1.element 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.label != 'Carcinogenic' 
GROUP BY T1.element 
ORDER BY COUNT(T1.atom_id) ASC 
LIMIT 1;
```

### Q213 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Compares atom.element to the value 'TR004_8' (an atom_id-shaped string, not a real element code) instead of filtering connected.atom_id = 'TR004_8'; also drops the symmetric OR check for the reverse atom_id/atom_id2 pairing.

**Gold SQL:**

```sql
SELECT distinct T1.bond_type FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.atom_id = 'TR004_8' AND T2.atom_id2 = 'TR004_20' OR T2.atom_id2 = 'TR004_8' AND T2.atom_id = 'TR004_20'
```

**Predicted SQL:**

```sql
SELECT T3.bond_type FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T1.element = 'TR004_8' AND T2.atom_id2 = 'TR004_20';
```

### Q215 (challenging, aggregate) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T3.atom_id where T3 is the bond alias; atom_id only exists on atom/connected (T1/T2), which are already joined -- an alias mix-up, compounded by replacing gold's two independent COUNT(DISTINCT...) values with a nonsensical INTERSECT of two aggregate rows.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT CASE WHEN atom.element = 'i' THEN atom.atom_id ELSE NULL END) AS iodine_nums, COUNT(DISTINCT CASE WHEN atom.element = 's' THEN atom.atom_id ELSE NULL END) AS sulfur_nums FROM atom WHERE atom.molecule_id IN (SELECT DISTINCT bond.molecule_id FROM bond WHERE bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.atom_id) AS iodine_count, COUNT(DISTINCT T3.atom_id) AS sulfur_count
FROM atom AS T1
JOIN connected AS T2 ON T1.atom_id = T2.atom_id
JOIN bond AS T3 ON T2.bond_id = T3.bond_id
WHERE T1.element = 'I' AND T3.bond_type = 'single'
INTERSECT
SELECT COUNT(DISTINCT T1.atom_id) AS iodine_count, COUNT(DISTINCT T3.atom_id) AS sulfur_count
FROM atom AS T1
JOIN connected AS T2 ON T1.atom_id = T2.atom_id
JOIN bond AS T3 ON T2.bond_id = T3.bond_id
WHERE T1.element = 'S' AND T3.bond_type = 'single';
```

### Q218 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through connected+bond unnecessarily to reach molecule_id, but connected has no molecule_id column; gold joins atom directly to molecule. Also uses element = 'F' and label = 'carcinogenic' instead of 'f'/'+', and drops the '100 -' inversion and DISTINCT.

**Gold SQL:**

```sql
SELECT 100 - CAST(COUNT(DISTINCT CASE WHEN T1.element = 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T2.molecule_id) FROM atom AS T1 INNER JOIN connected AS T3 ON T1.atom_id = T3.atom_id INNER JOIN bond AS T4 ON T3.bond_id = T4.bond_id INNER JOIN molecule AS T5 ON T4.molecule_id = T5.molecule_id WHERE T5.label = 'carcinogenic'
```

### Q219 (challenging, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the label = '+' population-restricting condition entirely and replaces gold's atom+molecule+bond triple join (counted with DISTINCT to avoid fan-out) with a raw bond-type fraction computed over connected+bond rows -- a different aggregation target, not just a different value.

**Gold SQL:**

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T2.label = '+' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.bond_type = 'triple' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = 'triple'
```

### Q220 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters molecule.label = 'TR000' instead of atom.molecule_id = 'TR000' -- label can only hold '+' or '-', so a molecule-id-shaped value never matches.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR000' ORDER BY T.element LIMIT 3
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.label = 'TR000' 
ORDER BY T1.element ASC 
LIMIT 3;
```

### Q226 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through connected unnecessarily to reach molecule_id, but connected has no such column; gold filters bond.molecule_id = 'TR008' directly with no join at all. Also uses bond_type = 'double' instead of '='.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T.bond_id),5) FROM bond AS T WHERE T.molecule_id = 'TR008'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.bond_type = 'double' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T3.bond_id) FROM molecule AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T1.label = 'TR008'
```

### Q227 (simple, aggregate) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Computes the percentage over joined atom/connected/bond rows instead of gold's simple single-table molecule query, and filters bond_type = 'carcinogenic' -- a value from label's domain, not a real bond_type value at all.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.label = '+' THEN T.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(T.molecule_id),3) FROM molecule t
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.bond_type = 'carcinogenic' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id INNER JOIN molecule AS T4 ON T1.molecule_id = T4.molecule_id
```

### Q228 (moderate, aggregate) -- **JOIN errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Joins connected to molecule via ON T2.atom_id2 = T3.molecule_id -- comparing an atom-id value to a molecule-id value, a domain mismatch that doesn't correspond to any real relationship; also filters molecule.label = 'TR206' instead of atom.molecule_id = 'TR206'.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.element = 'h' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id),4) FROM atom AS T WHERE T.molecule_id = 'TR206'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN molecule AS T3 ON T2.atom_id2 = T3.molecule_id WHERE T3.label = 'TR206'
```

### Q230 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** Selects T3.label where T3 is the bond alias (bond has no label column, only bond_type); label only exists on molecule (T4), which is already joined -- an alias mix-up, compounded by filtering label = 'TR060' (a molecule-id-shaped value) instead of molecule_id = 'TR060'.

**Gold SQL:**

```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Predicted SQL:**

```sql
SELECT T1.element, T3.label
FROM atom AS T1
JOIN connected AS T2 ON T1.atom_id = T2.atom_id
JOIN bond AS T3 ON T2.bond_id = T3.bond_id
JOIN molecule AS T4 ON T3.molecule_id = T4.molecule_id
WHERE T4.label = 'TR060';
```

### Q231 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through connected unnecessarily to reach molecule_id, but connected has no such column; gold filters bond.molecule_id = 'TR010' directly with no join needed at all.

**Gold SQL:**

```sql
SELECT T.bond_type FROM ( SELECT T1.bond_type, COUNT(T1.molecule_id) FROM bond AS T1  WHERE T1.molecule_id = 'TR010' GROUP BY T1.bond_type ORDER BY COUNT(T1.molecule_id) DESC LIMIT 1 ) AS T
```

**Predicted SQL:**

```sql
SELECT T3.bond_type FROM molecule AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T1.label = 'TR010' GROUP BY T3.bond_type ORDER BY COUNT(*) DESC LIMIT 1;
```

### Q232 (moderate, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through connected (no molecule_id column) instead of joining bond directly to molecule, and also selects label instead of gold's molecule_id, plus adds a fabricated HAVING COUNT(DISTINCT atom_id) = 2 condition not present in gold.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T2.label = '-' ORDER BY T2.molecule_id LIMIT 3
```

**Predicted SQL:**

```sql
SELECT m.label
FROM molecule m
JOIN connected c ON m.molecule_id = c.molecule_id
JOIN bond b ON c.bond_id = b.bond_id
WHERE b.bond_type = 'single'
GROUP BY m.molecule_id
HAVING COUNT(DISTINCT c.atom_id) = 2
ORDER BY m.label ASC
LIMIT 3;
```

### Q234 (moderate, aggregate) -- **Invalid SQL** (Other execution error)

**Outcome:** `error` -- **Reason:** Ambiguous column name: bond_id, after adding an unnecessary join to bond that duplicates the column also present on connected; also compares atom_id to the bare integer 12 instead of the string 'TR009_12', filters via molecule.label = 'TR009' (label can't hold that value), and drops the symmetric atom_id2 check.

**Gold SQL:**

```sql
SELECT COUNT(DISTINCT bond_id) FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'
```

**Predicted SQL:**

```sql
SELECT COUNT(bond_id) 
FROM connected 
JOIN bond ON connected.bond_id = bond.bond_id 
WHERE connected.atom_id = 12 AND molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR009');
```

### Q236 (moderate, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `error` -- **Reason:** References T1.element where T1 is the connected alias (connected has no element column, only atom does); also filters molecule.label against 'TR001_6_9', a bond_id-shaped value that label (holding only '+'/'-') could never match.

**Gold SQL:**

```sql
SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'
```

**Predicted SQL:**

```sql
SELECT T3.bond_type, T1.element, T2.element
FROM connected AS T1
JOIN atom AS T2 ON T1.atom_id2 = T2.atom_id
JOIN bond AS T3 ON T1.bond_id = T3.bond_id
WHERE T3.molecule_id = (SELECT molecule_id FROM molecule WHERE label = 'TR001_6_9')
```

### Q239 (simple, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the SUBSTR(atom_id, -2) = '19' suffix-match transformation, comparing the full formatted atom_id string directly to the bare integer 19 instead.

**Gold SQL:**

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE SUBSTR(T.atom_id, -2) = '19'
```

**Predicted SQL:**

```sql
SELECT COUNT(*) FROM connected WHERE atom_id = 19;
```

### Q240 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters molecule.label = 'TR004' instead of atom.molecule_id = 'TR004' -- label can only hold '+' or '-'.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.molecule_id = 'TR004'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element 
FROM atom AS T1 
JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE T2.label = 'TR004';
```

### Q242 (moderate, retrieval) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Drops the SUBSTR(atom_id, -2) BETWEEN '21' AND '25' suffix-range transformation, comparing the full atom_id string to bare integers instead, and replaces the label = '+' condition with an invented bond_type = 'carcinogenic' value that isn't part of that column's domain at all; also selects label instead of gold's molecule_id.

**Gold SQL:**

```sql
SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T3.label FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T4 ON T2.bond_id = T4.bond_id INNER JOIN molecule AS T3 ON T4.molecule_id = T3.molecule_id WHERE T1.atom_id BETWEEN 21 AND 25 AND T4.bond_type = 'carcinogenic'
```

### Q243 (moderate, retrieval) -- **Schema linking** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Joins bond to atom via a shared molecule_id instead of gold's actual bond-to-atom link through the connected junction table, so it matches any P/N atom anywhere in the molecule rather than specifically the two atoms a given bond connects.

**Gold SQL:**

```sql
SELECT T2.bond_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T2.bond_id IN ( SELECT T3.bond_id FROM connected AS T3 INNER JOIN atom AS T4 ON T3.atom_id = T4.atom_id WHERE T4.element = 'p' ) AND T1.element = 'n'
```

**Predicted SQL:**

```sql
SELECT DISTINCT b.bond_id
FROM bond b
JOIN atom a ON b.molecule_id = a.molecule_id
WHERE a.element IN ('P', 'N');
```

### Q244 (moderate, aggregate) -- **Nesting problem** (HAVING clause mismatch)

**Outcome:** `wrong_answer` -- **Reason:** Collapses gold's CTE + WHERE cnt = (SELECT MAX(cnt)...) tie-preserving pattern into a plain GROUP BY ... ORDER BY COUNT DESC LIMIT 1, which would miss any molecules tied for the maximum; also uses bond_type = 'double' instead of '='.

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

### Q245 (moderate, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted GROUP BY atom.molecule_id, turning gold's single overall bond-to-atom ratio into an average of per-molecule ratios; also uses the invented value 'Iodine' instead of the real element code 'i'.

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
    JOIN bond ON connected.bond_id = bond.bond_id 
    WHERE atom.element = 'Iodine' 
    GROUP BY atom.molecule_id
);
```

### Q247 (challenging, retrieval) -- **Other**

**Outcome:** `wrong_answer` -- **Reason:** Missing DISTINCT on the returned element column.

**Gold SQL:**

```sql
SELECT DISTINCT T.element FROM atom AS T WHERE T.atom_id NOT IN (SELECT DISTINCT atom_id FROM connected)
```

**Predicted SQL:**

```sql
SELECT element FROM atom WHERE atom_id NOT IN (SELECT atom_id FROM connected)
```

### Q248 (simple, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Drops the bond table entirely (joins molecule+connected+atom), so bond_type is unreachable, and filters molecule.label = 'TR041' instead of molecule_id = 'TR041' -- label can't hold that value.

**Gold SQL:**

```sql
SELECT DISTINCT T2.atom_id FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '#' AND T3.molecule_id = 'TR041'
```

**Predicted SQL:**

```sql
SELECT T3.atom_id FROM molecule AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.label = 'TR041' AND T2.bond_type = 'triple';
```

### Q249 (challenging, retrieval) -- **Schema linking** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Filters molecule.label against 'TR144_8_19', a bond_id-shaped value that label (only '+'/'-') could never match, reached via a nonsensical join comparing atom_id2 to molecule_id; gold simply filters connected.bond_id directly.

**Gold SQL:**

```sql
SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR144_8_19'
```

**Predicted SQL:**

```sql
SELECT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN molecule AS T3 ON T2.atom_id2 = T3.molecule_id WHERE T3.label = 'TR144_8_19'
```

### Q253 (challenging, retrieval) -- **JOIN errors** (Wrong table)

**Outcome:** `wrong_answer` -- **Reason:** Adds a spurious extra self-join on connected (connected-of-connected), traversing two bond-hops instead of gold's single connected+bond join, which changes which atoms are matched; also uses bond_type = 'triple' instead of '#'.

**Gold SQL:**

```sql
SELECT DISTINCT T3.element FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id INNER JOIN atom AS T3 ON T2.atom_id = T3.atom_id WHERE T1.bond_type = '#'
```

**Predicted SQL:**

```sql
SELECT DISTINCT T1.element 
FROM atom AS T1 
JOIN connected AS T2 ON T1.atom_id = T2.atom_id 
JOIN connected AS T3 ON T2.atom_id2 = T3.atom_id 
JOIN bond AS T4 ON T3.bond_id = T4.bond_id 
WHERE T4.bond_type = 'triple';
```

### Q255 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through connected unnecessarily to reach molecule_id, but connected has no such column; gold joins bond directly to molecule. Also filters bond_type = 'carcinogenic', a value from label's domain, not a real bond_type value.

**Gold SQL:**

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T3.bond_type = 'single' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T3.bond_id) FROM molecule AS T1 INNER JOIN connected AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = 'carcinogenic'
```

### Q260 (moderate, aggregate) -- **Predicate error** (Predicate semantic error)

**Outcome:** `wrong_answer` -- **Reason:** Collapses gold's two independent molecule-membership subqueries (has a triple bond; contains a P or Br atom) into a single joined WHERE clause, which restricts the final count to only phosphorus/bromine atoms instead of counting all atoms in qualifying molecules; also uses spelled-out names 'phosphorus'/'bromine' instead of the real codes 'p'/'br'.

**Gold SQL:**

```sql
SELECT COUNT(*) FROM atom WHERE molecule_id IN ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '#' ) AND molecule_id IN ( SELECT DISTINCT molecule_id FROM atom WHERE element IN ('p', 'br') )
```

**Predicted SQL:**

```sql
SELECT COUNT(DISTINCT T1.atom_id) 
FROM atom AS T1 
JOIN connected AS T2 ON T1.atom_id = T2.atom_id 
JOIN bond AS T3 ON T2.bond_id = T3.bond_id 
JOIN molecule AS T4 ON T3.molecule_id = T4.molecule_id 
WHERE T1.element IN ('phosphorus', 'bromine') AND T3.bond_type = 'triple';
```

### Q263 (challenging, aggregate) -- **GROUP BY errors** (Wrong column)

**Outcome:** `wrong_answer` -- **Reason:** Adds an unwarranted GROUP BY atom.molecule_id that gold doesn't have, turning a single overall chlorine percentage into a per-molecule breakdown; also uses element = 'Cl' instead of 'cl' and bond_type = 'single' instead of '-'.

**Gold SQL:**

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(T.atom_id) FROM atom AS T WHERE molecule_id IN (SELECT DISTINCT molecule.molecule_id FROM molecule JOIN bond ON molecule.molecule_id = bond.molecule_id AND bond.bond_type = '-')
```

**Predicted SQL:**

```sql
SELECT 
    SUM(CASE WHEN T1.element = 'Cl' THEN 1 ELSE 0 END) * 100 / COUNT(T1.atom_id) AS chlorine_percentage
FROM 
    atom AS T1
JOIN 
    connected AS T2 ON T1.atom_id = T2.atom_id
JOIN 
    bond AS T3 ON T2.bond_id = T3.bond_id
WHERE 
    T3.bond_type = 'single'
GROUP BY 
    T1.molecule_id;
```

### Q273 (moderate, aggregate) -- **Predicate error** (Filter value error)

**Outcome:** `wrong_answer` -- **Reason:** Uses element = 'Cl' instead of 'cl', and label = 'carcinogenic' instead of the real code '+'.

**Gold SQL:**

```sql
SELECT CAST(COUNT( CASE WHEN T1.element = 'cl' THEN T1.element ELSE NULL END) AS REAL) * 100 / COUNT(T1.element) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'
```

**Predicted SQL:**

```sql
SELECT CAST(SUM(CASE WHEN T1.element = 'Cl' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = 'carcinogenic'
```

### Q281 (challenging, retrieval) -- **Invalid SQL** (Wrong column)

**Outcome:** `error` -- **Reason:** References a 'carcinogenic' column on molecule that doesn't exist anywhere in the schema (molecule only has molecule_id and label); also drops the SUBSTR(atom_id, -2) = '_4' suffix-match transformation for a bare atom_id = 4 comparison.

**Gold SQL:**

```sql
SELECT element, COUNT(*) FROM atom JOIN molecule ON atom.molecule_id = molecule.molecule_id WHERE molecule.label = '+' AND substr(atom_id, -2) = '_4' GROUP BY element;
```

**Predicted SQL:**

```sql
SELECT 
    m.label,
    COUNT(a.element) AS toxicology_count
FROM 
    molecule m
JOIN 
    connected c ON m.molecule_id = c.molecule_id
JOIN 
    atom a ON c.atom_id = a.atom_id
WHERE 
    a.atom_id = 4 AND m.label IN (SELECT label FROM molecule WHERE carcinogenic = 1)
GROUP BY 
    m.label;
```

### Q282 (challenging, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Routes through connected unnecessarily to reach molecule_id, but connected has no such column; gold's CTE joins atom directly to molecule with no connected join needed at all.

**Gold SQL:**

```sql
WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label
```

**Predicted SQL:**

```sql
SELECT 
    T3.label AS molecule_label,
    CAST(SUM(CASE WHEN T1.element = 'H' THEN 1 ELSE 0 END) AS REAL) / COUNT(T1.atom_id) AS hydrogen_ratio
FROM 
    atom AS T1
JOIN 
    connected AS T2 ON T1.atom_id = T2.atom_id
JOIN 
    molecule AS T3 ON T2.molecule_id = T3.molecule_id
WHERE 
    T3.label = 'TR006'
GROUP BY 
    T3.label;
```

### Q327 (moderate, aggregate) -- **JOIN errors** (Wrong table)

**Outcome:** `error` -- **Reason:** Uses connected instead of atom to count atoms-per-molecule (connected represents bond-pairs, not molecule membership) and connected has no molecule_id column at all; also adds an entirely invented NOT EXISTS condition checking for the absence of a carbon atom, not present in gold, and selects label instead of gold's molecule_id.

**Gold SQL:**

```sql
SELECT T.molecule_id FROM ( SELECT T1.molecule_id, COUNT(T2.atom_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '-' GROUP BY T1.molecule_id HAVING COUNT(T2.atom_id) > 5 ) t
```

**Predicted SQL:**

```sql
SELECT m.label
FROM molecule m
JOIN connected c ON m.molecule_id = c.molecule_id
GROUP BY m.molecule_id
HAVING COUNT(DISTINCT c.atom_id) > 5 AND NOT EXISTS (
    SELECT 1
    FROM atom a
    JOIN connected co ON a.atom_id = co.atom_id
    WHERE a.element = 'C' AND co.molecule_id = m.molecule_id
);
```

---

